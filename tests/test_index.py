"""Phase 1, l'index public et « Situer un article » : la normalisation des adresses (mêmes vecteurs en Python et en
JavaScript), le contenu de l'index, sa fenêtre, ses octets, et la vue qui ne fait qu'un appel réseau.
Sans réseau ni modèle.  python3 -m unittest discover -s tests"""
import gzip, json, os, re, shutil, subprocess, sys, tempfile, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, ".."))
from comparateur import base, config, index, publier  # noqa: E402

_AVANT = None
VECTEURS = os.path.join(ICI, "vecteurs-adresses.json")


def setUpModule():
    global _AVANT, DOSSIER
    _AVANT = os.environ.get("COMPARATEUR_DONNEES")
    DOSSIER = tempfile.mkdtemp(prefix="comparateur-index-")
    os.environ["COMPARATEUR_DONNEES"] = DOSSIER


def tearDownModule():
    if _AVANT is None:
        os.environ.pop("COMPARATEUR_DONNEES", None)
    else:
        os.environ["COMPARATEUR_DONNEES"] = _AVANT
    shutil.rmtree(DOSSIER, ignore_errors=True)


def vecteurs():
    with open(VECTEURS, encoding="utf-8") as f:
        return json.load(f)


class Adresses(unittest.TestCase):
    def test_assez_de_vecteurs(self):
        v = vecteurs()
        self.assertGreaterEqual(len(v), 25)
        self.assertIn(None, [x["normalisee"] for x in v])   # les refus sont dans les vecteurs

    def test_vecteurs_en_python(self):
        for x in vecteurs():
            with self.subTest(x["entree"]):
                self.assertEqual(index.normaliser(x["entree"]), x["normalisee"])
                self.assertEqual(index.cle(x["entree"]), x["cle"])

    def test_la_cle_est_16_caracteres_hexadecimaux(self):
        for x in vecteurs():
            if x["normalisee"] is None:
                self.assertIsNone(x["cle"])
            else:
                self.assertRegex(x["cle"], r"^[0-9a-f]{16}$")

    def test_un_article_et_ses_variantes_ont_la_meme_cle(self):
        base_ = index.cle("https://www.lemonde.fr/a/b")
        for v in ("http://LEMONDE.fr/a/b/", "https://m.lemonde.fr/a/b?utm_source=x#c", "https://lemonde.fr:443/a/b"):
            self.assertEqual(index.cle(v), base_)
        self.assertNotEqual(index.cle("https://lemonde.fr/a/B"), base_)   # le chemin garde sa casse

    def test_pas_une_chaine(self):
        self.assertIsNone(index.normaliser(None))
        self.assertIsNone(index.cle(None))

    @unittest.skipUnless(shutil.which("node"), "node absent : la moitié JavaScript n'est pas essayée")
    def test_vecteurs_en_javascript(self):
        """Les mêmes vecteurs, passés dans js/adresse.js tel que le site le reçoit (chargé dans vm)."""
        script = r"""
const fs = require('fs'), vm = require('vm');
const [adresse, vecteurs] = process.argv.slice(1);
const ctx = vm.createContext({ crypto: globalThis.crypto, TextEncoder, Uint8Array, Promise, Array });
vm.runInContext(fs.readFileSync(adresse, 'utf8') + '\nthis.n = normaliserAdresse; this.c = cleAdresse;', ctx);
(async () => {
  const mauvais = [];
  for (const v of JSON.parse(fs.readFileSync(vecteurs, 'utf8'))) {
    const n = ctx.n(v.entree), c = await ctx.c(v.entree);
    if (n !== v.normalisee || c !== v.cle) mauvais.push({ entree: v.entree, n, c, attendu: [v.normalisee, v.cle] });
  }
  console.log(JSON.stringify(mauvais));
})();
"""
        r = subprocess.run(["node", "-e", script, os.path.join(publier.SITE, "js", "adresse.js"), VECTEURS],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [])


def media(nom, score, **plus):
    return {"nom": nom, "score": score, "bord": None, "proprietaire": None, **plus}


def sujet(sid, titre, articles):
    return {"id": sid, "titre": titre, "fait": "", "divergence": None, "analyse": {}, "mots": [],
            "articles": [{"media": m, "titre": f"{titre} ({m})", "lien": lien} for m, lien in articles]}


MEDIAS = [media("Journal A", -1.9), media("Journal B", -0.5), media("Journal C", 0.0), media("Journal D", 0.9),
          media("Journal fictif", None, statut="non-classe")]


