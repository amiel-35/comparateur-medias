"""Réglages, tous lus dans l'environnement (voir .env.example). Aucun secret dans le code."""
import os

ICI = os.path.dirname(os.path.abspath(__file__))

# Le nom du site. Les mails le lisent ici ; le manifeste et les pages l'écrivent en dur, et un test vérifie que
# c'est le même partout.
MARQUE = "Cadrages"


def env(nom, defaut):
    v = os.environ.get(nom)
    return defaut if v is None or v == "" else v


def donnees():
    """Dossier persistant : base SQLite, cache des appels modèle, site généré."""
    d = env("COMPARATEUR_DONNEES", os.path.join(os.path.dirname(ICI), "donnees"))
    os.makedirs(d, exist_ok=True)
    return d


def base():
    return os.path.join(donnees(), "comparateur.db")


def public():
    d = os.path.join(donnees(), "public")
    os.makedirs(os.path.join(d, "data"), exist_ok=True)
    return d


def port():
    return int(env("PORT", "8080"))


def mode_llm():
    """'cli' : `claude -p` (abonnement, poste de développement). 'api' : API Anthropic (serveur)."""
    return env("COMPARATEUR_LLM", "cli")


def budget_jour_usd():
    """Plafond de dépense modèle par jour, au tarif public. La fabrique s'arrête au-delà."""
    return float(env("COMPARATEUR_BUDGET_JOUR_USD", "2"))


def heures():
    """Fenêtre d'actualité : âge maximal d'un titre pris en compte."""
    return int(env("COMPARATEUR_HEURES", "24"))


def min_par_bord():
    """Nombre de votants requis dans chaque bord pour publier une note à l'aveugle sans réserve."""
    return int(env("COMPARATEUR_MIN_PAR_BORD", "5"))


def confiance_proxy():
    """1 derrière un proxy (Coolify/Traefik) : l'adresse du visiteur est lue dans X-Forwarded-For."""
    return env("COMPARATEUR_DERRIERE_PROXY", "0") == "1"


def fabrique_minutes():
    """Si > 0, le serveur lance lui-même la fabrique : c'est l'intervalle entre deux récoltes des flux, en minutes."""
    return int(env("COMPARATEUR_FABRIQUE_MINUTES", "0"))


def edition_heure():
    """Heure (0-23, heure de Paris) à laquelle l'édition du jour est fabriquée, une fois par jour."""
    return max(0, min(23, int(env("COMPARATEUR_EDITION_HEURE", "6"))))


def rubriques_ecartees():
    """Rubriques dont les articles ne sont ni proposés au regroupement ni comptés dans les sujets (ils restent
    en base). Liste séparée par des virgules ; « aucune » pour ne rien écarter."""
    v = env("COMPARATEUR_RUBRIQUES_ECARTEES", "sport,culture").lower()
    return sorted({x.strip() for x in v.split(",") if x.strip() and x.strip() != "aucune"})


def umami():
    """Mesure de fréquentation par Umami (sans cookie), hébergé par l'éditeur. Sans identifiant : aucune mesure.
    Rend None, ou {id, script, origine, domaines}."""
    ident = env("COMPARATEUR_UMAMI_ID", "")
    if not ident:
        return None
    script = env("COMPARATEUR_UMAMI_SCRIPT", "https://stats.inflexion.me/script.js")
    origine = "/".join(script.split("/")[:3])
    return {"id": ident, "script": script, "origine": origine,
            "domaines": env("COMPARATEUR_UMAMI_DOMAINES", "compare-media.inflexion.me")}


def site_url():
    """Adresse publique du site, sans barre finale : sert aux liens des mails."""
    return env("COMPARATEUR_SITE_URL", "https://compare-media.inflexion.me").rstrip("/")


def mail():
    """La synthèse de la semaine par mail, envoyée en SMTP (Brevo par défaut). Sans utilisateur ou sans mot de passe
    SMTP, la fonction est éteinte : pas de formulaire, aucun envoi. Rend None, ou les réglages d'envoi."""
    utilisateur, mot_de_passe = env("COMPARATEUR_SMTP_UTILISATEUR", ""), env("COMPARATEUR_SMTP_MOT_DE_PASSE", "")
    if not utilisateur or not mot_de_passe:
        return None
    return {"hote": env("COMPARATEUR_SMTP_HOTE", "smtp-relay.brevo.com"),
            "port": int(env("COMPARATEUR_SMTP_PORT", "587")),   # 587 : STARTTLS ; 465 : TLS direct
            "utilisateur": utilisateur, "mot_de_passe": mot_de_passe,
            "expediteur": env("COMPARATEUR_MAIL_EXPEDITEUR", "no-reply@inflexion.me"),
            "nom": MARQUE, "site": site_url()}


def identites():
    """Dossier du tiroir identité (identites.db). Dans le compose, un volume à part, monté sur le guichet seul :
    la fabrique ne le voit pas. Par défaut, le dossier des données."""
    d = env("COMPARATEUR_IDENTITES", donnees())
    os.makedirs(d, exist_ok=True)
    return d


def hotes():
    """Les trois noms d'hôte servis par le même serveur, triés sur l'en-tête Host : le site, le compte, l'urne.
    Par défaut, compte.<hôte du site> et urne.<hôte du site> (décision du 17/11/2026 : compte.compare-media.inflexion.me
    et urne.compare-media.inflexion.me). En local : compte.localhost et urne.localhost."""
    site = site_url().split("://", 1)[-1].split("/")[0].split(":")[0].lower()
    return {"site": site,
            "compte": env("COMPARATEUR_HOTE_COMPTE", "compte." + site).lower(),
            "urne": env("COMPARATEUR_HOTE_URNE", "urne." + site).lower()}


def mail_en_service():
    """Le mail est-il en service ? Le guichet le sait par ses réglages SMTP. La fabrique, qui ne tient pas la clé
    d'envoi, le sait par COMPARATEUR_MAIL_EN_SERVICE=1 : elle s'en sert pour montrer ou non le formulaire et le lien
    du compte dans les pages."""
    return mail() is not None or env("COMPARATEUR_MAIL_EN_SERVICE", "0") == "1"


def compte_url():
    """Adresse de la page du compte, ou None si le mail est éteint (sans mail, pas de compte : aucun code à envoyer)."""
    if not mail_en_service():
        return None
    schema = "http" if site_url().startswith("http://") else "https"
    return env("COMPARATEUR_COMPTE_URL", f"{schema}://{hotes()['compte']}").rstrip("/")
