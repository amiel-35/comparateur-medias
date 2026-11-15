"""La synthèse de la semaine, par mail. Envoi par SMTP (Brevo), bibliothèque standard seulement.

Inscription en double confirmation : l'adresse est gardée, avec un jeton aléatoire, puis confirmée par un clic
sur un bouton (POST) depuis la page mail.html. Rien ne se confirme ni ne se désinscrit sur un simple GET : les
antivirus de messagerie ouvrent les liens tout seuls. Une désinscription supprime la ligne. Une inscription non
confirmée sous 7 jours est supprimée.

Le lundi, une fois l'édition du jour faite, la boucle de la fabrique envoie la synthèse de la semaine ISO qui
vient de finir (lundi au dimanche). abonnes.dernier_envoi garde la clé de la dernière semaine envoyée
(« 2026-S46 ») : pas de double envoi, même après un redémarrage.

Aucune adresse n'est écrite dans les journaux : seulement des comptes.
"""
import html, json, re, secrets, smtplib, ssl, threading, time
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from . import base, config, syntheses

ADRESSE = re.compile(r"^[^@\s<>\"',;()\[\]\\]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
JOURS_SANS_CONFIRMATION = 7
TOP = 10                 # sujets dans le mail
ESSAIS = 3               # essais par adresse et par semaine avant d'abandonner jusqu'à la semaine suivante
PAUSE_ESSAIS = 30 * 60   # secondes entre deux essais pour une même adresse
EN_ARRIERE_PLAN = True   # le mail de confirmation part dans un fil à part (les tests le coupent)

_echecs, _verrou = {}, threading.Lock()


def dire(m):
    print("mail |", m, flush=True)


def normaliser(adresse):
    """L'adresse en minuscules, ou None si elle n'a pas la forme d'une adresse."""
    a = str(adresse or "").strip().lower()
    return a if len(a) <= 254 and ADRESSE.match(a) else None


# ---- la base

def purger(db):
    """Supprime les inscriptions non confirmées depuis plus de 7 jours. Rend le nombre supprimé."""
    borne = base.iso(base.maintenant() - timedelta(days=JOURS_SANS_CONFIRMATION))
    n = db.execute("DELETE FROM abonnes WHERE confirme_le IS NULL AND cree < ?", (borne,)).rowcount
    db.commit()
    return n


def inscrire(db, adresse):
    """Rend (adresse, jeton) s'il faut envoyer un mail de confirmation, sinon None : adresse invalide, ou déjà
    confirmée. Une adresse en attente reçoit de nouveau son lien (le débit est limité par le serveur)."""
    purger(db)
    a = normaliser(adresse)
    if not a:
        return None
    r = db.execute("SELECT jeton, confirme_le FROM abonnes WHERE adresse = ?", (a,)).fetchone()
    if r:
        return None if r["confirme_le"] else (a, r["jeton"])
    jeton = secrets.token_urlsafe(24)
    try:
        db.execute("INSERT INTO abonnes (adresse, jeton, cree) VALUES (?, ?, ?)", (a, jeton, base.iso()))
        db.commit()
    except base.sqlite3.IntegrityError:   # deux inscriptions simultanées de la même adresse
        db.rollback()
        return None
    return a, jeton


def confirmer(db, jeton):
    """Confirme l'inscription liée au jeton. Rend True si le jeton est connu (déjà confirmé compris)."""
    purger(db)
    if not jeton or len(jeton) > 100:
        return False
    db.execute("UPDATE abonnes SET confirme_le = ? WHERE jeton = ? AND confirme_le IS NULL", (base.iso(), jeton))
    db.commit()
    return db.execute("SELECT 1 FROM abonnes WHERE jeton = ?", (jeton,)).fetchone() is not None


def desinscrire(db, jeton):
    """Supprime la ligne de l'abonné. Rend True si une ligne a été supprimée."""
    if not jeton or len(jeton) > 100:
        return False
    n = db.execute("DELETE FROM abonnes WHERE jeton = ?", (jeton,)).rowcount
    db.commit()
    return n > 0


# ---- les messages

def _message(cfg, adresse, sujet, texte, page):
    m = EmailMessage()
    m["Subject"] = sujet
    m["From"] = formataddr((cfg["nom"], cfg["expediteur"]))
    m["To"] = adresse
    m["Date"] = formatdate(localtime=False)
    m["Message-ID"] = make_msgid(domain=cfg["expediteur"].split("@")[-1])
    m.set_content(texte)
    m.add_alternative(page, subtype="html")
    return m


def _page(corps):
    return ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"></head>'
            '<body style="margin:0;padding:0;background:#f1ede4;color:#16140f">'
            '<div style="max-width:600px;margin:0 auto;padding:20px 16px;font:16px/1.5 Georgia,serif;color:#16140f;background:#f1ede4">'
            '<p style="margin:0 0 16px;font:700 13px/1 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;'
            'border-bottom:2px solid #16140f;padding-bottom:8px">Cadrages</p>' + corps + '</div></body></html>')


