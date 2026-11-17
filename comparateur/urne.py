"""L'urne : un fichier SQLite par questionnaire (urnes/<questionnaire>.db), servi sur urne.<domaine>. Elle sait ce qui
est pensé, jamais par qui (premier cadrage, section 5).

Elle accepte un bulletin, sa signature, un bord et des réponses, sans session, sans cookie, sans en-tête d'identité.
Elle vérifie la signature avec la clé publique du questionnaire, refuse un bulletin déjà vu, et écrit une ligne sous
l'empreinte du bulletin. Aucune colonne de date, aucun rang : les tables sont WITHOUT ROWID, rangées par empreinte.
Le reçu, c'est le bulletin lui-même : celui qui le garde peut faire effacer sa ligne, personne d'autre.

La carte de votant (le vote à l'aveugle) suit la même règle : une carte signée à l'aveugle par trimestre, et les avis
rangés sous l'empreinte de la carte (un pseudonyme qui ne dure qu'un trimestre), dans urnes/aveugle-<trimestre>.db.

L'urne ne lit que ses fichiers et les clés publiques (public/panel/cles/<questionnaire>.json) : elle est déjà
déplaçable sur une autre machine. Elle n'importe ni le compte, ni la base publique, et n'écrit aucun journal qui
nomme quelqu'un : ni adresse IP, ni empreinte.
"""
import hashlib, json, os, re, sqlite3

from . import config, signature

ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,40}$")
TRIMESTRE = re.compile(r"^\d{4}T[1-4]$")
QUESTIONS_MAX = 10
PROFIL_MAX = 2          # deux questions de profil au plus (premier cadrage, règle 13)
PROFIL_MODALITES = 5    # une question de profil a cinq modalités au plus : plus fine, elle désignerait quelqu'un
CHOIX = (2, 7)          # de deux à sept réponses possibles par question
SEUIL_RIEN = 5          # sous 5 réponses dans un bord : rien n'est montré (décision D8)
SEUIL_PUBLIABLE = 10    # 10 réponses par bord pour un résultat sans réserve
ETIQUETTE = "Panel de volontaires. Ce n'est pas un sondage."

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS reponses (empreinte TEXT PRIMARY KEY, bord INTEGER NOT NULL, reponses TEXT NOT NULL) WITHOUT ROWID;
"""
SCHEMA_AVEUGLE = """
CREATE TABLE IF NOT EXISTS meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS avis (carte TEXT NOT NULL, lot INTEGER NOT NULL, note INTEGER NOT NULL, bord INTEGER NOT NULL,
  PRIMARY KEY (carte, lot)) WITHOUT ROWID;
"""


class Refus(Exception):
    """Un dépôt refusé. code : le statut HTTP (400, 403, 404, 409, 410)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def dossier():
    d = config.urnes()
    os.makedirs(d, exist_ok=True)
    return d


def chemin(questionnaire):
    if not ID.match(questionnaire or ""):
        raise Refus(404, "questionnaire inconnu")
    return os.path.join(dossier(), questionnaire + ".db")


