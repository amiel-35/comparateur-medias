"""Phase 2, le compte durable : registre des abonnements, connexion par code, cookie d'hôte, trois noms d'hôte,
migration d'abonnes, alerte du matin, flux par sujet, et la séparation fabrique / tiroir identité.
Sans réseau ni vrai SMTP.  python3 -m unittest discover -s tests"""
import contextlib, io, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, threading, unittest
import urllib.error, urllib.request
import xml.etree.ElementTree as ET

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RACINE)
from comparateur import abonnements, base, comptes, config, lettre, migrations, publier, serveur  # noqa: E402

REGLAGES = {"COMPARATEUR_SMTP_UTILISATEUR": "essai", "COMPARATEUR_SMTP_MOT_DE_PASSE": "secret",
            "COMPARATEUR_SITE_URL": "https://cadrages.test"}
_AVANT = {}


class FauxSMTP:
    envoyes = []

    def __init__(self, cfg):
        pass

    def send_message(self, msg):
        FauxSMTP.envoyes.append(msg)

    def quit(self):
        pass


def setUpModule():
    global DOSSIER
    DOSSIER = tempfile.mkdtemp(prefix="comparateur-compte-")
    for k, v in dict(REGLAGES, COMPARATEUR_DONNEES=DOSSIER).items():
        _AVANT[k] = os.environ.get(k)
        os.environ[k] = v
    _AVANT["smtp"], lettre.ouvrir_smtp = lettre.ouvrir_smtp, FauxSMTP
    lettre.EN_ARRIERE_PLAN = False


def tearDownModule():
    lettre.ouvrir_smtp, lettre.EN_ARRIERE_PLAN = _AVANT.pop("smtp"), True
    for k, v in _AVANT.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    shutil.rmtree(DOSSIER, ignore_errors=True)


