"""Le service des fichiers : cache, ETag et 304, compression, limite de débit sur l'API seulement, et le code du
site sorti des pages (actifs nommés par leur empreinte). Sans réseau ni modèle.  python3 -m unittest discover -s tests"""
import gzip, hashlib, http.client, json, os, re, shutil, sys, tempfile, threading, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from comparateur import base, publier, serveur  # noqa: E402

_AVANT = None


def setUpModule():
    global _AVANT, DOSSIER
    _AVANT = os.environ.get("COMPARATEUR_DONNEES")
    DOSSIER = tempfile.mkdtemp(prefix="comparateur-service-")
    os.environ["COMPARATEUR_DONNEES"] = DOSSIER


def tearDownModule():
    if _AVANT is None:
        os.environ.pop("COMPARATEUR_DONNEES", None)
    else:
        os.environ["COMPARATEUR_DONNEES"] = _AVANT
    shutil.rmtree(DOSSIER, ignore_errors=True)


class Actifs(unittest.TestCase):
    """publier.gabarit_en_actifs et ecrire_pages : le CSS et le JavaScript hors des pages."""

    @classmethod
    def setUpClass(cls):
        cls.db = base.connexion()
        publier.pages(cls.db)
        cls.pub = publier.config.public()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def lire(self, *chemin):
        with open(os.path.join(self.pub, *chemin), encoding="utf-8") as f:
            return f.read()

    def test_les_actifs_sont_nommes_par_leur_empreinte(self):
        noms = sorted(os.listdir(os.path.join(self.pub, "actifs")), key=lambda n: n.rsplit(".")[-1])
        self.assertEqual([re.sub(r"[0-9a-f]{12}", "H", n) for n in noms], ["site-H.css", "site-H.js"])
        for n in noms:
            corps = self.lire("actifs", n)
            self.assertEqual(n.split("-")[1].split(".")[0], hashlib.sha256(corps.encode("utf-8")).hexdigest()[:12])
        self.assertIn(":root{", self.lire("actifs", [n for n in noms if n.endswith(".css")][0]))
        self.assertIn("function vHome()", self.lire("actifs", [n for n in noms if n.endswith(".js")][0]))

    def test_la_page_cite_les_actifs_et_ne_les_contient_plus(self):
        page = self.lire("index.html")
        css = re.findall(r'<link rel="stylesheet" href="(/actifs/site-[0-9a-f]{12}\.css)">', page)
        js = re.findall(r'<script src="(/actifs/site-[0-9a-f]{12}\.js)"></script>', page)
        self.assertEqual((len(css), len(js)), (1, 1))
        for f in css + js:
            self.assertTrue(os.path.isfile(os.path.join(self.pub, f.lstrip("/"))), f)
        self.assertNotIn("<style>", page)
        self.assertNotIn('id="app-js"', page)
        for code in (":root{", "function vHome()", "function route(", "function bar5("):
            self.assertNotIn(code, page, code)
        # les données restent dans la page, déclarées avant le script qui les lit ; la mesure aussi se garde
        self.assertIn('<script id="donnees">\nconst DONNEES = {', page)
        self.assertLess(page.index("const DONNEES"), page.index(js[0]))
        self.assertLess(page.index(css[0]), page.index("</head>"))
        self.assertLess(len(page), len(publier.gabarit()) / 2)   # plus de la moitié du poids est sortie de la page

    def test_toutes_les_pages_citent_les_memes_actifs(self):
        pages = [self.lire("index.html")] + [self.lire("editions", n) for n in os.listdir(os.path.join(self.pub, "editions"))]
        citees = {tuple(re.findall(r'(?:href|src)="(/actifs/[^"]+)"', p)) for p in pages}
        self.assertEqual(len(citees), 1)

    def test_la_page_entiere_reste_disponible(self):
        page = publier.gabarit()          # d'un seul tenant : c'est celle que lisent les autres tests
        self.assertIn("<style>", page)
        self.assertIn('<script id="app-js">', page)
        modele, actifs = publier.gabarit_en_actifs()
        self.assertEqual(len(actifs), 2)
        self.assertEqual(modele.count("/*DONNEES*/null"), 1)

    def test_les_anciens_actifs_sont_retires_une_fois_les_nouveaux_ecrits(self):
        dossier = os.path.join(self.pub, "actifs")
        vieux = [os.path.join(dossier, n) for n in ("site-000000000000.css", "site-ffffffffffff.js")]
        autre = os.path.join(dossier, "autre.css")      # ce qui n'est pas un actif du site n'est pas touché
        for chemin in vieux + [autre]:
            with open(chemin, "w") as f:
                f.write("x")
        publier.pages(self.db)
        for chemin in vieux:
            self.assertFalse(os.path.exists(chemin), chemin)
        self.assertTrue(os.path.exists(autre))
        os.remove(autre)
        self.assertEqual(len(os.listdir(dossier)), 2)

    def test_un_changement_du_code_change_le_nom(self):
        avant = sorted(os.listdir(os.path.join(self.pub, "actifs")))
        vrai = publier.SITE
        publier.SITE = tempfile.mkdtemp(prefix="gabarit-")
        try:
            shutil.copytree(vrai, publier.SITE, dirs_exist_ok=True)
            with open(os.path.join(publier.SITE, "styles", "base.css"), "a", encoding="utf-8") as f:
                f.write("\n/* changement */\n")
            publier.pages(self.db)
            apres = sorted(os.listdir(os.path.join(self.pub, "actifs")))
            self.assertEqual(len(apres), 2)
            self.assertNotEqual([n for n in apres if n.endswith(".css")], [n for n in avant if n.endswith(".css")])
            self.assertEqual([n for n in apres if n.endswith(".js")], [n for n in avant if n.endswith(".js")])
        finally:
            shutil.rmtree(publier.SITE, ignore_errors=True)
            publier.SITE = vrai
            publier.pages(self.db)

    def test_la_politique_permet_les_actifs(self):
        p = serveur.politique()
        self.assertIn("default-src 'self'", p)
        self.assertIn("script-src 'self'", p)
        self.assertNotIn("style-src", p)      # sans style-src, default-src 'self' couvre la feuille du site


