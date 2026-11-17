"""Les migrations qui vident le tiroir public (comparateur.db) de ce qu'il ne doit plus porter. C'est le seul module
qui ouvre à la fois ce fichier et un autre tiroir. Aucun ATTACH : deux connexions, des lignes lues d'un côté et
écrites de l'autre.

Phase 2, la table abonnes vers le tiroir identité (identites.db) :

  python -m comparateur verser-abonnes    déplace chaque abonné ; le guichet la lance seul à son démarrage

C'est un déplacement, ligne par ligne : un abonné est écrit dans identites.db (et validé), puis retiré d'abonnes.
Un arrêt entre les deux se rattrape au passage suivant, sans doublon. Personne n'est donc versé deux fois : un abonné
qui se désinscrit après le passage ne revient pas au démarrage suivant.

Un abonné confirmé devient un compte et un abonnement « lettre » actif ; un abonné en attente, un abonnement en
attente. Le jeton d'abonnes devient le jeton de sortie : les liens de désinscription déjà envoyés marchent encore,
et la confirmation d'une inscription en cours aussi. La semaine du dernier envoi est gardée : personne ne reçoit
deux fois la même lettre. Une adresse invalide (qui ne recevait déjà rien) est retirée sans être versée. Les dates
sont arrondies au jour, comme partout dans le tiroir identité.

Phase 3, le vieux vote à l'aveugle (votants, avis_aveugle, avis_note, invitations) vers une urne :

  python -m comparateur verser-votes      copie les avis dans urnes/aveugle-historique.db et publie leurs sommes ;
                                          se relance sans doublon ; ne touche pas à comparateur.db
  python -m comparateur oublier-votes     vide les quatre tables, seulement si chaque avis est retrouvé dans l'urne

Un avis devient une ligne de l'urne, au même format que celles de la carte de votant : sous une empreinte du
pseudonyme du votant (jamais l'identifiant lui-même), avec le lot, la note et le bord déclaré ; sans date. Les
sommes par lot et par bord sont publiées dans public/panel/aveugle/historique.json, comme un trimestre clos. Les
accords sur la note affichée (avis_note) n'y sont publiés qu'en comptes par média, sans ligne. lots_aveugle reste
dans comparateur.db : ce sont des titres publics.

À essayer d'abord sur une copie de la vraie base, jamais directement sur elle.
"""
import json, os, secrets
from collections import Counter

from . import base, comptes, config, urne


def _lignes(public):
    if not public.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'abonnes'").fetchone():
        return []
    return public.execute("SELECT id, adresse, jeton, cree, confirme_le, dernier_envoi FROM abonnes ORDER BY id").fetchall()


def verser_abonnes(public=None, ident=None):
    """Rend {lues, comptes, abonnements, deja, invalides, retirees}."""
    propres = public is None, ident is None
    public = public or base.connexion()
    ident = ident or comptes.connexion()
    try:
        bilan = {"lues": 0, "comptes": 0, "abonnements": 0, "deja": 0, "invalides": 0, "retirees": 0}
        for r in _lignes(public):
            bilan["lues"] += 1
            adresse = comptes.normaliser(r["adresse"])
            if adresse:
                existe = ident.execute("SELECT id FROM comptes WHERE adresse = ?", (adresse,)).fetchone()
                if existe:
                    compte = existe["id"]
                else:
                    compte = ident.execute("INSERT INTO comptes (adresse, cree_jour) VALUES (?, ?)",
                                           (adresse, (r["cree"] or comptes.jour())[:10])).lastrowid
                    bilan["comptes"] += 1
                deja = ident.execute("SELECT id, etat FROM abonnements WHERE compte = ? AND type = 'lettre' AND cible = ''",
                                     (compte,)).fetchone()
                if deja:
                    # Une inscription refaite depuis le site, encore en attente, alors que l'abonné était confirmé : il
                    # reste confirmé, et l'ancien lien de désinscription, celui de ses mails, garde son effet.
                    if deja["etat"] == "attente" and r["confirme_le"]:
                        ident.execute("UPDATE abonnements SET etat = 'actif', sortie = ?, dernier_envoi = ? WHERE id = ?",
                                      (r["jeton"], r["dernier_envoi"], deja["id"]))
                    bilan["deja"] += 1
                else:
                    ident.execute("""INSERT INTO abonnements (compte, type, cible, etat, cree_jour, dernier_envoi, sortie)
                                     VALUES (?, 'lettre', '', ?, ?, ?, ?)""",
                                  (compte, "actif" if r["confirme_le"] else "attente", (r["cree"] or comptes.jour())[:10],
                                   r["dernier_envoi"], r["jeton"]))
                    bilan["abonnements"] += 1
                ident.commit()   # écrit d'abord dans le tiroir identité...
            else:
                bilan["invalides"] += 1
            public.execute("DELETE FROM abonnes WHERE id = ?", (r["id"],))   # ... puis retiré du tiroir public
            public.commit()
            bilan["retirees"] += 1
        if bilan["retirees"]:
            public.execute("VACUUM")   # les pages libérées ne gardent pas les adresses
        return bilan
    finally:
        if propres[0]:
            public.close()
        if propres[1]:
            ident.close()