class Registre(unittest.TestCase):
    def setUp(self):
        self.db = comptes.connexion()
        self.db.execute("DELETE FROM comptes")
        self.db.commit()
        self.c = comptes.compte_de(self.db, "registre@exemple.fr", creer=True)

    def tearDown(self):
        self.db.close()

    def test_16_type_inconnu_ou_d_opinion_refuse(self):
        with self.assertRaises(abonnements.Refus):
            comptes.abonner(self.db, self.c, "inconnu")
        faux = dict(abonnements.REGISTRE, journaux=abonnements.Type("Journaux suivis", "opinion", ("Le Monde",), 5, "", "", True, None))
        with self.assertRaises(ValueError):
            abonnements.verifier_registre(faux)
        self.assertNotIn("opinion", {t.classe for t in abonnements.REGISTRE.values()})

    def test_17_cible_hors_liste_refusee(self):
        for cible in ("immigration", "Le Monde", "gauche", "<script>", " politique"):
            with self.assertRaises(abonnements.Refus, msg=cible):
                comptes.abonner(self.db, self.c, "rubrique", cible)
        with self.assertRaises(abonnements.Refus):
            comptes.abonner(self.db, self.c, "lettre", "politique")    # la lettre ne prend pas de cible
        for r in ("politique", "international", "economie"):
            comptes.abonner(self.db, self.c, "rubrique", r)
        with self.assertRaises(abonnements.Refus):                       # trois au plus
            comptes.abonner(self.db, self.c, "rubrique", "sciences")

    def test_le_panel_est_declare_et_ferme(self):
        self.assertIn("panel", abonnements.REGISTRE)
        self.assertFalse(abonnements.REGISTRE["panel"].ouvert)
        with self.assertRaises(abonnements.Refus):
            comptes.abonner(self.db, self.c, "panel")
        for table in ("retraits", "cles"):                                # créées, vides
            self.assertEqual(self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

    def test_18_ajouter_un_type_ne_change_pas_le_schema(self):
        def schema():
            return {t: self.db.execute(f"PRAGMA table_info({t})").fetchall()
                    for (t,) in self.db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        avant = schema()
        faux = dict(abonnements.REGISTRE, essai=abonnements.Type("Essai", "rien", ("a", "b"), 2, "", "", True, "jour"))
        abonnements.verifier_registre(faux)
        comptes.abonner(self.db, self.c, "essai", "a", registre=faux)
        self.assertEqual(comptes.lire(self.db, self.c)["abonnements"][0]["type"], "essai")
        self.assertTrue(comptes.desabonner(self.db, self.c, "essai", "a"))
        self.assertEqual([tuple(x) for x in schema()["abonnements"]], [tuple(x) for x in avant["abonnements"]])
        self.assertEqual(schema().keys(), avant.keys())

    def test_le_mot_bord_n_existe_pas_cote_identite(self):
        for (sql,) in self.db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"):
            self.assertNotIn("bord", sql.lower())
        import tokenize
        for nom in ("comptes.py", "abonnements.py"):   # ni nom de variable, ni colonne, ni clé : la prose seule le cite
            with open(os.path.join(config.ICI, nom), "rb") as f:
                noms = [t.string.lower() for t in tokenize.tokenize(f.readline) if t.type == tokenize.NAME]
            self.assertFalse([n for n in noms if "bord" in n], nom)


class Separation(unittest.TestCase):
    """Règle 20 : la fabrique n'ouvre pas le tiroir identité ; aucun ATTACH nulle part."""
    COTE_PUBLIC = ("fabrique.py", "llm.py", "publier.py", "chaine.py", "flux.py", "export.py", "index.py",
                   "syntheses.py", "aveugle.py", "base.py", "methode.py", "schema.py")

    def test_aucun_import_du_tiroir_identite_cote_fabrique(self):
        for nom in self.COTE_PUBLIC:
            with open(os.path.join(config.ICI, nom), encoding="utf-8") as f:
                source = f.read()
            for interdit in ("comptes", "abonnements", "lettre", "migrations", "identites"):
                self.assertNotRegex(source, r"\b(import|from)\b[^\n]*\b%s\b" % interdit, f"{nom} : {interdit}")

    def test_le_processus_de_la_fabrique_ne_charge_pas_le_compte(self):
        code = ("import sys; import comparateur.__main__, comparateur.chaine; "
                "print(sorted(m for m in sys.modules if m.split('.')[-1] in ('comptes', 'abonnements', 'lettre', 'serveur')))")
        sortie = subprocess.run([sys.executable, "-c", code], cwd=RACINE, capture_output=True, text=True, timeout=60)
        self.assertEqual(sortie.stdout.strip(), "[]", sortie.stderr)

    def test_pas_d_attach(self):
        for dossier, _, fichiers in os.walk(config.ICI):
            for nom in fichiers:
                if nom.endswith(".py"):
                    with open(os.path.join(dossier, nom), encoding="utf-8") as f:
                        self.assertNotRegex(f.read(), r"(?i)\battach\s+database\b|\.execute\([^)]*\battach\b", nom)


class Guichet(unittest.TestCase):
    """Le serveur, sur un vrai port, avec les trois noms d'hôte."""

    @classmethod
    def setUpClass(cls):
        db = base.connexion()
        try:
            base.charger_medias(db)
            publier.pages(db)
        finally:
            db.close()
        cls.srv = serveur.creer(port=0, hote="127.0.0.1")
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        FauxSMTP.envoyes.clear()
        serveur.DEBIT.vus.clear()
        self.ident = comptes.connexion()
        self.ident.execute("DELETE FROM comptes")
        self.ident.execute("DELETE FROM codes")
        self.ident.commit()

    def tearDown(self):
        self.ident.close()

    def appel(self, methode, chemin, corps=None, hote="compte.cadrages.test", cookie=None, entetes=None):
        h = {"Host": hote}
        if corps is not None:
            h["Content-Type"] = "application/json"
        if cookie:
            h["Cookie"] = cookie
        h.update(entetes or {})
        req = urllib.request.Request(self.url + chemin, method=methode, headers=h,
                                     data=json.dumps(corps).encode() if corps is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def dernier_code(self):
        return re.search(r"\b(\d{6})\b", FauxSMTP.envoyes[-1].get_body(("plain",)).get_content()).group(1)

    def connecter(self, adresse="lea@exemple.fr"):
        self.assertEqual(self.appel("POST", "/api/compte/code", {"adresse": adresse})[0], 202)
        statut, entetes, _ = self.appel("POST", "/api/compte/connexion", {"adresse": adresse, "code": self.dernier_code()})
        self.assertEqual(statut, 200)
        return entetes["Set-Cookie"].split(";")[0]

    def test_trois_hotes(self):
        statut, entetes, corps = self.appel("GET", "/")
        self.assertEqual(statut, 200)
        self.assertIn(b"Une adresse mail suffit", corps)
        self.assertNotIn("stats.inflexion.me", entetes["Content-Security-Policy"])   # aucune mesure sur le compte
        self.assertEqual(self.appel("GET", "/index.html")[0], 404)                    # le site n'est pas servi ici
        self.assertEqual(self.appel("GET", "/api/compte/registre", hote="cadrages.test")[0], 404)   # le compte, sur son hôte seul
        self.assertEqual(self.appel("GET", "/", hote="urne.cadrages.test")[0], 404)   # l'urne se tait jusqu'au panel
        self.assertEqual(self.appel("GET", "/sante", hote="urne.cadrages.test")[0], 404)
        self.assertEqual(self.appel("GET", "/sante", hote="compte.cadrages.test")[0], 404)
        self.assertEqual(self.appel("GET", "/sante", hote="cadrages.test")[0], 200)
        os.environ.pop("COMPARATEUR_SMTP_MOT_DE_PASSE")
        try:   # règle 14 : éteint sans mail, aucun écran, aucune route du compte
            self.assertEqual(self.appel("GET", "/")[0], 404)
            self.assertEqual(self.appel("POST", "/api/compte/code", {"adresse": "a@exemple.fr"})[0], 404)
        finally:
            os.environ["COMPARATEUR_SMTP_MOT_DE_PASSE"] = REGLAGES["COMPARATEUR_SMTP_MOT_DE_PASSE"]
        self.assertEqual(self.appel("GET", "/", hote="cadrages.test")[0], 200)
        self.assertEqual(self.appel("GET", "/", hote="10.0.0.1:8080")[0], 200)        # un hôte inconnu est le site
        statut, _, corps = self.appel("GET", "/api/compte/registre")
        self.assertEqual({t["type"] for t in json.loads(corps)["registre"]}, set(abonnements.REGISTRE))

    def test_connexion_par_code_et_cookie_d_hote(self):
        journal = io.StringIO()
        with contextlib.redirect_stdout(journal):
            self.assertEqual(self.appel("POST", "/api/compte/code", {"adresse": "Lea@Exemple.fr"})[0], 202)
            code = self.dernier_code()
            self.assertEqual(FauxSMTP.envoyes[-1]["To"], "lea@exemple.fr")
            self.assertNotIn("http", FauxSMTP.envoyes[-1].get_body(("plain",)).get_content().split(code)[0])   # pas de lien avant le code
            with open(comptes.chemin(), "rb") as f:
                self.assertNotIn(code.encode(), f.read())                 # le code n'est gardé qu'en empreinte
            self.assertEqual(self.appel("GET", "/api/compte")[0], 401)
            faux = "000000" if code != "000000" else "111111"
            self.assertEqual(self.appel("POST", "/api/compte/connexion", {"adresse": "lea@exemple.fr", "code": faux})[0], 403)
            statut, entetes, _ = self.appel("POST", "/api/compte/connexion", {"adresse": "lea@exemple.fr", "code": code})
            self.assertEqual(statut, 200)
            c = entetes["Set-Cookie"]
            self.assertTrue(c.startswith(serveur.COOKIE + "="))
            for attendu in ("Path=/", "Secure", "HttpOnly", "SameSite=Strict"):
                self.assertIn(attendu, c)
            self.assertNotIn("Domain", c)
            cookie = c.split(";")[0]
            jeton = cookie.split("=", 1)[1]
            self.assertEqual(self.appel("POST", "/api/compte/connexion", {"adresse": "lea@exemple.fr", "code": code})[0], 403)   # une fois
            statut, _, corps = self.appel("GET", "/api/compte", cookie=cookie)
            self.assertEqual(statut, 200)
            self.assertEqual(self.appel("GET", "/api/compte", cookie=cookie, hote="cadrages.test")[0], 404)
        texte = journal.getvalue()
        for secret in ("lea@exemple.fr", code, jeton):
            self.assertNotIn(secret, texte)                                # les journaux comptent, ils ne nomment pas

    def test_cinq_essais_puis_le_code_est_efface(self):
        self.appel("POST", "/api/compte/code", {"adresse": "b@exemple.fr"})
        code = self.dernier_code()
        faux = "000000" if code != "000000" else "111111"
        for _ in range(comptes.CODE_ESSAIS):
            self.appel("POST", "/api/compte/connexion", {"adresse": "b@exemple.fr", "code": faux})
        self.assertEqual(self.appel("POST", "/api/compte/connexion", {"adresse": "b@exemple.fr", "code": code})[0], 403)

    def test_essais_simultanes_bornes(self):
        """Cinq essais par code, même lancés ensemble : chaque essai est compté avant la comparaison."""
        from concurrent.futures import ThreadPoolExecutor
        a, code = comptes.demander_code(self.ident, "course@exemple.fr")
        faux = [f"{(int(code) + k) % 10 ** 6:06d}" for k in range(1, 41)]
        compares = []
        vrai = comptes.hmac.compare_digest
        comptes.hmac.compare_digest = lambda x, y: (compares.append(1), vrai(x, y))[1]
        try:
            def essai(c):
                db = comptes.connexion()
                try:
                    return comptes.verifier_code(db, a, c)
                finally:
                    db.close()
            with ThreadPoolExecutor(20) as pool:
                rendus = list(pool.map(essai, faux))
        finally:
            comptes.hmac.compare_digest = vrai
        self.assertEqual(rendus, [None] * len(faux))
        self.assertLessEqual(len(compares), comptes.CODE_ESSAIS)
        self.assertIsNone(comptes.verifier_code(self.ident, a, code))      # le code est perdu après cinq essais

    def test_meme_reponse_et_limites(self):
        r1 = self.appel("POST", "/api/compte/code", {"adresse": "nouvelle@exemple.fr"})[2]
        r2 = self.appel("POST", "/api/compte/code", {"adresse": "pas une adresse"})[2]
        r3 = self.appel("POST", "/api/compte/code", {"adresse": "robot@exemple.fr", "site": "spam"})[2]
        self.assertEqual(r1, r2)
        self.assertEqual(r1, r3)
        self.assertEqual([m["To"] for m in FauxSMTP.envoyes], ["nouvelle@exemple.fr"])
        for _ in range(2):
            self.appel("POST", "/api/compte/code", {"adresse": "nouvelle@exemple.fr"})
        self.assertEqual(self.appel("POST", "/api/compte/code", {"adresse": "x@exemple.fr"})[0], 429)    # cinq par heure et par IP
        self.assertEqual(len(FauxSMTP.envoyes), 3)                                                       # trois par adresse

    def test_requete_forgee_refusee(self):
        cookie = self.connecter()
        corps = {"type": "lettre", "cible": "", "actif": True}
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", corps, cookie=cookie,
                                    entetes={"Origin": "https://ailleurs.test"})[0], 403)
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", corps, cookie=cookie,
                                    entetes={"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", corps, cookie=cookie,
                                    entetes={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", corps, cookie=cookie,
                                    entetes={"Origin": "https://cadrages.test"})[0], 403)          # le site public non plus
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", corps, cookie=cookie,
                                    entetes={"Sec-Fetch-Site": "same-site"})[0], 403)
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", corps, cookie=cookie,
                                    entetes={"Origin": "https://compte.cadrages.test"})[0], 200)

    def test_19_l_ecran_est_les_lignes_du_compte(self):
        cookie = self.connecter()
        for corps in ({"type": "lettre", "actif": True}, {"type": "alerte-edition", "actif": True},
                      {"type": "rubrique", "cible": "international", "actif": True}):
            self.assertEqual(self.appel("POST", "/api/compte/abonnement", corps, cookie=cookie)[0], 200)
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", {"type": "rubrique", "cible": "Le Monde", "actif": True}, cookie=cookie)[0], 400)
        self.assertEqual(self.appel("POST", "/api/compte/abonnement", {"type": "panel", "actif": True}, cookie=cookie)[0], 400)
        sait = json.loads(self.appel("GET", "/api/compte", cookie=cookie)[2])["sait"]
        cid = self.ident.execute("SELECT id FROM comptes").fetchone()["id"]
        self.assertEqual(sait, comptes.lire(self.ident, cid))
        lignes = self.ident.execute("SELECT type, cible, etat, cree_jour, fin_jour, dernier_envoi FROM abonnements ORDER BY type, cible").fetchall()
        self.assertEqual(sait["abonnements"], [dict(r) for r in lignes])
        self.assertEqual(sait["compte"]["adresse"], "lea@exemple.fr")
        self.assertRegex(sait["compte"]["cree_jour"], r"^\d{4}-\d{2}-\d{2}$")     # au jour
        self.assertRegex(sait["compte"]["vu_mois"], r"^\d{4}-\d{2}$")             # au mois
        page = self.appel("GET", "/")[2].decode()
        for mot in ("jeton", "signature", "clé", "anonymisation"):               # premier cadrage, règle 15
            self.assertNotIn(mot, page.lower())

    def test_deconnexion_et_suppression(self):
        cookie = self.connecter()
        self.appel("POST", "/api/compte/abonnement", {"type": "lettre", "actif": True}, cookie=cookie)
        statut, entetes, _ = self.appel("POST", "/api/compte/deconnexion", {}, cookie=cookie)
        self.assertIn("Max-Age=0", entetes["Set-Cookie"])
        self.assertEqual(self.appel("GET", "/api/compte", cookie=cookie)[0], 401)
        self.assertEqual(self.ident.execute("SELECT COUNT(*) FROM comptes").fetchone()[0], 1)   # la lettre le garde
        cookie = self.connecter()
        self.assertEqual(self.appel("POST", "/api/compte/suppression", {}, cookie=cookie)[0], 200)
        for t in ("comptes", "abonnements", "sessions"):
            self.assertEqual(self.ident.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], 0, t)

    def test_un_compte_sans_rien_est_efface(self):
        cookie = self.connecter()
        self.appel("POST", "/api/compte/deconnexion", {}, cookie=cookie)
        self.assertEqual(self.ident.execute("SELECT COUNT(*) FROM comptes").fetchone()[0], 0)


