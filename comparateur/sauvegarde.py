"""Sauvegardes de la base. Bibliothèque standard seulement.

Chaque jour, une fois l'édition faite, la boucle de la fabrique copie la base par l'API de sauvegarde de SQLite :
une copie cohérente, même pendant une écriture (un simple `cp` d'une base en WAL peut donner une copie cassée).
La copie est vérifiée (PRAGMA integrity_check), compressée, et gardée dans <données>/sauvegardes/ pendant
COMPARATEUR_SAUVEGARDE_JOURS jours (14 par défaut).

Ces copies vivent sur le même disque que la base : elles protègent d'une erreur ou d'une migration ratée, pas de la
perte du serveur. Pour cela, une Storage Box (ou tout serveur WebDAV en HTTPS) : si COMPARATEUR_SAUVEGARDE_URL,
_UTILISATEUR et _MOT_DE_PASSE sont réglés, chaque copie y part aussi, et les copies plus vieilles que la même durée
y sont effacées.

Sauvegardé : toute la base (éditions, abonnés au mail, votes, invitations, articles, journal de la fabrique).
Pas sauvegardé : le site publié (réécrit depuis les éditions) et le cache des appels au modèle (refait au besoin).
"""
import base64, gzip, os, re, shutil, sqlite3, ssl, tempfile, time, urllib.error, urllib.parse, urllib.request
from datetime import date, timedelta
from xml.etree import ElementTree

from . import base, config

NOM = re.compile(r"^comparateur-(\d{4}-\d{2}-\d{2})\.db\.gz$")
PAUSE_ENVOI = 3600   # secondes entre deux essais d'envoi vers la Storage Box

_dernier_essai = {}


def dire(m):
    print("sauvegarde |", m, flush=True)


def dossier():
    d = os.path.join(config.donnees(), "sauvegardes")
    os.makedirs(d, exist_ok=True)
    return d


def nom(jour):
    return f"comparateur-{jour}.db.gz"


def aujourdhui():
    return base.paris().strftime("%Y-%m-%d")


def verifier(chemin):
    """Lève une erreur si la base à ce chemin n'est pas intègre."""
    db = sqlite3.connect(chemin)
    try:
        r = db.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        db.close()
    if r != "ok":
        raise ValueError("copie non intègre : " + str(r)[:200])


def copier(jour=None):
    """Copie cohérente de la base, vérifiée puis compressée, dans le dossier des sauvegardes. Rend son chemin.
    Refaire la copie d'un jour la remplace."""
    jour = jour or aujourdhui()
    cible = os.path.join(dossier(), nom(jour))
    fd, brut = tempfile.mkstemp(suffix=".db", dir=dossier())
    os.close(fd)
    try:
        src, dst = sqlite3.connect(config.base(), timeout=30), sqlite3.connect(brut)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        verifier(brut)
        with open(brut, "rb") as f, gzip.open(cible + ".tmp", "wb", compresslevel=6) as g:
            shutil.copyfileobj(f, g)
        os.replace(cible + ".tmp", cible)
        envoye = cible + ".envoye"
        if os.path.exists(envoye):   # une copie refaite repart vers la Storage Box
            os.remove(envoye)
    finally:
        for p in (brut, cible + ".tmp"):
            if os.path.exists(p):
                os.remove(p)
    return cible


def locales():
    """[(jour, chemin, envoyé ?)] des copies du dossier, de la plus ancienne à la plus récente."""
    d = dossier()
    out = []
    for n in sorted(os.listdir(d)):
        m = NOM.match(n)
        if m:
            out.append((m.group(1), os.path.join(d, n), os.path.exists(os.path.join(d, n + ".envoye"))))
    return out


def trop_vieux(jour, jours=None):
    jours = config.sauvegarde_jours() if jours is None else jours
    return date.fromisoformat(jour) < date.fromisoformat(aujourdhui()) - timedelta(days=jours - 1)


def elaguer_local(jours=None):
    """Supprime les copies locales plus vieilles que la durée de garde. Rend le nombre supprimé."""
    n = 0
    for jour, chemin, _ in locales():
        if trop_vieux(jour, jours):
            for p in (chemin, chemin + ".envoye"):
                if os.path.exists(p):
                    os.remove(p)
            n += 1
    return n


# ---- la Storage Box, en WebDAV

