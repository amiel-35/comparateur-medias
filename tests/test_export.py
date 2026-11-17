"""Phase 1, l'export public de chaque édition : un JSON daté par jour, identique pour tous, décrit par un schéma.
Sans réseau ni modèle.  python3 -m unittest discover -s tests"""
import copy, json, os, shutil, subprocess, sys, tempfile, unittest

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RACINE)
from comparateur import base, config, export, publier, schema, syntheses  # noqa: E402

_AVANT = None
INTERDITES = {"adresse", "jeton", "votant", "abonne", "aveugle", "mail"}


def setUpModule():
    global _AVANT, DOSSIER
    _AVANT = os.environ.get("COMPARATEUR_DONNEES")
    DOSSIER = tempfile.mkdtemp(prefix="comparateur-export-")
    os.environ["COMPARATEUR_DONNEES"] = DOSSIER


def tearDownModule():
    if _AVANT is None:
        os.environ.pop("COMPARATEUR_DONNEES", None)
    else:
        os.environ["COMPARATEUR_DONNEES"] = _AVANT
    shutil.rmtree(DOSSIER, ignore_errors=True)


def cles(noeud):
    """Toutes les clés d'un document, à tous les niveaux."""
    if isinstance(noeud, dict):
        for k, v in noeud.items():
            yield k
            yield from cles(v)
    elif isinstance(noeud, list):
        for v in noeud:
            yield from cles(v)


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return f.read()


