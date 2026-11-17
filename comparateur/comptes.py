"""Le tiroir identité : identites.db, ouvert par le guichet seul. La fabrique ne l'ouvre jamais.

Il sait qui est la personne (une adresse), jamais ce qu'elle pense : ni bord, ni réponse, ni média suivi, ni
lecture. Les dates y sont arrondies : au jour pour une création, au mois pour la dernière visite. Seule exception,
écrite ici : un code de connexion porte son heure d'expiration à la seconde, et vit dix minutes.

  comptes      une adresse ; le compte vit tant qu'il a un abonnement ou une session ouverte
  abonnements  (compte, type, cible) : le registre d'abonnements.py dit ce qui est admis
  sessions     l'empreinte du jeton de session (le cookie __Host- de compte.<domaine>), jamais le jeton
  codes        l'empreinte salée du code à six chiffres envoyé par mail, cinq essais, dix minutes
  retraits     (questionnaire, compte) : qui a retiré son bulletin ; vidé à la clôture
  cles         la clé de chaque questionnaire ouvert, détruite à la clôture
  invitations_panel  l'empreinte des codes d'invitation au panel ; un code servi est effacé, sans trace de qui

Ce module n'importe que config, abonnements et signature (qui n'importe rien). Il ne lit ni comparateur.db ni une urne, et aucun ATTACH.
"""
import hashlib, hmac, os, re, secrets, sqlite3, time
from datetime import date, datetime, timedelta, timezone

from . import abonnements, config, signature

SCHEMA = """
CREATE TABLE IF NOT EXISTS comptes (
  id INTEGER PRIMARY KEY, adresse TEXT NOT NULL UNIQUE, cree_jour TEXT NOT NULL, vu_mois TEXT);
CREATE TABLE IF NOT EXISTS abonnements (
  id INTEGER PRIMARY KEY, compte INTEGER NOT NULL REFERENCES comptes(id) ON DELETE CASCADE,
  type TEXT NOT NULL, cible TEXT NOT NULL DEFAULT '', etat TEXT NOT NULL CHECK (etat IN ('attente', 'actif')),
  cree_jour TEXT NOT NULL, fin_jour TEXT, dernier_envoi TEXT, sortie TEXT NOT NULL UNIQUE,
  UNIQUE (compte, type, cible));
CREATE TABLE IF NOT EXISTS sessions (
  empreinte TEXT PRIMARY KEY, compte INTEGER NOT NULL REFERENCES comptes(id) ON DELETE CASCADE,
  cree_jour TEXT NOT NULL, fin_jour TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS codes (
  adresse TEXT PRIMARY KEY, sel TEXT NOT NULL, empreinte TEXT NOT NULL, expire INTEGER NOT NULL,
  essais INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS retraits (
  questionnaire TEXT NOT NULL, compte INTEGER NOT NULL REFERENCES comptes(id) ON DELETE CASCADE,
  PRIMARY KEY (questionnaire, compte)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS cles (
  questionnaire TEXT PRIMARY KEY, n TEXT NOT NULL, e INTEGER NOT NULL, d TEXT NOT NULL, ouverte_jour TEXT NOT NULL,
  delivres INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS invitations_panel (empreinte TEXT PRIMARY KEY, cree_jour TEXT NOT NULL) WITHOUT ROWID;
"""