def lien_page(cfg, action, jeton):
    """Lien vers la page du site qui demande un clic pour confirmer ou se désinscrire. Le jeton est dans le
    fragment (#) : il n'est envoyé à aucun serveur par le navigateur, ni écrit dans un journal."""
    return f"{cfg['site']}/mail.html#{action}={jeton}"


def message_confirmation(cfg, adresse, jeton):
    lien = lien_page(cfg, "confirmer", jeton)
    texte = ("Bonjour,\n\nCette adresse a été inscrite à la synthèse de la semaine de Cadrages.\n\n"
             f"Pour la recevoir, ouvrez ce lien et cliquez sur « Confirmer » :\n{lien}\n\n"
             f"Sans confirmation sous {JOURS_SANS_CONFIRMATION} jours, l'adresse est effacée.\n"
             "Si vous n'avez rien demandé, ignorez ce mail : rien ne sera envoyé.\n\n"
             f"Cadrages, {cfg['site']}\n")
    page = _page('<p>Bonjour,</p><p>Cette adresse a été inscrite à la synthèse de la semaine de Cadrages.</p>'
                 f'<p><a href="{html.escape(lien)}" style="display:inline-block;padding:10px 16px;border:2px solid #16140f;'
                 'background:#16140f;color:#f1ede4;text-decoration:none;font:700 15px Arial,sans-serif">Confirmer l’inscription</a></p>'
                 f'<p style="font-size:14px">Le lien ouvre une page de Cadrages où un bouton finit l’inscription. Sans confirmation sous '
                 f'{JOURS_SANS_CONFIRMATION} jours, l’adresse est effacée. Si vous n’avez rien demandé, ignorez ce mail : rien ne sera envoyé.</p>')
    return _message(cfg, adresse, "Cadrages : confirmez l'inscription à la synthèse de la semaine", texte, page)


BL = {"extreme-gauche": "Extrême gauche", "gauche": "Gauche", "centre-gauche": "Centre gauche", "centre": "Centre",
      "centre-droit": "Centre droit", "droite": "Droite", "extreme-droite": "Extrême droite"}
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre",
        "décembre")


def _jour(j):
    d = date.fromisoformat(j)
    return f"{d.day} {MOIS[d.month - 1]}"


def titre_semaine(p):
    debut = str(date.fromisoformat(p["debut"]).day) if p["debut"][:7] == p["fin"][:7] else _jour(p["debut"])
    return f"La semaine du {debut} au {_jour(p['fin'])} {p['fin'][:4]}"


def _pl(n, un, plusieurs):
    return f"{n} {plusieurs if n > 1 else un}"


