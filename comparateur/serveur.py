"""Le serveur : le site statique, le compte et l'urne. Bibliothèque standard seulement.

  GET  /sante                      état du service (pour le contrôle de santé de Coolify)
  POST /api/mail/inscription       {adresse}     -> 202, toujours la même réponse (synthèse de la semaine par mail)
  POST /api/mail/confirmation      {jeton}       confirme l'inscription (bouton de mail.html)
  POST /api/mail/desinscription    {jeton}, ou ?jeton= avec List-Unsubscribe=One-Click (RFC 8058) : supprime l'abonné
  compte.<domaine>  /api/compte/…  le compte, le panel, le bulletin et la carte de votant, les lots à juger
  urne.<domaine>    /api/urne/…    dépôt, effacement, avis à l'aveugle avec la carte ; sans cookie ni identité
  tout le reste                    fichiers de <données>/public/ (ETag et 304, gzip si le navigateur l'accepte)

Le vote à l'aveugle passe par la carte de votant (une par trimestre, signée sans être vue) : le site ne reçoit plus
aucun avis. Ses résultats sont lus dans ce que l'urne publie à chaque clôture (aveugle.resultats). Les abonnés au
mail de la semaine sont dans le tiroir identité (comptes.py) : leur adresse n'est écrite dans aucun journal.
"""
import gzip, hashlib, json, mimetypes, os, re, sys, threading, time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import abonnements, base, ceremonie, comptes, config, lettre, signature, urne

CORPS_MAX = 4096
# Le manifest de l'application : type exigé par certains navigateurs, absent des vieilles tables de Python.
mimetypes.add_type("application/manifest+json", ".webmanifest")


def politique():
    """Politique de sécurité des pages. Seule origine extérieure admise : celle d'Umami, s'il est réglé.
    Le manifest et le service worker (sw.js) viennent du site : default-src 'self' les couvre, et le dire
    explicitement évite qu'un resserrement de default-src les casse."""
    u = config.umami()
    ext = " " + u["origine"] if u else ""
    return ("default-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'" + ext + "; img-src 'self' data:; "
            "connect-src 'self'" + ext + "; manifest-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'none'")


def politique_compte():
    """Les pages de compte.<domaine> et urne.<domaine> : rien d'extérieur, aucune mesure d'audience (premier cadrage,
    règle 11). La page du compte n'appelle que son origine et l'urne (dépôt et effacement, sans cookie)."""
    return ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            f"connect-src 'self' {config.urne_url()}; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


COOKIE = "__Host-cadrages"   # préfixe __Host- : Secure, Path=/, sans Domain ; renvoyé à compte.<domaine> seul
COMPTE = os.path.join(config.ICI, "compte")   # les pages servies sur compte.<domaine>, hors du tiroir public

ENTETES = {
    "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
    "Content-Security-Policy": politique(),
}


class Debit:
    """Limite de débit en mémoire : au plus `maxi` appels par fenêtre de `secondes`, par clé.

    Une clé (une adresse IP, l'empreinte d'une adresse mail) est oubliée au plus tard une fenêtre et une minute après
    son dernier appel : un fil à part (`oublier`) purge toutes les minutes, même sans trafic. Rien n'est écrit
    ailleurs qu'en mémoire."""

    def __init__(self):
        self.vus, self.fenetres, self.verrou, self.purge = {}, {}, threading.Lock(), 0.0

    def purger(self, t=None):
        t = time.time() if t is None else t
        with self.verrou:
            self._purger(t)

    def _purger(self, t):
        self.vus = {k: v for k, v in self.vus.items() if v and t - v[-1] < self.fenetres.get(k, 3600)}
        self.fenetres = {k: f for k, f in self.fenetres.items() if k in self.vus}
        self.purge = t

    def autorise(self, cle, maxi, secondes):
        t = time.time()
        with self.verrou:
            if t - self.purge >= 60 or len(self.vus) > 20000:   # jamais de croissance sans borne
                self._purger(t)
            passes = [x for x in self.vus.get(cle, []) if t - x < secondes]
            self.fenetres[cle] = max(secondes, self.fenetres.get(cle, 0))
            if len(passes) >= maxi:
                self.vus[cle] = passes
                return False
            passes.append(t)
            self.vus[cle] = passes
            return True