# ---- phase 3 : le vieux vote à l'aveugle

# Les tables du vote d'avant la carte de votant, telles qu'elles sont encore dans une base d'avant la phase 3. Elles
# ne sont plus créées : ce texte sert aux essais, et dit ce que la migration lit.
ANCIEN_VOTE = """
CREATE TABLE IF NOT EXISTS invitations (code TEXT PRIMARY KEY, cree TEXT NOT NULL, utilisee_le TEXT);
CREATE TABLE IF NOT EXISTS votants (id TEXT PRIMARY KEY, bord INTEGER NOT NULL, cree TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS avis_aveugle (
  votant_id TEXT NOT NULL REFERENCES votants(id), lot_id INTEGER NOT NULL REFERENCES lots_aveugle(id),
  note INTEGER NOT NULL, cree TEXT NOT NULL, PRIMARY KEY (votant_id, lot_id));
CREATE TABLE IF NOT EXISTS avis_note (
  votant_id TEXT NOT NULL REFERENCES votants(id), media_id INTEGER NOT NULL REFERENCES medias(id),
  accord INTEGER NOT NULL, cree TEXT NOT NULL, PRIMARY KEY (votant_id, media_id));
"""
TABLES_DU_VOTE = ("avis_note", "avis_aveugle", "votants", "invitations")   # dans l'ordre où elles se vident


def _existe(db, table):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None


def _avis(public):
    """Les avis du vieux vote, chacun avec le bord déclaré de son votant : (votant, bord, lot, note)."""
    if not all(_existe(public, t) for t in ("avis_aveugle", "votants")):
        return []
    return public.execute("""SELECT a.votant_id AS votant, v.bord, a.lot_id AS lot, a.note
                             FROM avis_aveugle a JOIN votants v ON v.id = a.votant_id
                             JOIN lots_aveugle l ON l.id = a.lot_id ORDER BY a.lot_id, a.votant_id""").fetchall()


def _accords(public):
    """Les accords sur la note affichée, comptés par média : {nom: {oui, votes}}. Aucune ligne ne sort."""
    if not _existe(public, "avis_note"):
        return {}
    return {r["nom"]: {"oui": r["oui"] or 0, "votes": r["n"]} for r in public.execute(
        """SELECT m.nom, SUM(a.accord) AS oui, COUNT(*) AS n FROM avis_note a JOIN medias m ON m.id = a.media_id
           GROUP BY m.nom ORDER BY m.nom""")}


def pseudonyme(votant):
    """Ce qui tient lieu de carte dans l'urne historique : une empreinte du pseudonyme du votant (lui-même l'empreinte
    de son jeton), propre à cette urne. Jamais l'identifiant lui-même : aucune valeur de votants ne passe dans l'urne."""
    return urne.empreinte((urne.HISTORIQUE + "\x00" + votant).encode())


def chemin_historique():
    return os.path.join(config.public(), "panel", "aveugle", "historique.json")