def message_semaine(cfg, adresse, jeton, p):
    """Le mail de la semaine : sujets les plus couverts, silences par bord, éditions gardées, lien vers la page
    Semaine. p : la synthèse de syntheses.periode. Les titres des sujets sont écrits par un modèle : signalés."""
    n = len(p["jours"])
    lien = f"{cfg['site']}/editions/{p['jours'][-1]}.html#/semaine"
    sortie = lien_page(cfg, "desinscrire", jeton)
    titre = titre_semaine(p)
    partielle = n < 7
    editions = _pl(n, "édition gardée", "éditions gardées") + " sur 7" + (" : synthèse partielle." if partielle else ".")
    top = p["top"][:TOP]
    MDL = "écrit par un modèle"

    def stats(x):
        return (_pl(x["medias"], "média", "médias") + ", " + _pl(x["titres"], "titre", "titres")
                + (f", {x['jours']} jours" if x["jours"] > 1 else ""))

    t = [titre, "", editions, "Tout est compté par formule. Seuls les titres des sujets sont écrits par un modèle.", "",
         "LES SUJETS LES PLUS COUVERTS", ""]
    t += [f"{i}. {x['titre']} ({MDL})\n   {stats(x)}" for i, x in enumerate(top, 1)] or ["Aucun sujet."]
    t += ["", "LES SILENCES, BORD PAR BORD",
          f"Un silence : un sujet repris par {p['min_medias']} médias ou plus, sans aucun titre de tout un côté "
          "(gauche, centre ou droite). Il est compté pour chaque bord de ce côté.", ""]
    for c in syntheses.BORDS:
        b = p["bords"].get(c)
        if not b:
            continue
        if not b["medias"]:
            t.append(f"{BL[c]} : aucun journal lu sur la période.")
            continue
        t.append(f"{BL[c]} : {_pl(b['silences'], 'silence', 'silences')} sur {b['sur']} grands sujets.")
        t += [f"   - {x['titre']} ({MDL}), {x['medias']} médias ailleurs" for x in b["tus"]]
    t += ["", f"La synthèse complète : {lien}", "", "--",
          "Ce mail part chaque lundi vers les adresses inscrites sur Cadrages. Il ne sert à rien d'autre.",
          f"Se désinscrire : {sortie}", ""]

    e = html.escape
    tag = (' <span style="font:11px Arial,sans-serif;border:1px solid #5b564b;color:#5b564b;padding:0 4px;'
           f'white-space:nowrap">{MDL}</span>')
    h = [f'<h1 style="font-size:26px;line-height:1.2;margin:0 0 8px">{e(titre)}</h1>',
         f'<p style="font-size:14px;color:#5b564b;margin:0 0 20px">{e(editions)} Tout est compté par formule. '
         'Seuls les titres des sujets sont écrits par un modèle.</p>',
         '<h2 style="font-size:19px;margin:24px 0 8px">Les sujets les plus couverts</h2>']
    h.append('<ol style="padding-left:22px;margin:0">' + "".join(
        f'<li style="margin:0 0 10px"><a href="{e(cfg["site"])}/editions/{e(x["dernier"])}.html#/sujet/{e(x["id"])}" '
        f'style="color:#16140f">{e(x["titre"])}</a>{tag}<br><span style="font:13px Arial,sans-serif;color:#5b564b">'
        f'{e(stats(x))}</span></li>' for x in top) + '</ol>' if top else '<p>Aucun sujet.</p>')
    h.append('<h2 style="font-size:19px;margin:24px 0 8px">Les silences, bord par bord</h2>'
             f'<p style="font-size:14px;color:#5b564b;margin:0 0 12px">Un silence : un sujet repris par {p["min_medias"]} '
             'médias ou plus, sans aucun titre de tout un côté (gauche, centre ou droite). Il est compté pour chaque bord de ce côté.</p>')
    for c in syntheses.BORDS:
        b = p["bords"].get(c)
        if not b:
            continue
        if not b["medias"]:
            h.append(f'<p style="margin:0 0 10px"><b>{BL[c]}</b> : aucun journal lu sur la période.</p>')
            continue
        h.append(f'<p style="margin:0 0 4px"><b>{BL[c]}</b> : {_pl(b["silences"], "silence", "silences")} sur {b["sur"]} grands sujets.</p>')
        if b["tus"]:
            h.append('<ul style="margin:0 0 10px;padding-left:20px;font-size:15px">' + "".join(
                f'<li>{e(x["titre"])}{tag} <span style="font:13px Arial,sans-serif;color:#5b564b">{x["medias"]} médias ailleurs</span></li>'
                for x in b["tus"]) + '</ul>')
    h.append(f'<p style="margin:24px 0"><a href="{e(lien)}" style="display:inline-block;padding:10px 16px;border:2px solid #16140f;'
             'background:#16140f;color:#f1ede4;text-decoration:none;font:700 15px Arial,sans-serif">La synthèse complète</a></p>')
    h.append('<p style="font:13px/1.5 Arial,sans-serif;color:#5b564b;border-top:1px solid #cfc8b6;padding-top:12px">'
             'Ce mail part chaque lundi vers les adresses inscrites sur Cadrages. Il ne sert à rien d’autre. '
             f'<a href="{e(sortie)}" style="color:#5b564b">Se désinscrire</a>.</p>')

    m = _message(cfg, adresse, "Cadrages : " + titre[0].lower() + titre[1:], "\n".join(t), _page("".join(h)))
    # Désinscription en un clic (RFC 8058) : le logiciel de messagerie POSTe « List-Unsubscribe=One-Click » à
    # cette adresse, sans cookie ni page intermédiaire.
    m["List-Unsubscribe"] = f"<{cfg['site']}/api/mail/desinscription?jeton={jeton}>"
    m["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    return m


# ---- l'envoi

def ouvrir_smtp(cfg):
    """Une connexion SMTP authentifiée, en STARTTLS (port 587) ou TLS direct (port 465). Remplacée dans les tests."""
    ctx = ssl.create_default_context()
    if cfg["port"] == 465:
        s = smtplib.SMTP_SSL(cfg["hote"], cfg["port"], timeout=30, context=ctx)
    else:
        s = smtplib.SMTP(cfg["hote"], cfg["port"], timeout=30)
        s.starttls(context=ctx)
    s.login(cfg["utilisateur"], cfg["mot_de_passe"])
    return s


class Envoi:
    """Une connexion ouverte au premier message, rouverte après une panne. Les erreurs ne sortent pas : un
    échec ne bloque pas les messages suivants. Rend True si le message est accepté."""

    def __init__(self, cfg):
        self.cfg, self.smtp = cfg, None

    def envoyer(self, msg):
        try:
            if self.smtp is None:
                self.smtp = ouvrir_smtp(self.cfg)
            self.smtp.send_message(msg)
            return True
        except smtplib.SMTPRecipientsRefused:   # adresse refusée : la connexion reste bonne
            return False
        except Exception as e:                   # le type seulement : un message d'erreur peut citer l'adresse
            dire(f"échec d'envoi : {type(e).__name__}")
            self.fermer()
            return False

    def fermer(self):
        if self.smtp is not None:
            try:
                self.smtp.quit()
            except Exception:
                pass
            self.smtp = None


def envoyer_confirmation(adresse, jeton):
    cfg = config.mail()
    if not cfg:
        return False
    e = Envoi(cfg)
    try:
        ok = e.envoyer(message_confirmation(cfg, adresse, jeton))
    finally:
        e.fermer()
    dire("confirmation : " + ("1 envoyée" if ok else "1 en échec"))
    return ok


def confirmation_plus_tard(adresse, jeton):
    """Le mail de confirmation part dans un fil à part : la réponse au formulaire ne dépend pas de l'envoi, et
    son délai ne trahit pas si l'adresse était déjà connue."""
    if EN_ARRIERE_PLAN:
        threading.Thread(target=envoyer_confirmation, args=(adresse, jeton), daemon=True).start()
    else:
        envoyer_confirmation(adresse, jeton)


def semaine_finie(jour):
    """(clé, lundi, dimanche) de la semaine ISO qui précède celle du jour donné."""
    d = date.fromisoformat(jour) - timedelta(days=7)
    lundi, dimanche = syntheses.bornes_semaine(d.isoformat())
    return syntheses.cle_semaine(lundi), lundi, dimanche


def synthese(db, cle, lundi, dimanche):
    """La synthèse de la semaine, calculée par syntheses.py sur les éditions gardées. None s'il n'y en a aucune."""
    eds = [(r["jour"], json.loads(r["donnees"])) for r in db.execute(
        "SELECT jour, donnees FROM editions WHERE jour BETWEEN ? AND ? ORDER BY jour", (lundi, dimanche))]
    return syntheses.periode(eds, cle, lundi, dimanche) if eds else None


def envoyer_semaine(db, jour=None):
    """Envoie la synthèse de la semaine finie aux abonnés confirmés qui ne l'ont pas encore reçue. Sans effet si
    le mail est éteint ou si tout est déjà parti. Rend {semaine, envoyes, echecs}."""
    cfg = config.mail()
    if not cfg:
        return None
    purger(db)
    cle, lundi, dimanche = semaine_finie(jour or base.paris().strftime("%Y-%m-%d"))
    lignes = db.execute("""SELECT id, adresse, jeton FROM abonnes WHERE confirme_le IS NOT NULL
                           AND (dernier_envoi IS NULL OR dernier_envoi < ?) ORDER BY id""", (cle,)).fetchall()
    t = time.time()
    with _verrou:
        lignes = [r for r in lignes if _echecs.get((cle, r["id"]), (0, 0))[0] < ESSAIS
                  and t - _echecs.get((cle, r["id"]), (0, 0))[1] >= PAUSE_ESSAIS]
    if not lignes:
        return {"semaine": cle, "envoyes": 0, "echecs": 0}
    p = synthese(db, cle, lundi, dimanche)
    if p is None:
        return {"semaine": cle, "envoyes": 0, "echecs": 0, "editions": 0}
    envoi, ok, ko = Envoi(cfg), 0, 0
    try:
        for r in lignes:
            if envoi.envoyer(message_semaine(cfg, r["adresse"], r["jeton"], p)):
                db.execute("UPDATE abonnes SET dernier_envoi = ? WHERE id = ?", (cle, r["id"]))
                db.commit()
                ok += 1
            else:
                ko += 1
                with _verrou:
                    _echecs[(cle, r["id"])] = (_echecs.get((cle, r["id"]), (0, 0))[0] + 1, time.time())
    finally:
        envoi.fermer()
    dire(f"semaine {cle} : {ok} envoyé(s), {ko} en échec")
    return {"semaine": cle, "envoyes": ok, "echecs": ko, "editions": len(p["jours"])}


def essai(db, adresse):
    """Envoie à une seule adresse la synthèse de la dernière semaine finie (ou, à défaut, de la dernière semaine
    qui a des éditions). N'inscrit personne et ne touche pas dernier_envoi. Rend la clé de la semaine, ou None."""
    cfg = config.mail()
    a = normaliser(adresse)
    if not cfg or not a:
        return None
    cle, lundi, dimanche = semaine_finie(base.paris().strftime("%Y-%m-%d"))
    p = synthese(db, cle, lundi, dimanche)
    if p is None:
        r = db.execute("SELECT MAX(jour) AS j FROM editions").fetchone()
        if not r or not r["j"]:
            return None
        lundi, dimanche = syntheses.bornes_semaine(r["j"])
        cle = syntheses.cle_semaine(lundi)
        p = synthese(db, cle, lundi, dimanche)
    r = db.execute("SELECT jeton FROM abonnes WHERE adresse = ?", (a,)).fetchone()
    jeton = r["jeton"] if r else secrets.token_urlsafe(24)   # hors liste : le lien de désinscription ne mène à rien
    e = Envoi(cfg)
    try:
        return cle if e.envoyer(message_semaine(cfg, a, jeton, p)) else None
    finally:
        e.fermer()
