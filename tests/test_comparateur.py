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

    def test_dates_ramenees_en_temps_universel(self):
        # Une date en heure de Paris, gardée telle quelle, se compare mal en texte à une borne en temps universel.
        d = fabrique.lire_date("Sat, 14 Nov 2026 07:30:00 +0100")
        self.assertEqual(fabrique.base.iso(d), "2026-11-14T06:30:00+00:00")
        self.assertEqual(fabrique.base.iso(fabrique.lire_date("2026-11-14T07:30:00+01:00")), "2026-11-14T06:30:00+00:00")

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
        self.assertTrue(os.path.isfile(os.path.join(pub, "favicon.svg")))   # l'icône : sans elle, une 404 à chaque visite
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

    def test_migration_des_dates_en_temps_universel(self):
        db = base.connexion()
        base.charger_medias(db)
        mid = db.execute("SELECT id FROM medias LIMIT 1").fetchone()[0]
        db.executemany("INSERT INTO articles (cle, media_id, titre, date, recolte) VALUES (?,?,?,?,?)",
                       [("p", mid, "Paris", "2026-11-14T07:30:00+01:00", "2026-11-14T09:00:00+00:00"),
                        ("u", mid, "UTC", "2026-11-14T06:30:00+00:00", "2026-11-14T09:00:00+00:00"),
                        ("n", mid, "Sans date", None, "2026-11-14T09:00:00+00:00")])
        self.assertTrue(base.migrer(db))
        self.assertEqual([tuple(r) for r in db.execute("SELECT cle, date FROM articles WHERE cle IN ('p','u','n') ORDER BY cle")],
                         [("n", None), ("p", "2026-11-14T06:30:00+00:00"), ("u", "2026-11-14T06:30:00+00:00")])
        self.assertFalse(base.migrer(db))
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


