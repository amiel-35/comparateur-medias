"""Base de données. SQLite aujourd'hui ; SQL gardé simple pour passer à PostgreSQL sans réécriture.

Dates en UTC (ISO 8601). Un article = l'empreinte de son adresse. La note d'un média est une donnée
(table notes_media : une ligne par méthode, avec source et confiance), jamais une constante du code.
"""
import hashlib, json, os, sqlite3
from datetime import datetime, timedelta, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS medias (
  id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE, flux TEXT NOT NULL DEFAULT '[]',
  proprietaire TEXT, actif INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS notes_media (
  id INTEGER PRIMARY KEY, media_id INTEGER NOT NULL REFERENCES medias(id), note REAL NOT NULL,
  methode TEXT NOT NULL, source TEXT NOT NULL, confiance TEXT NOT NULL, effectif INTEGER, cree TEXT NOT NULL,
  UNIQUE (media_id, methode, source));
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY, cle TEXT NOT NULL UNIQUE, media_id INTEGER NOT NULL REFERENCES medias(id),
  titre TEXT NOT NULL, lien TEXT NOT NULL DEFAULT '', date TEXT, recolte TEXT NOT NULL,
  trie INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS articles_recolte ON articles(recolte);
CREATE TABLE IF NOT EXISTS sujets (id INTEGER PRIMARY KEY, libelle TEXT NOT NULL, cree TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sujet_articles (
  sujet_id INTEGER NOT NULL REFERENCES sujets(id), article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id));
CREATE INDEX IF NOT EXISTS sujet_articles_sujet ON sujet_articles(sujet_id);
CREATE TABLE IF NOT EXISTS analyses (
  sujet_id INTEGER PRIMARY KEY REFERENCES sujets(id), titre TEXT NOT NULL, fait TEXT NOT NULL,
  g TEXT NOT NULL, c TEXT NOT NULL, d TEXT NOT NULL, mots TEXT NOT NULL DEFAULT '[]', ecart INTEGER,
  empreinte TEXT NOT NULL, modele TEXT NOT NULL, cree TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invitations (code TEXT PRIMARY KEY, cree TEXT NOT NULL, utilisee_le TEXT);
CREATE TABLE IF NOT EXISTS votants (id TEXT PRIMARY KEY, bord INTEGER NOT NULL, cree TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lots_aveugle (
  id INTEGER PRIMARY KEY, media_id INTEGER NOT NULL REFERENCES medias(id), jour TEXT NOT NULL,
  titres TEXT NOT NULL, cree TEXT NOT NULL, UNIQUE (media_id, jour));
CREATE TABLE IF NOT EXISTS avis_aveugle (
  votant_id TEXT NOT NULL REFERENCES votants(id), lot_id INTEGER NOT NULL REFERENCES lots_aveugle(id),
  note INTEGER NOT NULL, cree TEXT NOT NULL, PRIMARY KEY (votant_id, lot_id));
CREATE TABLE IF NOT EXISTS avis_note (
  votant_id TEXT NOT NULL REFERENCES votants(id), media_id INTEGER NOT NULL REFERENCES medias(id),
  accord INTEGER NOT NULL, cree TEXT NOT NULL, PRIMARY KEY (votant_id, media_id));
-- Une édition par jour : la photographie complète de ce que le site affichait ce jour-là.
CREATE TABLE IF NOT EXISTS editions (jour TEXT PRIMARY KEY, cree TEXT NOT NULL, donnees TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS journal_fabrique (
  id INTEGER PRIMARY KEY, etape TEXT NOT NULL, debut TEXT NOT NULL, fin TEXT, ok INTEGER, detail TEXT);
"""


def maintenant():
    return datetime.now(timezone.utc)


def paris(d=None):
    """L'instant donné (défaut : maintenant) à l'heure de Paris : les éditions sont datées en heure française."""
    d = d or maintenant()
    try:
        from zoneinfo import ZoneInfo
        return d.astimezone(ZoneInfo("Europe/Paris"))
    except Exception:  # pas de base de fuseaux sur la machine : heure d'hiver, à une heure près l'été
        return d.astimezone(timezone(timedelta(hours=1)))


def iso(d=None):
    return (d or maintenant()).isoformat(timespec="seconds")


def depuis():
    """Borne basse de la fenêtre d'actualité (ISO)."""
    return iso(maintenant() - timedelta(hours=config.heures()))


def connexion():
    db = sqlite3.connect(config.base(), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    return db


def bord(score):
    """Découpage en cinq bords à partir du score (choix du comparateur, pas de FrIdéo)."""
    return ("gauche" if score <= -1.0 else "centre-gauche" if score <= -0.5 else
            "droite" if score >= 1.0 else "centre-droit" if score >= 0.5 else "centre")


COTE = {"gauche": "g", "centre-gauche": "g", "centre": "c", "centre-droit": "d", "droite": "d"}


def cle_article(media, titre, lien):
    return hashlib.sha256((lien or (media + "\0" + titre)).encode()).hexdigest()[:32]


def charger_medias(db, chemin=None):
    """Charge ou met à jour la liste des médias et leur note de départ (FrIdéo) depuis medias.json."""
    chemin = chemin or os.path.join(config.ICI, "medias.json")
    ref = json.load(open(chemin, encoding="utf-8"))
    for m in ref["medias"]:
        db.execute("INSERT INTO medias (nom, flux) VALUES (?, ?) ON CONFLICT(nom) DO UPDATE SET flux = excluded.flux",
                   (m["nom"], json.dumps(m["flux"])))
        mid = db.execute("SELECT id FROM medias WHERE nom = ?", (m["nom"],)).fetchone()["id"]
        db.execute("""INSERT INTO notes_media (media_id, note, methode, source, confiance, cree)
                      VALUES (?, ?, 'etude tierce', ?, 'moyenne', ?)
                      ON CONFLICT(media_id, methode, source) DO UPDATE SET note = excluded.note""",
                   (mid, m["score"], ref["source"], iso()))
    db.commit()
    return len(ref["medias"])


def scores(db):
    """Note de référence par média : la note 'etude tierce' (FrIdéo) la plus récente. Rend {media_id: note}.
    Une nouvelle version du classement s'ajoute sans effacer l'ancienne : l'historique des scores est gardé."""
    return {r["media_id"]: r["note"] for r in   # la plus récente écrase les précédentes, qui restent en base
            db.execute("SELECT media_id, note FROM notes_media WHERE methode = 'etude tierce' ORDER BY cree, id")}


class Etape:
    """Trace une étape de la fabrique dans journal_fabrique (durée, succès, détail)."""

    def __init__(self, db, nom):
        self.db, self.nom, self.detail = db, nom, {}

    def __enter__(self):
        cur = self.db.execute("INSERT INTO journal_fabrique (etape, debut) VALUES (?, ?)", (self.nom, iso()))
        self.id = cur.lastrowid
        self.db.commit()
        return self

    def __exit__(self, typ, err, tb):
        if err is not None:
            self.detail["erreur"] = f"{typ.__name__}: {err}"[:500]
        self.db.execute("UPDATE journal_fabrique SET fin = ?, ok = ?, detail = ? WHERE id = ?",
                        (iso(), 0 if err else 1, json.dumps(self.detail, ensure_ascii=False), self.id))
        self.db.commit()
        return False
