"""Jugement à l'aveugle : fabrication des lots et comptage des votes.

Un lot = 10 titres d'un même média, nom et indices retirés. Le votant place le lot sur l'échelle
gauche-droite (-2 à +2). Le comptage fait la moyenne par bord déclaré du votant, puis la moyenne
entre bords : mille votes d'un seul bord ne pèsent pas plus que cent.
"""
import json, re

from . import base, config
from .fabrique import norm

TAILLE_LOT = 10
# Autres noms sous lesquels un média se cite lui-même ou cite son groupe dans un titre.
ALIAS = {
    "TF1 INFO": ["tf1", "lci", "tf1info"], "BFMTV": ["bfm", "bfm tv", "rmc"], "CNews": ["cnews", "europe 1"],
    "Le JDD": ["jdd", "journal du dimanche"], "franceinfo": ["france info", "france télévisions", "france 2"],
    "Le Parisien": ["aujourd'hui en france"], "L'Humanité": ["l'huma", "humanité"], "Libération": ["libé", "checknews"],
    "Le Nouvel Obs": ["l'obs", "nouvel obs"], "Le Monde": ["les décodeurs"], "Le HuffPost": ["huffpost", "huffington"],
    "Valeurs actuelles": ["valeurs"], "Le Figaro": ["figaro", "figarovox"], "L'Express": ["express"],
    "L'Opinion": ["l'opinion"], "RFI": ["rfi"], "France 24": ["france 24", "france24"], "Slate.fr": ["slate"],
    "20 Minutes": ["20 minutes"], "Ouest-France": ["ouest-france", "ouest france"], "La Croix": ["la croix"],
    "Mediapart": ["mediapart"], "Blast": ["blast"], "Marianne": ["marianne"], "Challenges": ["challenges"],
    "Atlantico": ["atlantico"], "Causeur": ["causeur"], "Fdesouche": ["fdesouche"], "Les Echos": ["les echos"],
    "Le Point": ["le point"],
}
# Marques de rubrique en tête de titre, sans lien avec le média.
PREFIXES = r"^\s*(?:\[[^\]]{1,30}\]|en direct|direct|info|exclusif|exclu|vid[ée]o|en images|tribune|[ée]dito(?:rial)?)\s*[-:.,–—]*\s*"


def noms(media):
    return sorted({norm(media)} | {norm(a) for a in ALIAS.get(media, [])}, key=len, reverse=True)


def uniformiser(t):
    """Efface la typographie maison : guillemets, apostrophes, tirets, espaces, milliers. Un lecteur reconnaît
    un journal à ces détails plus qu'à ses mots (French News Lab, « Qui a publié ce titre ? », 2026) ; à
    l'aveugle, on ne doit juger que ce que le titre dit."""
    t = t.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    t = re.sub(r"[«»“”„‟]", '"', t)                      # tous les guillemets deviennent droits
    t = re.sub(r'"\s*([^"]*?)\s*"', r'"\1"', t)          # sans espace à l'intérieur
    t = re.sub(r"[’‘ʼ`´]", "'", t)
    t = re.sub(r"\s*[–—]\s*", " - ", t)
    t = t.replace("…", "...")
    t = re.sub(r"(?<=\d)[.\s](?=\d{3}(?!\d))", " ", t)   # 6.000 et 6 000 s'écrivent pareil
    t = re.sub(r"\s*([:;!?])", r" \1", t)               # une espace avant la ponctuation double, toujours
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"(?<!\.)\.$", "", t).rstrip()          # pas de point final (les points de suspension restent)


def nettoyer(titre, media):
    """Rend le titre sans indice sur le média, ou None s'il ne peut pas être rendu anonyme."""
    t = titre.strip()
    for _ in range(3):  # « EN DIRECT - INFO JDD. … » : plusieurs marques à la suite
        t2 = re.sub(PREFIXES, "", t, flags=re.I)
        for n in noms(media):
            # le nom du média en tête, suivi d'une ponctuation : « JDD. », « Le Figaro : »
            t2 = re.sub(r"^\s*%s\s*[-:.,–—]+\s*" % re.escape(n), "", t2, flags=re.I) if norm(t2).startswith(n) else t2
        if t2 == t:
            break
        t = t2
    t = uniformiser(t)
    t = t[:1].upper() + t[1:] if t else t
    bas = norm(t)
    if len(t) < 25 or any(re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(n), bas) for n in noms(media)):
        return None
    return t