def _publier_historique(u):
    """Écrit historique.json depuis l'urne seule : les sommes par lot et par bord, et les deux chiffres gardés dans sa
    meta (votants d'alors, accords par média). Rend le contenu publié."""
    meta = urne._meta(u)
    agg = {"v": 1, "mesure": "aveugle", "trimestre": "historique", "etiquette": urne.ETIQUETTE,
           "lots": urne.agregats_aveugle(urne.HISTORIQUE), "cartes_delivrees": int(meta.get("votants", "0")),
           "accords": json.loads(meta.get("accords", "{}"))}
    c = chemin_historique()
    os.makedirs(os.path.dirname(c), exist_ok=True)
    with open(c + ".tmp", "w", encoding="utf-8") as f:
        f.write(json.dumps(agg, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    os.replace(c + ".tmp", c)
    return agg


def verser_votes(public=None):
    """Copie les avis du vieux vote dans l'urne historique, garde dans sa meta le nombre de votants et les accords
    comptés par média, puis publie (historique.json, réécrit depuis l'urne seule : il se refait même après l'oubli).
    Rend {lues, versees, deja, accords, publie}. Se relance sans rien doubler. Ne touche pas à comparateur.db."""
    propre = public is None
    public = public or base.connexion()
    try:
        lignes, accords = _avis(public), _accords(public)
        u = urne.ouvrir_aveugle(urne.HISTORIQUE, creer=True)
        try:
            versees = 0
            for r in lignes:
                versees += u.execute("INSERT OR IGNORE INTO avis (carte, lot, note, bord) VALUES (?, ?, ?, ?)",
                                     (pseudonyme(r["votant"]), r["lot"], r["note"], r["bord"])).rowcount
            # close : aucune route ne mène à cette urne (urne.donner_avis n'ouvre que celle d'un trimestre)
            meta = [("etat", "clos"), ("origine", "avis d'avant la carte de votant (comparateur.db)")]
            if lignes or accords:   # une base déjà oubliée n'a plus rien à dire : la meta garde ce qu'elle savait
                votants = public.execute("SELECT COUNT(*) FROM votants").fetchone()[0] if _existe(public, "votants") else 0
                meta += [("votants", str(votants)), ("accords", json.dumps(accords, ensure_ascii=False, sort_keys=True))]
            u.executemany("INSERT OR REPLACE INTO meta (cle, valeur) VALUES (?, ?)", meta)
            u.commit()
            publie = "votants" in urne._meta(u)
            if publie:
                _publier_historique(u)
        finally:
            u.close()
        return {"lues": len(lignes), "versees": versees, "deja": len(lignes) - versees,
                "accords": sum(a["votes"] for a in accords.values()), "publie": publie}
    finally:
        if propre:
            public.close()


def oublier_votes(public=None):
    """Vide votants, avis_aveugle, avis_note et invitations, seulement si tout est retrouvé : chaque avis dans l'urne
    historique (même note, même bord, mêmes comptes par lot et par bord, aucun avis hors du compte), le nombre de
    votants et les accords dans sa meta, et historique.json publié avec ces mêmes chiffres. Sinon ne touche à rien.

    Puis compacte la base et vide son journal (la fabrique arrêtée : un lecteur le retient), et remplace dans l'urne
    chaque empreinte d'ancien votant par un tirage au hasard : une copie d'avant de comparateur.db ne permet plus de
    retrouver les avis d'un votant. Rend {retrouves, manquants, effaces: {table: lignes}, journal_vide}."""
    propre = public is None
    public = public or base.connexion()
    try:
        lignes, accords = _avis(public), _accords(public)
        total = public.execute("SELECT COUNT(*) FROM avis_aveugle").fetchone()[0] if _existe(public, "avis_aveugle") else 0
        votants = public.execute("SELECT COUNT(*) FROM votants").fetchone()[0] if _existe(public, "votants") else 0
        try:
            u = urne.ouvrir_aveugle(urne.HISTORIQUE)
        except urne.Refus:   # jamais versé
            u = None
        trouves, comptes_urne, meta, lots_urne = 0, Counter(), {}, None
        if u is not None:
            try:
                for r in lignes:
                    x = u.execute("SELECT note, bord FROM avis WHERE carte = ? AND lot = ?", (pseudonyme(r["votant"]), r["lot"])).fetchone()
                    trouves += 1 if x and (x["note"], x["bord"]) == (r["note"], r["bord"]) else 0
                comptes_urne = Counter({(r["lot"], r["bord"]): r["n"] for r in u.execute(
                    "SELECT lot, bord, COUNT(*) AS n FROM avis GROUP BY lot, bord")})
                meta = urne._meta(u)
            finally:
                u.close()
            lots_urne = urne.agregats_aveugle(urne.HISTORIQUE)
        attendus = Counter((r["lot"], r["bord"]) for r in lignes)
        manquants = len(lignes) - trouves + sum(1 for k, n in attendus.items() if comptes_urne[k] != n)
        manquants += total - len(lignes)                    # un avis que la lecture n'a pas vu (lot disparu)
        if lignes or accords or votants:                    # ce que seule la meta garde, une fois la base vidée
            manquants += 0 if meta.get("votants") == str(votants) else 1
            manquants += 0 if json.loads(meta.get("accords", "null")) == accords else 1
        try:
            with open(chemin_historique(), encoding="utf-8") as f:
                publie = json.load(f)
        except (OSError, ValueError):
            publie = None
        if lignes or u is not None:                         # ce qui est publié est ce que l'urne dit
            ok = isinstance(publie, dict) and publie.get("lots") == lots_urne \
                and publie.get("cartes_delivrees") == int(meta.get("votants", "-1")) \
                and publie.get("accords") == json.loads(meta.get("accords", "null"))
            manquants += 0 if ok else 1
        if manquants:
            return {"retrouves": trouves, "manquants": manquants, "effaces": {}, "journal_vide": None}
        effaces = {t: public.execute(f"DELETE FROM {t}").rowcount for t in TABLES_DU_VOTE if _existe(public, t)}
        public.commit()
        public.execute("VACUUM")                            # les pages libérées ne gardent pas les pseudonymes effacés
        vide = comptes.vider_journal(public)                # ni le journal (la base est en WAL)
        if u is not None:
            _brouiller_historique()
        return {"retrouves": trouves, "manquants": 0, "effaces": effaces, "journal_vide": vide}
    finally:
        if propre:
            public.close()


def _brouiller_historique():
    """Chaque empreinte d'ancien votant devient un tirage au hasard (une par votant : ses avis restent liés entre eux,
    comme sous une carte). Plus rien ne se recalcule depuis une copie de l'ancienne base."""
    u = urne.ouvrir_aveugle(urne.HISTORIQUE)
    try:
        for (carte,) in u.execute("SELECT DISTINCT carte FROM avis").fetchall():
            u.execute("UPDATE avis SET carte = ? WHERE carte = ?", (secrets.token_hex(32), carte))
        u.commit()
        u.execute("VACUUM")
    finally:
        u.close()