def edition(jour, sujets, seuls=(), versions=None):
    c = {"medias": MEDIAS, "non_classes": ["Journal fictif"], "sujets": sujets,
         "seuls": [{"media": m, "titre": "seul", "lien": lien} for m, lien in seuls],
         "classement": {"medias": [{"nom": "Journal A", "score": -1.9, "ic": [-2.4, -1.4]}]}}
    if versions:
        c["versions"] = versions
    return jour, c


def un_sujet_large(sid, jour):
    return sujet(sid, "Un sujet " + sid, [("Journal A", f"https://a.test/{jour}/{sid}"), ("Journal B", f"https://www.b.test/{jour}/{sid}?x=1"),
                                        ("Journal C", f"https://c.test/{jour}/{sid}"), ("Journal fictif", f"https://fictif.test/{jour}/{sid}")])


def charges_d_essai():
    return [edition("2026-11-10", [un_sujet_large("s1", "2026-11-10")]),
            edition("2026-11-15", [un_sujet_large("s1", "2026-11-15"), un_sujet_large("s2", "2026-11-15")],
                    seuls=[("Journal D", "https://d.test/seul")], versions={"methode": "1.2", "classement": "FrIdéo v1.0"}),
            edition("2026-11-16", [un_sujet_large("s3", "2026-11-16")], versions={"methode": "1.2", "classement": "FrIdéo v1.0"})]


class Contenu(unittest.TestCase):
    def setUp(self):
        self.ix = index.construire(charges_d_essai())

    def test_entete(self):
        self.assertEqual(self.ix["v"], 1)
        self.assertEqual(self.ix["genere_le"], "2026-11-16")   # un jour, pas d'heure : les mêmes octets
        self.assertEqual((self.ix["methode"], self.ix["classement"]), ("1.2", "FrIdéo v1.0"))

    def test_medias_par_domaine(self):
        m = self.ix["medias"]
        self.assertEqual(m["a.test"], {"nom": "Journal A", "statut": "classe", "bande": "extreme-gauche", "score": -1.9, "ic": [-2.4, -1.4]})
        self.assertEqual(m["b.test"]["nom"], "Journal B")      # www. retiré
        self.assertEqual(m["d.test"]["bande"], "droite")   # vu seulement dans les titres sans jumeau
        self.assertEqual(m["fictif.test"], {"nom": "Journal fictif", "statut": "non-classe"})
        self.assertEqual(set(m), {"a.test", "b.test", "c.test", "d.test", "fictif.test"})

    def test_sujets_et_articles(self):
        s = self.ix["sujets"]["s1"]
        self.assertEqual(s["jour"], "2026-11-15")               # la plus récente des éditions où il figure
        self.assertEqual(s["page"], "/editions/2026-11-15.html#/sujet/s1")
        self.assertEqual(sum(s["par"].values()), 3)             # le non classé n'est dans aucun bord
        self.assertEqual(set(s["par"]), set(base.BANDES))
        self.assertEqual(s["silences"], ["d"])                  # 4 médias, aucun titre de la droite, un média lu à droite
        self.assertEqual(self.ix["articles"][index.cle("https://b.test/2026-11-16/s3")], "s3")
        self.assertEqual(self.ix["articles"][index.cle("https://www.b.test/2026-11-16/s3?utm=1#x")], "s3")
        self.assertEqual(len(self.ix["articles"]), 16)           # 4 liens dans chacun des 4 sujets de la fenêtre

    def test_fenetre_de_sept_jours(self):
        charges = charges_d_essai()
        self.assertNotIn("2026-11-10", {s["jour"] for s in self.ix["sujets"].values()})
        ix = index.construire(charges + [edition("2026-11-09", [un_sujet_large("s0", "2026-11-09")])])
        self.assertNotIn("s0", ix["sujets"])                    # 11-09 est avant 11-10 : hors fenêtre (11-10 à 11-16)
        self.assertIn("s1", ix["sujets"])
        ix = index.construire(charges)
        self.assertEqual(index._fenetre(charges)[0][0], "2026-11-10")   # le septième jour est compris
        self.assertEqual(index._fenetre(charges + [edition("2026-11-17", [])])[0][0], "2026-11-15")

    def test_hote_ambigu_ecarte(self):
        a = edition("2026-11-16", [sujet("s1", "t", [("Journal A", "https://commun.test/a"), ("Journal B", "https://commun.test/b"),
                                                       ("Journal A", "https://a.test/x"), ("Journal C", "https://c.test/x")])])
        ix = index.construire([a])
        self.assertNotIn("commun.test", ix["medias"])
        self.assertIn("a.test", ix["medias"])
        self.assertIn(index.cle("https://commun.test/a"), ix["articles"])   # l'article reste cherchable

    def test_domaines_declares(self):
        a = edition("2026-11-16", [sujet("s1", "t", [("Journal A", "https://a.test/x")])])
        ix = index.construire([a], {"Journal A": ["www.autre.test", "A.TEST"]})
        self.assertEqual(ix["medias"]["autre.test"]["nom"], "Journal A")
        ix = index.construire([a], {"Journal B": ["a.test"]})   # un domaine déclaré chez deux médias : ambigu
        self.assertNotIn("a.test", ix["medias"])

    def test_aucune_donnee_personnelle(self):
        champs = {"v", "genere_le", "methode", "classement", "medias", "sujets", "articles"}
        self.assertEqual(set(self.ix), champs)
        for m in self.ix["medias"].values():
            self.assertLessEqual(set(m), {"nom", "statut", "bande", "score", "ic"})
        for s in self.ix["sujets"].values():
            self.assertEqual(set(s), {"titre", "jour", "par", "silences", "page"})
        for k, v in self.ix["articles"].items():
            self.assertRegex(k, r"^[0-9a-f]{16}$")            # des empreintes, pas des adresses
        brut = json.dumps(self.ix, ensure_ascii=False)
        self.assertNotRegex(brut, r"https?://|@|\?")
        for mot in ("abonn", "votant", "mail", "adresse_ip", "journal_fabrique"):
            self.assertNotIn(mot, brut.lower())

    def test_une_edition_ancienne_passe(self):
        """Sans `versions`, sans `statut`, sans `classement` ni `non_classes`, sans `seuls`."""
        c = {"medias": [{"nom": "Journal A", "score": -1.9}, {"nom": "Journal B", "score": -0.5}],
             "sujets": [sujet("s1", "t", [("Journal A", "https://a.test/x"), ("Journal B", "https://b.test/x")])]}
        ix = index.construire([("2026-11-16", c)])
        self.assertEqual((ix["methode"], ix["classement"]), ("", ""))
        self.assertEqual(ix["medias"]["a.test"], {"nom": "Journal A", "statut": "classe", "bande": "extreme-gauche", "score": -1.9, "ic": None})
        self.assertEqual(index.construire([])["genere_le"], "")


