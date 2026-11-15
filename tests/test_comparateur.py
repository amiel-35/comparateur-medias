"""Tests du back-end, sans réseau ni modèle.  Depuis back/ :  python3 -m unittest discover -s tests -v"""
import json, os, shutil, sys, tempfile, threading, unittest, urllib.error, urllib.request

DOSSIER = tempfile.mkdtemp(prefix="comparateur-test-")
os.environ["COMPARATEUR_DONNEES"] = DOSSIER
os.environ["COMPARATEUR_MIN_PAR_BORD"] = "2"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from comparateur import aveugle, base, fabrique, llm, publier, serveur, syntheses  # noqa: E402


def tearDownModule():
    shutil.rmtree(DOSSIER, ignore_errors=True)


RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Premier &amp; titre</title><link>https://exemple.test/a</link><pubDate>Sat, 14 Nov 2026 10:00:00 +0000</pubDate></item>
<item><title><![CDATA[Second titre]]></title><link>https://exemple.test/b</link></item>
</channel></rss>"""
ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Titre atom</title>
<link href="https://exemple.test/c"/><updated>2026-11-14T09:00:00Z</updated></entry></feed>"""


class Flux(unittest.TestCase):
    def test_rss_garde_dates_et_liens(self):
        its = fabrique.items(RSS)
        self.assertEqual([i["titre"] for i in its], ["Premier & titre", "Second titre"])
        self.assertEqual(its[0]["date"].hour, 10)       # le bogue du script d'origine perdait cette date
        self.assertIsNone(its[1]["date"])
        self.assertEqual(its[1]["lien"], "https://exemple.test/b")

    def test_atom(self):
        its = fabrique.items(ATOM)
        self.assertEqual((its[0]["titre"], its[0]["lien"]), ("Titre atom", "https://exemple.test/c"))
        self.assertIsNotNone(its[0]["date"])

    def test_flux_mal_forme(self):
        casse = b"<rss><channel><item><title>Titre & casse</title><link>https://exemple.test/d</link></item></channel>"
        self.assertEqual(fabrique.items(casse)[0]["titre"], "Titre & casse")


class Aveugle(unittest.TestCase):
    def test_retire_les_marques_du_media(self):
        self.assertEqual(aveugle.nettoyer("INFO JDD. Manifestations à Paris : une note du renseignement alerte", "Le JDD"),
                         "Manifestations à Paris : une note du renseignement alerte")
        self.assertEqual(aveugle.nettoyer("EN DIRECT - Colère sociale : 50 cortèges attendus dans tout le pays", "Le Figaro"),
                         "Colère sociale : 50 cortèges attendus dans tout le pays")

    def test_ecarte_un_titre_qui_nomme_le_media(self):
        self.assertIsNone(aveugle.nettoyer("Blocage des lycées : sur LCI, Jordan Bardella prône la tolérance zéro", "TF1 INFO"))
        self.assertIsNone(aveugle.nettoyer("Ukraine : invitée par Zelensky dans L'Express, Marine Le Pen accepte", "L'Express"))
        self.assertIsNone(aveugle.nettoyer("Trop court", "Le Monde"))

    def test_la_typographie_maison_est_effacee(self):
        a = aveugle.uniformiser("«Ce n’est pas arrivé depuis le 11-Septembre» : 6.000 vols annulés…")
        b = aveugle.uniformiser('« Ce n\'est pas arrivé depuis le 11-Septembre »: 6\u00a0000 vols annulés...')
        self.assertEqual(a, b)
        self.assertEqual(a, '"Ce n\'est pas arrivé depuis le 11-Septembre" : 6 000 vols annulés...')
        self.assertEqual(aveugle.uniformiser("Budget 2027 – la gauche vote contre."), "Budget 2027 - la gauche vote contre")

    def test_un_bord_nombreux_ne_pese_pas_plus(self):
        # 100 votants de gauche disent « centre » (0), 2 du centre et 2 de droite disent « gauche » (-2).
        avis = [(-2, 0)] * 100 + [(0, -2)] * 2 + [(2, -2)] * 2
        c = aveugle.compter(avis, minimum=2)
        self.assertEqual(c["note"], round((0 - 2 - 2) / 3, 2))
        self.assertEqual(c["statut"], "publiable")
        self.assertEqual(c["effectifs"], {"g": 100, "c": 2, "d": 2})

    def test_indicatif_si_un_bord_manque(self):
        self.assertEqual(aveugle.compter([(-1, 1), (-2, 1)], minimum=2)["statut"], "indicatif")
        self.assertIsNone(aveugle.compter([], minimum=2))


