"""La fabrique : récolte des flux, regroupement en sujets (Haiku), analyse des cadrages (Sonnet).

Chaque étape reprend où elle s'était arrêtée : un titre déjà récolté ou déjà trié n'est pas retraité,
un sujet n'est réanalysé que si ses titres ont changé. Aucune étape ne dépend du nombre de lecteurs.
"""
import hashlib, html, json, math, re, subprocess, unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from . import base, config
from .llm import demander

# ---------------------------------------------------------------- récolte

# Identité déclarée : un lecteur de flux RSS, pas un navigateur.
UA = "Mozilla/5.0 (compatible; ComparateurRSS/0.1; lecteur de flux RSS personnel) AppleWebKit/605.1.15 (KHTML, like Gecko)"
ACCEPT = "Accept: application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5"
MAX_PAR_MEDIA = 60


def telecharger(url):
    r = subprocess.run(["curl", "-sL", "-m", "20", "-A", UA, "-H", ACCEPT, url], capture_output=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"curl {r.returncode}")
    return r.stdout


def lire_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    # Toujours en temps universel : les dates sont gardées et comparées comme du texte ISO,
    # ce qui n'est juste que si elles portent toutes le même décalage.
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def propre(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def _items_tolerant(xml_bytes):
    """Flux mal formé : découpe des <item> à la main."""
    txt = xml_bytes.decode("utf-8", "replace")
    out = []
    for bloc in re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", txt, re.S):
        def champ(*noms):
            for n in noms:
                m = re.search(r"<%s\b[^>]*>(.*?)</%s>" % (n, n), bloc, re.S)
                if m:
                    return re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip())
            return ""
        lien = champ("link") or (re.search(r'<link[^>]*href="([^"]+)"', bloc) or [None, ""])[1]
        out.append({"titre": propre(champ("title")), "date": lire_date(champ("pubDate", "published", "updated", "dc:date")),
                    "lien": html.unescape(lien).strip()})
    return out


def items(xml_bytes):
    """Rend [{titre, date, lien}] d'un flux RSS ou Atom."""
    try:
        racine = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return _items_tolerant(xml_bytes)
    out = []
    for it in racine.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue

        def champ(*noms):
            # « x or y » serait faux ici : un élément XML sans enfant vaut False.
            for n in noms:
                for c in it:
                    if c.tag.split("}")[-1] == n:
                        return c
            return None

        t, date, lien = champ("title"), champ("pubDate", "published", "updated", "date"), champ("link")
        href = (lien.get("href") or (lien.text or "")) if lien is not None else ""
        out.append({"titre": propre(t.text if t is not None else ""),
                    "date": lire_date(date.text if date is not None else None), "lien": href.strip()})
    return out


# ---------------------------------------------------------------- rubriques

# La rubrique se lit dans l'adresse de l'article, sans modèle : un segment du chemin (/sport/, /culture/) ou un
# sous-domaine (sport24.lefigaro.fr). Seuls des segments entiers comptent, jamais un mot du titre.
RUBRIQUES = {
    "sport": """sport sports sport24 rmcsport football foot rugby tennis cyclisme basket handball athletisme
                formule-1 f1 jeux-olympiques jo""",
    "culture": """culture cultures loisirs culture-loisirs people cinema musique musiques tele television
                  televisions-radio tv tvmag series livres litterature arts arts-stars spectacles theatre
                  divertissement pop-culture jeux-video bd""",
    "politique": "politique elections",
    "international": "international monde",
    "economie": "economie eco entreprises bourse",
    "societe": "societe",
    "faits-divers": "faits-divers justice police-justice",
    "sciences": "sciences science sante",
    "environnement": "environnement planete climat",
    "opinions": "opinions idees debats tribunes editos chroniques",
}
_SEGMENTS = {seg: nom for nom, segs in RUBRIQUES.items() for seg in segs.split()}