class Export(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Les quatre éditions d'essai : la première au format d'avant (ni statut, ni non_classes, ni rubriques),
        # les deux dernières avec un média non classé fictif. Le script écrit le site, export compris.
        subprocess.run([sys.executable, os.path.join(RACINE, "essais", "editions_essai.py")], check=True,
                       env=dict(os.environ, COMPARATEUR_DONNEES=DOSSIER), stdout=subprocess.DEVNULL)
        cls.pub = config.public()
        cls.dossier = os.path.join(cls.pub, "export", "editions")
        cls.jours = json.loads(lire(os.path.join(cls.pub, "export", "editions.json")))
        cls.docs = {j: json.loads(lire(os.path.join(cls.dossier, j + ".json"))) for j in cls.jours}
        cls.schema = json.loads(lire(os.path.join(cls.pub, "export", "schema.json")))
        cls.db = base.connexion()
        cls.gardees = {r["jour"]: json.loads(r["donnees"]) for r in cls.db.execute("SELECT jour, donnees FROM editions")}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_la_liste_des_jours_et_le_schema_sont_publies(self):
        self.assertEqual(self.jours, ["2026-11-11", "2026-11-12", "2026-11-13", "2026-11-14"])
        self.assertEqual(self.schema, export.schema_publie())
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_chaque_export_passe_le_schema(self):
        for jour, doc in self.docs.items():
            self.assertEqual(schema.erreurs(doc, self.schema), [], jour)
            self.assertEqual((doc["v"], doc["jour"]), (1, jour))

    def test_une_edition_ancienne_s_exporte_avec_des_valeurs_par_defaut(self):
        ancienne = self.gardees["2026-11-11"]
        self.assertNotIn("non_classes", ancienne)                # le format d'avant
        self.assertNotIn("statut", ancienne["medias"][0])
        doc = self.docs["2026-11-11"]
        self.assertEqual(doc["non_classes"], [])
        self.assertEqual({m["statut"] for m in doc["medias"]}, {"classe"})
        for m in doc["medias"]:                                   # le bord se relit dans le score
            self.assertEqual(m["bande"], base.bord(m["score"]))
        self.assertEqual(doc["versions"], {"methode": "", "classement": ""})   # base d'essai sans versions
        self.assertEqual(export.edition("2026-11-01", {}, None)["sujets"], [])  # même une charge vide
        schema.verifier(export.edition("2026-11-01", {}, None), self.schema)

    def test_un_media_non_classe_n_a_ni_score_ni_bande(self):
        doc = self.docs["2026-11-14"]
        nc = [m for m in doc["medias"] if m["statut"] == "non-classe"]
        self.assertEqual([(m["nom"], m["score"], m["bande"]) for m in nc], [("Le Journal d'essai", None, None)])
        self.assertEqual(doc["non_classes"], ["Le Journal d'essai"])
        avec = [s for s in doc["sujets"] if any(a["media"] == "Le Journal d'essai" for a in s["articles"])]
        self.assertTrue(avec)                                       # il compte dans la couverture
        for s in avec:                                              # mais dans aucune bande
            self.assertEqual(sum(s["par_bande"].values()), sum(a["media"] != "Le Journal d'essai" for a in s["articles"]))

    def test_les_comptages_par_bande_sont_ceux_de_syntheses(self):
        for jour, doc in self.docs.items():
            charge = self.gardees[jour]
            bord = syntheses.bords_des_medias(charge)
            lus = syntheses.medias_lus(bord)
            for s, g in zip(doc["sujets"], charge["sujets"]):
                noms = [a["media"] for a in g["articles"]]
                par = syntheses.repartition(noms, bord)
                self.assertEqual(s["par_bande"], par)
                self.assertEqual(s["cotes_silencieux"], syntheses.silencieux(par, lus, len(set(noms))))
        self.assertTrue(any(s["cotes_silencieux"] for d in self.docs.values() for s in d["sujets"]))

    def test_deux_ecritures_donnent_les_memes_octets(self):
        avant = {j: lire(os.path.join(self.dossier, j + ".json")) for j in self.jours}
        liste, sch = (lire(os.path.join(self.pub, "export", n)) for n in ("editions.json", "schema.json"))
        publier.ecrire_pages(self.db)
        publier.ecrire_pages(self.db)
        for j in self.jours:
            self.assertEqual(lire(os.path.join(self.dossier, j + ".json")), avant[j])
        self.assertEqual(lire(os.path.join(self.pub, "export", "editions.json")), liste)
        self.assertEqual(lire(os.path.join(self.pub, "export", "schema.json")), sch)
        brut = avant["2026-11-14"]
        self.assertEqual(brut, json.dumps(json.loads(brut), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        self.assertIn("FrIdéo", brut)                              # UTF-8 direct, pas de é
        self.assertNotIn("recolte", brut)                          # aucune heure de génération
        self.assertFalse([f for f in os.listdir(self.dossier) if f.endswith(".tmp")])

    def test_aucune_cle_interdite_a_aucun_niveau(self):
        for jour, doc in self.docs.items():
            self.assertFalse(INTERDITES & set(cles(doc)), jour)
        self.assertFalse(INTERDITES & set(cles(self.schema)))
        # Un champ propre à une page n'est pas exporté : seules les clés du schéma sortent.
        self.assertEqual(set(self.docs["2026-11-14"]), set(self.schema["required"]))

    def test_aucune_base_dans_public(self):
        for dossier, _, fichiers in os.walk(self.pub):
            for nom in fichiers:
                chemin = os.path.join(dossier, nom)
                self.assertFalse(nom.endswith((".db", ".sqlite", ".sqlite3")), chemin)
                with open(chemin, "rb") as f:
                    self.assertNotEqual(f.read(16), b"SQLite format 3\x00", chemin)

    def test_une_edition_qui_ne_passe_pas_le_schema_arrete_l_ecriture(self):
        charge = copy.deepcopy(self.gardees["2026-11-14"])
        charge["sujets"][0]["id"] = "sujet-un"                    # pas de la forme s<nombre>
        sortie = os.path.join(DOSSIER, "refuse")
        with self.assertRaises(schema.ErreurSchema):
            export.ecrire(sortie, [("2026-11-14", charge, None)])
        self.assertFalse(os.path.exists(os.path.join(sortie, "export", "editions", "2026-11-14.json")))

    def test_le_serveur_sert_l_export_en_json(self):
        import threading, urllib.request
        from http.server import ThreadingHTTPServer
        from comparateur import serveur
        gestionnaire = next(getattr(serveur, n) for n in dir(serveur)
                            if isinstance(getattr(serveur, n), type) and hasattr(getattr(serveur, n), "do_GET"))
        srv = ThreadingHTTPServer(("127.0.0.1", 0), gestionnaire)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/export/editions/2026-11-14.json")
            self.assertTrue(r.headers["Content-Type"].startswith("application/json"))
            self.assertEqual(json.loads(r.read())["jour"], "2026-11-14")
        finally:
            srv.shutdown()
            srv.server_close()


class Validateur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = export.schema_publie()
        cls.bon = export.edition("2026-11-20", {"medias": [{"nom": "A", "score": -1.0}], "sujets": [
            {"id": "s1", "titre": "t", "articles": [{"media": "A", "titre": "x", "lien": "https://x.test/1"}]}]},
            {"methode": "1.0", "classement": "FrIdéo v1.0"})

    def test_le_bon_document_passe(self):
        self.assertEqual(schema.erreurs(self.bon, self.schema), [])

    def test_une_cle_en_trop_est_refusee(self):
        for chemin in (lambda d: d, lambda d: d["sujets"][0], lambda d: d["medias"][0]):
            doc = copy.deepcopy(self.bon)
            chemin(doc)["adresse"] = "x@y.z"
            self.assertTrue(any("clé non prévue : adresse" in e for e in schema.erreurs(doc, self.schema)))

    def test_un_type_faux_est_refuse(self):
        for modif in (lambda d: d.update(total="640"), lambda d: d.update(heures=True),
                      lambda d: d["medias"][0].update(score="-1"), lambda d: d["sujets"][0].update(divergence=2.5)):
            doc = copy.deepcopy(self.bon)
            modif(doc)
            self.assertTrue(schema.erreurs(doc, self.schema))

    def test_un_champ_requis_absent_est_refuse(self):
        doc = copy.deepcopy(self.bon)
        del doc["licences"]
        del doc["sujets"][0]["par_bande"]
        fautes = schema.erreurs(doc, self.schema)
        self.assertTrue(any("requis absent : licences" in e for e in fautes))
        self.assertTrue(any("requis absent : par_bande" in e for e in fautes))
        with self.assertRaises(schema.ErreurSchema):
            schema.verifier(doc, self.schema)

    def test_enum_motif_et_bornes(self):
        for modif in (lambda d: d.update(v=2), lambda d: d.update(jour="14/11/2026"),
                      lambda d: d["medias"][0].update(statut="inconnu"), lambda d: d["medias"][0].update(bande="milieu"),
                      lambda d: d["sujets"][0]["par_bande"].update(centre=-1), lambda d: d.update(heures=0)):
            doc = copy.deepcopy(self.bon)
            modif(doc)
            self.assertTrue(schema.erreurs(doc, self.schema))

    def test_null_permis_seulement_la_ou_le_schema_le_dit(self):
        doc = copy.deepcopy(self.bon)
        doc["medias"][0].update(statut="non-classe", score=None, bande=None)
        self.assertEqual(schema.erreurs(doc, self.schema), [])
        doc["sujets"][0]["fait"] = None
        self.assertTrue(schema.erreurs(doc, self.schema))

    def test_un_booleen_n_est_pas_un_nombre(self):
        self.assertTrue(schema.erreurs(True, {"type": "integer"}))
        self.assertTrue(schema.erreurs(True, {"type": ["number", "null"]}))
        self.assertEqual(schema.erreurs(None, {"type": ["number", "null"]}), [])
        self.assertTrue(schema.erreurs(1, {"enum": [True]}))


if __name__ == "__main__":
    unittest.main()
