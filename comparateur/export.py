"""Export public de chaque édition : un JSON daté par jour, identique pour tous, décrit par un schéma.

Règle 10 de DOCTRINE.md : un export n'est jamais une copie de comparateur.db. Il se construit ici champ par
champ, à partir de l'édition gardée (le JSON de la table `editions`, déjà chargé par `publier.ecrire_pages`),
et ne lit jamais la base. Ce que l'édition ne porte pas (une édition d'avant les statuts, les rubriques, les
versions) reçoit une valeur par défaut : une édition d'avant s'exporte toujours (règle 6).

Mêmes octets pour tous et d'un passage à l'autre : clés triées, aucune heure de génération, aucun paramètre.
Chaque export est validé contre `export_schema.json` avant d'être écrit.

Fichiers : <public>/export/editions/<jour>.json, <public>/export/editions.json (les jours),
<public>/export/schema.json.
"""
import json, os

from . import base, config, schema, syntheses

VERSION = 1
CHEMIN_SCHEMA = os.path.join(config.ICI, "export_schema.json")

LICENCES = {
    "code": "AGPL-3.0",
    "classement": "FrIdéo, French News Lab, CC BY 4.0",
    "titres": "Les titres appartiennent à leurs journaux.",
}

# Les champs écrits par un modèle de langage (règle 7 de DOCTRINE.md : tout texte écrit par un modèle porte
# l'étiquette « écrit par un modèle »).
ECRIT_PAR_UN_MODELE = ["sujets[].analyse", "sujets[].divergence", "sujets[].fait", "sujets[].mots", "sujets[].titre"]


def _texte(v):
    return v if isinstance(v, str) else ""


def _entier(v, defaut):
    return v if isinstance(v, int) and not isinstance(v, bool) else defaut


def _article(a):
    return {"media": _texte(a.get("media")), "titre": _texte(a.get("titre")), "lien": _texte(a.get("lien"))}


def _sujet(s, bord, lus):
    arts = [_article(a) for a in s.get("articles", [])]
    noms = [a["media"] for a in arts]
    par = syntheses.repartition(noms, bord)
    analyse = s.get("analyse") if isinstance(s.get("analyse"), dict) else {}
    return {"id": _texte(s.get("id")), "titre": _texte(s.get("titre")), "fait": _texte(s.get("fait")),
            "divergence": _entier(s.get("divergence"), None),
            "analyse": {k: _texte(analyse.get(k)) for k in "gcd"},
            "mots": [{"terme": _texte(m.get("terme")), "qui": _texte(m.get("qui"))}
                     for m in s.get("mots") or [] if isinstance(m, dict)],
            "articles": arts, "par_bande": par,
            "cotes_silencieux": syntheses.silencieux(par, lus, len(set(noms)))}


def edition(jour, charge, versions):
    """L'export d'une édition. charge : le JSON gardé de l'édition ; versions : {methode, classement} ou None."""
    bord = syntheses.bords_des_medias(charge)
    lus = syntheses.medias_lus(bord)
    versions = versions or {}
    medias = []
    for m in charge.get("medias", []):
        score = m.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            score = None
        # Le bord et le statut se relisent dans le score : une édition d'avant ne porte pas l'un ni l'autre.
        medias.append({"nom": _texte(m.get("nom")), "statut": base.statut(score), "score": score,
                       "bande": base.bord(score) if score is not None else None})
    return {
        "v": VERSION, "jour": jour,
        "versions": {"methode": _texte(versions.get("methode")), "classement": _texte(versions.get("classement"))},
        "licences": dict(LICENCES), "ecrit_par_un_modele": list(ECRIT_PAR_UN_MODELE),
        "heures": _entier(charge.get("heures"), 24), "total": _entier(charge.get("total"), 0),
        "medias": medias,
        "absents": [_texte(n) for n in charge.get("absents", [])],
        "non_classes": [_texte(n) for n in charge.get("non_classes", [])],   # facultatif dans l'édition
        "sujets": [_sujet(s, bord, lus) for s in charge.get("sujets", [])],
        "seuls": [_article(a) for a in charge.get("seuls", [])],
    }


def octets(doc):
    """La forme écrite : toujours la même pour le même contenu, pour tout le monde."""
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _ecrire(chemin, texte):
    # Même écriture atomique que publier._ecrire (non importée : publier importe ce module).
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texte)
    os.replace(tmp, chemin)


def schema_publie():
    with open(CHEMIN_SCHEMA, encoding="utf-8") as f:
        return json.load(f)


def ecrire(pub, editions):
    """Écrit l'export. editions : [(jour, charge, versions)] dans l'ordre des jours. Valide chaque export
    avant d'écrire quoi que ce soit ; un export qui ne passe pas le schéma lève schema.ErreurSchema."""
    sch = schema_publie()
    docs = []
    for jour, charge, versions in editions:
        doc = edition(jour, charge, versions)
        try:
            schema.verifier(doc, sch)
        except schema.ErreurSchema as e:
            raise schema.ErreurSchema(f"export de l'édition {jour} : {e}") from None
        docs.append(doc)
    jours = [d["jour"] for d in docs]
    schema.verifier(jours, {"type": "array", "items": sch["$defs"]["jour"]})
    os.makedirs(os.path.join(pub, "export", "editions"), exist_ok=True)
    for doc in docs:
        _ecrire(os.path.join(pub, "export", "editions", doc["jour"] + ".json"), octets(doc))
    _ecrire(os.path.join(pub, "export", "editions.json"), octets(jours))
    _ecrire(os.path.join(pub, "export", "schema.json"), octets(sch))
    return jours