DEBIT = Debit()

# Les fichiers texte de plus de 1 Ko partent compressés si le navigateur l'accepte.
COMPRESSIBLES = ("text/html", "text/css", "text/javascript", "application/javascript", "application/json",
                 "image/svg+xml", "application/manifest+json")
SEUIL_GZIP = 1024
IMMUABLE = re.compile(r"^actifs/site-[0-9a-f]{12}\.(css|js)$")   # nommé par son empreinte : ne change jamais


def accepte_gzip(entete):
    """Lecture de Accept-Encoding : gzip, ou « * » à défaut, avec un q non nul (gzip;q=0 le refuse)."""
    q = {}
    for part in (entete or "").split(","):
        nom, _, params = part.partition(";")
        poids = 1.0
        m = re.search(r"\bq\s*=\s*([^;,\s]*)", params, re.I)
        if m:
            try:
                poids = float(m.group(1))
            except ValueError:
                poids = 0.0
        q[nom.strip().lower()] = poids
    return q.get("gzip", q.get("*", 0.0)) > 0


class Memo:
    """Ce qu'on retient d'un fichier public : son ETag et sa version gzip, clé (chemin, date de modification,
    taille). Mémoire bornée (nombre d'entrées et octets), la plus anciennement servie part la première : un fichier
    n'est pas recompressé à chaque visite, et rien ne grossit sans fin."""

    def __init__(self, entrees=512, octets=32 * 1024 * 1024):
        self.gardes, self.entrees, self.maxi, self.verrou = OrderedDict(), entrees, octets, threading.Lock()

    def lire(self, cle, brut, comprimer):
        with self.verrou:
            e = self.gardes.get(cle)
            if e is not None:
                self.gardes.move_to_end(cle)
        if e is None:
            e = {"etag": hashlib.sha256(brut).hexdigest()[:16], "gz": None}
        if comprimer and e["gz"] is None:
            e["gz"] = gzip.compress(brut, 6, mtime=0)
        with self.verrou:
            self.gardes[cle] = e
            self.gardes.move_to_end(cle)
            while len(self.gardes) > 1 and (len(self.gardes) > self.entrees or
                                            sum(len(x["gz"] or b"") for x in self.gardes.values()) > self.maxi):
                self.gardes.popitem(last=False)
        return e


MEMO = Memo()


def correspond(si_aucun, etag):
    """If-None-Match : une liste d'ETag (faibles ou forts) ou « * »."""
    for x in (si_aucun or "").split(","):
        x = x.strip()
        if x == "*" or x == etag or (x.startswith("W/") and x[2:] == etag):
            return True
    return False


def oublier(debit=None, pause=60):
    """Le fil qui purge la limite de débit toutes les minutes : une adresse IP n'est jamais gardée plus d'une heure
    et une minute après sa dernière requête, qu'il y ait du trafic ou non."""
    debit = debit or DEBIT

    def boucle():
        while True:
            time.sleep(pause)
            debit.purger()

    threading.Thread(target=boucle, daemon=True, name="oubli").start()


def empreinte(jeton):
    return hashlib.sha256(jeton.encode()).hexdigest()


