"""Jugement à l'aveugle : fabrication des lots, et lecture des résultats publiés par l'urne.

Un lot = 10 titres d'un même média, nom et indices retirés. Le votant place le lot sur l'échelle
gauche-droite (-2 à +2). Le comptage fait la moyenne par bord déclaré du votant, puis la moyenne
entre bords : mille votes d'un seul bord ne pèsent pas plus que cent.

Les avis ne sont pas ici. Ils se donnent avec la carte de votant et vivent dans l'urne (urnes/aveugle-<trimestre>.db).
Ce module ne lit que ce que l'urne publie à la clôture d'un trimestre, des sommes par lot et par bord
(public/panel/aveugle/<trimestre>.json, et historique.json pour les avis d'avant la carte), et la table publique
lots_aveugle, qui dit de quel média est chaque lot. Le résultat est une mesure à part, versionnée : elle s'affiche à
côté du classement FrIdéo, jamais fondue en lui.
"""
import glob, json, os, re, secrets
from datetime import date, timedelta

from . import base, config
from .fabrique import norm

TAILLE_LOT = 10
VERSION = "lecture à l'aveugle v1"   # change si la règle de comptage change (comme methode.VERSION)
ETIQUETTE = "Panel de volontaires. Ce n'est pas un sondage."
FENETRE_LOTS = 7                      # jours : les lots proposés au panel (public/aveugle/lots.json)
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
        medias = db.execute("SELECT id, nom FROM medias WHERE actif = 1").fetchall()
        # Dans un ordre tiré au hasard : sinon les numéros des lots d'un jour suivraient l'ordre des médias, et le
        # numéro d'un lot dirait son média.
        secrets.SystemRandom().shuffle(medias)
        for m in medias:
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


def compter_agreges(par, minimum):
    """La même règle que compter, sur des sommes : par = {g: [n, somme], c: [...], d: [...]}, ce que l'urne publie.
    Rend exactement ce que compter rendrait sur les avis dont viennent ces sommes."""
    par = {k: (list(par.get(k) or [0, 0]) + [0, 0])[:2] for k in "gcd"}
    moyennes = {k: s / n for k, (n, s) in par.items() if n}
    if not moyennes:
        return None
    return {"note": round(sum(moyennes.values()) / len(moyennes), 2),
            "par_bord": {k: round(v, 2) for k, v in moyennes.items()},
            "effectifs": {k: n for k, (n, _) in par.items()},
            "statut": "publiable" if all(n >= minimum for n, _ in par.values()) else "indicatif"}


def _entiers(v):
    """[n, somme] : deux entiers, n positif."""
    return isinstance(v, list) and len(v) == 2 and all(isinstance(e, int) and not isinstance(e, bool) for e in v) and v[0] >= 0


def publies(dossier=None):
    """Les agrégats publiés par l'urne, rangés par nom de fichier : {« historique » ou « 2026T3 »: contenu}. Un
    fichier illisible, ou qui n'est pas une lecture à l'aveugle, est sauté."""
    dossier = dossier or os.path.join(config.public(), "panel", "aveugle")
    out = {}
    for chemin in sorted(glob.glob(os.path.join(dossier, "*.json"))):
        try:
            with open(chemin, encoding="utf-8") as f:
                x = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(x, dict) and x.get("mesure") == "aveugle" and isinstance(x.get("lots"), dict):
            out[os.path.basename(chemin)[:-5]] = x
    return out


def resultats(db, dossier=None):
    """La lecture à l'aveugle du panel, par média : une mesure à part, versionnée. Rend None s'il n'y a rien.

    Pour chaque fichier publié par l'urne (l'historique et les trimestres clos), chaque lot est rapporté à son média
    par lots_aveugle (base publique) ; les sommes s'additionnent par média et par bord déclaré ; puis la règle de
    compter (moyenne par bord, moyenne des bords ; « publiable » si chaque bord atteint COMPARATEUR_MIN_PAR_BORD
    avis). Aucune table de votants n'est lue. Aucune formule ne mêle cette note au score FrIdéo, et aucune bande
    n'en est déduite."""
    fichiers = publies(dossier)
    if not fichiers:
        return None
    media_du_lot = {r["id"]: r["nom"] for r in db.execute(
        "SELECT l.id, m.nom FROM lots_aveugle l JOIN medias m ON m.id = l.media_id")}
    sommes, inclus = {}, []
    for nom, x in fichiers.items():
        compte = False
        for lot, par in x["lots"].items():
            media = media_du_lot.get(int(lot)) if str(lot).isdigit() else None
            if media is None or not isinstance(par, dict):
                continue
            cumul = sommes.setdefault(media, {k: [0, 0] for k in "gcd"})
            for k in "gcd":
                if _entiers(par.get(k)):
                    cumul[k][0] += par[k][0]
                    cumul[k][1] += par[k][1]
                    compte = compte or par[k][0] > 0
        if compte:
            inclus.append(str(x.get("trimestre") or nom))
    minimum = config.min_par_bord()
    medias = {}
    for media, par in sorted(sommes.items()):
        c = compter_agreges(par, minimum)
        if c:
            medias[media] = c
    if not medias:
        return None
    inclus.sort(key=lambda t: (t != "historique", t))   # l'historique d'abord, puis les trimestres dans l'ordre
    return {"v": 1, "mesure": "aveugle", "version": VERSION, "etiquette": ETIQUETTE, "trimestres": inclus,
            "min_par_bord": minimum, "echelle": [-2, 2], "medias": medias}


def lots_publics(db, jour=None):
    """Les lots des sept derniers jours, pour public/aveugle/lots.json : {lots: [{id, titres}]}, sans le média. Les
    mêmes octets pour tous : aucune heure, aucun paramètre, les lots rangés par numéro."""
    jour = jour or base.iso()[:10]
    debut = (date.fromisoformat(jour) - timedelta(days=FENETRE_LOTS - 1)).isoformat()
    return {"lots": [{"id": r["id"], "titres": json.loads(r["titres"])} for r in db.execute(
        "SELECT id, titres FROM lots_aveugle WHERE jour >= ? AND jour <= ? ORDER BY id", (debut, jour))]}
