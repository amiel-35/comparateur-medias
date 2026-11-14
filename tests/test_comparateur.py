"""Tests du back-end, sans réseau ni modèle.  Depuis back/ :  python3 -m unittest discover -s tests -v"""
import json, os, shutil, sys, tempfile, threading, unittest, urllib.error, urllib.request

DOSSIER = tempfile.mkdtemp(prefix="comparateur-test-")
os.environ["COMPARATEUR_DONNEES"] = DOSSIER
os.environ["COMPARATEUR_MIN_PAR_BORD"] = "2"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from comparateur import aveugle, base, fabrique, llm, publier, serveur  # noqa: E402


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
        self.assertEqual([base.bord(x) for x in (-2.4, -0.7, 0.1, 0.6, 1.02)],
                         ["gauche", "centre-gauche", "centre", "centre-droit", "droite"])


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