def fabriquer_lots(db):
    """Un lot par média et par jour, pour les médias qui ont assez de titres anonymisables."""
    jour, faits = base.iso()[:10], 0
    with base.Etape(db, "lots aveugle") as etape:
        en_sujet = {r["article_id"] for r in db.execute("SELECT article_id FROM sujet_articles")}
        for m in db.execute("SELECT id, nom FROM medias WHERE actif = 1").fetchall():
            if db.execute("SELECT 1 FROM lots_aveugle WHERE media_id = ? AND jour = ?", (m["id"], jour)).fetchone():
                continue
            arts = db.execute(
                "SELECT id, titre FROM articles WHERE media_id = ? AND COALESCE(date, recolte) >= ? ORDER BY id DESC",
                (m["id"], base.depuis())).fetchall()
            propres = [(a["id"], nettoyer(a["titre"], m["nom"])) for a in arts]
            propres = [(i, t) for i, t in propres if t]
            # D'abord les titres sur des sujets que d'autres traitent aussi (comparables), puis les plus récents.
            choisis = [t for i, t in propres if i in en_sujet][:TAILLE_LOT // 2]
            choisis += [t for i, t in propres if t not in choisis][:TAILLE_LOT - len(choisis)]
            if len(choisis) < TAILLE_LOT:
                continue
            db.execute("INSERT INTO lots_aveugle (media_id, jour, titres, cree) VALUES (?,?,?,?)",
                       (m["id"], jour, json.dumps(choisis, ensure_ascii=False), base.iso()))
            faits += 1
        db.commit()
        etape.detail = {"lots": faits}
    return faits


def groupe(bord_declare):
    return "g" if bord_declare < 0 else "d" if bord_declare > 0 else "c"


def compter(avis, minimum):
    """avis : [(bord déclaré du votant, note)]. Rend la note pondérée par bord et son statut.

    Moyenne par groupe de votants (gauche, centre, droite), puis moyenne des groupes présents.
    'publiable' seulement si chaque groupe atteint le minimum ; sinon 'indicatif'."""
    par = {"g": [], "c": [], "d": []}
    for bord_declare, note in avis:
        par[groupe(bord_declare)].append(note)
    moyennes = {k: sum(v) / len(v) for k, v in par.items() if v}
    if not moyennes:
        return None
    return {"note": round(sum(moyennes.values()) / len(moyennes), 2),
            "par_bord": {k: round(v, 2) for k, v in moyennes.items()},
            "effectifs": {k: len(v) for k, v in par.items()},
            "statut": "publiable" if all(len(v) >= minimum for v in par.values()) else "indicatif"}


def resultats(db):
    """Note à l'aveugle par média (échelle -2 à +2), avec effectifs par bord, et désaccords sur la note affichée."""
    out = {}
    for m in db.execute("SELECT id, nom FROM medias ORDER BY nom").fetchall():
        avis = [(r["bord"], r["note"]) for r in db.execute(
            """SELECT v.bord, a.note FROM avis_aveugle a JOIN votants v ON v.id = a.votant_id
               JOIN lots_aveugle l ON l.id = a.lot_id WHERE l.media_id = ?""", (m["id"],))]
        accord = db.execute("SELECT SUM(accord) AS oui, COUNT(*) AS n FROM avis_note WHERE media_id = ?", (m["id"],)).fetchone()
        ligne = {}
        compte = compter(avis, config.min_par_bord())
        if compte:
            ligne["aveugle"] = compte
        if accord["n"]:
            ligne["accord"] = {"oui": accord["oui"] or 0, "votes": accord["n"]}
        if ligne:
            out[m["nom"]] = ligne
    return out