class Service(unittest.TestCase):
    """Le serveur : en-têtes de cache, ETag, 304, gzip, Vary, HEAD, limite de débit."""

    @classmethod
    def setUpClass(cls):
        db = base.connexion()
        try:
            publier.pages(db)
        finally:
            db.close()
        cls.pub = publier.config.public()
        cls.srv = serveur.creer(port=0, hote="127.0.0.1")
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        page = open(os.path.join(cls.pub, "index.html"), encoding="utf-8").read()
        cls.css, cls.js = re.findall(r'(?:href|src)="(/actifs/site-[0-9a-f]{12}\.\w+)"', page)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        serveur.DEBIT.vus.clear()

    def appel(self, chemin, methode="GET", entetes=None, conn=None):
        c = conn or http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request(methode, chemin, headers=entetes or {})
        r = c.getresponse()
        corps = r.read()
        if conn is None:
            c.close()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, corps

    def test_cache_control_par_type(self):
        for chemin in ("/", "/editions/" + sorted(os.listdir(os.path.join(self.pub, "editions")))[0], "/data/jour.json",
                       "/data/editions.json", "/aveugle.html", "/favicon.svg"):
            self.assertEqual(self.appel(chemin)[1]["cache-control"], "public, max-age=300", chemin)
        self.assertEqual(self.appel("/sw.js")[1]["cache-control"], "no-cache")
        for chemin in (self.css, self.js):
            self.assertEqual(self.appel(chemin)[1]["cache-control"], "public, max-age=31536000, immutable", chemin)
        self.assertEqual(self.appel("/api/resultats")[1]["cache-control"], "public, max-age=60")   # inchangé
        statut, entetes, _ = self.appel("/api/lot")
        self.assertEqual((statut, entetes["cache-control"]), (401, "no-store"))
        self.assertNotIn("etag", entetes)

    def test_etag_et_304(self):
        for chemin in ("/", self.css, "/sw.js", "/favicon.svg", "/apple-touch-icon.png"):
            statut, entetes, corps = self.appel(chemin)
            self.assertEqual(statut, 200, chemin)
            etag = entetes["etag"]
            self.assertTrue(re.fullmatch(r'"[0-9a-f]{16}"', etag), (chemin, etag))
            statut, ent2, corps2 = self.appel(chemin, entetes={"If-None-Match": etag})
            self.assertEqual((statut, corps2), (304, b""), chemin)
            self.assertEqual(ent2["etag"], etag)
            self.assertEqual(ent2["cache-control"], entetes["cache-control"])
            self.assertEqual(self.appel(chemin, entetes={"If-None-Match": '"autre"'})[0], 200)
            self.assertEqual(self.appel(chemin, entetes={"If-None-Match": '"x", W/' + etag})[0], 304)
            self.assertEqual(self.appel(chemin, entetes={"If-None-Match": "*"})[0], 304)

    def test_l_etag_change_avec_le_contenu(self):
        chemin = os.path.join(self.pub, "data", "essai.json")
        try:
            with open(chemin, "w") as f:
                f.write('{"a": 1}')
            a = self.appel("/data/essai.json")[1]["etag"]
            with open(chemin, "w") as f:
                f.write('{"a": 2}')
            b = self.appel("/data/essai.json")[1]["etag"]
            self.assertNotEqual(a, b)
        finally:
            os.remove(chemin)

    def test_pas_d_etag_ni_de_304_pour_l_api(self):
        statut, entetes, _ = self.appel("/api/resultats", entetes={"If-None-Match": "*"})
        self.assertEqual(statut, 200)
        self.assertNotIn("etag", entetes)

    def test_gzip_seulement_si_demande(self):
        statut, brut_ent, brut = self.appel(self.js)
        self.assertNotIn("content-encoding", brut_ent)
        self.assertEqual(int(brut_ent["content-length"]), len(brut))
        statut, ent, comprime = self.appel(self.js, entetes={"Accept-Encoding": "gzip, deflate, br"})
        self.assertEqual(ent["content-encoding"], "gzip")
        self.assertEqual(gzip.decompress(comprime), brut)
        self.assertEqual(int(ent["content-length"]), len(comprime))
        self.assertLess(len(comprime), len(brut) / 2)
        self.assertEqual(ent["vary"], "Accept-Encoding")
        self.assertEqual(brut_ent["vary"], "Accept-Encoding")      # Vary aussi sans compression
        self.assertNotEqual(ent["etag"], brut_ent["etag"])         # deux représentations, deux ETag
        self.assertEqual(self.appel(self.js, entetes={"Accept-Encoding": "gzip", "If-None-Match": ent["etag"]})[0], 304)
        self.assertEqual(self.appel(self.js, entetes={"Accept-Encoding": "identity", "If-None-Match": ent["etag"]})[0], 200)

    def test_lecture_de_accept_encoding(self):
        for entete, compresse in (("gzip", True), ("GZIP", True), ("deflate, gzip;q=0.5", True), ("*", True),
                                  ("gzip;q=0", False), ("gzip; q=0.0, deflate", False), ("identity", False),
                                  ("br", False), ("", False), ("*;q=0", False), ("gzip;q=0, *", False),
                                  ("gzip;q=oups", False)):
            ent = self.appel(self.css, entetes={"Accept-Encoding": entete})[1]
            self.assertEqual(ent.get("content-encoding") == "gzip", compresse, entete)

    def test_types_compresses_et_seuil(self):
        gros = {"/": "text/html", self.css: "text/css", self.js: "javascript", "/data/jour.json": "application/json"}
        for chemin, type_mime in gros.items():
            _, ent, corps = self.appel(chemin, entetes={"Accept-Encoding": "gzip"})
            self.assertIn(type_mime, ent["content-type"], chemin)
            plein = gzip.decompress(corps) if ent.get("content-encoding") else corps
            self.assertGreater(len(plein), 1024, chemin)
            self.assertEqual(ent.get("content-encoding"), "gzip", chemin)
        # une image n'est pas compressée, et n'a pas de Vary
        _, ent, _ = self.appel("/apple-touch-icon.png", entetes={"Accept-Encoding": "gzip"})
        self.assertNotIn("content-encoding", ent)
        self.assertNotIn("vary", ent)
        # un petit fichier texte non plus, mais il garde son Vary
        chemin = os.path.join(self.pub, "data", "petit.json")
        try:
            with open(chemin, "w") as f:
                f.write('{"a": 1}')
            _, ent, corps = self.appel("/data/petit.json", entetes={"Accept-Encoding": "gzip"})
            self.assertNotIn("content-encoding", ent)
            self.assertEqual((ent["vary"], corps), ("Accept-Encoding", b'{"a": 1}'))
            with open(chemin, "w") as f:
                f.write(json.dumps({"a": "x" * 2000}))
            self.assertEqual(self.appel("/data/petit.json", entetes={"Accept-Encoding": "gzip"})[1].get("content-encoding"), "gzip")
        finally:
            os.remove(chemin)

    def test_head_a_les_memes_entetes_sans_corps(self):
        for chemin, ae in ((self.js, "gzip"), (self.js, "identity"), ("/", "gzip"), ("/sw.js", "gzip"), ("/favicon.svg", "gzip")):
            entetes = {"Accept-Encoding": ae}
            _, get_ent, corps = self.appel(chemin, entetes=entetes)
            statut, head_ent, vide = self.appel(chemin, "HEAD", entetes)
            self.assertEqual((statut, vide), (200, b""), chemin)
            for k in ("content-length", "content-type", "content-encoding", "etag", "cache-control", "vary"):
                self.assertEqual(head_ent.get(k), get_ent.get(k), (chemin, k))
            self.assertEqual(int(get_ent["content-length"]), len(corps))

    def test_la_connexion_reste_utilisable_apres_un_304_et_un_head(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            etag = self.appel(self.css, conn=c)[1]["etag"]
            self.assertEqual(self.appel(self.css, entetes={"If-None-Match": etag}, conn=c)[0], 304)
            self.assertEqual(self.appel(self.css, "HEAD", conn=c)[0], 200)
            self.assertEqual(self.appel("/sante", conn=c)[0], 200)
        finally:
            c.close()

    def test_la_memoire_est_bornee_et_ne_recompresse_pas(self):
        m = serveur.Memo(entrees=3, octets=10 ** 6)
        brut = b"abc" * 1000
        premier = m.lire(("a", 1, 1), brut, True)
        self.assertIs(m.lire(("a", 1, 1), brut, True), premier)      # même entrée : pas recalculée
        for i in range(10):
            m.lire(("f", i, 1), brut, True)
        self.assertLessEqual(len(m.gardes), 3)
        m = serveur.Memo(entrees=100, octets=500)                    # bornée aussi en octets
        for i in range(10):
            m.lire(("f", i, 1), os.urandom(400), True)
        self.assertLessEqual(len(m.gardes), 1)

    def test_les_pages_ne_sont_pas_limitees_l_api_l_est(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            for i in range(330):   # plus que les 300 par minute : les fichiers publics passent tous
                statut = self.appel(self.css if i % 2 else "/", conn=c)[0]
                self.assertEqual(statut, 200, i)
            self.assertEqual(self.appel("/sante", conn=c)[0], 200)
            for i in range(300):
                self.assertEqual(self.appel("/api/resultats", conn=c)[0], 200, i)
            statut, ent, corps = self.appel("/api/resultats", conn=c)
            self.assertEqual(statut, 429)
            self.assertEqual(ent["cache-control"], "no-store")
            self.assertEqual(self.appel("/", conn=c)[0], 200)        # l'API bloquée ne bloque pas les pages
        finally:
            c.close()

    def test_les_autres_limites_restent(self):
        for i in range(10):
            self.assertEqual(self.appel("/api/inscription", "POST", {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.appel("/api/inscription", "POST")[0], 429)

    def test_un_fichier_hors_de_public_reste_introuvable(self):
        self.assertEqual(self.appel("/actifs/site-000000000000.css")[0], 404)
        self.assertEqual(self.appel("/../comparateur.db")[0], 404)


if __name__ == "__main__":
    unittest.main()
