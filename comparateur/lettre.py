"""Les mails du compte : la synthèse de la semaine et l'alerte du matin. Envoi par SMTP (Brevo), bibliothèque
standard seulement. Ce module tourne dans le guichet, jamais dans la fabrique.

Le partage du travail (docs/cadrage-long-terme.md, phase 2) : la fabrique calcule la synthèse de chaque semaine et
la liste des sujets de chaque édition, et les écrit dans le tiroir public (public/lettre/<semaine>.json,
public/alertes/<jour>.json), sans aucune adresse. Le guichet lit ces fichiers et envoie, aux abonnés du tiroir
identité (comptes.py). Il n'ouvre pas la base publique pour cela.

Inscription en double confirmation (comptes.inscrire_lettre), confirmation et désinscription par un bouton (POST)
sur mail.html : rien ne se fait sur un simple GET, les antivirus de messagerie ouvrent les liens tout seuls.
Chaque abonnement a son jeton de sortie ; abonnements.dernier_envoi garde la clé du dernier envoi (« 2026-S46 »,
« 2026-11-17 ») : pas de double envoi, même après un redémarrage.

Aucune adresse n'est écrite dans les journaux : seulement des comptes.
"""
import html, json, os, re, secrets, smtplib, ssl, threading, time
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from . import abonnements, base, comptes, config, syntheses

M = config.MARQUE   # le nom du site, dans chaque mail

JOURS_SANS_CONFIRMATION = comptes.JOURS_SANS_CONFIRMATION
TOP = 10                 # sujets dans le mail
ESSAIS = 3               # essais par adresse et par semaine avant d'abandonner jusqu'à la semaine suivante
PAUSE_ESSAIS = 30 * 60   # secondes entre deux essais pour une même adresse
EN_ARRIERE_PLAN = True   # le mail de confirmation part dans un fil à part (les tests le coupent)

_echecs, _verrou = {}, threading.Lock()


def dire(m):
    print("mail |", m, flush=True)


def normaliser(adresse):
    """L'adresse en minuscules, ou None si elle n'a pas la forme d'une adresse (comptes.normaliser)."""
    from .comptes import normaliser as n
    return n(adresse)


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
            'border-bottom:2px solid #16140f;padding-bottom:8px">' + M + '</p>' + corps + '</div></body></html>')


def lien_page(cfg, action, jeton):
    """Lien vers la page du site qui demande un clic pour confirmer ou se désinscrire. Le jeton est dans le
    fragment (#) : il n'est envoyé à aucun serveur par le navigateur, ni écrit dans un journal."""
    return f"{cfg['site']}/mail.html#{action}={jeton}"