# Une adresse simple : pas de « : » (un groupe d'adresses), pas de « =? » (un mot encodé), pas d'espace ni de
# guillemet. Ce que l'en-tête To affiche est exactement la boîte qui reçoit.
ADRESSE = re.compile(r"^[a-z0-9!#$%&'*+/^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/^_`{|}~-]+)*@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
CODE_SECONDES = 600          # un code vaut dix minutes
CODE_ESSAIS = 5              # puis il est effacé
SESSION_JOURS = 365          # douze mois : moins de codes à envoyer (quota de Brevo)
JOURS_SANS_CONFIRMATION = 7  # une inscription non confirmée est effacée


def chemin():
    return os.path.join(config.identites(), "identites.db")


def connexion():
    db = sqlite3.connect(chemin(), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    if "delivres" not in [c[1] for c in db.execute("PRAGMA table_info(cles)")]:   # une base de la phase 2
        db.execute("ALTER TABLE cles ADD COLUMN delivres INTEGER NOT NULL DEFAULT 0")
        db.commit()
    return db


def jour(d=None):
    return (d or datetime.now(timezone.utc)).date().isoformat()


def mois():
    return jour()[:7]


def empreinte(x):
    return hashlib.sha256(x.encode()).hexdigest()


def normaliser(adresse):
    """L'adresse en minuscules, ou None si elle n'a pas la forme d'une adresse."""
    a = str(adresse or "").strip().lower()
    return a if len(a) <= 254 and ADRESSE.match(a) else None


# ---- le compte

def compte_de(db, adresse, creer=False):
    a = normaliser(adresse)
    if not a:
        return None
    r = db.execute("SELECT id FROM comptes WHERE adresse = ?", (a,)).fetchone()
    if r:
        return r["id"]
    if not creer:
        return None
    try:
        return db.execute("INSERT INTO comptes (adresse, cree_jour) VALUES (?, ?)", (a, jour())).lastrowid
    except sqlite3.IntegrityError:   # deux créations simultanées
        return db.execute("SELECT id FROM comptes WHERE adresse = ?", (a,)).fetchone()["id"]


def lire(db, compte):
    """« Ce que ce site sait de vous » : exactement les lignes du compte, rien d'autre (règle 19). Les jetons de
    sortie et les empreintes de session ne sont pas montrés : ce sont des clés, pas des informations."""
    c = db.execute("SELECT adresse, cree_jour, vu_mois FROM comptes WHERE id = ?", (compte,)).fetchone()
    if not c:
        return None
    return {"compte": dict(c),
            "abonnements": [dict(r) for r in db.execute(
                """SELECT type, cible, etat, cree_jour, fin_jour, dernier_envoi FROM abonnements WHERE compte = ?
                   ORDER BY type, cible""", (compte,))],
            "sessions": [dict(r) for r in db.execute(
                "SELECT cree_jour, fin_jour FROM sessions WHERE compte = ? ORDER BY cree_jour", (compte,))]}


def supprimer(db, compte):
    """Efface le compte et tout ce qui en dépend (abonnements, sessions, retraits), et un code en cours pour son
    adresse."""
    r = db.execute("SELECT adresse FROM comptes WHERE id = ?", (compte,)).fetchone()
    if r:
        db.execute("DELETE FROM codes WHERE adresse = ?", (r["adresse"],))
    n = db.execute("DELETE FROM comptes WHERE id = ?", (compte,)).rowcount
    db.commit()
    return n > 0


def _effacer_si_vide(db, compte):
    """Un compte sans abonnement ni session ouverte n'a plus de raison d'être : l'adresse est effacée."""
    if not db.execute("SELECT 1 FROM abonnements WHERE compte = ? UNION SELECT 1 FROM sessions WHERE compte = ? AND fin_jour >= ?",
                      (compte, compte, jour())).fetchone():
        db.execute("DELETE FROM comptes WHERE id = ?", (compte,))


# ---- la connexion par code, sans mot de passe

def demander_code(db, adresse):
    """Rend (adresse, code) à envoyer, ou None si l'adresse n'en est pas une. Un nouveau code remplace l'ancien.
    Le code n'est gardé que sous une empreinte salée."""
    a = normaliser(adresse)
    if not a:
        return None
    code = f"{secrets.randbelow(10 ** 6):06d}"
    sel = secrets.token_hex(16)
    db.execute("""INSERT INTO codes (adresse, sel, empreinte, expire, essais) VALUES (?, ?, ?, ?, 0)
                  ON CONFLICT(adresse) DO UPDATE SET sel = excluded.sel, empreinte = excluded.empreinte,
                    expire = excluded.expire, essais = 0""",
               (a, sel, empreinte(sel + code), int(time.time()) + CODE_SECONDES))
    db.commit()
    return a, code


def verifier_code(db, adresse, code):
    """Rend l'identifiant du compte (créé à la première connexion) si le code est bon et frais, sinon None. Cinq
    essais par code, puis il est effacé. Chaque essai est compté avant la comparaison, d'un seul UPDATE : des
    requêtes simultanées ne passent pas la limite. Deviner six chiffres en cinq essais ne réussit qu'une fois sur
    200 000 ; le guichet borne en plus les codes par adresse (trois par heure) et les essais par adresse."""
    a = normaliser(adresse)
    code = str(code or "").strip()
    if not a or not re.fullmatch(r"\d{6}", code):
        return None
    if db.execute("UPDATE codes SET essais = essais + 1 WHERE adresse = ? AND essais < ? AND expire >= ?",
                  (a, CODE_ESSAIS, int(time.time()))).rowcount != 1:
        db.execute("DELETE FROM codes WHERE adresse = ? AND (essais >= ? OR expire < ?)", (a, CODE_ESSAIS, int(time.time())))
        db.commit()
        return None
    db.commit()
    r = db.execute("SELECT sel, empreinte FROM codes WHERE adresse = ?", (a,)).fetchone()
    if not r or not hmac.compare_digest(r["empreinte"], empreinte(r["sel"] + code)):
        return None
    # un code ne sert qu'une fois : seule la requête qui l'efface entre
    if db.execute("DELETE FROM codes WHERE adresse = ? AND empreinte = ?", (a, r["empreinte"])).rowcount != 1:
        db.rollback()
        return None
    compte = compte_de(db, a, creer=True)
    db.commit()
    return compte


def ouvrir_session(db, compte):
    """Rend le jeton de session, à poser dans le cookie. La base n'en garde que l'empreinte."""
    jeton = secrets.token_urlsafe(32)
    db.execute("INSERT INTO sessions (empreinte, compte, cree_jour, fin_jour) VALUES (?, ?, ?, ?)",
               (empreinte(jeton), compte, jour(), jour(datetime.now(timezone.utc) + timedelta(days=SESSION_JOURS))))
    db.execute("UPDATE comptes SET vu_mois = ? WHERE id = ?", (mois(), compte))
    db.commit()
    return jeton


def session(db, jeton):
    """L'identifiant du compte de cette session, ou None. Note le mois de la visite, pas le jour."""
    if not jeton or len(jeton) > 100:
        return None
    r = db.execute("SELECT compte FROM sessions WHERE empreinte = ? AND fin_jour >= ?", (empreinte(jeton), jour())).fetchone()
    if not r:
        return None
    db.execute("UPDATE comptes SET vu_mois = ? WHERE id = ? AND (vu_mois IS NULL OR vu_mois < ?)", (mois(), r["compte"], mois()))
    db.commit()
    return r["compte"]


def fermer_session(db, jeton):
    r = db.execute("SELECT compte FROM sessions WHERE empreinte = ?", (empreinte(jeton or ""),)).fetchone()
    db.execute("DELETE FROM sessions WHERE empreinte = ?", (empreinte(jeton or ""),))
    if r:
        _effacer_si_vide(db, r["compte"])
    db.commit()


# ---- les abonnements

def abonner(db, compte, type_, cible="", etat="actif", registre=None):
    """Ajoute un abonnement admis par le registre. Rend le jeton de sortie (lien de désinscription en un clic).
    Refus : type inconnu ou fermé, cible hors liste, plafond atteint."""
    cible = abonnements.verifier(type_, cible, registre)
    t = abonnements.type_de(type_, registre)
    deja = db.execute("SELECT sortie, etat FROM abonnements WHERE compte = ? AND type = ? AND cible = ?", (compte, type_, cible)).fetchone()
    if deja:
        if etat == "actif" and deja["etat"] != "actif":   # depuis le compte, l'adresse est prouvée : on active
            db.execute("UPDATE abonnements SET etat = 'actif' WHERE sortie = ?", (deja["sortie"],))
            db.commit()
        return deja["sortie"]
    sortie = secrets.token_urlsafe(24)
    # Le plafond se vérifie dans la même instruction que l'insertion : deux requêtes simultanées ne le dépassent pas.
    try:
        n = db.execute("""INSERT INTO abonnements (compte, type, cible, etat, cree_jour, sortie)
                          SELECT ?, ?, ?, ?, ?, ? WHERE (SELECT COUNT(*) FROM abonnements WHERE compte = ? AND type = ?) < ?""",
                       (compte, type_, cible, etat, jour(), sortie, compte, type_, t.plafond)).rowcount
    except sqlite3.IntegrityError:   # la même ligne, ajoutée entre-temps
        db.rollback()
        return db.execute("SELECT sortie FROM abonnements WHERE compte = ? AND type = ? AND cible = ?", (compte, type_, cible)).fetchone()["sortie"]
    if n != 1:
        db.rollback()
        raise abonnements.Refus(f"{t.plafond} au plus")
    db.commit()
    return sortie


def desabonner(db, compte, type_, cible=""):
    n = db.execute("DELETE FROM abonnements WHERE compte = ? AND type = ? AND cible = ?", (compte, type_, cible or "")).rowcount
    db.commit()
    return n > 0


def inscrire_lettre(db, adresse):
    """L'inscription à la lettre depuis le site, sans connexion : rend (adresse, jeton de sortie) s'il faut envoyer
    le lien de confirmation, sinon None (adresse invalide, ou déjà confirmée). Comme avant : un abonné à la lettre
    est un compte avec une ligne ; il ne se connecte jamais."""
    purger(db)
    a = normaliser(adresse)
    if not a:
        return None
    compte = compte_de(db, a, creer=True)
    r = db.execute("SELECT etat, sortie FROM abonnements WHERE compte = ? AND type = 'lettre'", (compte,)).fetchone()
    if r:
        db.commit()
        return None if r["etat"] == "actif" else (a, r["sortie"])
    sortie = abonner(db, compte, "lettre", "", etat="attente")
    return a, sortie


def confirmer(db, sortie):
    """La double confirmation : passe l'abonnement en attente à actif. Rend True si le jeton est connu."""
    purger(db)
    if not sortie or len(sortie) > 100:
        return False
    db.execute("UPDATE abonnements SET etat = 'actif' WHERE sortie = ? AND etat = 'attente'", (sortie,))
    db.commit()
    return db.execute("SELECT 1 FROM abonnements WHERE sortie = ?", (sortie,)).fetchone() is not None


def sortir(db, sortie):
    """La désinscription en un clic : supprime cet abonnement. Si le compte n'a plus rien (ni abonnement, ni appareil
    connecté), l'adresse est effacée. Rend True si une ligne a été supprimée."""
    if not sortie or len(sortie) > 100:
        return False
    r = db.execute("SELECT id, compte FROM abonnements WHERE sortie = ?", (sortie,)).fetchone()
    if not r:
        return False
    db.execute("DELETE FROM abonnements WHERE id = ?", (r["id"],))
    _effacer_si_vide(db, r["compte"])
    db.commit()
    return True


def deja_servis(db, types, cle):
    """Les comptes qui ont déjà reçu l'envoi `cle` pour l'un de ces types : un abonnement ajouté après l'envoi du
    jour attend le lendemain, il ne fait pas partir un second mail."""
    marques = ",".join("?" * len(types))
    return {r[0] for r in db.execute(f"SELECT DISTINCT compte FROM abonnements WHERE type IN ({marques}) AND dernier_envoi = ?",
                                     (*types, cle))}


def destinataires(db, types, cle):
    """Les abonnements actifs de ces types qui n'ont pas encore reçu l'envoi `cle` (« 2026-S47 », « 2026-11-17 »).
    Rend [{id, compte, adresse, type, cible, sortie}], groupables par compte."""
    marques = ",".join("?" * len(types))
    return [dict(r) for r in db.execute(
        f"""SELECT a.id, a.compte, c.adresse, a.type, a.cible, a.sortie FROM abonnements a JOIN comptes c ON c.id = a.compte
            WHERE a.etat = 'actif' AND a.type IN ({marques}) AND (a.dernier_envoi IS NULL OR a.dernier_envoi < ?)
              AND (a.fin_jour IS NULL OR a.fin_jour >= ?)
            ORDER BY a.compte, a.type, a.cible""", (*types, cle, jour()))]


def noter_envoi(db, ids, cle):
    db.executemany("UPDATE abonnements SET dernier_envoi = ? WHERE id = ?", [(cle, i) for i in ids])
    db.commit()


def purger(db):
    """Le ménage, chaque minute par le guichet : codes expirés, sessions finies, inscriptions non confirmées sous
    sept jours, abonnements éteints, comptes devenus vides. Rend le nombre de comptes effacés."""
    db.execute("DELETE FROM codes WHERE expire < ?", (int(time.time()),))
    db.execute("DELETE FROM sessions WHERE fin_jour < ?", (jour(),))
    borne = jour(datetime.now(timezone.utc) - timedelta(days=JOURS_SANS_CONFIRMATION))
    db.execute("DELETE FROM abonnements WHERE etat = 'attente' AND cree_jour < ?", (borne,))
    db.execute("DELETE FROM abonnements WHERE fin_jour IS NOT NULL AND fin_jour < ?", (jour(),))
    # un compte créé aujourd'hui est épargné : sa session peut être en train de s'ouvrir
    n = db.execute("""DELETE FROM comptes WHERE id NOT IN (SELECT compte FROM abonnements)
                      AND id NOT IN (SELECT compte FROM sessions) AND cree_jour < ?""", (jour(),)).rowcount
    db.commit()
    return n


# ---- le panel : le guichet sait qui est membre et qui a retiré son bulletin, jamais ce qu'il répond

CARENCE_JOURS = 7   # un membre arrivé moins de sept jours avant l'ouverture ne répond pas : le panel est figé


def inviter_panel(db, n=1):
    """Des codes d'invitation au panel, tant qu'il reste un cercle invité. Seule leur empreinte est gardée ; un code
    servi est effacé : rien ne relie ensuite un code à un compte."""
    codes = []
    for _ in range(n):
        code = secrets.token_urlsafe(9)
        db.execute("INSERT INTO invitations_panel (empreinte, cree_jour) VALUES (?, ?)", (empreinte(code), jour()))
        codes.append(code)
    db.commit()
    return codes


def rejoindre_panel(db, compte, code):
    """Consomme le code (d'un seul geste : deux usages simultanés ne passent pas) et inscrit le compte au panel.
    Rend True, ou False si le code est inconnu ou déjà servi. Le bord n'est jamais demandé ici : il reste sur
    l'appareil et voyage avec chaque réponse."""
    if db.execute("SELECT 1 FROM abonnements WHERE compte = ? AND type = 'panel'", (compte,)).fetchone():
        return True
    if not code or len(code) > 64:
        return False
    if db.execute("DELETE FROM invitations_panel WHERE empreinte = ?", (empreinte(str(code).strip()),)).rowcount != 1:
        db.rollback()
        return False
    cible = abonnements.verifier("panel", "", ouvert_requis=False)
    db.execute("INSERT INTO abonnements (compte, type, cible, etat, cree_jour, sortie) VALUES (?, 'panel', ?, 'actif', ?, ?)",
               (compte, cible, jour(), secrets.token_urlsafe(24)))
    db.commit()
    return True


def membre(db, compte):
    r = db.execute("SELECT cree_jour FROM abonnements WHERE compte = ? AND type = 'panel' AND etat = 'actif'", (compte,)).fetchone()
    return r["cree_jour"] if r else None


def ouvrir_cle(db, questionnaire, cle):
    """Garde la clé privée d'un questionnaire (ou d'une carte de votant) jusqu'à sa clôture."""
    db.execute("INSERT INTO cles (questionnaire, n, e, d, ouverte_jour) VALUES (?, ?, ?, ?, ?)",
               (questionnaire, format(cle["n"], "x"), cle["e"], format(cle["d"], "x"), jour()))
    db.commit()


def cles_ouvertes(db):
    return [dict(r) for r in db.execute("SELECT questionnaire, n, e, ouverte_jour FROM cles ORDER BY questionnaire")]


class RetraitRefuse(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def retirer(db, compte, questionnaire, aveugle):
    """Le retrait du bulletin : le guichet vérifie que le compte est membre depuis assez longtemps et n'a pas déjà
    retiré, note « retiré », puis signe sans voir. La contrainte d'unicité, pas le code, empêche deux retraits
    (premier cadrage, règle 7). Rend la signature aveugle. Il ne garde ni le bulletin aveuglé, ni la signature."""
    r = db.execute("SELECT n, e, d, ouverte_jour FROM cles WHERE questionnaire = ?", (questionnaire,)).fetchone()
    if not r:
        raise RetraitRefuse(410, "questionnaire clos ou inconnu")
    depuis = membre(db, compte)
    borne = jour(datetime.fromisoformat(r["ouverte_jour"]).replace(tzinfo=timezone.utc) - timedelta(days=CARENCE_JOURS))
    if depuis is None or (not questionnaire.startswith("carte-") and depuis > borne):
        raise RetraitRefuse(403, "réservé aux membres du panel inscrits avant l'ouverture")
    try:
        db.execute("INSERT INTO retraits (questionnaire, compte) VALUES (?, ?)", (questionnaire, compte))
        # compté à part : un compte supprimé emporte son retrait, pas le bulletin qu'il a reçu
        db.execute("UPDATE cles SET delivres = delivres + 1 WHERE questionnaire = ?", (questionnaire,))
    except sqlite3.IntegrityError:
        db.rollback()
        raise RetraitRefuse(409, "déjà retiré")
    try:
        sig = signature.signer_aveugle({"n": int(r["n"], 16), "e": r["e"], "d": int(r["d"], 16)}, aveugle)
    except signature.ErreurSignature:
        db.rollback()
        raise RetraitRefuse(400, "bulletin aveuglé invalide")
    db.commit()
    return sig


def delivres(db, questionnaire):
    """Le nombre de bulletins (ou de cartes) délivrés sous cette clé, ou None si elle est déjà détruite."""
    r = db.execute("SELECT delivres FROM cles WHERE questionnaire = ?", (questionnaire,)).fetchone()
    return r[0] if r else None


def fermer_cle(db, questionnaire):
    """La clôture, côté guichet : la clé privée est détruite, la liste des retraits est effacée. Rend le nombre de
    bulletins délivrés, le seul chiffre qui en reste (0 si la clé n'existait plus). Après cela, plus personne ne peut
    fabriquer un bulletin, ni savoir qui a participé. Les pages libérées et le journal (WAL) ne gardent ni la clé ni
    les retraits ; si un lecteur tient le journal, un avertissement le dit et le prochain point de contrôle le vide."""
    n = delivres(db, questionnaire) or 0
    db.execute("DELETE FROM retraits WHERE questionnaire = ?", (questionnaire,))
    db.execute("DELETE FROM cles WHERE questionnaire = ?", (questionnaire,))
    db.commit()
    db.execute("VACUUM")
    if not vider_journal(db):
        print("avertissement : le journal d'identites.db n'a pas pu être vidé tout de suite", flush=True)
    return n


def vider_journal(db, essais=20):
    """Ramène le journal WAL à zéro octet : ce qui vient d'être effacé n'y reste pas. Réessaie tant qu'un lecteur le
    tient. Rend True si le journal est vide."""
    import time
    for i in range(essais):
        if not db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]:
            return True
        time.sleep(.1)
    return False
