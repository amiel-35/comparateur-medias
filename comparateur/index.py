"""L'index public : un fichier unique (public/index.json) qui dit, pour les éditions des sept derniers jours,
quel média publie sous quel domaine, et quel article se range sous quel sujet. Le site s'en sert (« Situer un
article ») et une extension pourra le télécharger : la correspondance se fait sur l'appareil, rien n'est envoyé.

Il se construit à partir des éditions gardées, jamais de la base (règle 10 de DOCTRINE.md). Il ne contient rien
que le site ne publie déjà. Le contrat : docs/cadrage-long-terme.md, section 6.3.
"""
import hashlib, json, os, re
from datetime import date, timedelta

from . import base, config, syntheses

VERSION = 1
FENETRE_JOURS = 7
PREFIXES = ("www", "m", "mobile", "amp")
_BORDS = " \t\n\r\f\v"
_ADRESSE = re.compile(r"^(https?)://([^/?#]*)([^?#]*)", re.IGNORECASE)
_PORT = re.compile(r":[0-9]*\Z")


def _minuscules(s):
    """Minuscules ASCII seulement : la même règle en JavaScript, sans l'écart des alphabets non latins."""
    return re.sub(r"[A-Z]+", lambda m: m.group(0).lower(), s)


def normaliser(adresse):
    """La forme normalisée d'une adresse d'article, ou None. La règle, écrite telle quelle dans le README et dans
    js/adresse.js (mêmes vecteurs d'essai : tests/vecteurs-adresses.json) :

    1. les espaces des bords sont retirés ;
    2. le schéma doit être http ou https, sinon None ; il est ensuite oublié ;
    3. l'hôte est mis en minuscules, sans point final, sans port, sans identifiants (user:mot@) ;
    4. un préfixe d'usage est retiré une fois en tête d'hôte : www., m., mobile., amp., si l'hôte garde au moins
       deux étiquettes ;
    5. le chemin est gardé tel quel (casse et %xx conservés) ; vide, il devient « / » ; une barre finale est
       retirée, sauf pour « / » ;
    6. les paramètres (?...) et le fragment (#...) sont retirés.

    Résultat : hôte + chemin. Une adresse sans hôte, ou dont l'hôte est une adresse IPv6, rend None."""
    if not isinstance(adresse, str):
        return None
    m = _ADRESSE.match(adresse.strip(_BORDS))
    if not m:
        return None
    hote, chemin = m.group(2), m.group(3)
    hote = hote[hote.rfind("@") + 1:]
    hote = _minuscules(_PORT.sub("", hote)).rstrip(".")
    if not hote or ":" in hote or "[" in hote or "]" in hote:
        return None
    etiquettes = hote.split(".")
    if etiquettes[0] in PREFIXES and len(etiquettes) > 2:
        hote = ".".join(etiquettes[1:])
    if chemin == "":
        chemin = "/"
    elif len(chemin) > 1 and chemin.endswith("/"):
        chemin = chemin[:-1]
    return hote + chemin


def cle(adresse):
    """La clé d'un article : les 16 premiers caractères hexadécimaux du SHA-256 de la forme normalisée (UTF-8).
    None si l'adresse n'a pas de forme normalisée. Une empreinte tronquée réduit la taille, elle ne cache rien."""
    n = normaliser(adresse)
    return None if n is None else hashlib.sha256(n.encode("utf-8")).hexdigest()[:16]


def hote(adresse):
    n = normaliser(adresse)
    return None if n is None else n.split("/", 1)[0]


def _fenetre(charges):
    """Les éditions des sept derniers jours, la dernière édition gardée comprise."""
    charges = sorted(charges, key=lambda c: c[0])
    if not charges:
        return []
    debut = (date.fromisoformat(charges[-1][0]) - timedelta(days=FENETRE_JOURS - 1)).isoformat()
    return [c for c in charges if c[0] >= debut]


def construire(charges, domaines_declares=None):
    """L'index (format v 1) à partir des éditions gardées [(jour, charge)]. domaines_declares : {nom du média:
    [domaines]}, facultatif, ajouté aux hôtes vus dans les liens des articles."""
    fen = _fenetre(charges)
    vus, medias_lus, sujets, articles = {}, {}, {}, {}   # vus : hôte -> noms de médias
    for jour, charge in fen:
        bord = syntheses.bords_des_medias(charge)
        lus = syntheses.medias_lus(bord)
        ic = {m["nom"]: m.get("ic") for m in charge.get("classement", {}).get("medias", [])}
        for m in charge.get("medias", []):
            note = m.get("score")
            medias_lus[m["nom"]] = {"nom": m["nom"], "score": note, "ic": ic.get(m["nom"]),
                                    "statut": m.get("statut") or base.statut(note)}
        for nom in charge.get("non_classes", []):
            medias_lus.setdefault(nom, {"nom": nom, "score": None, "ic": None, "statut": "non-classe"})
        for s in charge.get("sujets", []):
            noms = [a["media"] for a in s["articles"]]
            par = syntheses.repartition(noms, bord)
            sujets[s["id"]] = {"titre": s["titre"], "jour": jour, "par": par,
                               "silences": syntheses.silencieux(par, lus, len(set(noms))),
                               "page": f"/editions/{jour}.html#/sujet/{s['id']}"}
            for a in s["articles"]:
                k = cle(a.get("lien"))
                if k:
                    articles[k] = s["id"]
        for a in [a for s in charge.get("sujets", []) for a in s["articles"]] + charge.get("seuls", []):
            h = hote(a.get("lien"))
            if h:
                vus.setdefault(h, set()).add(a["media"])
    for nom, doms in (domaines_declares or {}).items():
        for d in doms:
            h = hote("https://" + d)
            if h:
                vus.setdefault(h, set()).add(nom)
    medias = {}
    for h, noms in sorted(vus.items()):
        if len(noms) != 1:
            continue   # un hôte partagé entre deux médias est ambigu : il n'entre pas
        m = medias_lus.get(next(iter(noms)))
        if not m:
            continue
        if m["statut"] == "classe" and m["score"] is not None:
            medias[h] = {"nom": m["nom"], "statut": "classe", "bande": base.bord(m["score"]), "score": m["score"],
                         "ic": m["ic"]}
        else:
            medias[h] = {"nom": m["nom"], "statut": "non-classe"}
    v = fen[-1][1].get("versions", {}) if fen else {}
    return {"v": VERSION, "genere_le": fen[-1][0] if fen else "", "methode": v.get("methode") or "",
            "classement": v.get("classement") or "", "medias": medias, "sujets": sujets, "articles": articles}


def _domaines_declares():
    with open(os.path.join(config.ICI, "medias.json"), encoding="utf-8") as f:
        return {m["nom"]: m["domaines"] for m in json.load(f)["medias"] if m.get("domaines")}


def ecrire(pub, charges):
    """Écrit public/index.json : une seule adresse, les mêmes octets pour tous, écriture atomique."""
    texte = json.dumps(construire(charges, _domaines_declares()), sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False)
    chemin = os.path.join(pub, "index.json")
    with open(chemin + ".tmp", "w", encoding="utf-8") as f:
        f.write(texte)
    os.replace(chemin + ".tmp", chemin)
    return texte
