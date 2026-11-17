"""Fabrique quatre éditions d'essai et écrit le site, sans réseau ni modèle, pour voir le rendu en local.

La première édition a la forme d'avant les rubriques et le suivi : elle sert à vérifier les replis.
Efface les éditions de la base visée : à lancer sur un dossier de données à part.

    COMPARATEUR_DONNEES=/tmp/essai python3 essais/editions_essai.py
    COMPARATEUR_DONNEES=/tmp/essai python3 -m comparateur servir
"""
import json, os, random, re, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if not os.environ.get("COMPARATEUR_DONNEES"):
    sys.exit("COMPARATEUR_DONNEES n'est pas réglé : ce script efface les éditions, il lui faut un dossier à part.")
from comparateur import base, config, publier
random.seed(7)
def hote(nom):
    """Un domaine d'essai par média (« le-monde.exemple.test ») : l'index public déduit le média du domaine."""
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()).strip("-") + ".exemple.test"
ref = json.load(open(os.path.join(config.ICI, "medias.json"), encoding="utf-8"))
ABSENTS = {"Le Point", "Les Echos"}
tous = ref["medias"]
lus = [m for m in tous if m["nom"] not in ABSENTS]
B = lambda m: base.bord(m["score"])
par_bord = {}
for m in lus: par_bord.setdefault(B(m), []).append(m["nom"])
SUJETS = {  # id: (titre, {jour: {bord: nb médias}})
 "s45": ("Réforme des retraites : les syndicats appellent à une nouvelle journée de mobilisation", {
    "2026-11-11": {"gauche": 3, "centre-gauche": 2, "centre": 4}, "2026-11-12": {"gauche": 4, "centre-gauche": 3, "centre": 8, "centre-droit": 2, "droite": 3},
    "2026-11-13": {"gauche": 4, "centre-gauche": 3, "centre": 6, "droite": 2}, "2026-11-14": {"gauche": 2, "centre": 3, "centre-droit": 1}}),
 "s46": ("Budget 2027 : le gouvernement engage sa responsabilité sur le volet recettes", {
    "2026-11-12": {"centre-gauche": 2, "centre": 7, "centre-droit": 3, "droite": 4}, "2026-11-13": {"gauche": 1, "centre-gauche": 2, "centre": 6, "centre-droit": 2, "droite": 3},
    "2026-11-14": {"centre": 5, "centre-droit": 2, "droite": 4}}),
 "s47": ("Un policier mis en examen après la mort d'un adolescent à Nanterre", {"2026-11-13": {"gauche": 4, "centre-gauche": 2, "centre": 3}, "2026-11-14": {"gauche": 3, "centre-gauche": 1, "centre": 2}}),
 "s48": ("Immigration : le Sénat durcit le texte sur l'aide médicale d'État", {"2026-11-13": {"centre": 2, "centre-droit": 3, "droite": 5}, "2026-11-11": {"centre": 3, "droite": 4, "centre-droit": 1}}),
 "s49": ("COP31 : accord a minima sur la sortie des énergies fossiles", {"2026-11-14": {"gauche": 2, "centre-gauche": 3, "centre": 7}, "2026-11-11": {"gauche": 1, "centre-gauche": 2, "centre": 4, "centre-droit": 1, "droite": 1}}),
 "s50": ("Ukraine : Kiev annonce la reprise d'une ville du Donbass", {"2026-11-14": {"gauche": 1, "centre-gauche": 2, "centre": 6, "centre-droit": 2, "droite": 2}, "2026-11-12": {"centre": 3, "centre-gauche": 1}}),
 "s51": ("Agriculture : les éleveurs bloquent plusieurs autoroutes du Sud-Ouest", {"2026-11-14": {"centre": 3, "droite": 1}, "2026-11-13": {"centre": 2, "centre-droit": 1}}),
 "s52": ("Hôpital : la Cour des comptes alerte sur la dette des établissements publics", {"2026-11-12": {"gauche": 1, "centre": 2}, "2026-11-14": {"gauche": 2, "centre-gauche": 1, "centre": 1}}),
}
JOURS = ["2026-11-11", "2026-11-12", "2026-11-13", "2026-11-14"]
# Un média fictif, hors de FrIdéo, dans les deux dernières éditions : il sert à voir le statut « non classé ».
NC = "Le Journal d'essai"
def edition(jour, ancienne=False):
    sujets, pris = [], set()
    for sid, (titre, jours) in SUJETS.items():
        if jour not in jours: continue
        arts = []
        for bord, n in jours[jour].items():
            for nom in random.sample(par_bord[bord], min(n, len(par_bord[bord]))):
                pris.add(nom)
                for k in range(random.choice([1, 1, 2])):
                    arts.append({"media": nom, "titre": f"{titre.split(' : ')[-1].capitalize()}, vu par {nom}" + (" : la suite" if k else ""),
                                 "lien": f"https://{hote(nom)}/{sid}/{jour}/{k}"})
        nm = len({a["media"] for a in arts})
        analyse = nm >= 4
        vide = "Sujet non analysé (trop peu couvert)."
        sujets.append({"id": sid, "titre": titre, "fait": "Le fait commun, résumé en une phrase neutre par le modèle." if analyse else "",
                       "divergence": random.randint(1, 4) if analyse else None,
                       "analyse": {"g": "Met en avant la mobilisation et la colère sociale.", "c": "Décrit le calendrier et les chiffres.", "d": "Aucun titre." if not any(b in jours[jour] for b in ("droite", "centre-droit")) else "Insiste sur le coût et les blocages."} if analyse else {"g": vide, "c": vide, "d": vide},
                       "mots": [{"terme": "« mobilisation »", "qui": "L'Humanité, Libération"}, {"terme": "« blocages »", "qui": "Le Figaro"}] if analyse else [],
                       "articles": arts})
    if jour in JOURS[2:]:
        for s in sujets[:3]:
            s["articles"].append({"media": NC, "titre": "Un titre du journal non classé, sur ce sujet", "lien": f"https://journal-essai.test/{s['id']}/{jour}"})
    sujets.sort(key=lambda s: -len({a["media"] for a in s["articles"]}))
    seuls = [{"media": m["nom"], "titre": f"Un titre resté sans jumeau chez {m['nom']}", "lien": f"https://{hote(m['nom'])}/seul/{jour}/{i}"} for i, m in enumerate(lus[::3])]
    medias = sorted(({"nom": m["nom"], "score": m["score"], "bord": B(m), "proprietaire": None} for m in lus), key=lambda m: m["score"])
    cl = [{"nom": m["nom"], "score": m["score"]} if ancienne else {k: m.get(k) for k in ("nom", "score", "ic", "sources")} | {"peu_documente": bool(m.get("peu_documente"))} for m in tous]
    d = {"recolte": jour + "T05:02:11+00:00", "heures": 24, "total": 640, "mode": "auto", "medias": medias, "absents": sorted(ABSENTS),
         "source_classement": ref["source"], "classement": {"source": ref["source"], "seuils": publier.SEUILS, "medias": sorted(cl, key=lambda m: m["score"])},
         "sujets": sujets, "seuls": seuls, "aveugle": {}}
    if jour in JOURS[2:]:
        d["medias"].append({"nom": NC, "score": None, "bord": None, "statut": "non-classe", "proprietaire": None})
        d["non_classes"] = [NC]
    if not ancienne:
        d["ecartes"] = {"rubriques": ["culture", "sport"], "titres": 87}
        d["rythme"] = {"recolte_minutes": 180, "edition_heure": 6}
    return d
db = base.connexion()
db.execute("DELETE FROM editions")
for j in JOURS:
    db.execute("INSERT INTO editions (jour, cree, donnees) VALUES (?,?,?)", (j, base.iso(), json.dumps(edition(j, ancienne=(j == JOURS[0])), ensure_ascii=False)))
db.commit()
print(publier.ecrire_pages(db), config.public())
