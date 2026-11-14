"""Publication : la fabrique écrit le site statique (HTML + JSON) dans <données>/public/.

Les lecteurs ne lisent que ces fichiers : ni la base ni les modèles ne sont sollicités par une visite.
Écriture atomique (fichier temporaire puis renommage) : un lecteur ne voit jamais un fichier à moitié écrit.
"""
import json, os, shutil

from . import aveugle, base, config
from .fabrique import sujets_du_jour


SEUILS = ("bords dérivés du score par nos soins : gauche ≤ -1,0 ; centre-gauche ≤ -0,5 ; centre ; "
          "centre-droit ≥ +0,5 ; droite ≥ +1,0")


def _ecrire(chemin, texte):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texte)
    os.replace(tmp, chemin)


def donnees_du_jour(db):
    notes = base.scores(db)
    medias = [{"nom": r["nom"], "score": notes.get(r["id"], 0.0), "bord": base.bord(notes.get(r["id"], 0.0)),
               "proprietaire": r["proprietaire"], "id": r["id"]}
              for r in db.execute("SELECT id, nom, proprietaire FROM medias WHERE actif = 1").fetchall()]
    presents = {r["media_id"] for r in db.execute(
        "SELECT DISTINCT media_id FROM articles WHERE COALESCE(date, recolte) >= ?", (base.depuis(),))}
    analyses = {r["sujet_id"]: r for r in db.execute("SELECT * FROM analyses")}
    sujets, ranges = [], set()
    for s in sujets_du_jour(db):
        a = analyses.get(s["id"])
        if a is None and s["medias"] < 3:
            continue
        vide = "Sujet non analysé (trop peu couvert)."
        sujets.append({
            "id": f"s{s['id']}", "titre": a["titre"] if a else s["libelle"], "fait": a["fait"] if a else "",
            "divergence": a["ecart"] if a else None,
            "analyse": {k: a[k] for k in "gcd"} if a else {"g": vide, "c": vide, "d": vide},
            "mots": json.loads(a["mots"]) if a else [],
            "articles": [{"media": x["media"], "titre": x["titre"], "lien": x["lien"]} for x in s["articles"]]})
        ranges.update(x["id"] for x in s["articles"])
    # Titres de la fenêtre rangés sous aucun sujet publié : montrés à part, jamais comptés dans un bord.
    seuls = [{"media": r["nom"], "titre": r["titre"], "lien": r["lien"]} for r in db.execute(
        """SELECT a.id, a.titre, a.lien, m.nom FROM articles a JOIN medias m ON m.id = a.media_id
           WHERE COALESCE(a.date, a.recolte) >= ? AND m.actif = 1 ORDER BY m.nom, a.id""", (base.depuis(),))
             if r["id"] not in ranges]
    total = db.execute("SELECT COUNT(*) AS n FROM articles WHERE COALESCE(date, recolte) >= ?", (base.depuis(),)).fetchone()["n"]
    source = db.execute("SELECT source FROM notes_media WHERE methode = 'etude tierce' LIMIT 1").fetchone()
    return {"recolte": base.iso(), "heures": config.heures(), "total": total, "mode": "auto",
            "medias": sorted(({k: m[k] for k in ("nom", "score", "bord", "proprietaire")} for m in medias if m["id"] in presents),
                             key=lambda m: m["score"]),
            "absents": [m["nom"] for m in medias if m["id"] not in presents],
            "source_classement": source["source"] if source else "",
            "classement": {"source": source["source"] if source else "", "seuils": SEUILS,
                           "medias": sorted(({"nom": m["nom"], "score": m["score"]} for m in medias), key=lambda m: m["score"])},
            "sujets": sujets, "seuls": seuls,
            "aveugle": aveugle.resultats(db)}


def enregistrer_edition(db, jour=None):
    """Photographie l'état du jour et la garde : une édition par jour, datée en heure de Paris.
    Refaire l'édition d'un jour déjà fait la remplace."""
    charge = donnees_du_jour(db)
    charge["rythme"] = {"recolte_minutes": config.fabrique_minutes(), "edition_heure": config.edition_heure()}
    jour = jour or base.paris().strftime("%Y-%m-%d")
    db.execute("""INSERT INTO editions (jour, cree, donnees) VALUES (?, ?, ?)
                  ON CONFLICT(jour) DO UPDATE SET cree = excluded.cree, donnees = excluded.donnees""",
               (jour, base.iso(), json.dumps(charge, ensure_ascii=False)))
    db.commit()
    return jour, charge


def ecrire_pages(db):
    """Écrit le site à partir des éditions gardées : une page par jour (editions/<jour>.html), la dernière en
    page d'accueil. Tout est réécrit à chaque fois : un changement du gabarit vaut aussi pour les archives."""
    pub = config.public()
    os.makedirs(os.path.join(pub, "editions"), exist_ok=True)
    os.makedirs(os.path.join(pub, "data", "editions"), exist_ok=True)
    gabarit = open(os.path.join(config.ICI, "site", "gabarit.html"), encoding="utf-8").read()
    lignes = db.execute("SELECT jour, donnees FROM editions ORDER BY jour").fetchall()
    jours = [r["jour"] for r in lignes]
    for i, r in enumerate(lignes):
        charge = json.loads(r["donnees"])
        charge["edition"] = {"jour": r["jour"], "precedent": jours[i - 1] if i else None,
                             "suivant": jours[i + 1] if i + 1 < len(jours) else None, "toutes": jours}
        texte = json.dumps(charge, ensure_ascii=False)
        page = gabarit.replace("/*DONNEES*/null", texte.replace("</", "<\\/"))
        _ecrire(os.path.join(pub, "editions", r["jour"] + ".html"), page)
        _ecrire(os.path.join(pub, "data", "editions", r["jour"] + ".json"), texte)
        if i + 1 == len(jours):   # la dernière édition est la page d'accueil
            _ecrire(os.path.join(pub, "index.html"), page)
            _ecrire(os.path.join(pub, "data", "jour.json"), texte)
    _ecrire(os.path.join(pub, "data", "editions.json"), json.dumps(jours))
    for nom in os.listdir(os.path.join(config.ICI, "site")):
        if nom != "gabarit.html":
            shutil.copyfile(os.path.join(config.ICI, "site", nom), os.path.join(pub, nom))
    return jours


def publier(db, jour=None):
    """Fait l'édition du jour et réécrit le site."""
    with base.Etape(db, "publication") as etape:
        jour, charge = enregistrer_edition(db, jour)
        jours = ecrire_pages(db)
        etape.detail = {"edition": jour, "editions": len(jours), "sujets": len(charge["sujets"]),
                        "medias": len(charge["medias"]), "titres": charge["total"]}
        return etape.detail


def pages(db):
    """Au démarrage : réécrit le site depuis les éditions gardées, sans en refaire une. S'il n'y en a aucune
    (première mise en route), en fait une avec ce que la base contient."""
    if not db.execute("SELECT 1 FROM editions LIMIT 1").fetchone():
        return publier(db)
    return {"editions": len(ecrire_pages(db))}
