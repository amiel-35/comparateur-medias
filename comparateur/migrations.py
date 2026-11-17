"""La migration de la phase 2 : la table abonnes (dans comparateur.db, le tiroir public) passe dans le tiroir
identité (identites.db). C'est le seul module qui ouvre les deux fichiers. Aucun ATTACH : deux connexions, des lignes
lues d'un côté et écrites de l'autre.

  python -m comparateur verser-abonnes    déplace chaque abonné ; le guichet la lance seul à son démarrage

C'est un déplacement, ligne par ligne : un abonné est écrit dans identites.db (et validé), puis retiré d'abonnes.
Un arrêt entre les deux se rattrape au passage suivant, sans doublon. Personne n'est donc versé deux fois : un abonné
qui se désinscrit après le passage ne revient pas au démarrage suivant.

Un abonné confirmé devient un compte et un abonnement « lettre » actif ; un abonné en attente, un abonnement en
attente. Le jeton d'abonnes devient le jeton de sortie : les liens de désinscription déjà envoyés marchent encore,
et la confirmation d'une inscription en cours aussi. La semaine du dernier envoi est gardée : personne ne reçoit
deux fois la même lettre. Une adresse invalide (qui ne recevait déjà rien) est retirée sans être versée. Les dates
sont arrondies au jour, comme partout dans le tiroir identité.

À essayer d'abord sur une copie de la vraie base.
"""
from . import base, comptes


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