def _ouvrir(questionnaire, schema=SCHEMA, creer=False):
    c = chemin(questionnaire)
    if not creer and not os.path.isfile(c):
        raise Refus(404, "questionnaire inconnu")
    db = sqlite3.connect(c, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(schema)
    return db


def _meta(db):
    return {r["cle"]: r["valeur"] for r in db.execute("SELECT cle, valeur FROM meta")}


def cle_publique(questionnaire):
    """La clé publique d'un questionnaire ou d'une carte, lue dans le tiroir public. Rend {n, e} (entiers)."""
    if not ID.match(questionnaire or ""):
        raise Refus(404, "questionnaire inconnu")
    try:
        with open(os.path.join(config.public(), "panel", "cles", questionnaire + ".json"), encoding="utf-8") as f:
            return signature.de_hex(json.load(f))
    except (OSError, ValueError, KeyError, TypeError):
        raise Refus(404, "questionnaire inconnu")


def empreinte(octets):
    return hashlib.sha256(octets).hexdigest()


def _octets(x, nom, maxi=1024):
    if not isinstance(x, str) or not re.fullmatch(r"(?:[0-9a-f]{2}){1,%d}" % maxi, x):
        raise Refus(400, f"{nom} invalide")
    return bytes.fromhex(x)


def _bulletin_valide(questionnaire, bulletin, sig, pk):
    """Le bulletin (le message préparé, RFC 9474 : 32 octets au hasard, puis le message) doit nommer ce
    questionnaire, et sa signature doit être bonne. Un bulletin signé pour un autre questionnaire est refusé."""
    message = bulletin[signature.LONGUEUR_PREFIXE:]
    if not message.startswith(questionnaire.encode() + b"\x00") or len(message) != len(questionnaire) + 1 + 32:
        raise Refus(403, "bulletin refusé")
    if not signature.verifier(pk, bulletin, sig):
        raise Refus(403, "bulletin refusé")


def _bord(bord):
    if not isinstance(bord, int) or isinstance(bord, bool) or not -2 <= bord <= 2:
        raise Refus(400, "bord attendu : entier de -2 à 2")
    return bord


# ---- les questionnaires

def verifier_questionnaire(q):
    """Un questionnaire se refuse lui-même (premier cadrage, règle 13) : pas de texte libre, deux questions de profil
    au plus, cinq modalités au plus pour une question de profil. Rend la liste des fautes ; vide s'il est admis."""
    fautes = []
    if not isinstance(q, dict) or not ID.match(str(q.get("id", ""))):
        return ["identifiant attendu : minuscules, chiffres et tirets"]
    if not isinstance(q.get("titre"), str) or not q["titre"].strip():
        fautes.append("titre manquant")
    questions = q.get("questions")
    if not isinstance(questions, list) or not 1 <= len(questions) <= QUESTIONS_MAX:
        return fautes + [f"de 1 à {QUESTIONS_MAX} questions"]
    ids = set()
    for x in questions:
        if not isinstance(x, dict) or not re.fullmatch(r"[a-z0-9-]{1,20}", str(x.get("id", ""))) or x["id"] in ids:
            fautes.append("chaque question a un identifiant unique")
            continue
        ids.add(x["id"])
        if x.get("type", "choix") != "choix" or "texte_libre" in x:
            fautes.append(f"{x['id']} : pas de texte libre, seulement des choix")
        if not isinstance(x.get("texte"), str) or not x["texte"].strip():
            fautes.append(f"{x['id']} : intitulé manquant")
        choix = x.get("choix")
        if not isinstance(choix, list) or not CHOIX[0] <= len(choix) <= CHOIX[1] or not all(isinstance(c, str) and c.strip() for c in choix):
            fautes.append(f"{x['id']} : de {CHOIX[0]} à {CHOIX[1]} choix écrits")
        elif x.get("profil") and len(choix) > PROFIL_MODALITES:
            fautes.append(f"{x['id']} : une question de profil a {PROFIL_MODALITES} modalités au plus")
    if sum(1 for x in questions if isinstance(x, dict) and x.get("profil")) > PROFIL_MAX:
        fautes.append(f"{PROFIL_MAX} questions de profil au plus")
    return fautes


def creer(q, pk):
    """Crée l'urne d'un questionnaire déjà vérifié, avec sa clé publique. Refuse d'écraser une urne existante."""
    fautes = verifier_questionnaire(q)
    if fautes:
        raise ValueError("; ".join(fautes))
    if os.path.exists(chemin(q["id"])):
        raise ValueError("cette urne existe déjà")
    db = _ouvrir(q["id"], creer=True)
    try:
        db.executemany("INSERT INTO meta (cle, valeur) VALUES (?, ?)",
                       [("questionnaire", json.dumps(q, ensure_ascii=False, sort_keys=True)), ("etat", "ouvert"),
                        ("cle", json.dumps(signature.en_hex(pk), sort_keys=True))])
        db.commit()
    finally:
        db.close()


def _reponses_valides(q, reponses):
    if not isinstance(reponses, dict):
        raise Refus(400, "réponses attendues")
    questions = {x["id"]: x for x in q["questions"]}
    if set(reponses) != set(questions):
        raise Refus(400, "une réponse par question")
    for k, v in reponses.items():
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < len(questions[k]["choix"]):
            raise Refus(400, "réponse hors des choix")
    return json.dumps(reponses, sort_keys=True, separators=(",", ":"))


def deposer(questionnaire, bulletin, sig, bord, reponses):
    """Le dépôt. Rend l'empreinte du bulletin (le reçu, côté appareil, est le bulletin lui-même)."""
    db = _ouvrir(questionnaire)
    try:
        meta = _meta(db)
        if meta.get("etat") != "ouvert":
            raise Refus(410, "questionnaire clos")
        b, s = _octets(bulletin, "bulletin", 200), _octets(sig, "signature")
        _bulletin_valide(questionnaire, b, s, signature.de_hex(json.loads(meta["cle"])))
        texte = _reponses_valides(json.loads(meta["questionnaire"]), reponses)
        try:
            db.execute("INSERT INTO reponses (empreinte, bord, reponses) VALUES (?, ?, ?)", (empreinte(b), _bord(bord), texte))
            db.commit()
        except sqlite3.IntegrityError:
            raise Refus(409, "bulletin déjà déposé")
        return empreinte(b)
    finally:
        db.close()


def effacer(questionnaire, bulletin):
    """L'effacement par le reçu : seul celui qui garde le bulletin peut retrouver sa ligne. Rend True si une ligne
    est effacée. Après la clôture aussi : les résultats suivants ne la comptent plus."""
    b = _octets(bulletin, "bulletin", 200)
    db = _ouvrir(questionnaire)
    try:
        n = db.execute("DELETE FROM reponses WHERE empreinte = ?", (empreinte(b),)).rowcount
        db.commit()
        if n:
            db.execute("VACUUM")   # la page libérée ne garde pas la ligne
        return n > 0
    finally:
        db.close()


def groupe(bord):
    return "g" if bord < 0 else "d" if bord > 0 else "c"


def resultats(questionnaire):
    """Les résultats d'un questionnaire clos, par formule : pour chaque question et chaque bord déclaré (gauche,
    centre, droite), les réponses par choix. Un bord sous 5 réponses n'est pas montré ; entre 5 et 9, il est
    « indicatif ». Aucune ligne brute ne sort. Aucun modèle ne lit une réponse."""
    db = _ouvrir(questionnaire)
    try:
        meta = _meta(db)
        if meta.get("etat") != "clos":
            raise Refus(409, "les résultats ne se montrent qu'après la clôture")
        q = json.loads(meta["questionnaire"])
        lignes = [(r["bord"], json.loads(r["reponses"])) for r in db.execute("SELECT bord, reponses FROM reponses")]
    finally:
        db.close()
    effectifs = {g: sum(1 for b, _ in lignes if groupe(b) == g) for g in "gcd"}
    questions = []
    for x in q["questions"]:
        par = {}
        for g in "gcd":
            n = effectifs[g]
            if n < SEUIL_RIEN:
                par[g] = {"statut": "moins de 5"}
                continue
            nombres = [sum(1 for b, r in lignes if groupe(b) == g and r[x["id"]] == i) for i in range(len(x["choix"]))]
            par[g] = {"statut": "publiable" if n >= SEUIL_PUBLIABLE else "indicatif", "reponses": n, "par_choix": nombres}
        questions.append({"id": x["id"], "texte": x["texte"], "choix": x["choix"], "profil": bool(x.get("profil")), "par_bord": par})
    return {"v": 1, "mesure": "panel", "questionnaire": q["id"], "titre": q["titre"], "etiquette": ETIQUETTE,
            "delivres": int(meta.get("delivres", "0")), "recues": len(lignes),
            "effectifs": {g: (n if n >= SEUIL_RIEN else None) for g, n in effectifs.items()},
            "scellement": meta.get("scellement", ""), "questions": questions}


def fermer(questionnaire, delivres):
    """La clôture, côté urne : plus de dépôt, le nombre de bulletins délivrés inscrit, le fichier compacté, puis
    scellé (son empreinte publiée avec les résultats : chacun peut vérifier qu'il n'a pas bougé). Rend les résultats."""
    db = _ouvrir(questionnaire)
    try:
        if _meta(db).get("etat") != "ouvert":
            raise Refus(410, "questionnaire déjà clos")
        db.executemany("INSERT OR REPLACE INTO meta (cle, valeur) VALUES (?, ?)", [("etat", "clos"), ("delivres", str(int(delivres)))])
        db.commit()
        db.execute("VACUUM")
        lignes = sorted(f"{r['empreinte']}|{r['bord']}|{r['reponses']}" for r in db.execute("SELECT * FROM reponses"))
        db.execute("INSERT OR REPLACE INTO meta (cle, valeur) VALUES ('scellement', ?)",
                   (hashlib.sha256("\n".join(lignes).encode()).hexdigest(),))
        db.commit()
    finally:
        db.close()
    return resultats(questionnaire)


# ---- la carte de votant (le vote à l'aveugle)

def carte_id(trimestre):
    if not TRIMESTRE.match(trimestre or ""):
        raise Refus(404, "trimestre inconnu")
    return "carte-" + trimestre.lower()


def urne_aveugle(trimestre):
    return "aveugle-" + carte_id(trimestre)[6:]


def donner_avis(trimestre, carte, sig, lot, note, bord):
    """Un avis sur un lot, avec la carte de votant du trimestre. Un avis par carte et par lot. Rend True."""
    cid = carte_id(trimestre)
    c, s = _octets(carte, "carte", 200), _octets(sig, "signature")
    _bulletin_valide(cid, c, s, cle_publique(cid))
    if not isinstance(lot, int) or isinstance(lot, bool) or lot < 1:
        raise Refus(400, "lot invalide")
    if not isinstance(note, int) or isinstance(note, bool) or not -2 <= note <= 2:
        raise Refus(400, "note attendue : entier de -2 à 2")
    db = _ouvrir(urne_aveugle(trimestre), SCHEMA_AVEUGLE, creer=True)
    try:
        if _meta(db).get("etat") == "clos":
            raise Refus(410, "trimestre clos")
        try:
            db.execute("INSERT INTO avis (carte, lot, note, bord) VALUES (?, ?, ?, ?)", (empreinte(c), lot, note, _bord(bord)))
            db.commit()
        except sqlite3.IntegrityError:
            raise Refus(409, "lot déjà jugé")
        return True
    finally:
        db.close()


def lots_juges(trimestre, carte):
    """Les lots déjà jugés avec cette carte : l'appareil ne les repropose pas. La carte suffit, sans signature : ce
    n'est qu'une liste de numéros de lot, sous un pseudonyme que seul son porteur connaît."""
    c = _octets(carte, "carte", 200)
    try:
        db = _ouvrir(urne_aveugle(trimestre), SCHEMA_AVEUGLE)
    except Refus:
        return []
    try:
        return [r["lot"] for r in db.execute("SELECT lot FROM avis WHERE carte = ? ORDER BY lot", (empreinte(c),))]
    finally:
        db.close()


HISTORIQUE = "aveugle-historique"   # les avis d'avant la carte de votant, versés une fois (migrations.verser_votes)


def ouvrir_aveugle(nom_urne, creer=False):
    """Une urne du vote à l'aveugle, ouverte telle quelle : pour la migration des avis d'avant la carte seulement."""
    if not nom_urne.startswith("aveugle-"):
        raise Refus(404, "urne inconnue")
    return _ouvrir(nom_urne, SCHEMA_AVEUGLE, creer=creer)


def agregats_aveugle(nom_urne):
    """Pour chaque lot : nombre d'avis et somme des notes, par bord déclaré. Ce que l'urne publie, après la clôture
    du trimestre : jamais un avis, jamais une carte. Rend {lot: {g: [n, somme], c: [...], d: [...]}}."""
    db = _ouvrir(nom_urne, SCHEMA_AVEUGLE)
    try:
        out = {}
        for r in db.execute("SELECT lot, bord, COUNT(*) AS n, SUM(note) AS s FROM avis GROUP BY lot, bord"):
            g = out.setdefault(str(r["lot"]), {"g": [0, 0], "c": [0, 0], "d": [0, 0]})[groupe(r["bord"])]
            g[0] += r["n"]
            g[1] += r["s"]
        return out
    finally:
        db.close()


def clore_trimestre(trimestre):
    """Clôt l'urne du vote à l'aveugle d'un trimestre et rend ses agrégats, à publier dans le tiroir public."""
    nom = urne_aveugle(trimestre)
    db = _ouvrir(nom, SCHEMA_AVEUGLE, creer=True)
    try:
        db.execute("INSERT OR REPLACE INTO meta (cle, valeur) VALUES ('etat', 'clos')")
        db.commit()
        db.execute("VACUUM")
    finally:
        db.close()
    return {"v": 1, "mesure": "aveugle", "trimestre": trimestre, "etiquette": ETIQUETTE, "lots": agregats_aveugle(nom)}
