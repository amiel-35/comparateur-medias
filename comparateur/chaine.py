"""La chaîne complète de la fabrique, lancée par la tâche planifiée ou par le serveur lui-même."""
import json, threading, time

from . import aveugle, base, config, fabrique, llm, publier

VERROU = threading.Lock()


def recolte(db=None, afficher=print):
    """La récolte seule, sans modèle : plusieurs fois par jour, pour ne rien rater entre deux éditions."""
    return _lancer([("recolte", fabrique.recolter)], db, afficher)


def tout(db=None, afficher=print):
    """L'édition du jour : recolte -> regroupement -> analyse -> lots -> publication. Une fois par jour."""
    return _lancer([("recolte", fabrique.recolter), ("regroupement", fabrique.regrouper), ("analyse", fabrique.analyser),
                    ("lots", aveugle.fabriquer_lots), ("publication", publier.publier)], db, afficher)


def _lancer(etapes, db, afficher):
    """Une seule exécution à la fois."""
    if not VERROU.acquire(blocking=False):
        afficher("fabrique déjà en cours : passage ignoré")
        return False
    propre = db is None
    db = db or base.connexion()
    try:
        for nom, etape in etapes:
            try:
                rendu = etape(db)
            except llm.BudgetDepasse as e:
                afficher(f"{nom} : {e}")   # on publie quand même : le site reste à jour sur la récolte
                continue
            except Exception as e:         # une étape en panne n'empêche pas la publication
                afficher(f"{nom} : ÉCHEC {type(e).__name__}: {e}")
                continue
            if nom == "recolte":
                rendu = {"medias": len(rendu), "en_panne": [m for m, etat in rendu.items() if "nouveaux" not in etat]}
            afficher(f"{nom} : {json.dumps(rendu, ensure_ascii=False)}")
        return True
    finally:
        if propre:
            db.close()
        VERROU.release()


def edition_faite(jour):
    db = base.connexion()
    try:
        return db.execute("SELECT 1 FROM editions WHERE jour = ?", (jour,)).fetchone() is not None
    finally:
        db.close()


def boucle(minutes, tours=None):
    """La fabrique : la récolte des flux toutes les `minutes`, et l'édition une fois par jour, à l'heure réglée
    (heure de Paris). Un redémarrage après l'heure la rattrape. Elle n'écoute aucun port, n'ouvre pas le tiroir
    identité et n'envoie aucun mail : elle écrit le tiroir public, le guichet le lit."""
    def dire(m):
        print("fabrique |", m, flush=True)

    derniere, n = 0.0, 0
    while tours is None or n < tours:
        n += 1
        try:
            ici = base.paris()
            if ici.hour >= config.edition_heure() and not edition_faite(ici.strftime("%Y-%m-%d")):
                dire("édition du " + ici.strftime("%Y-%m-%d"))
                tout(afficher=dire)                  # l'édition commence par une récolte
                derniere = time.time()
            elif time.time() - derniere >= minutes * 60:
                recolte(afficher=dire)
                derniere = time.time()
        except Exception as e:
            dire(f"arrêt inattendu : {type(e).__name__} {e}")
            derniere = time.time()                   # pas de boucle serrée sur une panne
        if tours is None or n < tours:
            time.sleep(60)
