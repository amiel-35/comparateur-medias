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
  panel-inviter [n]    crée n codes d'invitation au panel et affiche leur lien (défaut : 1 ; mail réglé)
  questionnaire ouvrir <fichier.json>   ouvre un questionnaire du panel (clés, urne, description publique)
  questionnaire fermer <id>             la clôture : clé détruite, retraits effacés, urne scellée, résultats publiés
  questionnaire resultats <id>          recompte un questionnaire clos (après un effacement par le reçu) et republie
  jetons               bilan des appels aux modèles (jetons, coût)
  journal              dernières étapes de la fabrique
  servir               le guichet et la fabrique dans un seul processus (poste de développement)
  guichet              le guichet seul : site, compte, urne, mails (service « guichet » du compose)
  fabrique             la fabrique seule : récolte et édition, sans port (service « fabrique » du compose)
  verser-abonnes       déplace la table abonnes de comparateur.db dans identites.db (le guichet le fait au démarrage)
  verser-votes         copie les avis du vieux vote à l'aveugle dans urnes/aveugle-historique.db et publie leurs
                       sommes (public/panel/aveugle/historique.json) ; migration de la phase 3
  oublier-votes        vide votants, avis_aveugle, avis_note et invitations de comparateur.db, une fois chaque avis
                       retrouvé dans l'urne historique
  mail-essai <adresse> envoie à cette seule adresse la synthèse de la dernière semaine (SMTP réglé)
"""
import sys

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
    if cmd == "verser-abonnes":
        from . import migrations
        print(migrations.verser_abonnes())
        return 0
    if cmd in ("verser-votes", "oublier-votes"):
        from . import migrations
        bilan = migrations.verser_votes() if cmd == "verser-votes" else migrations.oublier_votes()
        print(bilan)
        if bilan.get("journal_vide") is False:
            print("le journal de comparateur.db n'a pas pu être vidé : arrêter la fabrique, puis relancer oublier-votes")
        return 1 if bilan.get("manquants") or bilan.get("journal_vide") is False else 0
    if cmd == "panel-inviter":
        if not config.compte_url():
            print("mail éteint : sans réglages SMTP, ni compte ni panel (COMPARATEUR_SMTP_UTILISATEUR, COMPARATEUR_SMTP_MOT_DE_PASSE)")
            return 1
        from . import comptes
        ident = comptes.connexion()
        try:
            for code in comptes.inviter_panel(ident, int(argv[2]) if len(argv) > 2 else 1):
                # le code dans le fragment : ni le serveur ni le journal du proxy ne le voient
                print(f"{code}  {config.compte_url()}/panel#code={code}")
        finally:
            ident.close()
        return 0
    if cmd == "questionnaire":
        return questionnaire(argv[2:])
    if cmd == "inviter":
        print("commande retirée avec l'ancien vote à l'aveugle : le panel invite par `python -m comparateur panel-inviter [n]`")
        return 2
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


def _resume(res):
    """Ce qui a été publié, en clair : les deux effectifs, et chaque bord (montré ou non)."""
    lignes = [f"  {res['titre']} ({res['questionnaire']})",
              f"  bulletins délivrés : {res['delivres']}, réponses reçues : {res['recues']}",
              "  par bord : " + ", ".join(f"{nom} {res['effectifs'][g] if res['effectifs'][g] is not None else 'moins de 5'}"
                                          for g, nom in (("g", "gauche"), ("c", "centre"), ("d", "droite"))),
              f"  scellement : {res['scellement']}"]
    return "\n".join(lignes)


def questionnaire(args):
    """python -m comparateur questionnaire ouvrir <fichier.json> | fermer <id> | resultats <id>. Dans le conteneur
    du guichet : il tient identites.db (les clés privées) et les urnes. Ne lit jamais une réponse une à une."""
    import json, os
    from datetime import date
    if len(args) != 2 or args[0] not in ("ouvrir", "fermer", "resultats"):
        print("usage : python -m comparateur questionnaire ouvrir <fichier.json> | fermer <id> | resultats <id>")
        return 2
    if not config.compte_url():
        print("mail éteint : sans réglages SMTP, ni compte ni panel (COMPARATEUR_SMTP_UTILISATEUR, COMPARATEUR_SMTP_MOT_DE_PASSE)")
        return 1
    from . import ceremonie, comptes, urne
    geste, x = args
    if geste == "ouvrir":
        try:
            with open(x, encoding="utf-8") as f:
                q = json.load(f)
        except (OSError, ValueError) as e:
            print(f"fichier illisible : {e}")
            return 2
        fin = q.get("fermeture") if isinstance(q, dict) else None
        try:
            futur = isinstance(fin, str) and date.fromisoformat(fin) > date.today()
        except ValueError:
            futur = False
        if not futur:
            print("fermeture attendue : une date AAAA-MM-JJ après aujourd'hui (le guichet clôt seul le lendemain)")
            return 2
        try:
            public = ceremonie.ouvrir(q)
        except ValueError as e:
            print(f"questionnaire refusé : {e}")
            return 2
        print(f"ouvert : {public['id']}, {len(public['questions'])} question(s), jusqu'au {public['fermeture']} inclus")
        print(f"  description publique : {os.path.join(config.public(), 'panel', 'questionnaires', public['id'] + '.json')}")
        print(f"  page du panel : {config.compte_url()}/panel ; seuls les membres arrivés au moins "
              f"{comptes.CARENCE_JOURS} jours avant aujourd'hui peuvent répondre")
        return 0
    if not urne.ID.match(x) or x.startswith(("carte-", "aveugle-")):
        print("identifiant de questionnaire attendu")
        return 2
    if geste == "fermer":
        ident = comptes.connexion()
        try:
            ouvert = any(r["questionnaire"] == x for r in comptes.cles_ouvertes(ident)) or x in ceremonie.a_reprendre(ident)
            if not ouvert:   # un questionnaire inconnu, ou déjà clos ; une clôture interrompue, elle, se reprend
                print(f"aucun questionnaire ouvert sous ce nom : {x}")
                return 1
            res = ceremonie.fermer(x, ident)
        finally:
            ident.close()
        print("clos. Clé détruite, retraits effacés, urne scellée. Résultats publiés :")
    else:
        try:
            res = ceremonie.republier(x)
        except urne.Refus as e:
            print(f"pas de résultats : {e.message}")
            return 1
        print("recompté et republié :")
    print(_resume(res))
    print(f"  fichier : {os.path.join(config.public(), 'panel', 'resultats', x + '.json')}")
    print("  le site les montre (vue #/panel) à la prochaine écriture des pages par la fabrique")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
