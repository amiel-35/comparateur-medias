"""Réglages, tous lus dans l'environnement (voir .env.example). Aucun secret dans le code."""
import os

ICI = os.path.dirname(os.path.abspath(__file__))


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
    return int(env("COMPARATEUR_HEURES", "30"))


def min_par_bord():
    """Nombre de votants requis dans chaque bord pour publier une note à l'aveugle sans réserve."""
    return int(env("COMPARATEUR_MIN_PAR_BORD", "5"))


def confiance_proxy():
    """1 derrière un proxy (Coolify/Traefik) : l'adresse du visiteur est lue dans X-Forwarded-For."""
    return env("COMPARATEUR_DERRIERE_PROXY", "0") == "1"


def fabrique_minutes():
    """Si > 0, le serveur lance lui-même la fabrique à cet intervalle (sinon : tâche planifiée externe)."""
    return int(env("COMPARATEUR_FABRIQUE_MINUTES", "0"))
