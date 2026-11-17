"""Les migrations qui vident le tiroir public (comparateur.db) de ce qu'il ne doit plus porter. C'est le seul module
qui ouvre à la fois ce fichier et un autre tiroir, et seulement en ligne de commande, une fois. Aucun ATTACH : deux
connexions, des lignes lues d'un côté et écrites de l'autre.

Phase 2, la table abonnes vers le tiroir identité (identites.db) :

  python -m comparateur verser-abonnes    copie ; se relance sans doublon ; ne touche pas à abonnes
  python -m comparateur oublier-abonnes   vide abonnes, seulement si chaque ligne est retrouvée dans identites.db

Un abonné confirmé devient un compte et un abonnement « lettre » actif ; un abonné en attente, un abonnement en
attente. Le jeton d'abonnes devient le jeton de sortie : les liens de désinscription déjà envoyés marchent encore,
et la confirmation d'une inscription en cours aussi. La semaine du dernier envoi est gardée : personne ne reçoit
deux fois la même lettre. Les dates sont arrondies au jour, comme partout dans le tiroir identité.

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
import json, os
from collections import Counter

from . import base, comptes, config, urne


def _lignes(public):
    if not public.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'abonnes'").fetchone():
        return []
    return public.execute("SELECT adresse, jeton, cree, confirme_le, dernier_envoi FROM abonnes ORDER BY id").fetchall()


def verser_abonnes(public=None, ident=None):
    """Rend {lues, comptes, abonnements, deja, invalides}. Se relance sans rien doubler."""
    propres = public is None, ident is None
    public = public or base.connexion()
    ident = ident or comptes.connexion()
    try:
        bilan = {"lues": 0, "comptes": 0, "abonnements": 0, "deja": 0, "invalides": 0}
        for r in _lignes(public):
            bilan["lues"] += 1
            adresse = comptes.normaliser(r["adresse"])
            if not adresse:
                bilan["invalides"] += 1
                continue
            existe = ident.execute("SELECT id FROM comptes WHERE adresse = ?", (adresse,)).fetchone()
            if existe:
                compte = existe["id"]
            else:
                compte = ident.execute("INSERT INTO comptes (adresse, cree_jour) VALUES (?, ?)",
                                       (adresse, (r["cree"] or comptes.jour())[:10])).lastrowid
                bilan["comptes"] += 1
            if ident.execute("SELECT 1 FROM abonnements WHERE compte = ? AND type = 'lettre' AND cible = ''", (compte,)).fetchone():
                bilan["deja"] += 1
                continue
            ident.execute("""INSERT INTO abonnements (compte, type, cible, etat, cree_jour, dernier_envoi, sortie)
                             VALUES (?, 'lettre', '', ?, ?, ?, ?)""",
                          (compte, "actif" if r["confirme_le"] else "attente", (r["cree"] or comptes.jour())[:10],
                           r["dernier_envoi"], r["jeton"]))
            bilan["abonnements"] += 1
        ident.commit()
        return bilan
    finally:
        if propres[0]:
            public.close()
        if propres[1]:
            ident.close()


def oublier_abonnes(public=None, ident=None):
    """Vide abonnes si chaque ligne a son abonnement dans identites.db (même adresse, même jeton, même état).
    Sinon ne touche à rien. Rend {retrouvees, manquantes, effacees}."""
    propres = public is None, ident is None
    public = public or base.connexion()
    ident = ident or comptes.connexion()
    try:
        manquantes, lignes = 0, _lignes(public)
        for r in lignes:
            ok = ident.execute("""SELECT 1 FROM abonnements a JOIN comptes c ON c.id = a.compte
                                  WHERE c.adresse = ? AND a.type = 'lettre' AND a.sortie = ? AND a.etat = ?""",
                               (comptes.normaliser(r["adresse"]), r["jeton"], "actif" if r["confirme_le"] else "attente")).fetchone()
            manquantes += 0 if ok else 1
        if manquantes:
            return {"retrouvees": len(lignes) - manquantes, "manquantes": manquantes, "effacees": 0}
        n = public.execute("DELETE FROM abonnes").rowcount if lignes else 0
        public.commit()
        public.execute("VACUUM")   # les pages libérées ne gardent pas les adresses effacées
        return {"retrouvees": len(lignes), "manquantes": 0, "effacees": n}
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


def verser_votes(public=None):
    """Copie les avis du vieux vote dans l'urne historique, puis en publie les sommes (historique.json). Rend
    {lues, versees, deja, accords, publie}. Se relance sans rien doubler. Ne touche pas à comparateur.db."""
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
            u.executemany("INSERT OR REPLACE INTO meta (cle, valeur) VALUES (?, ?)",
                          [("etat", "clos"), ("origine", "avis d'avant la carte de votant (comparateur.db)")])
            u.commit()
        finally:
            u.close()
        bilan = {"lues": len(lignes), "versees": versees, "deja": len(lignes) - versees,
                 "accords": sum(a["votes"] for a in accords.values()), "publie": False}
        # Une base déjà oubliée n'a plus rien à dire : le fichier publié n'est pas réécrit, ses accords restent.
        if lignes or accords:
            votants = public.execute("SELECT COUNT(*) FROM votants").fetchone()[0] if _existe(public, "votants") else 0
            agg = {"v": 1, "mesure": "aveugle", "trimestre": "historique", "etiquette": urne.ETIQUETTE,
                   "lots": urne.agregats_aveugle(urne.HISTORIQUE), "cartes_delivrees": votants, "accords": accords}
            c = chemin_historique()
            os.makedirs(os.path.dirname(c), exist_ok=True)
            with open(c + ".tmp", "w", encoding="utf-8") as f:
                f.write(json.dumps(agg, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            os.replace(c + ".tmp", c)
            bilan["publie"] = True
        return bilan
    finally:
        if propre:
            public.close()


def oublier_votes(public=None):
    """Vide votants, avis_aveugle, avis_note et invitations, seulement si chaque avis est retrouvé dans l'urne
    historique (même note, même bord, et les mêmes comptes par lot et par bord) et si les accords publiés sont ceux de
    avis_note. Sinon ne touche à rien. Puis compacte la base, journal compris : les pages libérées ne gardent rien.
    Rend {retrouves, manquants, effaces: {table: lignes}}."""
    propre = public is None
    public = public or base.connexion()
    try:
        lignes, accords = _avis(public), _accords(public)
        try:
            u = urne.ouvrir_aveugle(urne.HISTORIQUE)
        except urne.Refus:   # jamais versé
            u = None
        trouves, comptes_urne = 0, Counter()
        if u is not None:
            try:
                for r in lignes:
                    x = u.execute("SELECT note, bord FROM avis WHERE carte = ? AND lot = ?", (pseudonyme(r["votant"]), r["lot"])).fetchone()
                    trouves += 1 if x and (x["note"], x["bord"]) == (r["note"], r["bord"]) else 0
                comptes_urne = Counter({(r["lot"], r["bord"]): r["n"] for r in u.execute(
                    "SELECT lot, bord, COUNT(*) AS n FROM avis GROUP BY lot, bord")})
            finally:
                u.close()
        attendus = Counter((r["lot"], r["bord"]) for r in lignes)
        manquants = len(lignes) - trouves + sum(1 for k, n in attendus.items() if comptes_urne[k] != n)
        if accords:
            try:
                with open(chemin_historique(), encoding="utf-8") as f:
                    publies = json.load(f).get("accords")
            except (OSError, ValueError, AttributeError):
                publies = None
            manquants += 0 if publies == accords else sum(a["votes"] for a in accords.values())
        if manquants:
            return {"retrouves": trouves, "manquants": manquants, "effaces": {}}
        effaces = {t: public.execute(f"DELETE FROM {t}").rowcount for t in TABLES_DU_VOTE if _existe(public, t)}
        public.commit()
        public.execute("VACUUM")                            # les pages libérées ne gardent pas les pseudonymes effacés
        public.execute("PRAGMA wal_checkpoint(TRUNCATE)")   # ni le journal (la base est en WAL)
        return {"retrouves": trouves, "manquants": 0, "effaces": effaces}
    finally:
        if propre:
            public.close()