class Ecriture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = base.connexion()
        base.charger_medias(cls.db)
        for jour, charge in charges_d_essai():
            charge["medias"] = [m for m in charge["medias"] if m["nom"] != "Journal fictif"]
            charge["classement"] = {"source": "", "medias": []}
            cls.db.execute("INSERT INTO editions (jour, cree, donnees) VALUES (?,?,?)", (jour, base.iso(), json.dumps(charge)))
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def lire(self):
        with open(os.path.join(config.public(), "index.json"), "rb") as f:
            return f.read()

    def test_ecrit_par_ecrire_pages_les_memes_octets(self):
        publier.ecrire_pages(self.db)
        un = self.lire()
        publier.ecrire_pages(self.db)
        self.assertEqual(un, self.lire())
        ix = json.loads(un)
        self.assertEqual(ix["v"], 1)
        self.assertEqual(ix["genere_le"], "2026-11-16")
        self.assertEqual(ix["methode"], "")                      # éditions insérées sans version : le repli
        self.assertFalse(os.path.exists(os.path.join(config.public(), "index.json.tmp")))
        self.assertEqual(un.decode("utf-8"), json.dumps(ix, sort_keys=True, separators=(",", ":"), ensure_ascii=False))

    def test_taille(self):
        publier.ecrire_pages(self.db)
        brut = self.lire()
        self.assertLess(len(gzip.compress(brut)), 200_000)


class Vue(unittest.TestCase):
    def test_un_seul_appel_reseau_vers_l_index(self):
        with open(os.path.join(publier.SITE, "js", "vues", "situer.js"), encoding="utf-8") as f:
            src = f.read()
        self.assertEqual(re.findall(r"fetch\(([^)]*)\)", src), ["'/index.json'"])   # une adresse, sans paramètre
        self.assertEqual(len(re.findall(r"\bfetch\b", src)), 1)
        for interdit in ("XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "<img", "<script", "<iframe"):
            self.assertNotIn(interdit, src)
        self.assertNotIn("?", re.search(r"fetch\(([^)]*)\)", src).group(1))
        with open(os.path.join(publier.SITE, "js", "adresse.js"), encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"fetch|XMLHttpRequest|sendBeacon")

    def test_la_vue_est_branchee(self):
        page = publier.gabarit()
        self.assertIn("function vSituer", page)
        self.assertIn("function normaliserAdresse", page)
        self.assertIn('data-nav="situer"', page)
        self.assertIn("vSituer()", page)


if __name__ == "__main__":
    unittest.main()
