"""Synthèses de la semaine et du mois, calculées à partir des éditions gardées. Aucun modèle : des comptages.

Un sujet qui dure plusieurs jours garde le même identifiant d'une édition à l'autre (la fabrique rattache les
nouveaux titres aux sujets déjà ouverts) : c'est ce qui permet de le suivre. Deux sujets ouverts séparément sur
le même fait restent comptés deux fois : c'est la limite de l'exercice.
"""
from datetime import date, timedelta

from . import base

TOP = 15          # sujets montrés
MIN_MEDIAS = 4    # en dessous, un silence ne dit rien
BORDS = ("gauche", "centre-gauche", "centre", "centre-droit", "droite")


def bords_des_medias(charge):
    """{nom du média: bord} d'une édition. Une édition très ancienne sans bord le retrouve par le score."""
    return {m["nom"]: m.get("bord") or base.bord(m.get("score", 0.0)) for m in charge.get("medias", [])}


def medias_lus(bord):
    """Nombre de médias lus dans chaque bord. Un bord sans aucun média lu ne peut pas être dit silencieux."""
    return {b: sum(1 for v in bord.values() if v == b) for b in BORDS}


def repartition(medias, bord):
    """Titres par bord (cinq niveaux). medias : le média de chaque titre."""
    par = dict.fromkeys(BORDS, 0)
    for m in medias:
        if bord.get(m) in par:
            par[bord[m]] += 1
    return par


def silencieux(par, lus, medias):
    """Côtés silencieux sur un sujet (« g », « c », « d ») : aucun titre de tout un côté, alors que le sujet est
    repris par MIN_MEDIAS médias ou plus et que ce côté a au moins un média lu. Les comptages se font sur cinq
    bords, mais sur cinq bords presque chaque sujet aurait un absent : le silence se juge donc sur trois côtés
    (gauche et centre gauche, centre, centre droit et droite)."""
    if medias < MIN_MEDIAS:
        return []
    return [c for c in "gcd" if sum(lus.get(b, 0) for b in BORDS if base.COTE[b] == c)
            and not sum(par[b] for b in BORDS if base.COTE[b] == c)]


def suivi(editions):
    """Présence de chaque sujet dans les éditions gardées : {id: [{jour, titres, medias, par, silences}]},
    dans l'ordre des jours. Un sujet garde son identifiant d'une édition à l'autre."""
    out = {}
    for jour, d in editions:
        bord = bords_des_medias(d)
        lus = medias_lus(bord)
        for s in d.get("sujets", []):
            noms = [a["media"] for a in s["articles"]]
            par = repartition(noms, bord)
            out.setdefault(s["id"], []).append({"jour": jour, "titres": len(noms), "medias": len(set(noms)), "par": par,
                                                "silences": silencieux(par, lus, len(set(noms)))})
    return out


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
    """editions : [(jour, charge)] de la période, dans l'ordre. Rend la synthèse, prête à afficher.
    Les comptages et les silences se font sur cinq bords."""
    bord, sujets = {}, {}
    for jour, d in editions:
        bord.update(bords_des_medias(d))
        for s in d["sujets"]:
            a = sujets.setdefault(s["id"], {"id": s["id"], "jours": [], "titres": {}, "ecart": None})
            a["titre"], a["dernier"] = s["titre"], jour
            a["jours"].append(jour)
            if s.get("divergence") is not None:
                a["ecart"] = max(a["ecart"] or 0, s["divergence"])
            for art in s["articles"]:   # un même article repris d'un jour sur l'autre ne compte qu'une fois
                a["titres"][art.get("lien") or art["titre"]] = art["media"]
    lus = medias_lus(bord)
    lignes = []
    for a in sujets.values():
        medias = set(a["titres"].values())
        lignes.append({"id": a["id"], "titre": a["titre"], "dernier": a["dernier"], "jours": len(set(a["jours"])),
                       "medias": len(medias), "titres": len(a["titres"]), "ecart": a["ecart"],
                       "par": repartition(a["titres"].values(), bord), "noms": sorted(medias)})
    lignes.sort(key=lambda s: (s["medias"], s["titres"]), reverse=True)
    larges = [s for s in lignes if s["medias"] >= MIN_MEDIAS]
    bords = {}
    for c in BORDS:
        # le silence d'un côté est compté pour chacun de ses bords qui a au moins un média lu
        tus = [s for s in larges if lus.get(c) and base.COTE[c] in silencieux(s["par"], lus, s["medias"])]
        bords[c] = {"medias": lus[c], "titres": sum(s["par"][c] for s in lignes),
                    "sujets": sum(1 for s in larges if s["par"][c]), "sur": len(larges), "silences": len(tus),
                    "plus_couverts": [{"id": s["id"], "titre": s["titre"], "dernier": s["dernier"], "titres": s["par"][c]}
                                      for s in sorted((s for s in lignes if s["par"][c]), key=lambda s: s["par"][c],
                                                      reverse=True)[:5]],
                    "tus": [{"id": s["id"], "titre": s["titre"], "dernier": s["dernier"], "medias": s["medias"]}
                            for s in tus[:5]]}
    top = lignes[:TOP]
    medias = []
    for nom in sorted(bord, key=lambda n: n.lower()):
        medias.append({"nom": nom, "bord": bord[nom], "cote": base.COTE.get(bord[nom], "c"),
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
