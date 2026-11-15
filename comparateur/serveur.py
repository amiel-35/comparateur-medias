"""Le serveur : le site statique et le guichet des votes. Bibliothèque standard seulement.

  GET  /sante                      état du service (pour le contrôle de santé de Coolify)
  POST /api/inscription            {code, bord}  -> {jeton}     un code d'invitation ouvre un jeton anonyme
  GET  /api/lot                    -> {lot: {id, titres} | null, restants}   (Authorization: Bearer <jeton>)
  POST /api/avis-aveugle           {lot, note}   note de -2 (gauche) à +2 (droite)
  POST /api/avis-note              {media, accord}
  GET  /api/resultats              notes à l'aveugle par média, avec effectifs par bord
  tout le reste                    fichiers de <données>/public/

Anonymat : la base ne garde que l'empreinte du jeton et le bord déclaré. Aucun lien entre une
invitation et un votant, aucun nom, aucune adresse (ni courriel ni IP).
"""
import hashlib, json, mimetypes, os, secrets, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from . import aveugle, base, config

CORPS_MAX = 4096


def politique():
    """Politique de sécurité des pages. Seule origine extérieure admise : celle d'Umami, s'il est réglé."""
    u = config.umami()
    ext = " " + u["origine"] if u else ""
    return ("default-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'" + ext + "; img-src 'self' data:; "
            "connect-src 'self'" + ext + "; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


ENTETES = {
    "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
    "Content-Security-Policy": politique(),
}


class Debit:
    """Limite de débit en mémoire : au plus `maxi` appels par fenêtre de `secondes`, par clé."""

    def __init__(self):
        self.vus, self.verrou = {}, threading.Lock()

    def autorise(self, cle, maxi, secondes):
        t = time.time()
        with self.verrou:
            if len(self.vus) > 20000:  # purge grossière : jamais de croissance sans borne
                self.vus = {k: v for k, v in self.vus.items() if v and t - v[-1] < 3600}
            passes = [x for x in self.vus.get(cle, []) if t - x < secondes]
            if len(passes) >= maxi:
                self.vus[cle] = passes
                return False
            passes.append(t)
            self.vus[cle] = passes
            return True


DEBIT = Debit()


def empreinte(jeton):
    return hashlib.sha256(jeton.encode()).hexdigest()


class Erreur(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


class Guichet(BaseHTTPRequestHandler):
    server_version = "Comparateur"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # journal sans adresse du visiteur
        print("%s %s" % (time.strftime("%H:%M:%S"), fmt % args), flush=True)

    # ---- utilitaires

    def adresse(self):
        if config.confiance_proxy():
            xff = self.headers.get("X-Forwarded-For", "")
            if xff:
                return xff.split(",")[0].strip()
        return self.client_address[0]

    def envoyer(self, code, corps, type_mime="application/json; charset=utf-8", cache="no-store"):
        if isinstance(corps, (dict, list)):
            corps = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", cache)
        for k, v in ENTETES.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corps)

    def corps_json(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise Erreur(400, "longueur invalide")
        if n > CORPS_MAX:
            raise Erreur(413, "requête trop longue")
        try:
            d = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, UnicodeDecodeError):
            raise Erreur(400, "JSON invalide")
        if not isinstance(d, dict):
            raise Erreur(400, "objet JSON attendu")
        return d

    def votant(self, db):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or len(auth) > 200:
            raise Erreur(401, "jeton manquant")
        vid = empreinte(auth[7:].strip())
        if not db.execute("SELECT 1 FROM votants WHERE id = ?", (vid,)).fetchone():
            raise Erreur(401, "jeton inconnu")
        if not DEBIT.autorise("v:" + vid, 120, 60):
            raise Erreur(429, "trop de requêtes")
        return vid

    # ---- routes

    def do_GET(self):
        self.router()

    def do_HEAD(self):
        self.router()

    def do_POST(self):
        self.router()

    def router(self):
        chemin = urlsplit(self.path).path
        try:
            if not DEBIT.autorise("ip:" + self.adresse(), 300, 60):
                raise Erreur(429, "trop de requêtes")
            if chemin == "/sante":
                return self.sante()
            if chemin.startswith("/api/"):
                db = base.connexion()
                try:
                    return self.api(chemin, db)
                finally:
                    db.close()
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

    def api(self, chemin, db):
        route = (self.command, chemin)
        if route == ("POST", "/api/inscription"):
            if not DEBIT.autorise("insc:" + self.adresse(), 10, 3600):
                raise Erreur(429, "trop d'essais, réessayez plus tard")
            d = self.corps_json()
            code, bord = str(d.get("code", "")).strip(), d.get("bord")
            if not isinstance(bord, int) or isinstance(bord, bool) or not -2 <= bord <= 2:
                raise Erreur(400, "bord attendu : entier de -2 à 2")
            # Le code est consommé d'un seul geste : deux inscriptions simultanées ne passent pas toutes deux.
            cur = db.execute("UPDATE invitations SET utilisee_le = ? WHERE code = ? AND utilisee_le IS NULL",
                             (base.iso()[:10], code))
            if cur.rowcount != 1:
                db.rollback()
                raise Erreur(403, "code d'invitation inconnu ou déjà utilisé")
            jeton = secrets.token_urlsafe(32)
            db.execute("INSERT INTO votants (id, bord, cree) VALUES (?, ?, ?)", (empreinte(jeton), bord, base.iso()[:10]))
            db.commit()
            return self.envoyer(201, {"jeton": jeton})

        if route == ("GET", "/api/resultats"):
            return self.envoyer(200, aveugle.resultats(db), cache="public, max-age=60")

        if route == ("GET", "/api/lot"):
            vid = self.votant(db)
            lots = db.execute(
                """SELECT id, titres FROM lots_aveugle WHERE id NOT IN
                   (SELECT lot_id FROM avis_aveugle WHERE votant_id = ?) ORDER BY id DESC""", (vid,)).fetchall()
            if not lots:
                return self.envoyer(200, {"lot": None, "restants": 0})
            lot = lots[secrets.randbelow(len(lots))]  # ordre aléatoire : pas d'indice par la position
            return self.envoyer(200, {"lot": {"id": lot["id"], "titres": json.loads(lot["titres"])}, "restants": len(lots)})

        if route == ("POST", "/api/avis-aveugle"):
            vid, d = self.votant(db), self.corps_json()
            lot, note = d.get("lot"), d.get("note")
            if not isinstance(lot, int) or not isinstance(note, int) or isinstance(note, bool) or not -2 <= note <= 2:
                raise Erreur(400, "attendu : lot (entier), note (entier de -2 à 2)")
            if not db.execute("SELECT 1 FROM lots_aveugle WHERE id = ?", (lot,)).fetchone():
                raise Erreur(404, "lot inconnu")
            try:
                db.execute("INSERT INTO avis_aveugle (votant_id, lot_id, note, cree) VALUES (?,?,?,?)",
                           (vid, lot, note, base.iso()[:10]))
                db.commit()
            except base.sqlite3.IntegrityError:
                raise Erreur(409, "lot déjà jugé")
            return self.envoyer(201, {"ok": True})

        if route == ("POST", "/api/avis-note"):
            vid, d = self.votant(db), self.corps_json()
            m = db.execute("SELECT id FROM medias WHERE nom = ?", (str(d.get("media", "")),)).fetchone()
            if not m or not isinstance(d.get("accord"), bool):
                raise Erreur(400, "attendu : media (nom connu), accord (booléen)")
            db.execute("""INSERT INTO avis_note (votant_id, media_id, accord, cree) VALUES (?,?,?,?)
                          ON CONFLICT(votant_id, media_id) DO UPDATE SET accord = excluded.accord, cree = excluded.cree""",
                       (vid, m["id"], int(d["accord"]), base.iso()[:10]))
            db.commit()
            return self.envoyer(201, {"ok": True})

        raise Erreur(404, "route inconnue")

    def fichier(self, chemin):
        racine = os.path.realpath(config.public())
        rel = chemin.lstrip("/") or "index.html"
        if rel.endswith("/"):
            rel += "index.html"
        cible = os.path.realpath(os.path.join(racine, rel))
        if not (cible == racine or cible.startswith(racine + os.sep)) or not os.path.isfile(cible):
            raise Erreur(404, "introuvable")
        type_mime = mimetypes.guess_type(cible)[0] or "application/octet-stream"
        if type_mime.startswith("text/") or type_mime in ("application/json", "application/javascript"):
            type_mime += "; charset=utf-8"
        with open(cible, "rb") as f:
            self.envoyer(200, f.read(), type_mime, cache="public, max-age=300")


def creer(port=None, hote="0.0.0.0"):
    base.connexion().close()  # crée le schéma au démarrage
    return ThreadingHTTPServer((hote, config.port() if port is None else port), Guichet)


def _planifier(minutes):
    """Dans un fil à part (une visite n'attend jamais la fabrique) : la récolte des flux toutes les `minutes`,
    et l'édition une fois par jour, à l'heure réglée (heure de Paris). Un redémarrage après l'heure la rattrape."""
    from . import chaine

    def dire(m):
        print("fabrique |", m, flush=True)

    def edition_faite(jour):
        db = base.connexion()
        try:
            return db.execute("SELECT 1 FROM editions WHERE jour = ?", (jour,)).fetchone() is not None
        finally:
            db.close()

    def boucle():
        derniere = 0.0
        while True:
            try:
                ici = base.paris()
                if ici.hour >= config.edition_heure() and not edition_faite(ici.strftime("%Y-%m-%d")):
                    dire("édition du " + ici.strftime("%Y-%m-%d"))
                    chaine.tout(afficher=dire)       # l'édition commence par une récolte
                    derniere = time.time()
                elif time.time() - derniere >= minutes * 60:
                    chaine.recolte(afficher=dire)
                    derniere = time.time()
            except Exception as e:
                dire(f"arrêt inattendu : {type(e).__name__} {e}")
                derniere = time.time()               # pas de boucle serrée sur une panne
            time.sleep(60)

    threading.Thread(target=boucle, daemon=True, name="fabrique").start()


def servir():
    srv = creer()
    print(f"comparateur : écoute sur le port {srv.server_address[1]}", flush=True)
    if config.fabrique_minutes() > 0:
        print(f"comparateur : récolte toutes les {config.fabrique_minutes()} min, édition chaque jour à "
              f"{config.edition_heure()} h (Paris)", flush=True)
        _planifier(config.fabrique_minutes())
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