class Application(unittest.TestCase):
    """Le site s'installe comme une application : manifest, icônes, service worker, liens dans les pages."""

    @classmethod
    def setUpClass(cls):
        db = base.connexion()
        try:
            publier.pages(db)
        finally:
            db.close()
        cls.pub = publier.config.public()
        cls.srv = serveur.creer(port=0, hote="127.0.0.1")
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def lire(self, chemin):
        with urllib.request.urlopen(self.url + chemin, timeout=10) as r:
            return r.status, r.headers, r.read()

    def taille_png(self, brut):
        import struct
        self.assertEqual(brut[:8], b"\x89PNG\r\n\x1a\n")
        return struct.unpack(">II", brut[16:24])

    def test_manifest_publie_et_valide(self):
        statut, entetes, brut = self.lire("/manifest.webmanifest")
        self.assertEqual(statut, 200)
        self.assertTrue(entetes["Content-Type"].startswith("application/manifest+json"))
        m = json.loads(brut)
        self.assertEqual((m["name"], m["short_name"], m["start_url"], m["scope"], m["display"], m["lang"]),
                         ("Cadrages", "Cadrages", "/", "/", "standalone", "fr"))
        self.assertEqual((m["background_color"], m["theme_color"]), ("#f1ede4", "#16140f"))
        tailles = {(i["sizes"], i.get("purpose", "any")) for i in m["icons"]}
        self.assertTrue({("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= tailles)
        for i in m["icons"]:   # chaque icône nommée est publiée, à la taille annoncée
            chemin = os.path.join(self.pub, i["src"].lstrip("/"))
            self.assertTrue(os.path.isfile(chemin), i["src"])
            if i["type"] == "image/png":
                with open(chemin, "rb") as f:
                    n = int(i["sizes"].split("x")[0])
                    self.assertEqual(self.taille_png(f.read()), (n, n))

    def test_icones_d_ecran_d_accueil(self):
        for chemin in ("/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"):   # Safari demande les deux
            statut, entetes, brut = self.lire(chemin)
            self.assertEqual((statut, entetes["Content-Type"]), (200, "image/png"), chemin)
            self.assertEqual(self.taille_png(brut), (180, 180))

    def test_service_worker_a_la_racine(self):
        statut, entetes, brut = self.lire("/sw.js")
        self.assertEqual(statut, 200)
        self.assertIn("javascript", entetes["Content-Type"])
        self.assertEqual(entetes["Cache-Control"], "no-cache")
        self.assertIn(b"fetch(r)", brut)   # réseau d'abord
        p = entetes["Content-Security-Policy"]
        self.assertIn("manifest-src 'self'", p)
        self.assertIn("worker-src 'self'", p)

    def test_liens_dans_les_pages(self):
        for nom in ("index.html", "aveugle.html"):
            with open(os.path.join(self.pub, nom), encoding="utf-8") as f:
                page = f.read()
            for attendu in ('<link rel="manifest" href="/manifest.webmanifest">',
                            '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
                            'name="theme-color" content="#f1ede4" media="(prefers-color-scheme: light)"',
                            'name="theme-color" content="#14130f" media="(prefers-color-scheme: dark)"',
                            '<meta name="apple-mobile-web-app-title" content="Cadrages">',
                            "navigator.serviceWorker.register('/sw.js')"):
                self.assertIn(attendu, page, nom)
        page = publier.gabarit()
        self.assertIn("function vInstaller()", page)
        self.assertIn("v==='installer'", page)
        self.assertIn('href="#/installer"', page)


class FauxSMTP:
    """Remplace la connexion SMTP : garde les messages, refuse le mail de la semaine aux adresses « refus »."""
    envoyes = []

    def __init__(self, cfg):
        self.cfg = cfg

    def send_message(self, msg):
        import smtplib
        if "refus" in msg["To"] and msg["List-Unsubscribe"]:
            raise smtplib.SMTPRecipientsRefused({msg["To"]: (550, b"non")})
        FauxSMTP.envoyes.append(msg)

    def quit(self):
        pass


class MailEteint(unittest.TestCase):
    def test_sans_reglages_rien(self):
        for k in ("COMPARATEUR_SMTP_UTILISATEUR", "COMPARATEUR_SMTP_MOT_DE_PASSE"):
            os.environ.pop(k, None)
        from comparateur import config, lettre
        self.assertIsNone(config.mail())
        os.environ["COMPARATEUR_SMTP_UTILISATEUR"] = "u"   # l'un sans l'autre ne suffit pas
        try:
            self.assertIsNone(config.mail())
        finally:
            os.environ.pop("COMPARATEUR_SMTP_UTILISATEUR")
        db = base.connexion()
        try:
            publier.pages(db)
            self.assertIsNone(lettre.envoyer_semaine(db, "2026-11-16"))
        finally:
            db.close()
        with open(os.path.join(publier.config.public(), "data", "jour.json"), encoding="utf-8") as f:
            self.assertIsNone(json.load(f)["mail"])
        srv = serveur.creer(port=0, hote="127.0.0.1")
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/api/mail/inscription" % srv.server_address[1],
                                         method="POST", data=b'{"adresse": "a@exemple.fr"}')
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(e.exception.code, 404)
        finally:
            srv.shutdown()
            srv.server_close()


class Mail(unittest.TestCase):
    """La synthèse de la semaine par mail : double confirmation, désinscription, envoi du lundi. Sans vrai SMTP."""
    SEMAINE = ("2026-03-02", "2026-03-03", "2026-03-04")   # une semaine passée : aucune autre édition dedans

    @classmethod
    def setUpClass(cls):
        from comparateur import lettre
        cls.lettre = lettre
        os.environ.update(COMPARATEUR_SMTP_UTILISATEUR="essai", COMPARATEUR_SMTP_MOT_DE_PASSE="secret",
                          COMPARATEUR_SITE_URL="https://cadrages.test")
        cls._vrai, lettre.ouvrir_smtp = lettre.ouvrir_smtp, FauxSMTP
        lettre.EN_ARRIERE_PLAN = False
        cls.srv = serveur.creer(port=0, hote="127.0.0.1")
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.lettre.ouvrir_smtp, cls.lettre.EN_ARRIERE_PLAN = cls._vrai, True
        for k in ("COMPARATEUR_SMTP_UTILISATEUR", "COMPARATEUR_SMTP_MOT_DE_PASSE", "COMPARATEUR_SITE_URL"):
            os.environ.pop(k, None)
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        FauxSMTP.envoyes.clear()
        serveur.DEBIT.vus.clear()
        self.lettre._echecs.clear()
        self.db = base.connexion()
        self.db.execute("DELETE FROM abonnes")
        self.db.commit()

    def tearDown(self):
        self.db.execute("DELETE FROM abonnes")
        self.db.execute("DELETE FROM editions WHERE jour IN (?, ?, ?)", self.SEMAINE)
        self.db.commit()
        self.db.close()

    def appel(self, methode, chemin, corps=None, brut=None, entetes=None):
        data = brut if brut is not None else (json.dumps(corps).encode() if corps is not None else None)
        req = urllib.request.Request(self.url + chemin, method=methode, data=data, headers=entetes or {})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def jeton_du_dernier_mail(self):
        import re
        texte = FauxSMTP.envoyes[-1].get_body(("plain",)).get_content()
        return re.search(r"/mail\.html#confirmer=([\w-]+)", texte).group(1)

    def inscrit(self, adresse):
        self.assertEqual(self.appel("POST", "/api/mail/inscription", {"adresse": adresse})[0], 202)
        jeton = self.jeton_du_dernier_mail()
        self.assertEqual(self.appel("POST", "/api/mail/confirmation", {"jeton": jeton})[0], 200)
        return jeton

    def semaine(self):
        medias = [{"nom": "Gauche Hebdo", "score": -1.0}, {"nom": "Le Milieu", "score": 0.0},
                  {"nom": "Centre Info", "score": 0.1}, {"nom": "Droite Matin", "score": 1.2},
                  {"nom": "Gauche Soir", "score": -0.9}]
        for jour in self.SEMAINE:
            charge = {"recolte": jour + "T05:00:00+00:00", "medias": medias, "seuls": [], "sujets": [
                {"id": "s1", "titre": "Grève <générale>", "divergence": 2, "articles": [
                    {"media": m, "titre": "t " + m, "lien": f"https://x.test/{jour}/{m}"} for m in ("Gauche Hebdo", "Le Milieu", "Centre Info", "Gauche Soir")]
                 + [{"media": "Le Milieu", "titre": "bis", "lien": f"https://x.test/{jour}/bis"}]}]}
            self.db.execute("INSERT OR REPLACE INTO editions (jour, cree, donnees) VALUES (?, ?, ?)", (jour, base.iso(), json.dumps(charge)))
        self.db.commit()

    def test_inscription_confirmation_desinscription(self):
        import contextlib, io
        journal = io.StringIO()
        with contextlib.redirect_stdout(journal):
            self.assertEqual(self.appel("POST", "/api/mail/inscription", {"adresse": "  Lea@Exemple.FR "}), (202, b'{"ok": true}'))
            self.assertEqual(len(FauxSMTP.envoyes), 1)
            msg = FauxSMTP.envoyes[0]
            self.assertEqual(msg["To"], "lea@exemple.fr")                 # en minuscules
            self.assertIn("Cadrages", msg["From"])
            r = self.db.execute("SELECT * FROM abonnes").fetchone()
            self.assertEqual((r["adresse"], r["confirme_le"]), ("lea@exemple.fr", None))
            jeton = self.jeton_du_dernier_mail()
            self.assertEqual(jeton, r["jeton"])
            # ouvrir le lien (GET) ne confirme rien ni ne désinscrit : seul le bouton (POST) agit
            self.assertEqual(self.appel("GET", "/mail.html")[0], 200)
            self.assertIsNone(self.db.execute("SELECT confirme_le FROM abonnes").fetchone()["confirme_le"])
            self.assertEqual(self.appel("POST", "/api/mail/confirmation", {"jeton": "inconnu-inconnu"})[0], 404)
            self.assertEqual(self.appel("POST", "/api/mail/confirmation", {"jeton": jeton})[0], 200)
            self.assertIsNotNone(self.db.execute("SELECT confirme_le FROM abonnes").fetchone()["confirme_le"])
            self.appel("GET", "/api/mail/desinscription?jeton=" + jeton)
            self.assertEqual(self.db.execute("SELECT COUNT(*) AS n FROM abonnes").fetchone()["n"], 1)
            self.assertEqual(self.appel("POST", "/api/mail/desinscription", {"jeton": jeton})[0], 200)
            self.assertEqual(self.db.execute("SELECT COUNT(*) AS n FROM abonnes").fetchone()["n"], 0)   # la ligne est supprimée
            self.assertEqual(self.appel("POST", "/api/mail/desinscription", {"jeton": jeton})[0], 200)
        self.assertNotIn("exemple.fr", journal.getvalue().lower())          # aucune adresse dans les journaux
        self.assertNotIn(jeton, journal.getvalue())                          # ni jeton

    def test_reponse_identique_quelle_que_soit_l_adresse(self):
        self.inscrit("deja@exemple.fr")
        FauxSMTP.envoyes.clear()
        nouvelle = self.appel("POST", "/api/mail/inscription", {"adresse": "nouvelle@exemple.fr"})
        deja = self.appel("POST", "/api/mail/inscription", {"adresse": "deja@exemple.fr"})
        invalide = self.appel("POST", "/api/mail/inscription", {"adresse": "pas une adresse"})
        robot = self.appel("POST", "/api/mail/inscription", {"adresse": "robot@exemple.fr", "site": "http://spam"})
        self.assertEqual(nouvelle, deja)
        self.assertEqual(nouvelle, invalide)
        self.assertEqual(nouvelle, robot)
        self.assertEqual([m["To"] for m in FauxSMTP.envoyes], ["nouvelle@exemple.fr"])   # ni la déjà inscrite, ni le robot
        self.assertEqual(self.appel("POST", "/api/mail/inscription", {"adresse": "x@exemple.fr"})[0], 429)   # 5 par heure

    def test_inscription_non_confirmee_effacee_apres_7_jours(self):
        self.appel("POST", "/api/mail/inscription", {"adresse": "lente@exemple.fr"})
        self.db.execute("UPDATE abonnes SET cree = '2026-01-01T00:00:00+00:00'")
        self.db.commit()
        self.assertEqual(self.lettre.purger(self.db), 1)

    def test_envoi_de_la_semaine_sans_double_envoi(self):
        self.semaine()
        a, b = self.inscrit("a@exemple.fr"), self.inscrit("refus@exemple.fr")
        self.inscrit("c@exemple.fr")
        self.appel("POST", "/api/mail/inscription", {"adresse": "pas-confirme@exemple.fr"})
        FauxSMTP.envoyes.clear()
        rendu = self.lettre.envoyer_semaine(self.db, "2026-03-09")   # lundi : la semaine du 2 au 8 mars
        self.assertEqual(rendu, {"semaine": "2026-S10", "envoyes": 2, "echecs": 1, "editions": 3})
        self.assertEqual(sorted(m["To"] for m in FauxSMTP.envoyes), ["a@exemple.fr", "c@exemple.fr"])   # l'échec ne bloque pas
        msg = FauxSMTP.envoyes[0]
        self.assertEqual(msg["List-Unsubscribe"], f"<https://cadrages.test/api/mail/desinscription?jeton={a}>")
        self.assertEqual(msg["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        texte, page = msg.get_body(("plain",)).get_content(), msg.get_body(("html",)).get_content()
        for corps in (texte, page):
            self.assertIn("écrit par un modèle", corps)
            self.assertIn("synthèse partielle", corps)                     # 3 éditions sur 7
            self.assertIn("https://cadrages.test/editions/2026-03-04.html#/semaine", corps)
            self.assertIn("/mail.html#desinscrire=" + a, corps)
            self.assertIn("Droite : 1 silence", corps.replace("<b>", "").replace("</b>", ""))
        self.assertIn("Grève <générale>", texte)
        self.assertIn("Grève &lt;générale&gt;", page)                     # échappé dans le HTML
        self.assertIn("3 éditions gardées sur 7", texte)
        # le même lundi, et après un redémarrage (l'état est en base) : rien ne repart vers qui l'a reçu
        FauxSMTP.envoyes.clear()
        self.lettre._echecs.clear()
        rendu = self.lettre.envoyer_semaine(self.db, "2026-03-09")
        self.assertEqual([m["To"] for m in FauxSMTP.envoyes], [])          # « refus » échoue de nouveau, rien n'est accepté
        self.assertEqual(rendu["envoyes"], 0)
        self.assertEqual({r["adresse"]: r["dernier_envoi"] for r in self.db.execute("SELECT * FROM abonnes")},
                         {"a@exemple.fr": "2026-S10", "refus@exemple.fr": None, "c@exemple.fr": "2026-S10", "pas-confirme@exemple.fr": None})
        # désinscription en un clic (RFC 8058) : le POST du logiciel de messagerie, sans JSON
        statut, _ = self.appel("POST", "/api/mail/desinscription?jeton=" + a, brut=b"List-Unsubscribe=One-Click",
                               entetes={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(statut, 200)
        self.assertIsNone(self.db.execute("SELECT 1 FROM abonnes WHERE jeton = ?", (a,)).fetchone())
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM abonnes WHERE jeton = ?", (b,)).fetchone())

    def test_le_site_montre_le_formulaire_seulement_si_le_mail_est_regle(self):
        publier.pages(self.db)
        with open(os.path.join(publier.config.public(), "data", "jour.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["mail"], {"prestataire": "Brevo"})
        page = publier.gabarit()
        self.assertIn("if(!D.mail)return '';", page)
        self.assertIn("/api/mail/inscription", page)
        self.assertTrue(os.path.isfile(os.path.join(publier.config.public(), "mail.html")))


def faux_webdav():
    """Un serveur WebDAV minimal en mémoire, avec authentification Basic : MKCOL, PUT, GET, PROPFIND, DELETE."""
    import base64
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    fichiers, attendu = {}, "Basic " + base64.b64encode(b"sub1:bon-secret").decode()

    class Gestion(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def repondre(self, code, corps=b""):
            self.send_response(code)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def autorise(self):
            if self.headers.get("Authorization") != attendu:
                self.repondre(401)
                return False
            return True

        def lire(self):
            return self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))

        def do_MKCOL(self):
            if self.autorise():
                self.lire()
                self.repondre(405)   # le dossier existe déjà

        def do_PUT(self):
            if self.autorise():
                fichiers[self.path.rsplit("/", 1)[-1]] = self.lire()
                self.repondre(201)

        def do_GET(self):
            if self.autorise():
                n = self.path.rsplit("/", 1)[-1]
                self.repondre(200, fichiers[n]) if n in fichiers else self.repondre(404)

        def do_DELETE(self):
            if self.autorise():
                fichiers.pop(self.path.rsplit("/", 1)[-1], None)
                self.repondre(204)

        def do_PROPFIND(self):
            if self.autorise():
                self.lire()
                corps = '<?xml version="1.0"?><d:multistatus xmlns:d="DAV:"><d:response><d:href>/sauv/</d:href></d:response>' + "".join(
                    f"<d:response><d:href>/sauv/{n}</d:href></d:response>" for n in fichiers) + "</d:multistatus>"
                self.repondre(207, corps.encode())

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, fichiers


class Sauvegarde(unittest.TestCase):
    """Une copie cohérente de la base par jour, gardée N jours, envoyée vers une Storage Box en WebDAV."""

    @classmethod
    def setUpClass(cls):
        from comparateur import sauvegarde
        cls.s = sauvegarde
        cls.srv, cls.distants = faux_webdav()
        cls.url = "http://127.0.0.1:%d/sauv/" % cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        shutil.rmtree(os.path.join(DOSSIER, "sauvegardes"), ignore_errors=True)
        self.distants.clear()
        self.s._dernier_essai.clear()
        self.db = base.connexion()
        self.db.execute("INSERT OR REPLACE INTO editions (jour, cree, donnees) VALUES ('2025-01-01', ?, '{}')", (base.iso(),))
        self.db.commit()

    def tearDown(self):
        for k in ("COMPARATEUR_SAUVEGARDE_URL", "COMPARATEUR_SAUVEGARDE_UTILISATEUR", "COMPARATEUR_SAUVEGARDE_MOT_DE_PASSE"):
            os.environ.pop(k, None)
        self.db.execute("DELETE FROM editions WHERE jour = '2025-01-01'")
        self.db.commit()
        self.db.close()

    def distant(self, mot_de_passe="bon-secret"):
        os.environ.update(COMPARATEUR_SAUVEGARDE_URL=self.url, COMPARATEUR_SAUVEGARDE_UTILISATEUR="sub1",
                          COMPARATEUR_SAUVEGARDE_MOT_DE_PASSE=mot_de_passe)

    def ouvrir(self, chemin):
        import gzip, sqlite3
        brut = os.path.join(DOSSIER, "lu.db")
        with gzip.open(chemin, "rb") as g, open(brut, "wb") as f:
            f.write(g.read())
        return sqlite3.connect(brut)

    def test_copie_coherente_et_verifiee(self):
        chemin = self.s.copier()
        self.assertTrue(os.path.basename(chemin).startswith("comparateur-2") and chemin.endswith(".db.gz"))
        copie = self.ouvrir(chemin)
        try:
            self.assertEqual(copie.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(copie.execute("SELECT COUNT(*) FROM editions WHERE jour = '2025-01-01'").fetchone()[0], 1)
            self.assertIn("abonnes", {r[0] for r in copie.execute("SELECT name FROM sqlite_master")})
        finally:
            copie.close()
        self.assertTrue(self.s.faite())
        self.assertIsNone(self.s.envoyer_en_attente(force=True))   # pas de Storage Box réglée : rien à envoyer

    def test_les_vieilles_copies_sont_effacees(self):
        self.s.copier("2026-01-01")
        self.s.copier()
        self.assertEqual(self.s.elaguer_local(), 1)
        self.assertEqual([j for j, _, _ in self.s.locales()], [self.s.aujourdhui()])

    def test_envoi_vers_la_storage_box(self):
        import contextlib, io
        self.distant()
        self.distants["comparateur-2026-01-01.db.gz"] = b"vieux"   # trop vieux : effacé là-bas aussi
        self.distants["autre-fichier.txt"] = b"x"                  # pas une copie : pas touché
        journal = io.StringIO()
        with contextlib.redirect_stdout(journal):
            chemin = self.s.sauvegarder()
        n = os.path.basename(chemin)
        self.assertEqual(sorted(self.distants), ["autre-fichier.txt", n])
        with open(chemin, "rb") as f:
            self.assertEqual(self.distants[n], f.read())
        self.assertTrue(self.s.locales()[-1][2])                   # marquée envoyée
        self.assertEqual(self.s.envoyer_en_attente(force=True), 0)  # rien ne repart
        self.assertNotIn("bon-secret", journal.getvalue())

    def test_une_storage_box_en_panne_ne_casse_rien(self):
        import contextlib, io
        self.distant("mauvais")
        journal = io.StringIO()
        with contextlib.redirect_stdout(journal):
            self.s.sauvegarder()                                   # pas d'exception
            self.assertEqual(self.s.envoyer_en_attente(), 0)       # pas de nouvel essai avant une heure
        self.assertIn("échec", journal.getvalue())
        self.assertIn("401", journal.getvalue())
        self.assertNotIn("mauvais", journal.getvalue())
        self.assertFalse(self.s.locales()[-1][2])
        self.assertEqual(self.distants, {})
        self.distant()                                             # la Storage Box revient : la copie part
        self.assertEqual(self.s.envoyer_en_attente(force=True), 1)

    def test_https_obligatoire_hors_local(self):
        with self.assertRaises(ValueError):
            self.s.Distant({"url": "http://u1-sub1.your-storagebox.de/", "utilisateur": "u", "mot_de_passe": "p"})
        self.s.Distant({"url": "https://u1-sub1.your-storagebox.de/", "utilisateur": "u", "mot_de_passe": "p"})

    def test_restaurer_une_copie_locale_puis_distante(self):
        self.distant()
        n = os.path.basename(self.s.sauvegarder())
        self.db.execute("DELETE FROM editions WHERE jour = '2025-01-01'")
        self.db.commit()
        avant = self.s.restaurer(n)
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM editions WHERE jour = '2025-01-01'").fetchone())
        self.assertTrue(os.path.isfile(avant) and "avant-restauration" in avant)
        copie = self.ouvrir(avant)   # la base d'avant la restauration est gardée telle quelle
        try:
            self.assertIsNone(copie.execute("SELECT 1 FROM editions WHERE jour = '2025-01-01'").fetchone())
        finally:
            copie.close()
        # le volume est perdu : plus de copie locale, la copie vient de la Storage Box
        os.remove(os.path.join(self.s.dossier(), n))
        self.db.execute("DELETE FROM editions WHERE jour = '2025-01-01'")
        self.db.commit()
        self.s.restaurer(n)
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM editions WHERE jour = '2025-01-01'").fetchone())
        with self.assertRaises(FileNotFoundError):
            self.s.restaurer("comparateur-1999-01-01.db.gz")

    def test_la_page_mentions_dit_la_duree_de_garde(self):
        self.db.execute("DELETE FROM editions WHERE jour = '2025-01-01'")   # pas une vraie édition : hors du site
        self.db.commit()
        publier.pages(self.db)
        with open(os.path.join(publier.config.public(), "data", "jour.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["sauvegardes"], {"jours": 14, "distante": False})
        self.assertIn("D.sauvegardes||null", publier.gabarit())