def rubrique(lien):
    """Rubrique d'un article d'après son adresse : 'sport', 'culture'... ou '' si rien ne se reconnaît.
    Le premier segment reconnu l'emporte ; le dernier segment du chemin (le titre de l'article) n'est pas lu."""
    try:
        u = urlsplit(lien or "")
    except ValueError:
        return ""
    chemin = [x for x in u.path.split("/") if x]
    for seg in (u.hostname or "").split(".")[:-2] + chemin[:-1]:
        nom = _SEGMENTS.get(norm(seg).replace("_", "-"))
        if nom:
            return nom
    return ""


def hors_ecartees(table="a"):
    """Condition SQL (et ses paramètres) qui laisse de côté les articles des rubriques écartées."""
    r = config.rubriques_ecartees()
    if not r:
        return "1 = 1", ()
    return f"COALESCE({table}.rubrique, '') NOT IN ({', '.join('?' * len(r))})", tuple(r)


def recolter(db):
    """Lit les flux des médias actifs et range les titres nouveaux. Rend le détail par média."""
    borne, quand, detail = base.depuis(), base.iso(), {}
    with base.Etape(db, "recolte") as etape:
        for m in db.execute("SELECT id, nom, flux FROM medias WHERE actif = 1 ORDER BY id").fetchall():
            etat = "aucun flux lisible"
            for url in json.loads(m["flux"]):
                try:
                    lus = items(telecharger(url))
                    if not lus:
                        raise RuntimeError("0 article")
                except Exception as e:  # un flux en panne ne doit pas arrêter la récolte
                    etat = f"{type(e).__name__}: {e}"[:80]
                    continue
                for a in lus:   # un flux qui annonce une date dans le futur se trompe : on date à la récolte
                    if a["date"] is not None and base.iso(a["date"]) > quand:
                        a["date"] = None
                gardes = [a for a in lus if a["titre"] and (a["date"] is None or base.iso(a["date"]) >= borne)]
                neufs = 0
                for a in gardes[:MAX_PAR_MEDIA]:
                    cur = db.execute(
                        "INSERT OR IGNORE INTO articles (cle, media_id, titre, lien, date, recolte, rubrique) VALUES (?,?,?,?,?,?,?)",
                        (base.cle_article(m["nom"], a["titre"], a["lien"]), m["id"], a["titre"], a["lien"],
                         base.iso(a["date"]) if a["date"] else None, quand, rubrique(a["lien"])))
                    neufs += cur.rowcount
                etat = f"{len(gardes)} dans la fenêtre, {neufs} nouveaux"
                break
            detail[m["nom"]] = etat
        db.commit()
        etape.detail = detail
    return detail


def importer_json(db, chemin):
    """Charge une récolte au format du test de concept (articles.json). Sert aux essais."""
    data = json.load(open(chemin, encoding="utf-8"))
    ids = {r["nom"]: r["id"] for r in db.execute("SELECT id, nom FROM medias")}
    n = 0
    for a in data["articles"]:
        if a["media"] not in ids:
            continue
        d = lire_date(a.get("date"))
        cur = db.execute("INSERT OR IGNORE INTO articles (cle, media_id, titre, lien, date, recolte, rubrique) VALUES (?,?,?,?,?,?,?)",
                         (base.cle_article(a["media"], a["title"], a["link"]), ids[a["media"]], a["title"], a["link"],
                          base.iso(d) if d else None, data["recolte"][:19] + "+00:00", rubrique(a["link"])))
        n += cur.rowcount
    db.commit()
    return n


# ---------------------------------------------------------------- regroupement

LOT_A, LOT_B, SEUIL, PARALLELES = 20, 25, 0.30, 4
STOP = set("""le la les un une des du de d l au aux et ou en dans sur pour par avec sans sous ce cette ces son sa ses
leur leurs qui que quoi dont est sont a ont ete etre fait faire plus moins pas ne se s y il elle ils elles on nous vous
je tu apres avant contre entre comme mais selon vers chez lors quand tout tous toute toutes tres bien aussi encore deja
ans an deux trois va vont peut veut faut comment pourquoi voici face fin debut nouveau nouvelle nouvelles nouveaux
direct video videos info infos france francais francaise paris jour jours monde pays the and of to in for qu c n j m
ca cela etait avoir cet quel quelle quels depuis pendant jusqu notre nos votre vos trop peu meme autres autre dit
annonce premier premiere grand grande retenir savoir samedi dimanche vendredi novembre 2026 sait""".split())