class Migration(unittest.TestCase):
    def test_abonnes_deplaces_sans_perte_ni_retour(self):
        public = sqlite3.connect(":memory:")
        public.row_factory = sqlite3.Row
        public.execute("""CREATE TABLE abonnes (id INTEGER PRIMARY KEY, adresse TEXT NOT NULL UNIQUE, jeton TEXT NOT NULL UNIQUE,
                          cree TEXT NOT NULL, confirme_le TEXT, dernier_envoi TEXT)""")
        lignes = [("a@exemple.fr", "jeton-a-0123456789", "2026-11-15T08:12:00+00:00", "2026-11-15T08:20:00+00:00", "2026-S46"),
                  ("b@exemple.fr", "jeton-b-0123456789", "2026-11-16T09:00:00+00:00", None, None),
                  ("pas une adresse", "jeton-c-0123456789", "2026-11-16T09:00:00+00:00", None, None),
                  ("d@exemple.fr", "jeton-d-0123456789", "2026-11-10T09:00:00+00:00", "2026-11-10T09:05:00+00:00", None)]
        public.executemany("INSERT INTO abonnes (adresse, jeton, cree, confirme_le, dernier_envoi) VALUES (?,?,?,?,?)", lignes)
        public.commit()
        ident = comptes.connexion()
        try:
            ident.execute("DELETE FROM comptes")
            ident.commit()
            # d s'est réinscrit depuis le site avant le passage : sa ligne en attente redevient confirmée, avec son ancien lien
            comptes.inscrire_lettre(ident, "d@exemple.fr")
            self.assertEqual(migrations.verser_abonnes(public, ident),
                             {"lues": 4, "comptes": 2, "abonnements": 2, "deja": 1, "invalides": 1, "retirees": 4})
            self.assertEqual(public.execute("SELECT COUNT(*) FROM abonnes").fetchone()[0], 0)   # plus rien dans le tiroir public
            r = {x["adresse"]: x for x in ident.execute(
                "SELECT c.adresse, c.cree_jour, a.etat, a.sortie, a.dernier_envoi FROM abonnements a JOIN comptes c ON c.id = a.compte")}
            self.assertEqual(dict(r["a@exemple.fr"]), {"adresse": "a@exemple.fr", "cree_jour": "2026-11-15", "etat": "actif",
                                                       "sortie": "jeton-a-0123456789", "dernier_envoi": "2026-S46"})
            self.assertEqual(r["b@exemple.fr"]["etat"], "attente")
            self.assertEqual((r["d@exemple.fr"]["etat"], r["d@exemple.fr"]["sortie"]), ("actif", "jeton-d-0123456789"))
            # le lien de désinscription d'avant la migration marche encore, et la personne ne revient pas
            self.assertTrue(comptes.sortir(ident, "jeton-a-0123456789"))
            self.assertIsNone(ident.execute("SELECT 1 FROM comptes WHERE adresse = 'a@exemple.fr'").fetchone())
            self.assertEqual(migrations.verser_abonnes(public, ident)["lues"], 0)
            self.assertIsNone(ident.execute("SELECT 1 FROM comptes WHERE adresse = 'a@exemple.fr'").fetchone())
        finally:
            ident.execute("DELETE FROM comptes")
            ident.commit()
            ident.close()