class Erreur(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


class Guichet(BaseHTTPRequestHandler):
    server_version = "Comparateur"
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True   # en-têtes puis corps en deux envois : sans cela, 40 ms d'attente par réponse en connexion gardée

    def log_message(self, fmt, *args):  # journal sans adresse du visiteur, et sans paramètres d'adresse (jetons)
        args = tuple(re.sub(r"\?\S*", "?…", a) if isinstance(a, str) else a for a in args)
        print("%s %s" % (time.strftime("%H:%M:%S"), fmt % args), flush=True)

    # ---- utilitaires

    def adresse(self):
        if config.confiance_proxy():
            xff = self.headers.get("X-Forwarded-For", "")
            if xff:
                return xff.split(",")[0].strip()
        return self.client_address[0]

    def envoyer(self, code, corps, type_mime="application/json; charset=utf-8", cache="no-store", plus=None):
        """`plus` : en-têtes en plus (ETag, Vary, Content-Encoding). Un 304 n'a ni corps ni Content-Length ;
        un HEAD a les en-têtes du GET (dont sa Content-Length) et pas de corps."""
        if isinstance(corps, (dict, list)):
            corps = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        if code != 304:
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", cache)
        for k, v in (plus or {}).items():
            self.send_header(k, v)
        for k, v in ENTETES.items():
            self.send_header(k, v if k != "Content-Security-Policy" or getattr(self, "cote", "site") == "site"
                             else politique_compte())
        self.end_headers()
        if self.command != "HEAD" and code != 304:
            self.wfile.write(corps)

    def corps_brut(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise Erreur(400, "longueur invalide")
        if n > CORPS_MAX:
            raise Erreur(413, "requête trop longue")
        return self.rfile.read(n) if n > 0 else b""

    def corps_json(self, brut=None):
        brut = self.corps_brut() if brut is None else brut
        try:
            d = json.loads(brut or b"{}")
        except (ValueError, UnicodeDecodeError):
            raise Erreur(400, "JSON invalide")
        if not isinstance(d, dict):
            raise Erreur(400, "objet JSON attendu")
        return d

    # ---- routes

    def do_GET(self):
        self.router()

    def do_HEAD(self):
        self.router()

    def do_POST(self):
        self.router()

    def do_OPTIONS(self):
        self.router()

    def hote(self):
        """L'hôte demandé, en minuscules, sans port. Derrière Traefik, l'en-tête Host est celui du visiteur."""
        h = (self.headers.get("Host") or "").strip().lower()
        if h.startswith("["):   # une adresse IPv6 : le site
            return ""
        return h.rsplit(":", 1)[0] if ":" in h else h

    def router(self):
        chemin = urlsplit(self.path).path
        h = config.hotes()
        # Trois noms d'hôte, un processus (docs/cadrage-long-terme.md, 5.2) : le site, le compte, l'urne. Un hôte
        # inconnu (une adresse IP, le contrôle de santé du conteneur) est le site.
        self.cote = "compte" if self.hote() == h["compte"] else "urne" if self.hote() == h["urne"] else "site"
        try:
            if chemin == "/sante":   # ouvre la base : limité, comme l'API
                if not DEBIT.autorise("sante:" + self.adresse(), 120, 60):
                    raise Erreur(429, "trop de requêtes")
                return self.sante()
            if self.cote == "compte":
                return self.compte(chemin)
            if self.cote == "urne":
                return self.urne(chemin)
            if chemin.startswith("/api/compte/") or chemin == "/api/compte":
                raise Erreur(404, "route inconnue")   # le compte ne répond que sur son hôte, où vit son cookie
            if chemin.startswith("/api/"):
                # La limite de débit ne vaut que pour l'API : les fichiers publics (cachés, compressés) ne sont pas limités.
                if not DEBIT.autorise("ip:" + self.adresse(), 300, 60):
                    raise Erreur(429, "trop de requêtes")
                return self.api(chemin)
            if self.command == "POST":
                raise Erreur(405, "méthode non permise")
            return self.fichier(chemin)
        except Erreur as e:
            self.envoyer(e.code, {"erreur": e.message})
        except Exception as e:  # jamais de trace d'exécution vers le client
            print("erreur interne :", type(e).__name__, e, flush=True)
            self.envoyer(500, {"erreur": "erreur interne"})

    def sante(self):
        db = base.connexion()
        try:
            derniere = db.execute("SELECT fin FROM journal_fabrique WHERE etape = 'publication' AND ok = 1 "
                                  "ORDER BY id DESC LIMIT 1").fetchone()
        finally:
            db.close()
        self.envoyer(200, {"ok": True, "derniere_publication": derniere["fin"] if derniere else None})

    def api(self, chemin):
        """L'API du site. Le vote à l'aveugle n'y est plus : il passe par la carte de votant (compte et urne), et ses
        résultats sont publiés comme des fichiers (public/panel/aveugle/). Ce côté n'ouvre plus comparateur.db."""
        route = (self.command, chemin)
        if chemin.startswith("/api/mail/") and config.mail():
            ident = comptes.connexion()
            try:
                return self.mail(route, ident)
            finally:
                ident.close()

        raise Erreur(404, "route inconnue")

    def mail(self, route, ident):
        """La synthèse de la semaine par mail, sans connexion : une adresse suffit. Le tiroir identité garde un
        compte et une ligne d'abonnement (comptes.inscrire_lettre). Routes absentes (404) quand le mail est éteint."""
        if route == ("POST", "/api/mail/inscription"):
            if not DEBIT.autorise("mail:" + self.adresse(), 5, 3600):
                raise Erreur(429, "trop d'essais, réessayez plus tard")
            d = self.corps_json()
            # Champ caché : un humain ne le voit pas, un robot le remplit. Même réponse, rien n'est fait.
            if not str(d.get("site", "")).strip():
                a = comptes.inscrire_lettre(ident, d.get("adresse"))
                # une adresse en attente ne reçoit pas plus de deux liens par jour, d'où qu'ils soient demandés
                if a and DEBIT.autorise("mailadr:" + empreinte(a[0]), 2, 86400):
                    lettre.plus_tard(lettre.envoyer_confirmation, *a)
            # La même réponse, que l'adresse soit nouvelle, déjà inscrite ou invalide : rien n'est révélé.
            return self.envoyer(202, {"ok": True})

        if route == ("POST", "/api/mail/confirmation"):
            if not DEBIT.autorise("mailj:" + self.adresse(), 20, 3600):
                raise Erreur(429, "trop d'essais, réessayez plus tard")
            if not comptes.confirmer(ident, str(self.corps_json().get("jeton", ""))):
                raise Erreur(404, "lien inconnu ou expiré")
            return self.envoyer(200, {"ok": True})

        if route[1] == "/api/mail/desinscription":
            jeton = (parse_qs(urlsplit(self.path).query).get("jeton") or [""])[0]
            if route[0] == "GET":   # un lien ouvert ne désinscrit pas : il mène à la page et à son bouton
                self.send_response(303)
                self.send_header("Location", "/mail.html#desinscrire=" + re.sub(r"[^\w-]", "", jeton))
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                for k, v in ENTETES.items():
                    self.send_header(k, v)
                self.end_headers()
                return
            if route[0] == "POST":
                brut = self.corps_brut()
                if not jeton:   # depuis la page : {jeton} en JSON ; en un clic (RFC 8058) : ?jeton= dans l'adresse
                    jeton = str(self.corps_json(brut).get("jeton", ""))
                if not DEBIT.autorise("mailj:" + self.adresse(), 20, 3600):
                    raise Erreur(429, "trop d'essais, réessayez plus tard")
                comptes.sortir(ident, jeton)
                return self.envoyer(200, {"ok": True})   # déjà désinscrit : même réponse

        raise Erreur(404, "route inconnue")

    # ---- compte.<domaine>

    def jeton_session(self):
        for morceau in (self.headers.get("Cookie") or "").split(";"):
            nom, _, valeur = morceau.strip().partition("=")
            if nom == COOKIE:
                return valeur
        return None

    def poser_cookie(self, jeton):
        """Un seul cookie, strictement nécessaire : il garde la connexion. Sans Domain, il n'est renvoyé qu'à
        compte.<domaine> ; l'urne et le site ne le reçoivent jamais."""
        if jeton:
            return {"Set-Cookie": f"{COOKIE}={jeton}; Path=/; Max-Age={comptes.SESSION_JOURS * 86400}; Secure; HttpOnly; SameSite=Strict"}
        return {"Set-Cookie": f"{COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Strict"}

    def meme_origine(self):
        """Contre une requête forgée depuis un autre site : JSON seulement (un formulaire ne peut pas en envoyer sans
        demande préalable du navigateur), et, quand le navigateur les donne, Origin et Sec-Fetch-Site du compte."""
        if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
            raise Erreur(415, "JSON attendu")
        origine = self.headers.get("Origin")
        if origine and origine.split("://", 1)[-1].lower() != config.hotes()["compte"] and origine != config.compte_url():
            raise Erreur(403, "origine refusée")
        if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin"):
            raise Erreur(403, "origine refusée")

    def compte(self, chemin):
        """compte.<domaine> : la page du compte et son API. Éteint (404) sans mail : pas de code à envoyer."""
        if not config.mail():
            raise Erreur(404, "introuvable")
        if not chemin.startswith("/api/"):
            if self.command == "POST":
                raise Erreur(405, "méthode non permise")
            nom = {"/": "compte.html", "/panel": "panel.html"}.get(chemin, chemin.lstrip("/"))
            types = {"compte.html": "text/html; charset=utf-8", "panel.html": "text/html; charset=utf-8",
                     "aveugle-rsa.js": "application/javascript; charset=utf-8"}
            if nom not in types or not os.path.isfile(os.path.join(COMPTE, nom)):
                raise Erreur(404, "introuvable")
            with open(os.path.join(COMPTE, nom), "rb") as f:
                return self.envoyer(200, f.read(), types[nom], cache="no-store")
        if not DEBIT.autorise("ip:" + self.adresse(), 300, 60):
            raise Erreur(429, "trop de requêtes")
        ident = comptes.connexion()
        try:
            return self.compte_api(chemin, ident)
        finally:
            ident.close()

    def compte_api(self, chemin, ident):
        route = (self.command, chemin)
        if route == ("GET", "/api/compte/registre"):
            return self.envoyer(200, {"registre": abonnements.ecran()})
        if self.command == "POST":
            self.meme_origine()

        if route == ("POST", "/api/compte/code"):
            if not DEBIT.autorise("code:" + self.adresse(), 5, 3600):
                raise Erreur(429, "trop d'essais, réessayez dans une heure")
            d = self.corps_json()
            if not str(d.get("site", "")).strip():          # champ caché contre les robots
                a = comptes.normaliser(d.get("adresse"))
                # trois codes par heure et par adresse, d'où qu'ils soient demandés
                if a and DEBIT.autorise("codeadr:" + empreinte(a), 3, 3600):
                    _, code = comptes.demander_code(ident, a)
                    lettre.plus_tard(lettre.envoyer_code, a, code)
            return self.envoyer(202, {"ok": True})        # la même réponse, adresse connue ou non

        if route == ("POST", "/api/compte/connexion"):
            if not DEBIT.autorise("cnx:" + self.adresse(), 20, 3600):
                raise Erreur(429, "trop d'essais, réessayez dans une heure")
            d = self.corps_json()
            compte = comptes.verifier_code(ident, d.get("adresse"), d.get("code"))
            if not compte:
                raise Erreur(403, "code faux ou expiré")
            jeton = comptes.ouvrir_session(ident, compte)
            return self.envoyer(200, {"ok": True}, plus=self.poser_cookie(jeton))

        compte = comptes.session(ident, self.jeton_session())
        if compte is None:
            raise Erreur(401, "non connecté")
        if route == ("GET", "/api/compte"):
            return self.envoyer(200, {"sait": comptes.lire(ident, compte), "registre": abonnements.ecran()})
        if route == ("POST", "/api/compte/abonnement"):
            d = self.corps_json()
            type_, cible, actif = d.get("type"), d.get("cible") or "", d.get("actif")
            if not isinstance(type_, str) or not isinstance(cible, str) or not isinstance(actif, bool):
                raise Erreur(400, "attendu : type, cible, actif")
            try:
                if actif:   # l'adresse est prouvée par le code : l'abonnement est actif tout de suite
                    comptes.abonner(ident, compte, type_, cible)
                else:
                    comptes.desabonner(ident, compte, type_, cible)
            except abonnements.Refus as e:
                raise Erreur(400, str(e))
            return self.envoyer(200, {"sait": comptes.lire(ident, compte), "registre": abonnements.ecran()})
        if route == ("GET", "/api/compte/panel"):
            return self.envoyer(200, self.etat_panel(ident, compte))
        if route == ("POST", "/api/compte/panel/rejoindre"):
            d = self.corps_json()
            if d.get("consentement") is not True:
                raise Erreur(400, "le consentement est requis")
            if not DEBIT.autorise("panel:" + self.adresse(), 10, 3600):
                raise Erreur(429, "trop d'essais, réessayez dans une heure")
            if not comptes.rejoindre_panel(ident, compte, d.get("code")):
                raise Erreur(403, "code d'invitation inconnu ou déjà utilisé")
            return self.envoyer(200, self.etat_panel(ident, compte))
        if route == ("POST", "/api/compte/panel/quitter"):
            comptes.desabonner(ident, compte, "panel")
            return self.envoyer(200, self.etat_panel(ident, compte))
        if route == ("POST", "/api/compte/bulletin"):
            d = self.corps_json()
            q, aveugle_hex = d.get("questionnaire"), d.get("aveugle")
            if not isinstance(q, str) or not urne.ID.match(q) or not isinstance(aveugle_hex, str) \
                    or not re.fullmatch(r"(?:[0-9a-f]{2}){64,1024}", aveugle_hex):
                raise Erreur(400, "attendu : questionnaire, bulletin aveuglé")
            if q == urne.carte_id(ceremonie.trimestre()):
                ceremonie.assurer_carte(ident)
            try:
                sig = comptes.retirer(ident, compte, q, bytes.fromhex(aveugle_hex))
            except comptes.RetraitRefuse as e:
                raise Erreur(e.code, e.message)
            return self.envoyer(200, {"signature": sig.hex()})
        if route == ("GET", "/api/compte/lots"):
            try:
                with open(os.path.join(config.public(), "aveugle", "lots.json"), "rb") as f:
                    return self.envoyer(200, f.read(), cache="no-store")
            except OSError:
                return self.envoyer(200, {"lots": []})
        if route == ("POST", "/api/compte/deconnexion"):
            comptes.fermer_session(ident, self.jeton_session())
            return self.envoyer(200, {"ok": True}, plus=self.poser_cookie(None))
        if route == ("POST", "/api/compte/suppression"):
            comptes.supprimer(ident, compte)
            return self.envoyer(200, {"ok": True}, plus=self.poser_cookie(None))
        raise Erreur(404, "route inconnue")

    def etat_panel(self, ident, compte):
        """Ce que la page du panel montre : l'appartenance, les questionnaires ouverts (leur description publique,
        et si ce compte a déjà retiré son bulletin), la carte de votant du trimestre. Le bord n'y est jamais."""
        depuis = comptes.membre(ident, compte)
        retires = {r[0] for r in ident.execute("SELECT questionnaire FROM retraits WHERE compte = ?", (compte,))}
        questionnaires = []
        dossier = os.path.join(config.public(), "panel", "questionnaires")
        for nom in sorted(os.listdir(dossier)) if os.path.isdir(dossier) else []:
            try:
                with open(os.path.join(dossier, nom), encoding="utf-8") as f:
                    q = json.load(f)
            except (OSError, ValueError):
                continue
            q["retire"] = q.get("id") in retires
            questionnaires.append(q)
        cid = urne.carte_id(ceremonie.trimestre())
        carte = None
        if depuis:
            ceremonie.assurer_carte(ident)
            try:
                with open(os.path.join(config.public(), "panel", "cles", cid + ".json"), encoding="utf-8") as f:
                    carte = {"id": cid, "trimestre": ceremonie.trimestre(), "cle": json.load(f), "retiree": cid in retires}
            except (OSError, ValueError):
                carte = None
        return {"membre": depuis is not None, "membre_depuis": depuis, "questionnaires": questionnaires if depuis else [],
                "carte": carte, "urne": config.urne_url(), "etiquette": urne.ETIQUETTE}

    # ---- urne.<domaine> : sans session, sans cookie, sans en-tête d'identité

    def cors(self):
        """La page du compte appelle l'urne depuis une autre origine : elle seule est admise, sans cookie."""
        if self.headers.get("Origin") == config.compte_url():
            return {"Access-Control-Allow-Origin": config.compte_url(), "Vary": "Origin"}
        return {"Vary": "Origin"}

    def urne(self, chemin):
        """L'urne refuse l'identité : un Cookie ou un Authorization donne 400, avant toute lecture du corps
        (premier cadrage, règle 4). Elle ne lit que ses fichiers et les clés publiques."""
        if not config.mail() or not chemin.startswith("/api/urne/"):
            raise Erreur(404, "introuvable")
        if self.command == "OPTIONS":
            plus = self.cors()
            if "Access-Control-Allow-Origin" not in plus:
                raise Erreur(403, "origine refusée")
            plus.update({"Access-Control-Allow-Methods": "POST", "Access-Control-Allow-Headers": "Content-Type",
                         "Access-Control-Max-Age": "600"})
            return self.envoyer(204, b"", plus=plus)
        if self.headers.get("Cookie") is not None or self.headers.get("Authorization") is not None:
            raise Erreur(400, "l'urne ne reçoit ni cookie ni identité")
        if self.command != "POST":
            raise Erreur(405, "méthode non permise")
        if not DEBIT.autorise("ip:" + self.adresse(), 300, 60):
            raise Erreur(429, "trop de requêtes")
        d = self.corps_json()
        try:
            if chemin == "/api/urne/depot":
                urne.deposer(d.get("questionnaire"), d.get("bulletin"), d.get("signature"), d.get("bord"), d.get("reponses"))
                return self.envoyer(201, {"ok": True}, plus=self.cors())
            if chemin == "/api/urne/effacement":
                ok = urne.effacer(d.get("questionnaire"), d.get("bulletin"))
                return self.envoyer(200, {"efface": ok}, plus=self.cors())
            if chemin == "/api/urne/avis":
                urne.donner_avis(d.get("trimestre"), d.get("carte"), d.get("signature"), d.get("lot"), d.get("note"), d.get("bord"))
                return self.envoyer(201, {"ok": True}, plus=self.cors())
            if chemin == "/api/urne/lots-juges":
                return self.envoyer(200, {"lots": urne.lots_juges(d.get("trimestre"), d.get("carte"))}, plus=self.cors())
        except urne.Refus as e:
            raise Erreur(e.code, e.message)
        raise Erreur(404, "route inconnue")

    def fichier(self, chemin):
        racine = os.path.realpath(config.public())
        rel = chemin.lstrip("/") or "index.html"
        if rel == "favicon.ico":   # demandé d'office par certains navigateurs : l'icône SVG répond
            rel = "favicon.svg"
        if rel == "apple-touch-icon-precomposed.png":   # demandé d'office par Safari, comme apple-touch-icon.png
            rel = "apple-touch-icon.png"
        if rel.endswith("/"):
            rel += "index.html"
        cible = os.path.realpath(os.path.join(racine, rel))
        if not (cible == racine or cible.startswith(racine + os.sep)) or not os.path.isfile(cible):
            raise Erreur(404, "introuvable")
        type_mime = mimetypes.guess_type(cible)[0] or "application/octet-stream"
        comprimable = type_mime in COMPRESSIBLES
        if type_mime.startswith("text/") or type_mime in ("application/json", "application/javascript"):
            type_mime += "; charset=utf-8"
        # Le service worker est revérifié à chaque visite : une nouvelle version prend effet tout de suite.
        # Un actif nommé par son empreinte ne change jamais : un an, sans revalidation.
        cache = "no-cache" if rel == "sw.js" else "public, max-age=31536000, immutable" if IMMUABLE.search(rel) \
            else "public, max-age=300"
        with open(cible, "rb") as f:
            st = os.fstat(f.fileno())   # la date et la taille de ce qu'on lit, pas d'un fichier remplacé entre-temps
            brut = f.read()
        e = MEMO.lire((cible, st.st_mtime_ns, st.st_size), brut, comprimable and len(brut) > SEUIL_GZIP)
        plus = {"Vary": "Accept-Encoding"} if comprimable else {}
        etag = '"%s"' % e["etag"]
        if e["gz"] is not None and accepte_gzip(self.headers.get("Accept-Encoding")):
            brut, etag = e["gz"], '"%s-gzip"' % e["etag"]
            plus["Content-Encoding"] = "gzip"
        plus["ETag"] = etag
        if correspond(self.headers.get("If-None-Match"), etag):
            return self.envoyer(304, b"", type_mime, cache=cache, plus=plus)
        self.envoyer(200, brut, type_mime, cache=cache, plus=plus)


class Serveur(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        """socketserver écrirait l'adresse du client et la trace : ici, le type de l'erreur seulement."""
        print("erreur de connexion :", sys.exc_info()[0].__name__, flush=True)


def creer(port=None, hote="0.0.0.0"):
    base.connexion().close()  # crée le schéma au démarrage
    return Serveur((hote, config.port() if port is None else port), Guichet)


def envois():
    """Un passage de la boucle du guichet : le ménage du tiroir identité, puis les mails dus. L'alerte du matin part
    dès que la fabrique a écrit public/alertes/<jour>.json ; la synthèse de la semaine finie, dès que l'édition du
    jour est faite, et une seule fois par abonné (abonnements.dernier_envoi)."""
    if not config.mail():
        return None
    ident = comptes.connexion()
    try:
        comptes.purger(ident)
        ceremonie.echeances(ident)   # trimestres finis, questionnaires arrivés à leur jour de fermeture
        jour = base.paris().strftime("%Y-%m-%d")
        if lettre.alerte(jour) is None:   # l'édition du jour n'est pas encore là
            return {"jour": jour, "edition": False}
        return {"alertes": lettre.envoyer_alertes(ident, jour), "semaine": lettre.envoyer_semaine(ident, jour)}
    finally:
        ident.close()


def boucle_envois(pause=60):
    """Dans un fil à part du guichet : envois() chaque minute. La fabrique n'envoie plus rien : elle écrit, le
    guichet envoie (docs/cadrage-long-terme.md, phase 2)."""
    def boucle():
        while True:
            try:
                envois()
            except Exception as e:
                print(f"mails : arrêt inattendu {type(e).__name__}", flush=True)
            time.sleep(pause)

    threading.Thread(target=boucle, daemon=True, name="envois").start()


def guichet():
    """Le guichet seul : sert le site, le compte et l'urne ; envoie les mails. Il tient la clé d'envoi, pas celle
    des modèles, et n'écrit pas le tiroir public."""
    srv = creer()
    oublier()
    print(f"guichet : écoute sur le port {srv.server_address[1]}", flush=True)
    boucle_envois()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def servir():
    """Guichet et fabrique dans un seul processus : pour un poste de développement, ou un déploiement d'avant la
    phase 2. En production, deux services du compose : `guichet` et `fabrique`."""
    if config.fabrique_minutes() > 0:
        from . import chaine
        print(f"comparateur : récolte toutes les {config.fabrique_minutes()} min, édition chaque jour à "
              f"{config.edition_heure()} h (Paris)", flush=True)
        threading.Thread(target=chaine.boucle, args=(config.fabrique_minutes(),), daemon=True, name="fabrique").start()
    guichet()
