"""La migration de la phase 2 : la table abonnes (dans comparateur.db, le tiroir public) est versée dans le tiroir
identité (identites.db). C'est le seul module qui ouvre les deux fichiers, et seulement en ligne de commande, une
fois. Aucun ATTACH : deux connexions, des lignes lues d'un côté et écrites de l'autre.

  python -m comparateur verser-abonnes    copie ; se relance sans doublon ; ne touche pas à abonnes
  python -m comparateur oublier-abonnes   vide abonnes, seulement si chaque ligne est retrouvée dans identites.db

Un abonné confirmé devient un compte et un abonnement « lettre » actif ; un abonné en attente, un abonnement en
attente. Le jeton d'abonnes devient le jeton de sortie : les liens de désinscription déjà envoyés marchent encore,
et la confirmation d'une inscription en cours aussi. La semaine du dernier envoi est gardée : personne ne reçoit
deux fois la même lettre. Les dates sont arrondies au jour, comme partout dans le tiroir identité.

À essayer d'abord sur une copie de la vraie base, jamais directement sur elle.
"""
from . import base, comptes


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