class Alertes(unittest.TestCase):
    JOUR = "2026-03-17"

    def setUp(self):
        FauxSMTP.envoyes.clear()
        lettre._echecs.clear()
        self.db = base.connexion()
        medias = [{"nom": n, "score": s} for n, s in (("A", -1.0), ("B", -0.5), ("C", 0.0), ("D", 1.0))]
        sujets = [{"id": "s1", "titre": "Un sujet international", "articles": [
                      {"media": m, "titre": "t", "lien": f"https://{m.lower()}.test/international/{m}"} for m in "ABCD"]},
                  {"id": "s2", "titre": "Un sujet politique", "articles": [
                      {"media": m, "titre": "t", "lien": f"https://{m.lower()}.test/politique/{m}"} for m in "AB"]}]
        self.db.execute("INSERT OR REPLACE INTO editions (jour, cree, donnees) VALUES (?, ?, ?)",
                        (self.JOUR, base.iso(), json.dumps({"recolte": self.JOUR + "T05:00:00+00:00", "medias": medias, "seuls": [], "sujets": sujets})))
        self.db.commit()
        publier.ecrire_pages(self.db)
        self.ident = comptes.connexion()
        self.ident.execute("DELETE FROM comptes")
        self.ident.commit()

    def tearDown(self):
        self.db.execute("DELETE FROM editions WHERE jour = ?", (self.JOUR,))
        self.db.commit()
        self.db.close()
        self.ident.execute("DELETE FROM comptes")
        self.ident.commit()
        self.ident.close()

    def test_un_mail_par_compte_une_fois_par_jour(self):
        a = lettre.alerte(self.JOUR)
        self.assertEqual([(s["id"], s["rubriques"]) for s in a["sujets"]], [("s1", ["international"]), ("s2", ["politique"])])
        c1 = comptes.compte_de(self.ident, "un@exemple.fr", creer=True)
        comptes.abonner(self.ident, c1, "alerte-edition")
        comptes.abonner(self.ident, c1, "rubrique", "international")
        c2 = comptes.compte_de(self.ident, "deux@exemple.fr", creer=True)
        comptes.abonner(self.ident, c2, "rubrique", "politique")
        self.assertEqual(lettre.envoyer_alertes(self.ident, self.JOUR), {"jour": self.JOUR, "envoyes": 2, "echecs": 0})
        par = {m["To"]: m for m in FauxSMTP.envoyes}
        texte = par["un@exemple.fr"].get_body(("plain",)).get_content()
        self.assertIn("écrit par un modèle", texte)
        self.assertIn("RUBRIQUE INTERNATIONAL", texte)
        self.assertEqual(texte.count("/mail.html#desinscrire="), 2)      # une sortie par abonnement
        self.assertIn("Un sujet politique", par["deux@exemple.fr"].get_body(("plain",)).get_content())
        self.assertNotIn("Un sujet international", par["deux@exemple.fr"].get_body(("plain",)).get_content())
        self.assertEqual(par["un@exemple.fr"]["List-Unsubscribe"].count("jeton="), 2)   # « se désabonner » arrête tout le mail
        FauxSMTP.envoyes.clear()
        self.assertEqual(lettre.envoyer_alertes(self.ident, self.JOUR)["envoyes"], 0)   # pas deux fois
        comptes.abonner(self.ident, c1, "rubrique", "politique")                       # ajoutée après l'envoi du jour
        self.assertEqual(lettre.envoyer_alertes(self.ident, self.JOUR)["envoyes"], 0)   # elle attend le lendemain

    def test_la_lettre_part_le_lundi_seulement(self):
        c = comptes.compte_de(self.ident, "lundi@exemple.fr", creer=True)
        comptes.abonner(self.ident, c, "lettre")
        r = lettre.envoyer_semaine(self.ident, "2026-03-18")                           # un mercredi : rien
        self.assertEqual((r["envoyes"], r["lundi"]), (0, False))
        self.assertEqual(FauxSMTP.envoyes, [])

    def test_flux_atom_par_sujet(self):
        chemin = os.path.join(config.public(), "flux", "sujets", "s1.xml")
        with open(chemin, "rb") as f:
            avant = f.read()
        racine = ET.fromstring(avant)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        self.assertTrue(racine.findall("a:entry", ns))
        self.assertIn("écrit par un modèle", racine.find("a:entry/a:summary", ns).text)
        publier.ecrire_pages(self.db)
        with open(chemin, "rb") as f:
            self.assertEqual(f.read(), avant)                               # les mêmes octets, pour tous et à chaque fois
        page = publier.gabarit()
        self.assertIn("cadrages.sujets", page)                              # « Mes sujets » sur l'appareil
        with open(os.path.join(config.ICI, "site", "js", "mes-sujets.js"), encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"fetch\(|XMLHttpRequest|sendBeacon")   # rien ne part


if __name__ == "__main__":
    unittest.main()
