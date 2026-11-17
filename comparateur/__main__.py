"""Ligne de commande du comparateur.  python -m comparateur <commande>

  init                 crée la base et charge les médias (medias.json)
  recolter             lit les flux RSS
  regrouper            range les nouveaux titres en sujets (Haiku)
  analyser             analyse le cadrage des sujets (Sonnet)
  lots                 fabrique les lots à juger à l'aveugle
  publier              fait l'édition du jour avec ce que la base contient, et réécrit le site
  pages                réécrit le site depuis les éditions gardées, sans en refaire une (au démarrage)
  tout                 l'édition du jour : recolter + regrouper + analyser + lots + publier
  importer <fichier>   charge une récolte du test de concept (articles.json)
  inviter [n]          crée n codes d'invitation et les affiche (défaut : 1)
  jetons               bilan des appels aux modèles (jetons, coût)
  journal              dernières étapes de la fabrique
  servir               le guichet et la fabrique dans un seul processus (poste de développement)
  guichet              le guichet seul : site, compte, urne, mails (service « guichet » du compose)
  fabrique             la fabrique seule : récolte et édition, sans port (service « fabrique » du compose)
  verser-abonnes       copie la table abonnes de comparateur.db dans identites.db (migration de la phase 2)
  oublier-abonnes      vide la table abonnes de comparateur.db, une fois chaque ligne retrouvée dans identites.db
  mail-essai <adresse> envoie à cette seule adresse la synthèse de la dernière semaine (SMTP réglé)
"""
import secrets, sys

from . import aveugle, base, chaine, config, fabrique, llm, publier
# Le guichet (serveur, lettre, comptes) n'est importé que par ses commandes : le processus de la fabrique ne
# charge même pas le code du tiroir identité.


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "aide"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "servir":
        from . import serveur
        serveur.servir()
        return 0
    if cmd == "guichet":
        from . import serveur
        serveur.guichet()
        return 0
    if cmd == "fabrique":
        print(f"fabrique : récolte toutes les {config.fabrique_minutes() or 180} min, édition chaque jour à "
              f"{config.edition_heure()} h (Paris)", flush=True)
        chaine.boucle(config.fabrique_minutes() or 180)
        return 0
    if cmd in ("verser-abonnes", "oublier-abonnes"):
        from . import migrations
        print(migrations.verser_abonnes() if cmd == "verser-abonnes" else migrations.oublier_abonnes())
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
        elif cmd == "pages":
            print(publier.pages(db), "->", config.public())
        elif cmd == "tout":
            chaine.tout(db)
        elif cmd == "importer":
            print(fabrique.importer_json(db, argv[2]), "titres importés")
        elif cmd == "inviter":
            for _ in range(int(argv[2]) if len(argv) > 2 else 1):
                code = secrets.token_urlsafe(9)
                db.execute("INSERT INTO invitations (code, cree) VALUES (?, ?)", (code, base.iso()))
                # le code dans le fragment : ni le serveur ni le journal du proxy ne le voient
                print(f"{code}  {config.site_url()}/aveugle.html#code={code}")
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
        elif cmd == "mail-essai":
            if len(argv) < 3:
                print("usage : python -m comparateur mail-essai <adresse>")
                return 2
            if not config.mail():
                print("mail éteint : COMPARATEUR_SMTP_UTILISATEUR et COMPARATEUR_SMTP_MOT_DE_PASSE manquent")
                return 1
            from . import lettre
            cle = lettre.essai(argv[2])
            print(f"synthèse {cle} envoyée" if cle else "rien envoyé : adresse invalide, aucune édition, ou échec SMTP")
            return 0 if cle else 1
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