def message_confirmation(cfg, adresse, jeton):
    lien = lien_page(cfg, "confirmer", jeton)
    texte = (f"Bonjour,\n\nCette adresse a été inscrite à la synthèse de la semaine de {M}.\n\n"
             f"Pour la recevoir, ouvrez ce lien et cliquez sur « Confirmer » :\n{lien}\n\n"
             f"Sans confirmation sous {JOURS_SANS_CONFIRMATION} jours, l'adresse est effacée.\n"
             "Si vous n'avez rien demandé, ignorez ce mail : rien ne sera envoyé.\n\n"
             f"{M}, {cfg['site']}\n")
    page = _page(f'<p>Bonjour,</p><p>Cette adresse a été inscrite à la synthèse de la semaine de {M}.</p>'
                 f'<p><a href="{html.escape(lien)}" style="display:inline-block;padding:10px 16px;border:2px solid #16140f;'
                 'background:#16140f;color:#f1ede4;text-decoration:none;font:700 15px Arial,sans-serif">Confirmer l’inscription</a></p>'
                 f'<p style="font-size:14px">Le lien ouvre une page de {M} où un bouton finit l’inscription. Sans confirmation sous '
                 f'{JOURS_SANS_CONFIRMATION} jours, l’adresse est effacée. Si vous n’avez rien demandé, ignorez ce mail : rien ne sera envoyé.</p>')
    return _message(cfg, adresse, f"{M} : confirmez l'inscription à la synthèse de la semaine", texte, page)


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
          f"Ce mail part chaque lundi vers les adresses inscrites sur {M}. Il ne sert à rien d'autre.",
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
             f'Ce mail part chaque lundi vers les adresses inscrites sur {M}. Il ne sert à rien d’autre. '
             f'<a href="{e(sortie)}" style="color:#5b564b">Se désinscrire</a>.</p>')

    m = _message(cfg, adresse, M + " : " + titre[0].lower() + titre[1:], "\n".join(t), _page("".join(h)))
    # Désinscription en un clic (RFC 8058) : le logiciel de messagerie POSTe « List-Unsubscribe=One-Click » à
    # cette adresse, sans cookie ni page intermédiaire.
    m["List-Unsubscribe"] = f"<{cfg['site']}/api/mail/desinscription?jeton={jeton}>"
    m["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    return m


def message_alerte(cfg, adresse, lignes, a):
    """L'alerte du matin d'un compte : l'édition est parue (type alerte-edition), et les sujets du jour de chaque
    rubrique suivie (type rubrique). `lignes` : les abonnements du compte à servir ; `a` : public/alertes/<jour>.json.
    Les titres des sujets sont écrits par un modèle : signalés. Un lien de sortie par abonnement."""
    MDL = "écrit par un modèle"
    e = html.escape
    page = f"{cfg['site']}{a.get('page') or '/'}"
    sujets = a.get("sujets", [])
    titre = f"L’édition du {_jour(a['jour'])} est parue"
    t, h = [titre, ""], [f'<h1 style="font-size:24px;line-height:1.2;margin:0 0 12px">{e(titre)}</h1>']
    tag = (' <span style="font:11px Arial,sans-serif;border:1px solid #5b564b;color:#5b564b;padding:0 4px;'
           f'white-space:nowrap">{MDL}</span>')

    def liste(ss):
        t.extend(f"- {x['titre']} ({MDL}), {_pl(x['medias'], 'média', 'médias')}\n  {cfg['site']}{x['page']}" for x in ss)
        h.append('<ul style="padding-left:20px;margin:0 0 14px">' + "".join(
            f'<li style="margin:0 0 6px"><a href="{e(cfg["site"] + x["page"])}" style="color:#16140f">{e(x["titre"])}</a>{tag}'
            f' <span style="font:13px Arial,sans-serif;color:#5b564b">{_pl(x["medias"], "média", "médias")}</span></li>'
            for x in ss) + '</ul>')

    types = {r["type"] for r in lignes}
    if "alerte-edition" in types:
        t.append(f"{_pl(len(sujets), 'sujet', 'sujets')} dans l'édition. Les plus couverts :")
        h.append(f'<p style="margin:0 0 8px">{_pl(len(sujets), "sujet", "sujets")} dans l’édition. Les plus couverts :</p>')
        liste(sujets[:5])
    for r in (r for r in lignes if r["type"] == "rubrique"):
        nom = abonnements.NOMS_RUBRIQUES.get(r["cible"], r["cible"])
        ss = [x for x in sujets if r["cible"] in x.get("rubriques", [])]
        t += ["", f"RUBRIQUE {nom.upper()}"]
        h.append(f'<h2 style="font-size:18px;margin:18px 0 6px">Rubrique {e(nom)}</h2>')
        if ss:
            liste(ss[:8])
        else:
            t.append("Aucun sujet de cette rubrique aujourd'hui.")
            h.append('<p style="margin:0 0 10px">Aucun sujet de cette rubrique aujourd’hui.</p>')
    t += ["", f"L'édition complète : {page}", "", "--",
          "La rubrique d'un sujet est lue dans l'adresse de ses articles, par un programme. Les comptes ne gardent rien d'autre que ces choix."]
    h.append(f'<p style="margin:20px 0"><a href="{e(page)}" style="display:inline-block;padding:10px 16px;border:2px solid #16140f;'
             'background:#16140f;color:#f1ede4;text-decoration:none;font:700 15px Arial,sans-serif">L’édition complète</a></p>')
    sorties = []
    for r in lignes:
        quoi = "l’alerte du matin" if r["type"] == "alerte-edition" else "la rubrique " + abonnements.NOMS_RUBRIQUES.get(r["cible"], r["cible"])
        sorties.append((quoi, lien_page(cfg, "desinscrire", r["sortie"])))
    t += [f"Ne plus recevoir {q} : {l}" for q, l in sorties] + [""]
    h.append('<p style="font:13px/1.6 Arial,sans-serif;color:#5b564b;border-top:1px solid #cfc8b6;padding-top:12px">'
             'La rubrique d’un sujet est lue dans l’adresse de ses articles, par un programme.<br>' +
             "<br>".join(f'<a href="{e(l)}" style="color:#5b564b">Ne plus recevoir {e(q)}</a>' for q, l in sorties) + '</p>')
    m = _message(cfg, adresse, f"{M} : " + titre[0].lower() + titre[1:], "\n".join(t), _page("".join(h)))
    premiere = next((r for r in lignes if r["type"] == "alerte-edition"), lignes[0])
    m["List-Unsubscribe"] = f"<{cfg['site']}/api/mail/desinscription?jeton={premiere['sortie']}>"
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


def message_code(cfg, adresse, code):
    """Le code de connexion au compte : six chiffres, dix minutes, sans lien (un lien serait ouvert par les
    antivirus de messagerie)."""
    texte = (f"Bonjour,\n\nVotre code pour {M} : {code}\n\nTapez-le sur la page qui vous l'a demandé. Il vaut dix "
             "minutes et ne sert qu'une fois.\nSi vous n'avez rien demandé, ignorez ce mail : sans le code, personne ne "
             f"peut entrer.\n\n{M}, {cfg['site']}\n")
    page = _page(f'<p>Bonjour,</p><p>Votre code pour {M} :</p><p style="font:700 32px/1.2 Arial,sans-serif;letter-spacing:.2em;'
                 f'margin:12px 0">{html.escape(code)}</p><p style="font-size:14px">Tapez-le sur la page qui vous l’a demandé. '
                 'Il vaut dix minutes et ne sert qu’une fois. Si vous n’avez rien demandé, ignorez ce mail : sans le code, '
                 'personne ne peut entrer.</p>')
    return _message(cfg, adresse, f"{M} : votre code, {code}", texte, page)


def _envoyer_un(fabriquer, nom):
    cfg = config.mail()
    if not cfg:
        return False
    e = Envoi(cfg)
    try:
        ok = e.envoyer(fabriquer(cfg))
    finally:
        e.fermer()
    dire(f"{nom} : " + ("1 envoyé" if ok else "1 en échec"))
    return ok


def plus_tard(fonction, *args):
    """Un mail court (code, confirmation) part dans un fil à part : la réponse au formulaire ne dépend pas de
    l'envoi, et son délai ne trahit pas si l'adresse était déjà connue."""
    if EN_ARRIERE_PLAN:
        threading.Thread(target=fonction, args=args, daemon=True).start()
    else:
        fonction(*args)


def envoyer_code(adresse, code):
    return _envoyer_un(lambda cfg: message_code(cfg, adresse, code), "code")


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


def _lire_public(*chemin):
    """Un fichier du tiroir public écrit par la fabrique, ou None. Le guichet ne lit que cela."""
    try:
        with open(os.path.join(config.public(), *chemin), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def synthese(cle):
    """La synthèse de la semaine `cle`, telle que la fabrique l'a écrite (publier.ecrire_tiroir_mails)."""
    if not re.fullmatch(r"\d{4}-S\d{2}", cle or ""):
        return None
    return _lire_public("lettre", cle + ".json")


def alerte(jour):
    """Les sujets de l'édition du jour, avec leurs rubriques, tels que la fabrique les a écrits."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", jour or ""):
        return None
    return _lire_public("alertes", jour + ".json")


def _envoyer_par_lots(ident, lignes, cle, fabriquer):
    """Un mail par compte (ses lignes d'abonnement groupées), trois essais espacés en cas d'échec. Rend (ok, ko)."""
    cfg = config.mail()
    t = time.time()
    par_compte = {}
    for r in lignes:
        par_compte.setdefault(r["compte"], []).append(r)
    with _verrou:
        comptes_ = [c for c in par_compte if _echecs.get((cle, c), (0, 0))[0] < ESSAIS
                    and t - _echecs.get((cle, c), (0, 0))[1] >= PAUSE_ESSAIS]
    envoi, ok, ko = Envoi(cfg), 0, 0
    try:
        for c in comptes_:
            ls = par_compte[c]
            if envoi.envoyer(fabriquer(cfg, ls[0]["adresse"], ls)):
                comptes.noter_envoi(ident, [r["id"] for r in ls], cle)
                ok += 1
            else:
                ko += 1
                with _verrou:
                    _echecs[(cle, c)] = (_echecs.get((cle, c), (0, 0))[0] + 1, time.time())
    finally:
        envoi.fermer()
    return ok, ko


def envoyer_semaine(ident, jour=None):
    """Envoie la synthèse de la semaine finie aux abonnés de la lettre qui ne l'ont pas encore reçue. Sans effet si
    le mail est éteint, si la fabrique n'a pas encore écrit la synthèse, ou si tout est déjà parti.
    Rend {semaine, envoyes, echecs[, editions]}, ou None."""
    if not config.mail():
        return None
    comptes.purger(ident)
    cle, _, _ = semaine_finie(jour or base.paris().strftime("%Y-%m-%d"))
    lignes = comptes.destinataires(ident, ["lettre"], cle)
    if not lignes:
        return {"semaine": cle, "envoyes": 0, "echecs": 0}
    p = synthese(cle)
    if p is None:
        return {"semaine": cle, "envoyes": 0, "echecs": 0, "editions": 0}
    ok, ko = _envoyer_par_lots(ident, lignes, cle, lambda cfg, a, ls: message_semaine(cfg, a, ls[0]["sortie"], p))
    dire(f"semaine {cle} : {ok} envoyé(s), {ko} en échec")
    return {"semaine": cle, "envoyes": ok, "echecs": ko, "editions": len(p["jours"])}


def envoyer_alertes(ident, jour=None):
    """L'alerte du matin : l'édition du jour est parue, et les sujets des rubriques suivies. Un mail par compte, une
    fois par jour, quand la fabrique a écrit public/alertes/<jour>.json. Rend {jour, envoyes, echecs}, ou None."""
    if not config.mail():
        return None
    jour = jour or base.paris().strftime("%Y-%m-%d")
    lignes = comptes.destinataires(ident, ["alerte-edition", "rubrique"], jour)
    if not lignes:
        return {"jour": jour, "envoyes": 0, "echecs": 0}
    a = alerte(jour)
    if a is None:
        return {"jour": jour, "envoyes": 0, "echecs": 0, "edition": False}
    ok, ko = _envoyer_par_lots(ident, lignes, jour, lambda cfg, ad, ls: message_alerte(cfg, ad, ls, a))
    dire(f"alerte du {jour} : {ok} envoyée(s), {ko} en échec")
    return {"jour": jour, "envoyes": ok, "echecs": ko}


def essai(adresse):
    """Envoie à une seule adresse la synthèse de la dernière semaine écrite par la fabrique. N'inscrit personne.
    Rend la clé de la semaine, ou None."""
    cfg = config.mail()
    a = normaliser(adresse)
    if not cfg or not a:
        return None
    cle, _, _ = semaine_finie(base.paris().strftime("%Y-%m-%d"))
    p = synthese(cle)
    if p is None:
        try:
            cles = sorted(n[:-5] for n in os.listdir(os.path.join(config.public(), "lettre")) if n.endswith(".json"))
        except OSError:
            cles = []
        if not cles:
            return None
        cle, p = cles[-1], synthese(cles[-1])
    e = Envoi(cfg)
    try:   # un jeton de sortie qui ne mène à rien : l'adresse d'essai n'est inscrite nulle part
        return cle if e.envoyer(message_semaine(cfg, a, secrets.token_urlsafe(24), p)) else None
    finally:
        e.fermer()
