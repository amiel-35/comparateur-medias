"""Publication : la fabrique écrit le site statique (HTML + JSON) dans <données>/public/.

Les lecteurs ne lisent que ces fichiers : ni la base ni les modèles ne sont sollicités par une visite.
Écriture atomique (fichier temporaire puis renommage) : un lecteur ne voit jamais un fichier à moitié écrit.
"""
import json, os, shutil

from . import aveugle, base, config
from .fabrique import sujets_du_jour


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
    sujets = []
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
    total = db.execute("SELECT COUNT(*) AS n FROM articles WHERE COALESCE(date, recolte) >= ?", (base.depuis(),)).fetchone()["n"]
    source = db.execute("SELECT source FROM notes_media WHERE methode = 'etude tierce' LIMIT 1").fetchone()
    return {"recolte": base.iso(), "heures": config.heures(), "total": total, "mode": "auto",
            "medias": sorted(({k: m[k] for k in ("nom", "score", "bord", "proprietaire")} for m in medias if m["id"] in presents),
                             key=lambda m: m["score"]),
            "absents": [m["nom"] for m in medias if m["id"] not in presents],
            "source_classement": source["source"] if source else "", "sujets": sujets, "seuls": [],
            "aveugle": aveugle.resultats(db)}


def publier(db):
    with base.Etape(db, "publication") as etape:
        charge = donnees_du_jour(db)
        pub = config.public()
        texte = json.dumps(charge, ensure_ascii=False)
        _ecrire(os.path.join(pub, "data", "jour.json"), texte)
        gabarit = open(os.path.join(config.ICI, "site", "gabarit.html"), encoding="utf-8").read()
        _ecrire(os.path.join(pub, "index.html"), gabarit.replace("/*DONNEES*/null", texte.replace("</", "<\\/")))
        for nom in os.listdir(os.path.join(config.ICI, "site")):
            if nom != "gabarit.html":
                shutil.copyfile(os.path.join(config.ICI, "site", nom), os.path.join(pub, nom))
        etape.detail = {"sujets": len(charge["sujets"]), "medias": len(charge["medias"]), "titres": charge["total"]}
        return etape.detail