class Analyse(unittest.TestCase):
    def test_citation_absente_des_titres_retiree(self):
        corpus = fabrique.norm_strict("Un adolescent tué lors d'un rodéo urbain près de Clermont-Ferrand")
        texte, n = fabrique.verifier_citations("Parle de « rodéo urbain » et de « chaos total ».", corpus)
        self.assertEqual((texte, n), ("Parle de « rodéo urbain » et de chaos total.", 1))

    def test_bords(self):
        # les sept bandes de FrIdéo, avec ses seuils (-1,5 ; -0,75 ; -0,25 ; +0,25 ; +0,75 ; +1,5)
        self.assertEqual([base.bord(x) for x in (-2.41, -1.0, -0.71, 0.1, 0.36, 1.02, 1.87)],
                         ["extreme-gauche", "gauche", "centre-gauche", "centre", "centre-droit", "droite", "extreme-droite"])
        # la bande calculée est celle que FrIdéo publie, pour chacun des trente médias
        ref = json.load(open(os.path.join(base.config.ICI, "medias.json"), encoding="utf-8"))["medias"]
        self.assertEqual([m["nom"] for m in ref if base.bord(m["score"]) != m["bande"]], [])
        self.assertEqual(sorted(set(base.COTE.values())), ["c", "d", "g"])


