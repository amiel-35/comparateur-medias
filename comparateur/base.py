"""Base de données. SQLite aujourd'hui ; SQL gardé simple pour passer à PostgreSQL sans réécriture.

Dates en UTC (ISO 8601). Un article = l'empreinte de son adresse. La note d'un média est une donnée
(table notes_media : une ligne par méthode, avec source et confiance), jamais une constante du code.
"""
import hashlib, json, os, re, sqlite3
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
  trie INTEGER NOT NULL DEFAULT 0, rubrique TEXT);
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
-- methode, classement : les versions qui l'ont produite (« 1.0 », « FrIdéo v1.0 »). '' : édition d'avant la
-- numérotation de la méthode. Elles sont à côté des données, qui ne sont jamais réécrites.
CREATE TABLE IF NOT EXISTS editions (jour TEXT PRIMARY KEY, cree TEXT NOT NULL, donnees TEXT NOT NULL,
  methode TEXT, classement TEXT);
-- La synthèse de la semaine par mail. Une désinscription supprime la ligne. dernier_envoi : clé de la dernière
-- semaine envoyée (« 2026-S46 »), contre tout double envoi.
CREATE TABLE IF NOT EXISTS abonnes (
  id INTEGER PRIMARY KEY, adresse TEXT NOT NULL UNIQUE, jeton TEXT NOT NULL UNIQUE, cree TEXT NOT NULL,
  confirme_le TEXT, dernier_envoi TEXT);
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
    migrer(db)
    return db


def migrer(db):
    """Met une base d'avant au schéma courant, sans rien perdre. Rend True si quelque chose a changé."""
    a = migrer_rubrique(db)
    b = migrer_dates(db)
    c = migrer_versions(db)
    return a or b or c


def migrer_versions(db):
    """Les colonnes editions.methode et editions.classement. Une édition déjà gardée reçoit les versions qui l'ont
    produite, sans que ses données soient réécrites : méthode '' si elle précède la version 1.0 (première numérotée),
    la version 1.0 si elle est de son jour ou d'après,
    classement relu dans la source citée par l'édition elle-même (« FrIdéo v1.0 »), '' s'il n'y figure pas."""
    from . import methode
    colonnes = {c[1] for c in db.execute("PRAGMA table_info(editions)")}
    if not colonnes:   # pas de table editions (une base partielle, dans un essai)
        return False
    try:
        for c in ("methode", "classement"):
            if c not in colonnes:
                db.execute(f"ALTER TABLE editions ADD COLUMN {c} TEXT")
    except sqlite3.OperationalError:   # une autre connexion vient de les ajouter
        pass
    # Les lignes encore sans version : celles d'avant les colonnes, et celles qu'un arrêt entre l'ALTER et l'UPDATE
    # aurait laissées. Une édition faite le jour de la version 1.0 ou après en suit les règles.
    maj = []
    for jour, donnees in db.execute("SELECT jour, donnees FROM editions WHERE methode IS NULL").fetchall():
        try:
            source = str(json.loads(donnees).get("source_classement") or "")
        except ValueError:
            source = ""
        m = re.search(r"FrIdéo v[\d.]+\d", source)
        maj.append((methode.VERSION if jour >= methode.DATE else "", m.group(0) if m else "", jour))
    if not maj:
        return False
    db.executemany("UPDATE editions SET methode = ?, classement = ? WHERE jour = ?", maj)
    db.commit()
    return True


def migrer_rubrique(db):
    """La colonne articles.rubrique. NULL = rubrique pas encore déduite (article d'avant la colonne),
    '' = aucune rubrique reconnue."""
    if "rubrique" in {c[1] for c in db.execute("PRAGMA table_info(articles)")}:
        return False
    try:
        db.execute("ALTER TABLE articles ADD COLUMN rubrique TEXT")
    except sqlite3.OperationalError:   # une autre connexion vient de l'ajouter
        return False
    from .fabrique import rubrique     # import tardif : fabrique importe base
    db.executemany("UPDATE articles SET rubrique = ? WHERE id = ?",
                   [(rubrique(r[1]), r[0]) for r in db.execute("SELECT id, lien FROM articles").fetchall()])
    db.commit()
    return True


def migrer_dates(db):
    """Ramène en temps universel les dates gardées avec le décalage de leur flux (+01:00 par exemple).
    Elles sont comparées comme du texte à des bornes en temps universel : un autre décalage les fausse."""
    lignes = db.execute("SELECT id, date FROM articles WHERE date IS NOT NULL AND date NOT LIKE '%+00:00'").fetchall()
    maj = []
    for i, d in lignes:
        try:
            x = datetime.fromisoformat(d)
        except ValueError:   # date illisible : on la laisse telle quelle
            continue
        maj.append((iso((x if x.tzinfo else x.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)), i))
    if not maj:
        return False
    db.executemany("UPDATE articles SET date = ? WHERE id = ?", maj)
    db.commit()
    return True


BANDES = ("extreme-gauche", "gauche", "centre-gauche", "centre", "centre-droit", "droite", "extreme-droite")
SEUILS_FRIDEO = (-1.5, -0.75, -0.25, 0.25, 0.75, 1.5)   # `label_cutoffs` du jeu de données FrIdéo v1.0


def bord(score):
    """La bande FrIdéo d'un score : sept bandes, avec les seuils publiés par FrIdéo. Ce n'est pas un choix du
    comparateur : le classement, ses bandes et leurs noms sont ceux du French News Lab."""
    return BANDES[sum(1 for seuil in SEUILS_FRIDEO if score >= seuil)]


# Les trois côtés servent aux textes d'angle et aux silences : c'est le seul regroupement fait par le comparateur.
COTE = {"extreme-gauche": "g", "gauche": "g", "centre-gauche": "g", "centre": "c",
        "centre-droit": "d", "droite": "d", "extreme-droite": "d"}


def cle_article(media, titre, lien):
    return hashlib.sha256((lien or (media + "\0" + titre)).encode()).hexdigest()[:32]


def statut(note):
    """« classe » : le média a une note FrIdéo, donc une bande. « non-classe » : il est lu, ses titres comptent dans
    la couverture d'un sujet, mais dans aucun bord ni aucun silence. Ce site ne classe aucun média lui-même : un
    média hors de FrIdéo reste non classé."""
    return "non-classe" if note is None else "classe"


def charger_medias(db, chemin=None):
    """Charge ou met à jour la liste des médias et leur note de départ (FrIdéo) depuis medias.json. Un média sans
    score (« score »: null) est non classé : il est lu, aucune note n'est écrite pour lui."""
    chemin = chemin or os.path.join(config.ICI, "medias.json")
    ref = json.load(open(chemin, encoding="utf-8"))
    for m in ref["medias"]:
        db.execute("INSERT INTO medias (nom, flux) VALUES (?, ?) ON CONFLICT(nom) DO UPDATE SET flux = excluded.flux",
                   (m["nom"], json.dumps(m["flux"])))
        mid = db.execute("SELECT id FROM medias WHERE nom = ?", (m["nom"],)).fetchone()["id"]
        if m.get("score") is None:
            continue
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