def norm(s):
    s = unicodedata.normalize("NFD", s.lower().replace("’", "'"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def mots(titre):
    out = set()
    for w in re.findall(r"[a-z0-9]+", norm(titre)):
        if len(w) < 3 or w in STOP:
            continue
        out.add(w[:-1] if len(w) > 5 and w.endswith("s") else w)
    return out


def paquets(arts):
    """Présélection sans modèle : paquets de titres proches par mots rares partagés.

    C'est ce qui garde le coût sous contrôle quand le nombre de médias monte : seuls les titres qui
    ont un voisin passent par la première passe du modèle."""
    df = Counter(w for a in arts for w in a["tok"])
    idf = {w: math.log(len(arts) / c) for w, c in df.items()}

    def sim(x, y):
        inter = x & y
        if len(inter) < 2:
            return 0.0
        den = min(sum(idf[w] for w in x), sum(idf[w] for w in y))
        return sum(idf[w] for w in inter) / den if den else 0.0

    groupes = []
    for a in arts:
        best, best_s = None, 0.0
        for g in groupes:
            sc = max(sim(a["tok"], b["tok"]) for b in g)
            if sc > best_s:
                best, best_s = g, sc
        if best is not None and best_s >= SEUIL:
            best.append(a)
        else:
            groupes.append([a])
    return groupes


CONSIGNE_A = """Range des titres de presse dans des sujets. Un sujet = un même événement ou une même affaire
(« Candidature de Teddy Riner à la présidentielle »), jamais un thème général (« politique », « sport »).

Sujets déjà ouverts :
{sujets}

Titres à ranger :
{titres}

Pour chaque numéro de titre, réponds soit l'identifiant d'un sujet ouvert (ex. "S3"), soit "N: <libellé court>" pour
ouvrir un sujet. Si plusieurs titres du lot ouvrent le même nouveau sujet, donne-leur exactement le même libellé.
Réponds par un seul objet JSON : {{"1": "S3", "2": "N: ...", ...}} avec tous les numéros."""

CONSIGNE_FUSION = """Voici une liste de sujets d'actualité, chacun avec un identifiant. Certains désignent le même
événement ou la même affaire sous deux libellés. Rends les groupes à fusionner, et seulement ceux-là.

{sujets}

Réponds par un seul objet JSON : {{"fusions": [["S3", "S17"], ["S5", "S9", "S21"]]}} (liste vide si rien à fusionner).
Ne fusionne pas deux événements distincts d'un même thème."""

CONSIGNE_B = """Voici des sujets d'actualité déjà ouverts et des titres de presse isolés. Pour chaque titre, dis s'il
traite précisément de l'un de ces sujets (le même événement, la même affaire), sinon 0.

Sujets :
{sujets}

Titres :
{titres}

Réponds par un seul objet JSON : {{"1": "S3", "2": 0, ...}} avec tous les numéros."""


def _sujets_ouverts(db):
    """Sujets ayant au moins un titre dans la fenêtre : {id: libellé}, dans l'ordre de création."""
    garde, rubs = hors_ecartees("a")
    return {r["id"]: r["libelle"] for r in db.execute(
        f"""SELECT DISTINCT s.id, s.libelle FROM sujets s JOIN sujet_articles sa ON sa.sujet_id = s.id
            JOIN articles a ON a.id = sa.article_id WHERE COALESCE(a.date, a.recolte) >= ? AND {garde}
            ORDER BY s.id""", (base.depuis(),) + rubs)}


def _liste(sujets):
    return "\n".join(f"S{k}: {v}" for k, v in sujets.items())


def _medias_par_sujet(db):
    garde, rubs = hors_ecartees("a")
    return {r["sujet_id"]: r["n"] for r in db.execute(
        f"""SELECT sa.sujet_id, COUNT(DISTINCT a.media_id) AS n FROM sujet_articles sa
            JOIN articles a ON a.id = sa.article_id WHERE {garde} GROUP BY sa.sujet_id""", rubs)}


def regrouper(db):
    """Range les titres pas encore triés dans des sujets. Le modèle ne voit jamais le nom des médias.
    Les articles des rubriques écartées (sport, culture) ne sont pas proposés : ils restent en base, non triés."""
    with base.Etape(db, "regroupement") as etape:
        garde, rubs = hors_ecartees("articles")
        arts = [dict(r) for r in db.execute(
            f"SELECT id, titre FROM articles WHERE trie = 0 AND COALESCE(date, recolte) >= ? AND {garde} ORDER BY id",
            (base.depuis(),) + rubs)]
        if not arts:
            etape.detail = {"nouveaux": 0}
            return etape.detail
        for a in arts:
            a["tok"] = mots(a["titre"])
        groupes = paquets(arts)
        noyau = [a for g in sorted(groupes, key=len, reverse=True) if len(g) >= 2 for a in g]
        seuls = [g[0] for g in groupes if len(g) == 1]
        sujets, crees = _sujets_ouverts(db), 0

        def rattacher(sujet_id, article_id):
            db.execute("INSERT OR IGNORE INTO sujet_articles (sujet_id, article_id) VALUES (?, ?)", (sujet_id, article_id))

        # Passe A, en série : la liste des sujets grandit d'un lot à l'autre.
        for debut in range(0, len(noyau), LOT_A):
            lot = noyau[debut:debut + LOT_A]
            titres = "\n".join(f"{n}. {a['titre']}" for n, a in enumerate(lot, 1))
            rep = demander(CONSIGNE_A.format(sujets=_liste(sujets) or "(aucun pour l'instant)", titres=titres),
                           "tri", "regroupement A")
            # Un libellé déjà ouvert (dans ce lot ou un précédent) ne rouvre pas un second sujet.
            nouveaux = {norm(v): k for k, v in sujets.items()}
            for n, a in enumerate(lot, 1):
                v = str(rep.get(str(n), "")).strip()
                if re.fullmatch(r"S\d+", v) and int(v[1:]) in sujets:
                    rattacher(int(v[1:]), a["id"])
                elif v.upper().startswith("N:") and v[2:].strip():
                    lib = v[2:].strip()[:200]
                    k = nouveaux.get(norm(lib))
                    if k is None:
                        k = db.execute("INSERT INTO sujets (libelle, cree) VALUES (?, ?)", (lib, base.iso())).lastrowid
                        nouveaux[norm(lib)] = k
                        sujets[k] = lib
                        crees += 1
                    rattacher(k, a["id"])
            db.commit()

        # Fusion des doublons de libellé (1 appel), seulement si des sujets viennent d'être ouverts.
        fusions = 0
        if crees and len(sujets) > 1:
            rep = demander(CONSIGNE_FUSION.format(sujets=_liste(sujets)), "tri", "regroupement fusion")
            for groupe in rep.get("fusions", []):
                ids = [int(k[1:]) for k in groupe if re.fullmatch(r"S\d+", str(k)) and int(k[1:]) in sujets]
                for k in ids[1:]:
                    db.execute("UPDATE sujet_articles SET sujet_id = ? WHERE sujet_id = ?", (ids[0], k))
                    db.execute("DELETE FROM analyses WHERE sujet_id = ?", (k,))
                    db.execute("DELETE FROM sujets WHERE id = ?", (k,))
                    del sujets[k]
                    fusions += 1
            db.commit()

        # Passe B, en parallèle : les isolés sont proposés aux sujets déjà couverts par 2 médias ou plus.
        nb = _medias_par_sujet(db)
        retenus = {k: v for k, v in sujets.items() if nb.get(k, 0) >= 2}
        rattaches = 0
        if retenus and seuls:
            liste = _liste(retenus)
            lots = [seuls[d:d + LOT_B] for d in range(0, len(seuls), LOT_B)]

            def passe_b(lot):
                titres = "\n".join(f"{n}. {a['titre']}" for n, a in enumerate(lot, 1))
                return lot, demander(CONSIGNE_B.format(sujets=liste, titres=titres), "tri", "regroupement B")

            with ThreadPoolExecutor(PARALLELES) as pool:
                for lot, rep in pool.map(passe_b, lots):
                    for n, a in enumerate(lot, 1):
                        v = str(rep.get(str(n), "0")).strip()
                        if re.fullmatch(r"S\d+", v) and int(v[1:]) in retenus:
                            rattacher(int(v[1:]), a["id"])
                            rattaches += 1
        db.executemany("UPDATE articles SET trie = 1 WHERE id = ?", [(a["id"],) for a in arts])
        db.commit()
        etape.detail = {"nouveaux": len(arts), "en_paquets": len(noyau), "isoles": len(seuls),
                        "sujets_ouverts": crees, "fusions": fusions, "isoles_rattaches": rattaches}
        return etape.detail


# ---------------------------------------------------------------- analyse

MIN_MEDIAS, MAX_SUJETS, PARALLELES_ANALYSE = 4, 20, 3
NOM_COTE = {"g": "GAUCHE", "c": "CENTRE", "d": "DROITE"}

CONSIGNE_ANALYSE = """Tu compares la façon dont des médias français, classés par bord (classement fourni, à ne pas discuter),
titrent sur un même sujet. Tu n'as que les titres, pas les articles : ne prétends rien savoir de plus. Tu décris le
traitement, jamais le fond, sans avis personnel.

Sujet proposé : {libelle}

{titres}

Réponds par un seul objet JSON :
{{
 "titre": "titre neutre du sujet, 12 mots au plus",
 "fait": "le fait commun en une phrase neutre",
 "g": "l'angle des médias de gauche en une ou deux phrases (ce qui est mis en avant) ; « Aucun titre. » s'il n'y en a pas",
 "c": "idem pour le centre",
 "d": "idem pour la droite",
 "mots": [{{"terme": "mot ou expression repris tel quel d'un titre", "qui": "médias qui l'emploient"}}],
 "ecart": 0,
 "hors_sujet": []
}}
Règles : « ecart » va de 0 (même traitement partout) à 5 (on dirait deux histoires différentes). « mots » : 4 entrées au
plus, seulement des différences de vocabulaire parlantes entre bords, copiées à la lettre. Toute citation entre « » doit
être copiée à la lettre d'un titre. « hors_sujet » : numéros des titres qui ne relèvent pas de ce sujet."""


def norm_strict(s):
    return re.sub(r"[^a-z0-9]+", " ", norm(s)).strip()


def verifier_citations(texte, corpus):
    """Garde-fou : retire les guillemets autour de toute citation absente des titres. Rend (texte, retirées)."""
    retirees = 0

    def remplace(m):
        nonlocal retirees
        if norm_strict(m.group(1)) and norm_strict(m.group(1)) in corpus:
            return m.group(0)
        retirees += 1
        return m.group(1).strip()

    return re.sub(r"«\s*([^»]{1,120}?)\s*»", remplace, texte), retirees


def empreinte(ids):
    return hashlib.sha256(",".join(str(i) for i in sorted(ids)).encode()).hexdigest()[:16]


def sujets_du_jour(db):
    """Sujets de la fenêtre avec leurs titres : [{id, libelle, articles:[{id, titre, lien, media, cote}]}].
    Un article d'une rubrique écartée n'est pas compté, même s'il a été rangé sous un sujet auparavant."""
    notes = base.scores(db)
    garde, rubs = hors_ecartees("a")
    out = {}
    for r in db.execute(
            f"""SELECT s.id AS sid, s.libelle, a.id, a.titre, a.lien, a.media_id, m.nom FROM sujets s
                JOIN sujet_articles sa ON sa.sujet_id = s.id JOIN articles a ON a.id = sa.article_id
                JOIN medias m ON m.id = a.media_id WHERE COALESCE(a.date, a.recolte) >= ? AND {garde}
                ORDER BY s.id, a.id""", (base.depuis(),) + rubs):
        s = out.setdefault(r["sid"], {"id": r["sid"], "libelle": r["libelle"], "articles": []})
        s["articles"].append({"id": r["id"], "titre": r["titre"], "lien": r["lien"], "media": r["nom"],
                              # un média non classé n'a pas de côté : ses titres comptent dans la couverture seulement
                              "cote": base.COTE[base.bord(notes[r["media_id"]])] if r["media_id"] in notes else None})
    sujets = list(out.values())
    for s in sujets:
        s["medias"] = len({a["media"] for a in s["articles"]})
    sujets.sort(key=lambda s: (s["medias"], len(s["articles"])), reverse=True)
    return sujets


def analyser(db):
    """Analyse le cadrage des sujets assez couverts ; ne refait pas un sujet dont les titres n'ont pas changé."""
    with base.Etape(db, "analyse") as etape:
        candidats = [s for s in sujets_du_jour(db)
                     if s["medias"] >= MIN_MEDIAS and len({a["cote"] for a in s["articles"]} - {None}) >= 2][:MAX_SUJETS]
        faites = {r["sujet_id"]: r["empreinte"] for r in db.execute("SELECT sujet_id, empreinte FROM analyses")}
        a_faire = [s for s in candidats if faites.get(s["id"]) != empreinte(a["id"] for a in s["articles"])]

        def une(s):
            lignes, numeros, n = [], {}, 0
            for cote in "gcd":
                lignes.append(f"--- {NOM_COTE[cote]} ---")
                for a in s["articles"]:
                    if a["cote"] == cote:
                        n += 1
                        numeros[n] = a
                        lignes.append(f"{n}. {a['media']} : {a['titre']}")
                if lignes[-1].startswith("---"):
                    lignes.append("(aucun titre)")
            rep = demander(CONSIGNE_ANALYSE.format(libelle=s["libelle"], titres="\n".join(lignes)), "analyse", "analyse")
            return s, numeros, rep

        retirees = ecartes = 0
        with ThreadPoolExecutor(PARALLELES_ANALYSE) as pool:
            for s, numeros, rep in pool.map(une, a_faire):
                hors = {numeros[int(x)]["id"] for x in rep.get("hors_sujet", []) if str(x).isdigit() and int(x) in numeros}
                gardes = [a for a in s["articles"] if a["id"] not in hors]
                if hors and len(hors) < len(s["articles"]):
                    db.executemany("DELETE FROM sujet_articles WHERE article_id = ?", [(i,) for i in hors])
                    ecartes += len(hors)
                else:
                    gardes = s["articles"]
                corpus = " | ".join(norm_strict(a["titre"]) for a in gardes)
                textes = {}
                for k in ("fait", "g", "c", "d"):
                    textes[k], r = verifier_citations(str(rep.get(k, "")), corpus)
                    retirees += r
                vocabulaire = []
                for m in (rep.get("mots") or [])[:4]:
                    terme = str(m.get("terme", "")).strip(" «»\"")
                    if norm_strict(terme) and norm_strict(terme) in corpus:
                        vocabulaire.append({"terme": f"« {terme} »", "qui": str(m.get("qui", ""))[:200]})
                    else:
                        retirees += 1
                try:
                    ecart = max(0, min(5, int(rep.get("ecart"))))
                except (TypeError, ValueError):
                    ecart = None
                db.execute(
                    """INSERT INTO analyses (sujet_id, titre, fait, g, c, d, mots, ecart, empreinte, modele, cree)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(sujet_id) DO UPDATE SET titre=excluded.titre, fait=excluded.fait, g=excluded.g,
                         c=excluded.c, d=excluded.d, mots=excluded.mots, ecart=excluded.ecart,
                         empreinte=excluded.empreinte, modele=excluded.modele, cree=excluded.cree""",
                    (s["id"], str(rep.get("titre") or s["libelle"])[:200], textes["fait"], textes["g"], textes["c"],
                     textes["d"], json.dumps(vocabulaire, ensure_ascii=False), ecart,
                     empreinte(a["id"] for a in gardes), "sonnet", base.iso()))
        db.commit()
        etape.detail = {"sujets_eligibles": len(candidats), "analyses_faites": len(a_faire),
                        "titres_ecartes": ecartes, "citations_retirees": retirees}
        return etape.detail