class Chaine(unittest.TestCase):
    """Fabrique sans réseau : faux modèle, puis publication et guichet des votes sur un vrai port."""

    @classmethod
    def setUpClass(cls):
        cls.db = base.connexion()
        base.charger_medias(cls.db)
        ids = {r["nom"]: r["id"] for r in cls.db.execute("SELECT id, nom FROM medias")}
        titres = {
            "L'Humanité": "La réforme des retraites dénoncée par les syndicats dans la rue ce samedi",
            "Le Monde": "Réforme des retraites : les syndicats mobilisés dans la rue ce samedi",
            "franceinfo": "Retraites : des milliers de manifestants contre la réforme ce samedi",
            "Le Figaro": "Réforme des retraites : la rue bloquée par les syndicats ce samedi",
        }
        for media, titre in titres.items():
            for k in range(12):  # 12 titres par média : assez pour un lot à l'aveugle
                t = titre if k == 0 else f"{titre.split(':')[-1].strip()} et autre nouvelle numéro {k} du jour"
                cls.db.execute("INSERT INTO articles (cle, media_id, titre, lien, recolte) VALUES (?,?,?,?,?)",
                               (f"{media}-{k}", ids[media], t, f"https://exemple.test/{k}", base.iso()))
        cls.db.commit()

        def faux_modele(prompt, nature, etape):
            if etape == "regroupement A":
                return {str(n): "N: Réforme des retraites" for n in range(1, 21)}
            if etape == "regroupement fusion":
                return {"fusions": []}
            if etape == "regroupement B":
                return {}
            return {"titre": "Réforme des retraites : mobilisation syndicale", "fait": "Des syndicats manifestent.",
                    "g": "Parle de réforme « dénoncée ».", "c": "Compte les manifestants.", "d": "Parle de « rue bloquée » et de « pagaille ».",
                    "mots": [{"terme": "dénoncée", "qui": "L'Humanité"}, {"terme": "inventé", "qui": "personne"}],
                    "ecart": 9, "hors_sujet": []}

        cls._vrai = fabrique.demander
        fabrique.demander = faux_modele
        cls.regroupement = fabrique.regrouper(cls.db)
        cls.analyse = fabrique.analyser(cls.db)
        cls.lots = aveugle.fabriquer_lots(cls.db)
        cls.publication = publier.publier(cls.db)
        cls.srv = serveur.creer(port=0, hote="127.0.0.1")
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        fabrique.demander = cls._vrai
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.db.close()

    def appel(self, methode, chemin, corps=None, jeton=None):
        req = urllib.request.Request(self.url + chemin, method=methode,
                                     data=json.dumps(corps).encode() if corps is not None else None)
        if jeton:
            req.add_header("Authorization", "Bearer " + jeton)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                brut = r.read()
                return r.status, (json.loads(brut) if "json" in r.headers["Content-Type"] else brut)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def inviter(self):
        code = "code-%d" % self.db.execute("SELECT COUNT(*) AS n FROM invitations").fetchone()["n"]
        self.db.execute("INSERT INTO invitations (code, cree) VALUES (?, ?)", (code, base.iso()))
        self.db.commit()
        return code

    def test_1_fabrique(self):
        self.assertEqual(self.regroupement["sujets_ouverts"], 1)
        a = self.db.execute("SELECT * FROM analyses").fetchone()
        self.assertEqual(a["ecart"], 5)                                # borné à 0-5
        self.assertEqual(a["d"], "Parle de « rue bloquée » et de pagaille.")   # citation inventée dégonflée
        self.assertEqual([m["terme"] for m in json.loads(a["mots"])], ["« dénoncée »"])
        self.assertEqual(fabrique.analyser(self.db)["analyses_faites"], 0)     # rien n'a changé : pas de second appel
        self.assertEqual(fabrique.regrouper(self.db)["nouveaux"], 0)
        self.assertEqual(self.lots, 4)

    def test_2_site_et_sante(self):
        code, page = self.appel("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn(b"R\xc3\xa9forme des retraites", page)
        code, jour = self.appel("GET", "/data/jour.json")
        self.assertEqual((code, len(jour["sujets"]), jour["sujets"][0]["divergence"]), (200, 1, 5))
        self.assertEqual(self.appel("GET", "/sante")[1]["ok"], True)
        self.assertEqual(self.appel("GET", "/../comparateur.db")[0], 404)
        self.assertEqual(self.appel("GET", "/%2e%2e/comparateur.db")[0], 404)

    def test_3_vote_anonyme(self):
        self.assertEqual(self.appel("GET", "/api/lot")[0], 401)
        self.assertEqual(self.appel("POST", "/api/inscription", {"code": "faux", "bord": 0})[0], 403)
        code = self.inviter()
        self.assertEqual(self.appel("POST", "/api/inscription", {"code": code, "bord": 7})[0], 400)
        statut, d = self.appel("POST", "/api/inscription", {"code": code, "bord": -1})
        self.assertEqual(statut, 201)
        jeton = d["jeton"]
        self.assertEqual(self.appel("POST", "/api/inscription", {"code": code, "bord": 1})[0], 403)   # code à usage unique
        # la base ne contient ni le jeton ni un lien invitation -> votant
        self.assertIsNone(self.db.execute("SELECT 1 FROM votants WHERE id = ?", (jeton,)).fetchone())
        self.assertEqual([c[1] for c in self.db.execute("PRAGMA table_info(votants)")], ["id", "bord", "cree"])

        statut, d = self.appel("GET", "/api/lot", jeton=jeton)
        self.assertEqual((statut, d["restants"], len(d["lot"]["titres"])), (200, 4, 10))
        self.assertNotIn("media", json.dumps(d))            # aucun indice sur le média dans la réponse
        lot = d["lot"]["id"]
        self.assertEqual(self.appel("POST", "/api/avis-aveugle", {"lot": lot, "note": 3}, jeton)[0], 400)
        self.assertEqual(self.appel("POST", "/api/avis-aveugle", {"lot": lot, "note": -2}, jeton)[0], 201)
        self.assertEqual(self.appel("POST", "/api/avis-aveugle", {"lot": lot, "note": 2}, jeton)[0], 409)   # un vote par lot
        self.assertEqual(self.appel("GET", "/api/lot", jeton=jeton)[1]["restants"], 3)
        self.assertEqual(self.appel("POST", "/api/avis-note", {"media": "Le Monde", "accord": False}, jeton)[0], 201)
        res = self.appel("GET", "/api/resultats")[1]
        juge = [m for m, v in res.items() if "aveugle" in v]
        self.assertEqual(len(juge), 1)
        self.assertEqual(res[juge[0]]["aveugle"]["statut"], "indicatif")
        self.assertEqual(res["Le Monde"]["accord"], {"oui": 0, "votes": 1})

    def test_4_garde_fous(self):
        self.assertEqual(self.appel("POST", "/api/inscription", {"x": "y" * 5000})[0], 413)
        self.assertEqual(self.appel("GET", "/api/inconnu")[0], 404)
        self.assertEqual(self.appel("POST", "/")[0], 405)
        for _ in range(12):   # 10 essais d'inscription par heure et par adresse
            dernier = self.appel("POST", "/api/inscription", {"code": "faux", "bord": 0})[0]
        self.assertEqual(dernier, 429)


class Editions(unittest.TestCase):
    """Une édition par jour, gardée ; une page par édition ; le démarrage n'en refait pas."""

    def setUp(self):
        self.db = base.connexion()
        self.db.execute("DELETE FROM editions")
        self.db.commit()

    def tearDown(self):
        self.db.execute("DELETE FROM editions")
        self.db.commit()
        publier.publier(self.db)   # rend au site une édition, pour les autres tests
        self.db.close()

    def test_deux_jours_deux_pages_et_la_navigation(self):
        publier.publier(self.db, jour="2026-01-01")
        rendu = publier.publier(self.db, jour="2026-01-02")
        self.assertEqual(rendu["editions"], 2)
        pub = publier.config.public()
        for j in ("2026-01-01", "2026-01-02"):
            self.assertTrue(os.path.isfile(os.path.join(pub, "editions", j + ".html")))
        hier = json.load(open(os.path.join(pub, "data", "editions", "2026-01-01.json"), encoding="utf-8"))
        self.assertEqual(hier["edition"], {"jour": "2026-01-01", "precedent": None, "suivant": "2026-01-02",
                                            "toutes": ["2026-01-01", "2026-01-02"]})
        accueil = json.load(open(os.path.join(pub, "data", "jour.json"), encoding="utf-8"))
        self.assertEqual(accueil["edition"]["jour"], "2026-01-02")   # la dernière édition est l'accueil
        self.assertEqual(json.load(open(os.path.join(pub, "data", "editions.json"))), ["2026-01-01", "2026-01-02"])

    def test_le_suivi_des_sujets_est_injecte_dans_les_pages(self):
        medias = [{"nom": "Gauche Hebdo", "score": -1.5, "bord": "gauche"}, {"nom": "Le Milieu", "score": 0.0, "bord": "centre"},
                  {"nom": "Centre Info", "score": 0.1, "bord": "centre"}, {"nom": "Droite Matin", "score": 1.2, "bord": "droite"}]

        def edition(sujets):   # la forme d'une édition gardée avant ce changement : ni suivi, ni rubriques écartées
            return {"recolte": "2026-01-01T05:00:00+00:00", "heures": 24, "total": 9, "medias": medias, "absents": [],
                    "classement": {"source": "essai", "seuils": "", "medias": [{"nom": m["nom"], "score": m["score"]} for m in medias]},
                    "seuls": [], "sujets": [
                        {"id": i, "titre": t, "fait": "", "divergence": None, "analyse": {"g": "", "c": "", "d": ""}, "mots": [],
                         "articles": [{"media": m, "titre": f"{t} {m}", "lien": f"https://x.test/{i}/{m}"} for m in ms]}
                        for i, t, ms in sujets]}

        jours = {"2026-01-01": edition([("s1", "Grève", ["Gauche Hebdo", "Le Milieu", "Centre Info", "Droite Matin"]),
                                        ("s2", "Budget", ["Le Milieu", "Droite Matin"])]),
                 "2026-01-02": edition([("s1", "Grève, suite", ["Le Milieu", "Centre Info"])]),
                 "2026-01-03": edition([("s3", "Autre chose", ["Le Milieu"])])}
        for jour, charge in jours.items():
            self.db.execute("INSERT INTO editions (jour, cree, donnees) VALUES (?, ?, ?)", (jour, base.iso(), json.dumps(charge)))
        self.db.commit()
        self.assertEqual(publier.ecrire_pages(self.db), list(jours))
        pub = publier.config.public()

        def lire(j):
            with open(os.path.join(pub, "data", "editions", j + ".json"), encoding="utf-8") as f:
                return json.load(f)

        un, deux, trois = (lire(j) for j in jours)
        self.assertEqual(list(un["suivi"]), ["s1"])                # s2 ne vit qu'un jour : pas de frise
        self.assertEqual(un["suivi"], deux["suivi"])               # le même suivi, vu des deux éditions
        self.assertEqual([(x["jour"], x["titres"], x["medias"]) for x in un["suivi"]["s1"]],
                         [("2026-01-01", 4, 4), ("2026-01-02", 2, 2)])
        self.assertEqual(un["suivi"]["s1"][0]["par"], {"extreme-gauche": 0, "gauche": 1, "centre-gauche": 0, "centre": 2, "centre-droit": 0, "droite": 1, "extreme-droite": 0})
        self.assertEqual(un["suivi"]["s1"][1]["par"]["centre"], 2)
        self.assertEqual(trois["suivi"], {})
        self.assertEqual(un["min_medias"], syntheses.MIN_MEDIAS)
        self.assertEqual(list(un["periodes"]["semaine"]["bords"]), list(syntheses.BORDS))
        # ce qui est gardé en base n'est pas réécrit : le suivi se recalcule à chaque écriture des pages
        self.assertNotIn("suivi", json.loads(self.db.execute("SELECT donnees FROM editions WHERE jour = '2026-01-01'").fetchone()["donnees"]))
        with open(os.path.join(pub, "editions", "2026-01-01.html"), encoding="utf-8") as f:
            self.assertIn('"suivi": {"s1"', f.read())

    def test_refaire_un_jour_le_remplace(self):
        publier.publier(self.db, jour="2026-01-01")
        publier.publier(self.db, jour="2026-01-01")
        self.assertEqual(self.db.execute("SELECT COUNT(*) AS n FROM editions").fetchone()["n"], 1)

    def test_le_demarrage_ne_refait_pas_une_edition(self):
        publier.publier(self.db, jour="2026-01-01")
        avant = self.db.execute("SELECT cree FROM editions").fetchone()["cree"]
        self.assertEqual(publier.pages(self.db), {"editions": 1})
        self.assertEqual([r["jour"] for r in self.db.execute("SELECT jour FROM editions")], ["2026-01-01"])
        self.assertEqual(self.db.execute("SELECT cree FROM editions").fetchone()["cree"], avant)

    def test_le_demarrage_fait_la_premiere_edition(self):
        publier.pages(self.db)
        self.assertEqual(self.db.execute("SELECT COUNT(*) AS n FROM editions").fetchone()["n"], 1)


class Gabarit(unittest.TestCase):
    """La page unique est assemblée à partir de morceaux : une vue, un fichier (voir DOCTRINE.md)."""

    def test_tous_les_morceaux_sont_assembles_une_fois(self):
        site = publier.SITE
        with open(os.path.join(site, "gabarit.html"), encoding="utf-8") as f:
            nommes = publier.INCLURE.findall(f.read())
        presents = sorted(os.path.relpath(os.path.join(d, n), site).replace(os.sep, "/")
                          for sous in ("styles", "js") for d, _, noms in os.walk(os.path.join(site, sous)) for n in noms)
        self.assertEqual(sorted(nommes), presents)          # ni morceau oublié, ni morceau nommé deux fois
        self.assertEqual(nommes[0], "styles/base.css")      # le socle d'abord
        self.assertLess(nommes.index("js/donnees.js"), nommes.index("js/commun.js"))
        self.assertEqual(nommes[-1], "js/routage.js")       # le routage en dernier : il lance la première vue
        page = publier.gabarit()
        self.assertNotIn("INCLURE", page)
        self.assertEqual(page.count("/*DONNEES*/null"), 1)
        for attendu in ("function vHome()", "function vSilences()", "function route(", "function bar5(", ":root{"):
            self.assertEqual(page.count(attendu), 1, attendu)
        self.assertNotIn("</script", page.split('<script id="app-js">')[1].rsplit("</script>", 1)[0])

    def test_un_morceau_absent_arrete_la_publication(self):
        vrai, publier.SITE = publier.SITE, tempfile.mkdtemp(prefix="gabarit-")
        try:
            with open(os.path.join(publier.SITE, "gabarit.html"), "w", encoding="utf-8") as f:
                f.write("<style>\n/*INCLURE styles/absent.css*/\n</style>")
            with self.assertRaises(FileNotFoundError):
                publier.gabarit()
        finally:
            shutil.rmtree(publier.SITE, ignore_errors=True)
            publier.SITE = vrai

    def test_les_morceaux_ne_sont_pas_publies(self):
        db = base.connexion()
        try:
            publier.pages(db)
        finally:
            db.close()
        pub = publier.config.public()
        self.assertTrue(os.path.isfile(os.path.join(pub, "aveugle.html")))
        self.assertFalse(os.path.exists(os.path.join(pub, "js")) or os.path.exists(os.path.join(pub, "styles")))
        self.assertFalse(os.path.exists(os.path.join(pub, "gabarit.html")))


class Rubriques(unittest.TestCase):
    """La rubrique d'un article se lit dans son adresse, sans modèle ; le sport et la culture sont écartés."""

    def test_rubrique_lue_dans_l_adresse(self):
        cas = {
            "https://www.lemonde.fr/sport/article/2026/11/14/le-xv-de-france-s-impose_1.html": "sport",
            "https://www.francetvinfo.fr/sports/foot/ligue-1/psg-om-le-resume_2.html": "sport",
            "https://sport24.lefigaro.fr/football/un-titre-123": "sport",
            "https://www.liberation.fr/culture/cinema/le-film-de-la-semaine-20261114/": "culture",
            "https://www.leparisien.fr/culture-loisirs/tv/une-serie-14-11-2026.php": "culture",
            "https://www.bfmtv.com/people/une-vedette_AN-1.html": "culture",
            "https://www.lefigaro.fr/musique/un-concert-20261114": "culture",
            "https://www.20minutes.fr/Télé/4-une-emission": "culture",
            "https://www.lemonde.fr/politique/article/2026/11/14/budget_3.html": "politique",
            # un mot du titre ne fait pas une rubrique : seuls les segments entiers comptent, pas le dernier
            "https://www.lemonde.fr/politique/article/2026/11/14/le-sport-a-l-ecole_4.html": "politique",
            "https://www.causeur.fr/culture": "",
            "https://www.causeur.fr/le-budget-de-la-culture-en-baisse-123": "",
            "https://exemple.test/7": "", "": "", None: "",
        }
        for lien, attendu in cas.items():
            self.assertEqual(fabrique.rubrique(lien), attendu, lien)

    def test_liste_des_rubriques_ecartees_reglable(self):
        self.assertEqual(fabrique.config.rubriques_ecartees(), ["culture", "sport"])
        os.environ["COMPARATEUR_RUBRIQUES_ECARTEES"] = " Sport, opinions ,"
        try:
            self.assertEqual(fabrique.config.rubriques_ecartees(), ["opinions", "sport"])
            self.assertEqual(fabrique.hors_ecartees("a"), ("COALESCE(a.rubrique, '') NOT IN (?, ?)", ("opinions", "sport")))
            os.environ["COMPARATEUR_RUBRIQUES_ECARTEES"] = "aucune"
            self.assertEqual(fabrique.config.rubriques_ecartees(), [])
            self.assertEqual(fabrique.hors_ecartees("a"), ("1 = 1", ()))
        finally:
            del os.environ["COMPARATEUR_RUBRIQUES_ECARTEES"]

    def test_migration_d_une_base_existante_sans_perte(self):
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE articles (id INTEGER PRIMARY KEY, cle TEXT NOT NULL UNIQUE, media_id INTEGER NOT NULL,
                      titre TEXT NOT NULL, lien TEXT NOT NULL DEFAULT '', date TEXT, recolte TEXT NOT NULL,
                      trie INTEGER NOT NULL DEFAULT 0)""")   # le schéma d'avant, sans la colonne rubrique
        db.executemany("INSERT INTO articles (cle, media_id, titre, lien, recolte, trie) VALUES (?,?,?,?,?,?)",
                       [("a", 1, "Un match", "https://x.test/sport/un-match", "2026-11-14T06:00:00+00:00", 1),
                        ("b", 1, "Un vote", "https://x.test/politique/un-vote", "2026-11-14T06:00:00+00:00", 0),
                        ("c", 2, "Sans adresse", "", "2026-11-14T06:00:00+00:00", 0)])
        self.assertTrue(base.migrer(db))
        self.assertEqual([tuple(r) for r in db.execute("SELECT cle, titre, trie, rubrique FROM articles ORDER BY id")],
                         [("a", "Un match", 1, "sport"), ("b", "Un vote", 0, "politique"), ("c", "Sans adresse", 0, "")])
        self.assertFalse(base.migrer(db))   # déjà faite : rien à refaire
        db.close()

    def test_sport_et_culture_hors_du_regroupement_et_des_sujets(self):
        db = base.connexion()
        base.charger_medias(db)
        ids = {r["nom"]: r["id"] for r in db.execute("SELECT id, nom FROM medias")}
        avant = {t: db.execute(f"SELECT COALESCE(MAX(id), 0) AS n FROM {t}").fetchone()["n"] for t in ("articles", "sujets")}
        medias = ["Libération", "Le Monde", "Ouest-France", "Le Figaro"]
        lignes = [(m, f"Finale de la coupe : la victoire des Bleus vue par {m}", f"https://x.test/{k}/sport/finale-coupe") for k, m in enumerate(medias)]
        lignes += [(m, f"Budget de la sécurité sociale : le vote des députés vu par {m}", f"https://x.test/{k}/politique/budget-secu") for k, m in enumerate(medias)]
        # des titres sans rapport, pour que les mots du budget soient rares (la présélection compte les mots rares)
        divers = ["Tempête annoncée sur le littoral breton", "Grève surprise dans les transports lyonnais",
                  "Hausse inattendue du chômage au trimestre", "Incendie maîtrisé dans une usine chimique"]
        lignes += [("Le Monde", t, f"https://x.test/societe/divers-{k}") for k, t in enumerate(divers)]
        lignes.append(("Le Monde", "Prix Goncourt : le palmarès de la saison littéraire", "https://x.test/culture/livres/goncourt"))
        for media, titre, lien in lignes:
            db.execute("INSERT INTO articles (cle, media_id, titre, lien, recolte, rubrique) VALUES (?,?,?,?,?,?)",
                       (lien, ids[media], titre, lien, base.iso(), fabrique.rubrique(lien)))
        db.commit()
        vus = []

        def faux_modele(prompt, nature, etape):
            vus.append(prompt)
            if etape == "regroupement A":
                return {str(n): "N: Budget de la sécurité sociale" for n in range(1, 21)}
            return {"fusions": []} if etape == "regroupement fusion" else {}

        vrai, fabrique.demander = fabrique.demander, faux_modele
        try:
            rendu = fabrique.regrouper(db)
            self.assertEqual(rendu["nouveaux"], 8)                           # budget et divers, pas les 5 écartés
            self.assertTrue(vus and not any("Finale" in p or "Goncourt" in p for p in vus))   # jamais montrés au modèle
            sujets = [s for s in fabrique.sujets_du_jour(db) if s["id"] > avant["sujets"]]
            self.assertEqual([(s["libelle"], s["medias"], len(s["articles"])) for s in sujets], [("Budget de la sécurité sociale", 4, 4)])
            # ils restent en base, non triés, avec leur rubrique
            self.assertEqual([(r["rubrique"], r["trie"], r["n"]) for r in db.execute(
                "SELECT rubrique, trie, COUNT(*) AS n FROM articles WHERE id > ? GROUP BY rubrique, trie ORDER BY rubrique",
                (avant["articles"],))], [("culture", 0, 1), ("politique", 1, 4), ("societe", 1, 4), ("sport", 0, 4)])
            # un article de sport rangé sous un sujet avant ce changement n'y est plus compté
            sport = db.execute("SELECT id FROM articles WHERE rubrique = 'sport' AND id > ? LIMIT 1", (avant["articles"],)).fetchone()["id"]
            db.execute("INSERT INTO sujet_articles (sujet_id, article_id) VALUES (?, ?)", (sujets[0]["id"], sport))
            db.commit()
            self.assertEqual(len([s for s in fabrique.sujets_du_jour(db) if s["id"] == sujets[0]["id"]][0]["articles"]), 4)
            jour = publier.donnees_du_jour(db)
            self.assertEqual(jour["ecartes"], {"rubriques": ["culture", "sport"], "titres": 5})
            self.assertFalse([t for t in jour["seuls"] if "Finale" in t["titre"] or "Goncourt" in t["titre"]])
            # la liste est réglable : sans rubrique écartée, les mêmes titres sont proposés
            os.environ["COMPARATEUR_RUBRIQUES_ECARTEES"] = "aucune"
            self.assertEqual(fabrique.regrouper(db)["nouveaux"], 5)
            self.assertTrue(any("Finale" in p for p in vus))
        finally:
            os.environ.pop("COMPARATEUR_RUBRIQUES_ECARTEES", None)
            fabrique.demander = vrai
            db.execute("DELETE FROM sujet_articles WHERE article_id > ?", (avant["articles"],))
            db.execute("DELETE FROM analyses WHERE sujet_id > ?", (avant["sujets"],))
            db.execute("DELETE FROM sujets WHERE id > ?", (avant["sujets"],))
            db.execute("DELETE FROM articles WHERE id > ?", (avant["articles"],))
            db.commit()
            db.close()


class Syntheses(unittest.TestCase):
    """La semaine et le mois : des comptages sur les éditions gardées."""

    def edition(self, sujets):
        medias = [{"nom": "Gauche Hebdo", "bord": "gauche"}, {"nom": "Le Milieu", "bord": "centre"},
                  {"nom": "Centre Info", "bord": "centre"}, {"nom": "Droite Matin", "bord": "droite"},
                  {"nom": "Droite Soir", "bord": "centre-droit"}]
        return {"medias": medias, "sujets": [
            {"id": i, "titre": t, "divergence": e, "articles": [{"media": m, "titre": f"{t} {m}", "lien": f"https://x.test/{i}/{m}"}
                                                              for m in ms]} for i, t, e, ms in sujets]}

    def test_un_sujet_qui_dure_est_suivi_et_les_silences_comptes(self):
        lundi = self.edition([("s1", "Grève", 2, ["Gauche Hebdo", "Le Milieu", "Centre Info", "Droite Matin"]),
                              ("s2", "Budget", 1, ["Le Milieu", "Centre Info", "Droite Matin", "Droite Soir"])])
        mardi = self.edition([("s1", "Grève, suite", 4, ["Gauche Hebdo", "Le Milieu", "Droite Soir"])])
        semaines, mois = syntheses.toutes([("2026-11-09", lundi), ("2026-11-10", mardi)])
        s = semaines["2026-S46"]
        self.assertEqual((s["debut"], s["fin"], s["jours"]), ("2026-11-09", "2026-11-15", ["2026-11-09", "2026-11-10"]))
        greve = s["top"][0]
        self.assertEqual((greve["id"], greve["titre"], greve["jours"], greve["medias"], greve["ecart"]), ("s1", "Grève, suite", 2, 5, 4))
        self.assertEqual(greve["titres"], 5)                      # un article repris le lendemain ne compte qu'une fois
        self.assertEqual(greve["par"], {"extreme-gauche": 0, "gauche": 1, "centre-gauche": 0, "centre": 2, "centre-droit": 1, "droite": 1, "extreme-droite": 0})
        self.assertEqual(list(s["bords"]), list(syntheses.BORDS))  # cinq bords, de la gauche à la droite
        self.assertEqual(s["bords"]["gauche"]["silences"], 1)      # la gauche n'a rien sur le budget
        self.assertEqual(s["bords"]["gauche"]["tus"], [{"id": "s2", "titre": "Budget", "dernier": "2026-11-09", "medias": 4}])
        self.assertEqual(s["bords"]["droite"]["silences"], 0)
        self.assertEqual(s["bords"]["centre-droit"]["silences"], 0)
        # aucun média de centre gauche n'est lu : ce bord ne peut pas être dit silencieux
        self.assertEqual((s["bords"]["centre-gauche"]["medias"], s["bords"]["centre-gauche"]["silences"]), (0, 0))
        self.assertEqual({m["nom"]: m["bord"] for m in s["medias"]}["Droite Soir"], "centre-droit")
        self.assertEqual(mois["2026-11"]["debut"], "2026-11-01")
        self.assertEqual(mois["2026-11"]["fin"], "2026-11-30")

    def test_un_silence_se_juge_sur_trois_cotes(self):
        # La droite (bord) n'a pas de titre, mais le centre droit en a un : le côté droit parle, pas de silence.
        e = self.edition([("s1", "Grève", 2, ["Gauche Hebdo", "Le Milieu", "Centre Info", "Droite Soir"])])
        b = syntheses.toutes([("2026-11-09", e)])[0]["2026-S46"]["bords"]
        self.assertEqual(sum(v["silences"] for v in b.values()), 0)
        # Tout le côté droit se tait : le silence est compté pour chacun de ses bords lus.
        e = self.edition([("s1", "Grève", 2, ["Gauche Hebdo", "Le Milieu", "Centre Info"]),
                          ("s2", "Budget", 1, ["Gauche Hebdo", "Le Milieu", "Centre Info", "Droite Matin"])])
        e["sujets"][0]["articles"].append({"media": "Gauche Hebdo", "titre": "Grève bis", "lien": "https://x.test/s1/bis"})
        e["medias"].append({"nom": "Gauche Soir", "bord": "gauche"})
        e["sujets"][0]["articles"].append({"media": "Gauche Soir", "titre": "Grève ter", "lien": "https://x.test/s1/ter"})
        b = syntheses.toutes([("2026-11-09", e)])[0]["2026-S46"]["bords"]
        self.assertEqual({k: v["silences"] for k, v in b.items()},
                         {"extreme-gauche": 0, "gauche": 0, "centre-gauche": 0, "centre": 0, "centre-droit": 1, "droite": 1, "extreme-droite": 0})
        self.assertEqual(syntheses.silencieux({"extreme-gauche": 0, "gauche": 2, "centre-gauche": 0, "centre": 2, "centre-droit": 0, "droite": 0, "extreme-droite": 0},
                                              {"extreme-gauche": 0, "gauche": 2, "centre-gauche": 0, "centre": 2, "centre-droit": 1, "droite": 1, "extreme-droite": 0}, 4), ["d"])
        # en dessous de MIN_MEDIAS médias, un silence ne dit rien
        petit = self.edition([("s1", "Grève", 2, ["Gauche Hebdo", "Le Milieu", "Centre Info"])])
        b = syntheses.toutes([("2026-11-09", petit)])[0]["2026-S46"]["bords"]
        self.assertEqual(sum(v["silences"] for v in b.values()), 0)

    def test_le_suivi_d_un_sujet_jour_par_jour(self):
        lundi = self.edition([("s1", "Grève", 2, ["Gauche Hebdo", "Le Milieu", "Centre Info", "Droite Matin"]),
                              ("s2", "Budget", 1, ["Le Milieu", "Centre Info", "Droite Matin", "Droite Soir"])])
        mardi = self.edition([("s1", "Grève, suite", 4, ["Gauche Hebdo", "Le Milieu", "Droite Soir"])])
        suivi = syntheses.suivi([("2026-11-09", lundi), ("2026-11-10", mardi)])
        self.assertEqual([x["jour"] for x in suivi["s1"]], ["2026-11-09", "2026-11-10"])
        self.assertEqual(suivi["s1"][0], {"jour": "2026-11-09", "titres": 4, "medias": 4, "silences": [],
                                          "par": {"extreme-gauche": 0, "gauche": 1, "centre-gauche": 0, "centre": 2, "centre-droit": 0, "droite": 1, "extreme-droite": 0}})
        self.assertEqual((suivi["s1"][1]["titres"], suivi["s1"][1]["medias"], suivi["s1"][1]["silences"]), (3, 3, []))
        self.assertEqual(len(suivi["s2"]), 1)

    def test_la_semaine_change_au_lundi(self):
        self.assertEqual(syntheses.cle_semaine("2026-11-15"), "2026-S46")
        self.assertEqual(syntheses.cle_semaine("2026-11-16"), "2026-S47")


class Budget(unittest.TestCase):
    def test_plafond_arrete_la_fabrique(self):
        os.environ["COMPARATEUR_BUDGET_JOUR_USD"] = "0"
        try:
            with self.assertRaises(llm.BudgetDepasse):
                llm.demander("un prompt jamais vu", "tri", "essai")
        finally:
            del os.environ["COMPARATEUR_BUDGET_JOUR_USD"]


if __name__ == "__main__":
    unittest.main()


class Mesure(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("COMPARATEUR_UMAMI_ID", None)

    def test_sans_identifiant_aucune_mesure(self):
        os.environ.pop("COMPARATEUR_UMAMI_ID", None)
        self.assertEqual(publier.balise_mesure(), "")
        self.assertNotIn("<!--MESURE-->", publier.gabarit())
        self.assertNotIn("stats.", serveur.politique())

    def test_umami_dans_la_page_et_la_politique(self):
        os.environ["COMPARATEUR_UMAMI_ID"] = "abc-123"
        self.assertIn('data-website-id="abc-123"', publier.gabarit())
        self.assertIn('data-domains="compare-media.inflexion.me"', publier.balise_mesure())
        p = serveur.politique()
        self.assertIn("script-src 'self' 'unsafe-inline' https://stats.inflexion.me;", p)
        self.assertIn("connect-src 'self' https://stats.inflexion.me;", p)