class Distant:
    """Un dossier WebDAV (Storage Box Hetzner, ou autre). Authentification Basic : HTTPS seulement, sauf en local."""

    def __init__(self, cfg):
        u = urllib.parse.urlsplit(cfg["url"])
        if u.scheme != "https" and u.hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("COMPARATEUR_SAUVEGARDE_URL doit commencer par https://")
        self.url = cfg["url"].rstrip("/") + "/"
        self.auth = "Basic " + base64.b64encode(f"{cfg['utilisateur']}:{cfg['mot_de_passe']}".encode()).decode()
        self.ctx = ssl.create_default_context()

    def requete(self, methode, url, data=None, entetes=None, ok=(200, 201, 204, 207)):
        req = urllib.request.Request(url, data=data, method=methode, headers={"Authorization": self.auth, **(entetes or {})})
        try:
            with urllib.request.urlopen(req, timeout=120, context=self.ctx if url.startswith("https") else None) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in ok:
                return e.code, e.read()
            raise RuntimeError(f"{methode} : HTTP {e.code}") from None

    def preparer(self):
        """Crée le dossier s'il n'existe pas (405 : il existe déjà)."""
        self.requete("MKCOL", self.url, ok=(200, 201, 204, 207, 405))

    def envoyer(self, chemin):
        self.preparer()
        with open(chemin, "rb") as f:
            donnees = f.read()
        self.requete("PUT", self.url + os.path.basename(chemin), data=donnees,
                     entetes={"Content-Type": "application/gzip", "Content-Length": str(len(donnees))})

    def lister(self):
        """Les noms des copies présentes dans le dossier distant."""
        corps = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getcontentlength/></d:prop></d:propfind>')
        _, brut = self.requete("PROPFIND", self.url, data=corps, entetes={"Depth": "1", "Content-Type": "application/xml"})
        noms = []
        for href in ElementTree.fromstring(brut).iter("{DAV:}href"):
            n = urllib.parse.unquote((href.text or "").rstrip("/").rsplit("/", 1)[-1])
            if NOM.match(n):
                noms.append(n)
        return sorted(noms)

    def effacer(self, n):
        self.requete("DELETE", self.url + n, ok=(200, 204, 404))

    def telecharger(self, n, cible):
        _, brut = self.requete("GET", self.url + n)
        with open(cible, "wb") as f:
            f.write(brut)


def distant():
    cfg = config.sauvegarde_distante()
    return Distant(cfg) if cfg else None


def envoyer_en_attente(force=False):
    """Envoie vers la Storage Box les copies locales pas encore envoyées, puis y efface les copies trop vieilles.
    Une panne n'empêche rien : l'essai suivant vient une heure plus tard. Rend le nombre envoyé, ou None."""
    try:
        dav = distant()
    except ValueError as e:
        dire(str(e))
        return None
    if dav is None:
        return None
    if not force and time.time() - _dernier_essai.get("t", 0) < PAUSE_ENVOI:
        return 0
    _dernier_essai["t"] = time.time()
    n = 0
    try:
        for jour, chemin, envoye in locales():
            if not envoye and not trop_vieux(jour):
                dav.envoyer(chemin)
                open(chemin + ".envoye", "w").close()
                n += 1
        effaces = [x for x in dav.lister() if trop_vieux(NOM.match(x).group(1))]
        for x in effaces:
            dav.effacer(x)
        dire(f"Storage Box : {n} copie(s) envoyée(s), {len(effaces)} effacée(s)")
    except Exception as e:   # pas de détail : un message d'erreur peut citer l'adresse et l'identifiant
        dire(f"Storage Box : échec ({type(e).__name__} {str(e)[:80] if isinstance(e, RuntimeError) else ''})".rstrip())
    return n


def sauvegarder(jour=None):
    """La sauvegarde du jour : copie locale, élagage, envoi vers la Storage Box si elle est réglée."""
    chemin = copier(jour)
    vieux = elaguer_local()
    dire(f"{os.path.basename(chemin)} : {os.path.getsize(chemin)} octets, {vieux} copie(s) ancienne(s) effacée(s)")
    envoyer_en_attente(force=True)
    return chemin


def faite(jour=None):
    return os.path.exists(os.path.join(dossier(), nom(jour or aujourdhui())))


def restaurer(source):
    """Remplace le contenu de la base par celui d'une copie : un chemin, ou un nom (comparateur-AAAA-MM-JJ.db.gz)
    pris dans le dossier local, sinon sur la Storage Box. La copie est vérifiée avant. La base en service est
    d'abord copiée elle-même (avant-restauration-…), pour pouvoir revenir en arrière."""
    chemin = source if os.path.isfile(source) else os.path.join(dossier(), os.path.basename(source))
    temp = []
    try:
        if not os.path.isfile(chemin):
            dav = distant()
            if dav is None or os.path.basename(source) not in dav.lister():
                raise FileNotFoundError(f"copie introuvable : {source}")
            fd, chemin = tempfile.mkstemp(suffix=".db.gz", dir=dossier())
            os.close(fd)
            temp.append(chemin)
            dav.telecharger(os.path.basename(source), chemin)
        fd, brut = tempfile.mkstemp(suffix=".db", dir=dossier())
        os.close(fd)
        temp.append(brut)
        with gzip.open(chemin, "rb") as g, open(brut, "wb") as f:
            shutil.copyfileobj(g, f)
        verifier(brut)
        avant = copier("avant-restauration-" + time.strftime("%Y%m%d-%H%M%S"))
        src, dst = sqlite3.connect(brut), sqlite3.connect(config.base(), timeout=30)
        try:
            src.backup(dst)   # écrit sous verrou : la base reste utilisable par le serveur pendant ce temps
        finally:
            src.close()
            dst.close()
        return avant
    finally:
        for p in temp:
            if os.path.exists(p):
                os.remove(p)
