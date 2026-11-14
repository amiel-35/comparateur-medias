"""Synthèses de la semaine et du mois, calculées à partir des éditions gardées. Aucun modèle : des comptages.

Un sujet qui dure plusieurs jours garde le même identifiant d'une édition à l'autre (la fabrique rattache les
nouveaux titres aux sujets déjà ouverts) : c'est ce qui permet de le suivre. Deux sujets ouverts séparément sur
le même fait restent comptés deux fois : c'est la limite de l'exercice.
"""
from datetime import date, timedelta

from . import base

TOP = 15          # sujets montrés
MIN_MEDIAS = 4    # en dessous, un silence ne dit rien


def cle_semaine(jour):
    a, s, _ = date.fromisoformat(jour).isocalendar()
    return f"{a}-S{s:02d}"


def bornes_semaine(jour):
    d = date.fromisoformat(jour)
    lundi = d - timedelta(days=d.weekday())
    return lundi.isoformat(), (lundi + timedelta(days=6)).isoformat()


def bornes_mois(jour):
    d = date.fromisoformat(jour)
    fin = (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return d.replace(day=1).isoformat(), fin.isoformat()


def periode(editions, cle, debut, fin):
    """editions : [(jour, charge)] de la période, dans l'ordre. Rend la synthèse, prête à afficher."""
    cote, sujets = {}, {}
    for jour, d in editions:
        for m in d["medias"]:
            cote[m["nom"]] = base.COTE[m["bord"]]
        for s in d["sujets"]:
            a = sujets.setdefault(s["id"], {"id": s["id"], "jours": [], "titres": {}, "ecart": None})
            a["titre"], a["dernier"] = s["titre"], jour
            a["jours"].append(jour)
            if s.get("divergence") is not None:
                a["ecart"] = max(a["ecart"] or 0, s["divergence"])
            for art in s["articles"]:   # un même article repris d'un jour sur l'autre ne compte qu'une fois
                a["titres"][art.get("lien") or art["titre"]] = art["media"]
    lignes = []
    for a in sujets.values():
        medias = set(a["titres"].values())
        par = {c: sum(1 for m in a["titres"].values() if cote.get(m) == c) for c in "gcd"}
        lignes.append({"id": a["id"], "titre": a["titre"], "dernier": a["dernier"], "jours": len(set(a["jours"])),
                       "medias": len(medias), "titres": len(a["titres"]), "ecart": a["ecart"], "par": par,
                       "noms": sorted(medias)})
    lignes.sort(key=lambda s: (s["medias"], s["titres"]), reverse=True)
    larges = [s for s in lignes if s["medias"] >= MIN_MEDIAS]
    bords = {}
    for c in "gcd":
        tus = [s for s in larges if s["par"][c] == 0]
        bords[c] = {"titres": sum(s["par"][c] for s in lignes), "sujets": sum(1 for s in larges if s["par"][c]),
                    "sur": len(larges), "silences": len(tus),
                    "plus_couverts": [{"id": s["id"], "titre": s["titre"], "dernier": s["dernier"], "titres": s["par"][c]}
                                      for s in sorted((s for s in lignes if s["par"][c]), key=lambda s: s["par"][c],
                                                      reverse=True)[:5]],
                    "tus": [{"id": s["id"], "titre": s["titre"], "dernier": s["dernier"], "medias": s["medias"]}
                            for s in tus[:5]]}
    top = lignes[:TOP]
    medias = []
    for nom in sorted(cote, key=lambda n: n.lower()):
        medias.append({"nom": nom, "cote": cote[nom],
                       "titres": sum(1 for s in lignes for m in sujets[s["id"]]["titres"].values() if m == nom),
                       "sujets": sum(1 for s in larges if nom in s["noms"]),
                       "top": sum(1 for s in top if nom in s["noms"])})
    medias.sort(key=lambda m: (-m["top"], -m["sujets"], m["nom"].lower()))
    return {"cle": cle, "debut": debut, "fin": fin, "jours": [j for j, _ in editions], "sujets": len(lignes),
            "larges": len(larges), "titres": sum(s["titres"] for s in lignes), "min_medias": MIN_MEDIAS,
            "top": [{k: s[k] for k in ("id", "titre", "dernier", "jours", "medias", "titres", "ecart", "par")} for s in top],
            "bords": bords, "medias": medias}


def toutes(editions):
    """editions : [(jour, charge)] de toute la base. Rend ({clé de semaine: synthèse}, {clé de mois: synthèse})."""
    semaines, mois = {}, {}
    for jour, d in editions:
        semaines.setdefault(cle_semaine(jour), []).append((jour, d))
        mois.setdefault(jour[:7], []).append((jour, d))
    return ({k: periode(v, k, *bornes_semaine(v[0][0])) for k, v in semaines.items()},
            {k: periode(v, k, *bornes_mois(v[0][0])) for k, v in mois.items()})
