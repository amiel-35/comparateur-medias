"""Ligne de commande du comparateur.  python -m comparateur <commande>

  init                 crée la base et charge les médias (medias.json)
  recolter             lit les flux RSS
  regrouper            range les nouveaux titres en sujets (Haiku)
  analyser             analyse le cadrage des sujets (Sonnet)
  lots                 fabrique les lots à juger à l'aveugle
  publier              écrit le site statique
  tout                 recolter + regrouper + analyser + lots + publier (la tâche planifiée)
  importer <fichier>   charge une récolte du test de concept (articles.json)
  inviter [n]          crée n codes d'invitation et les affiche (défaut : 1)
  jetons               bilan des appels aux modèles (jetons, coût)
  journal              dernières étapes de la fabrique
  servir               lance le site et le guichet des votes
"""
import secrets, sys

from . import aveugle, base, chaine, config, fabrique, llm, publier, serveur


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "aide"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "servir":
        serveur.servir()
        return 0
    db = base.connexion()
    try:
        if cmd == "init":
            print(base.charger_medias(db), "médias chargés dans", config.base())
        elif cmd == "recolter":
            for media, etat in fabrique.recolter(db).items():
                print(f"  {media:20} {etat}")
        elif cmd == "regrouper":
            print(fabrique.regrouper(db))
        elif cmd == "analyser":
            print(fabrique.analyser(db))
        elif cmd == "lots":
            print(aveugle.fabriquer_lots(db), "lots créés")
        elif cmd == "publier":
            print(publier.publier(db), "->", config.public())
        elif cmd == "tout":
            chaine.tout(db)
        elif cmd == "importer":
            print(fabrique.importer_json(db, argv[2]), "titres importés")
        elif cmd == "inviter":
            for _ in range(int(argv[2]) if len(argv) > 2 else 1):
                code = secrets.token_urlsafe(9)
                db.execute("INSERT INTO invitations (code, cree) VALUES (?, ?)", (code, base.iso()))
                print(code)
            db.commit()
        elif cmd == "jetons":
            total = {"appels": 0, "entree": 0, "sortie": 0, "cout": 0.0}
            for (etape, modele), b in sorted(llm.bilan().items()):
                print(f"  {etape:22} {modele:18} {b['appels']:3} appels  {b['entree']:7} entrée  {b['sortie']:7} sortie  "
                      f"{b['cout']:.4f} $  {b['secondes']:.0f} s")
                for k in total:
                    total[k] += b[k]
            print(f"  TOTAL {total['appels']} appels, {total['entree']} jetons en entrée, {total['sortie']} en sortie, "
                  f"{total['cout']:.4f} $ au tarif public")
        elif cmd == "journal":
            for r in db.execute("SELECT etape, debut, fin, ok, detail FROM journal_fabrique ORDER BY id DESC LIMIT 15"):
                print(f"  {r['debut'][:19]}  {r['etape']:14} {'ok ' if r['ok'] else 'KO ' if r['ok'] == 0 else '...'} {r['detail'] or ''}"[:220])
        else:
            print("commande inconnue :", cmd, "\n", __doc__)
            return 2
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
