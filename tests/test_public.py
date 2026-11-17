"""Phase 1, le public solide : statuts « classé » et « non classé », versions gardées avec chaque édition.
Sans réseau ni modèle.  python3 -m unittest discover -s tests"""
import json, os, shutil, sqlite3, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from comparateur import base, config, methode, publier, syntheses  # noqa: E402
from comparateur import fabrique  # noqa: E402

_AVANT = None


def setUpModule():
    global _AVANT, DOSSIER
    _AVANT = os.environ.get("COMPARATEUR_DONNEES")
    DOSSIER = tempfile.mkdtemp(prefix="comparateur-public-")
    os.environ["COMPARATEUR_DONNEES"] = DOSSIER


def tearDownModule():
    if _AVANT is None:
        os.environ.pop("COMPARATEUR_DONNEES", None)
    else:
        os.environ["COMPARATEUR_DONNEES"] = _AVANT
    shutil.rmtree(DOSSIER, ignore_errors=True)


def ref_avec_un_non_classe():
    """medias.json, plus un média fictif sans score : le mécanisme, sans ajouter de média réel."""
    with open(os.path.join(config.ICI, "medias.json"), encoding="utf-8") as f:
        ref = json.load(f)
    ref["medias"].append({"nom": "Journal fictif", "score": None, "flux": ["https://fictif.test/rss"]})
    chemin = os.path.join(DOSSIER, "medias-essai.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False)
    return chemin


class NonClasse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = base.connexion()
        base.charger_medias(cls.db, ref_avec_un_non_classe())
        ids = {r["nom"]: r["id"] for r in cls.db.execute("SELECT id, nom FROM medias")}
        cls.ids = ids
        for k, nom in enumerate(["L'Humanité", "Le Monde", "franceinfo", "Journal fictif", "Le JDD"]):
            cls.db.execute("INSERT INTO articles (cle, media_id, titre, lien, recolte) VALUES (?,?,?,?,?)",
                           (f"nc-{k}", ids[nom], f"Un titre {k}", f"https://x.test/{k}", base.iso()))
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_aucune_note_et_jamais_au_centre(self):
        mid = self.ids["Journal fictif"]
        self.assertIsNone(self.db.execute("SELECT 1 FROM notes_media WHERE media_id = ?", (mid,)).fetchone())
        self.assertNotIn(mid, base.scores(self.db))
        self.assertEqual(base.statut(None), "non-classe")
        self.assertEqual(base.statut(0.0), "classe")      # un score nul est le centre, pas l'absence de score
        d = publier.donnees_du_jour(self.db)
        lu = {m["nom"]: m for m in d["medias"]}["Journal fictif"]
        self.assertEqual((lu["score"], lu["bord"], lu["statut"]), (None, None, "non-classe"))
        self.assertEqual({m["statut"] for m in d["medias"] if m["nom"] != "Journal fictif"}, {"classe"})
        self.assertNotIn("Journal fictif", [m["nom"] for m in d["classement"]["medias"]])   # le classement est FrIdéo
        self.assertEqual(d["non_classes"], ["Journal fictif"])

    def test_couverture_oui_bord_et_silence_non(self):
        charge = {"medias": [{"nom": "A", "score": -1.0}, {"nom": "B", "score": -0.9}, {"nom": "C", "score": 0.0},
                             {"nom": "D", "score": 1.0}, {"nom": "Fictif", "score": None, "bord": None}],
                  "sujets": [{"id": "s1", "titre": "t", "articles": [
                      {"media": m, "titre": m, "lien": "https://x.test/" + m} for m in ("A", "B", "C", "Fictif")]}]}
        bord = syntheses.bords_des_medias(charge)
        self.assertIsNone(bord["Fictif"])
        su = syntheses.suivi([("2026-11-20", charge)])["s1"][0]
        self.assertEqual(su["medias"], 4)                      # la couverture compte le non classé
        self.assertEqual(sum(su["par"].values()), 3)           # aucun bord ne le compte
        self.assertEqual(su["silences"], ["d"])                # il ne comble pas le silence de la droite
        p = syntheses.periode([("2026-11-20", charge)], "2026-S47", "2026-11-16", "2026-11-22")
        f = {m["nom"]: m for m in p["medias"]}["Fictif"]
        self.assertEqual((f["bord"], f["cote"]), (None, None))

    def test_le_modele_ne_le_range_sous_aucun_cote(self):
        self.db.execute("INSERT INTO sujets (id, libelle, cree) VALUES (900, 'essai', ?)", (base.iso(),))
        self.db.executemany("INSERT INTO sujet_articles (sujet_id, article_id) VALUES (900, ?)",
                            [(r["id"],) for r in self.db.execute("SELECT id FROM articles WHERE cle LIKE 'nc-%'")])
        self.db.commit()
        s = [x for x in fabrique.sujets_du_jour(self.db) if x["id"] == 900][0]
        cotes = {a["media"]: a["cote"] for a in s["articles"]}
        self.assertIsNone(cotes["Journal fictif"])
        self.assertEqual(cotes["Le JDD"], "d")
        self.assertEqual(s["medias"], 5)

    def test_les_vues_prevoient_le_non_classe(self):
        page = publier.gabarit()
        self.assertIn("(D.non_classes||[])", page)            # facultatif : une édition d'avant s'affiche
        self.assertIn('<span class="bchip b-nc">Non classé</span>', page)
        self.assertIn("if(m.nc){", page)                       # fiche d'un média non classé
        self.assertIn("r.nc&&r.nc.length", page)               # page d'un sujet


class Versions(unittest.TestCase):
    def test_une_base_d_avant_recoit_les_versions_sans_reecrire_les_donnees(self):
        dossier = tempfile.mkdtemp(prefix="comparateur-versions-")
        avant = os.environ["COMPARATEUR_DONNEES"]
        os.environ["COMPARATEUR_DONNEES"] = dossier
        try:
            vieux = sqlite3.connect(config.base())
            vieux.execute("CREATE TABLE editions (jour TEXT PRIMARY KEY, cree TEXT NOT NULL, donnees TEXT NOT NULL)")
            d1 = json.dumps({"source_classement": "FrIdéo v1.0, French News Lab (Amr Sobhy), CC BY 4.0", "sujets": []})
            d2 = json.dumps({"sujets": []})
            vieux.executemany("INSERT INTO editions VALUES (?, ?, ?)", [("2026-11-14", "x", d1), ("2026-11-15", "x", d2)])
            vieux.commit()
            vieux.close()
            db = base.connexion()
            try:
                lignes = {r["jour"]: r for r in db.execute("SELECT * FROM editions")}
                self.assertEqual((lignes["2026-11-14"]["methode"], lignes["2026-11-14"]["classement"]), ("", "FrIdéo v1.0"))
                self.assertEqual((lignes["2026-11-15"]["methode"], lignes["2026-11-15"]["classement"]), ("", ""))
                self.assertEqual(lignes["2026-11-14"]["donnees"], d1)      # les données gardées ne bougent pas
                self.assertFalse(base.migrer_versions(db))                  # une seconde fois : rien à faire
                base.charger_medias(db)
                publier.enregistrer_edition(db, "2026-11-16")
                r = db.execute("SELECT methode, classement FROM editions WHERE jour = '2026-11-16'").fetchone()
                self.assertEqual((r["methode"], r["classement"]), (methode.VERSION, "FrIdéo v1.0"))
                publier.ecrire_pages(db)
                with open(os.path.join(config.public(), "data", "editions", "2026-11-14.json"), encoding="utf-8") as f:
                    self.assertEqual(json.load(f)["versions"], {"methode": "", "classement": "FrIdéo v1.0"})
                with open(os.path.join(config.public(), "data", "editions", "2026-11-16.json"), encoding="utf-8") as f:
                    self.assertEqual(json.load(f)["versions"], {"methode": methode.VERSION, "classement": "FrIdéo v1.0"})
            finally:
                db.close()
        finally:
            os.environ["COMPARATEUR_DONNEES"] = avant
            shutil.rmtree(dossier, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
