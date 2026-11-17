"""Phase 3, le panel : signature aveugle (RFC 9474), urne par questionnaire, carte de votant, séparation tenue par des
tests. Sans réseau ni vrai SMTP.  python3 -m unittest discover -s tests"""
import contextlib, io, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, threading, unittest
import urllib.error, urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, ".."))
from comparateur import aveugle, base, ceremonie, comptes, config, lettre, migrations, serveur, signature, urne  # noqa: E402

REGLAGES = {"COMPARATEUR_SMTP_UTILISATEUR": "essai", "COMPARATEUR_SMTP_MOT_DE_PASSE": "secret",
            "COMPARATEUR_SITE_URL": "https://cadrages.test"}
_AVANT = {}
BITS = 1024   # des clés courtes pour que les essais aillent vite ; 2048 en vrai (ceremonie.ouvrir)


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
    DOSSIER = tempfile.mkdtemp(prefix="comparateur-panel-")
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


def vecteurs():
    with open(os.path.join(ICI, "vecteurs-rfc9474.json"), encoding="utf-8") as f:
        return json.load(f)


class Signature(unittest.TestCase):
    """Premier cadrage, règle 8 : la cryptographie suit la RFC, vecteurs à l'appui, des deux côtés."""

    def test_vecteurs_de_la_rfc_en_python(self):
        v = vecteurs()
        h, i = (lambda k: bytes.fromhex(v[k])), (lambda k: int(v[k], 16))
        cle = {"n": i("n"), "e": i("e"), "d": i("d")}
        pk = signature.publique(cle)
        prep = signature.preparer(h("msg"), h("msg_prefix"))
        self.assertEqual(prep, h("prepared_msg"))
        self.assertEqual(signature.emsa_pss_encoder(prep, pk["n"].bit_length() - 1, h("salt")), h("encoded_msg"))
        av, inv = signature.aveugler(pk, prep, h("salt"), pow(i("inv"), -1, pk["n"]))
        self.assertEqual((av, inv), (h("blinded_msg"), i("inv")))
        self.assertEqual(signature.signer_aveugle(cle, av), h("blind_sig"))
        self.assertEqual(signature.finaliser(pk, prep, h("blind_sig"), inv), h("sig"))
        self.assertTrue(signature.verifier(pk, prep, h("sig")))
        self.assertFalse(signature.verifier(pk, prep + b"x", h("sig")))

    @unittest.skipUnless(shutil.which("node"), "node absent : la moitié JavaScript n'est pas essayée")
    def test_vecteurs_en_javascript_et_d_un_cote_a_l_autre(self):
        """Les mêmes vecteurs dans compte/aveugle-rsa.js ; puis un bulletin aveuglé en JS, signé en Python, dévoilé et
        vérifié en JS ; et vérifié en Python."""
        cle = signature.nouvelle_cle(BITS)
        pk = signature.en_hex(signature.publique(cle))
        script = r"""
const A = require(process.argv[1]), v = require(process.argv[2]), pk = JSON.parse(process.argv[3]);
const modinv = (a, m) => { let [r0, r1, t0, t1] = [m, a % m, 0n, 1n]; while (r1) { const q = r0 / r1; [r0, r1] = [r1, r0 - q * r1]; [t0, t1] = [t1, t0 - q * t1]; } return ((t0 % m) + m) % m; };
(async () => {
  const prep = A.preparer(A.deHex(v.msg), A.deHex(v.msg_prefix));
  const a = await A.aveugler({ n: v.n, e: v.e }, prep, A.deHex(v.salt), modinv(BigInt('0x' + v.inv), BigInt('0x' + v.n)));
  const sig = await A.finaliser({ n: v.n, e: v.e }, prep, A.deHex(v.blind_sig), a.inv);
  const neuf = A.preparer(new TextEncoder().encode('essai'));
  const b = await A.aveugler(pk, neuf);
  console.log(JSON.stringify({ prep: A.hex(prep) === v.prepared_msg, blind: A.hex(a.aveugle) === v.blinded_msg,
    sig: A.hex(sig) === v.sig, neuf: A.hex(neuf), aveugle: A.hex(b.aveugle), inv: b.inv.toString(16) }));
})();
"""
        js = os.path.join(config.ICI, "compte", "aveugle-rsa.js")
        r = subprocess.run(["node", "-e", script, js, os.path.join(ICI, "vecteurs-rfc9474.json"), json.dumps(pk)],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        x = json.loads(r.stdout)
        self.assertEqual((x["prep"], x["blind"], x["sig"]), (True, True, True))
        sig_aveugle = signature.signer_aveugle(cle, bytes.fromhex(x["aveugle"]))           # le guichet signe sans voir
        script2 = r"""
const A = require(process.argv[1]), pk = JSON.parse(process.argv[2]);
A.finaliser(pk, A.deHex(process.argv[3]), A.deHex(process.argv[4]), BigInt('0x' + process.argv[5])).then(s => console.log(A.hex(s)), e => { console.error(e.message); process.exit(1); });
"""
        r = subprocess.run(["node", "-e", script2, js, json.dumps(pk), x["neuf"], sig_aveugle.hex(), x["inv"]],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.assertTrue(signature.verifier(signature.publique(cle), bytes.fromhex(x["neuf"]), bytes.fromhex(r.stdout.strip())))

    def test_le_guichet_masque_et_reverifie(self):
        cle = signature.nouvelle_cle(BITS)
        with self.assertRaises(signature.ErreurSignature):
            signature.signer_aveugle(cle, b"\x01" * 3)                                     # taille fausse
        with self.assertRaises(signature.ErreurSignature):
            signature.signer_aveugle(cle, b"\xff" * (BITS // 8))                          # au-delà du module


class Questionnaire(unittest.TestCase):
    """Premier cadrage, règle 13 : un questionnaire se refuse lui-même."""
    BON = {"id": "essai-confiance", "titre": "Questionnaire factice", "fermeture": "2099-01-01",
           "questions": [{"id": "q1", "texte": "Question factice ?", "choix": ["Oui", "Non", "Je ne sais pas"]},
                         {"id": "age", "texte": "Votre tranche d'âge ?", "choix": ["Moins de 30 ans", "30 à 59 ans", "60 ans et plus"], "profil": True}]}

    def test_trois_questionnaires_fautifs_refuses(self):
        self.assertEqual(urne.verifier_questionnaire(self.BON), [])
        libre = json.loads(json.dumps(self.BON)); libre["questions"][0]["type"] = "texte"
        profils = json.loads(json.dumps(self.BON)); profils["questions"] += [
            {"id": f"p{i}", "texte": "Profil ?", "choix": ["a", "b"], "profil": True} for i in range(2)]
        fin = json.loads(json.dumps(self.BON)); fin["questions"][1]["choix"] = [f"{x} ans" for x in range(15, 75, 10)]
        for q in (libre, profils, fin):
            self.assertTrue(urne.verifier_questionnaire(q))


class Parcours(unittest.TestCase):
    """Le parcours entier, sur un vrai port, avec les trois noms d'hôte : code, session, adhésion, retrait, dépôt,
    effacement, clôture, résultats ; puis la carte de votant."""

    @classmethod
    def setUpClass(cls):
        cls._vraie = signature.nouvelle_cle
        signature.nouvelle_cle = lambda bits=2048: cls._vraie(BITS)
        cls.srv = serveur.creer(port=0, hote="127.0.0.1")
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        signature.nouvelle_cle = cls._vraie
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        FauxSMTP.envoyes.clear()
        serveur.DEBIT.vus.clear()

    def appel(self, methode, chemin, corps=None, hote="compte.cadrages.test", cookie=None, entetes=None):
        h = {"Host": hote}
        if corps is not None:
            h["Content-Type"] = "application/json"
        if cookie:
            h["Cookie"] = cookie
        h.update(entetes or {})
        req = urllib.request.Request(self.url + chemin, method=methode, headers=h, data=json.dumps(corps).encode() if corps is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, r.headers, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, json.loads(e.read() or b"{}")

    def connecter(self, adresse):
        serveur.DEBIT.vus.clear()   # plusieurs comptes depuis la même adresse IP d'essai
        self.appel("POST", "/api/compte/code", {"adresse": adresse})
        code = re.search(r"\b(\d{6})\b", FauxSMTP.envoyes[-1].get_body(("plain",)).get_content()).group(1)
        s, e, _ = self.appel("POST", "/api/compte/connexion", {"adresse": adresse, "code": code})
        self.assertEqual(s, 200)
        return e["Set-Cookie"].split(";")[0]

    def membre(self, adresse, anciennete=30):
        cookie = self.connecter(adresse)
        ident = comptes.connexion()
        try:
            code = comptes.inviter_panel(ident)[0]
        finally:
            ident.close()
        self.assertEqual(self.appel("POST", "/api/compte/panel/rejoindre", {"code": code, "consentement": False}, cookie=cookie)[0], 400)
        self.assertEqual(self.appel("POST", "/api/compte/panel/rejoindre", {"code": code, "consentement": True}, cookie=cookie)[0], 200)
        self.assertEqual(self.appel("POST", "/api/compte/panel/rejoindre", {"code": "inconnu", "consentement": True},
                                    cookie=self.connecter("autre-" + adresse))[0], 403)
        ident = comptes.connexion()
        try:   # l'adhésion date de `anciennete` jours : le panel est figé sept jours avant l'ouverture
            ident.execute("UPDATE abonnements SET cree_jour = date('now', ?) WHERE type = 'panel' AND compte = "
                          "(SELECT id FROM comptes WHERE adresse = ?)", (f"-{anciennete} days", adresse))
            ident.commit()
        finally:
            ident.close()
        return cookie

    def bulletin(self, cookie, q, pk, extra=b""):
        """Ce que fait l'appareil (ici en Python ; la page fait la même chose en JavaScript). `extra` : le bord, pour
        une carte de votant."""
        prep = signature.preparer(q.encode() + b"\x00" + extra + os.urandom(32))
        av, inv = signature.aveugler(pk, prep)
        s, _, r = self.appel("POST", "/api/compte/bulletin", {"questionnaire": q, "aveugle": av.hex()}, cookie=cookie)
        if s != 200:
            return s, None, None
        return s, prep, signature.finaliser(pk, prep, bytes.fromhex(r["signature"]), inv)

    def deposer(self, q, prep, sig, bord=-1, reponses=None, entetes=None):
        return self.appel("POST", "/api/urne/depot", {"questionnaire": q, "bulletin": prep.hex(), "signature": sig.hex(), "bord": bord,
                                                      "reponses": reponses or {"q1": 0, "age": 1}},
                          hote="urne.cadrages.test", entetes=dict({"Origin": "https://compte.cadrages.test"}, **(entetes or {})))

    def test_parcours_entier(self):
        journal = io.StringIO()
        with contextlib.redirect_stdout(journal):
            q = json.loads(json.dumps(Questionnaire.BON))
            public = ceremonie.ouvrir(q)
            pk = signature.de_hex(public["cle"])
            membres = [self.membre(f"membre{i}@exemple.fr") for i in range(6)]
            tard = self.membre("tard@exemple.fr", anciennete=2)
            etat = self.appel("GET", "/api/compte/panel", cookie=membres[0])[2]
            self.assertTrue(etat["membre"])
            self.assertEqual([x["id"] for x in etat["questionnaires"]], [q["id"]])
            self.assertNotIn("bord", json.dumps(etat))
            # un membre arrivé après le gel ne retire rien
            self.assertEqual(self.bulletin(tard, q["id"], pk)[0], 403)
            recus = []
            for i, cookie in enumerate(membres):
                s, prep, sig = self.bulletin(cookie, q["id"], pk)
                self.assertEqual(s, 200)
                self.assertEqual(self.bulletin(cookie, q["id"], pk)[0], 409)               # un seul retrait
                s, e, _ = self.deposer(q["id"], prep, sig, bord=[-2, -1, 0, 1, 2, -1][i])
                self.assertEqual(s, 201)
                self.assertEqual(e["Access-Control-Allow-Origin"], "https://compte.cadrages.test")
                self.assertEqual(self.deposer(q["id"], prep, sig)[0], 409)                  # un dépôt par bulletin
                recus.append(prep)
            # un bulletin forgé, un bulletin d'un autre questionnaire, une identité jointe : refusés
            faux = signature.preparer(q["id"].encode() + b"\x00" + os.urandom(32))
            self.assertEqual(self.deposer(q["id"], faux, b"\x01" * (BITS // 8))[0], 403)
            self.assertEqual(self.deposer(q["id"], recus[0], b"\x01" * (BITS // 8), entetes={"Cookie": "x=y"})[0], 400)
            self.assertEqual(self.deposer(q["id"], recus[0], b"\x01" * (BITS // 8), entetes={"Authorization": "Bearer x"})[0], 400)
            self.assertEqual(self.appel("OPTIONS", "/api/urne/depot", hote="urne.cadrages.test",
                                        entetes={"Origin": "https://ailleurs.test"})[0], 403)
            # l'urne n'a ni heure ni rang
            with sqlite3.connect(urne.chemin(q["id"])) as u:
                for (sql,) in u.execute("SELECT sql FROM sqlite_master WHERE type = 'table'"):
                    self.assertIn("WITHOUT ROWID", sql)
                    self.assertNotRegex(sql.lower(), r"date|jour|heure|cree|rang|autoincrement")
                ordre = [r[0] for r in u.execute("SELECT empreinte FROM reponses")]
            self.assertEqual(ordre, sorted(ordre))
            # l'effacement par le reçu
            s, _, r = self.appel("POST", "/api/urne/effacement", {"questionnaire": q["id"], "bulletin": recus[-1].hex()}, hote="urne.cadrages.test")
            self.assertEqual((s, r["efface"]), (200, True))
            # rien avant la clôture
            with self.assertRaises(urne.Refus):
                urne.resultats(q["id"])
            res = ceremonie.fermer(q["id"])
            self.assertEqual((res["delivres"], res["recues"]), (6, 5))
            self.assertEqual(res["etiquette"], "Panel de volontaires. Ce n’est pas un sondage.")
            self.assertEqual(res["questions"][0]["par_bord"]["g"]["statut"], "moins de 5")   # 3 à gauche : rien
            self.assertEqual(self.bulletin(membres[0], q["id"], pk)[0], 410)               # après : plus de bulletin
            self.assertEqual(self.deposer(q["id"], *self.bulletin_signe_hors_guichet(q["id"], pk))[0], 410)
            ident = comptes.connexion()
            try:
                self.assertEqual(ident.execute("SELECT COUNT(*) FROM cles WHERE questionnaire = ?", (q["id"],)).fetchone()[0], 0)
                self.assertEqual(ident.execute("SELECT COUNT(*) FROM retraits WHERE questionnaire = ?", (q["id"],)).fetchone()[0], 0)
            finally:
                ident.close()
            self.assertTrue(os.path.isfile(os.path.join(config.public(), "panel", "resultats", q["id"] + ".json")))
            self.assertFalse(os.path.exists(os.path.join(config.public(), "panel", "cles", q["id"] + ".json")))
            # aucune valeur commune entre les deux fichiers, hors l'identifiant du questionnaire
            self.assertEqual(self.valeurs_communes(comptes.chemin(), urne.chemin(q["id"])) - {q["id"]}, set())
        texte = journal.getvalue()
        for secret in ["membre0@exemple.fr", "127.0.0.1"] + [p.hex() for p in recus] + [urne.empreinte(p) for p in recus]:
            self.assertNotIn(secret, texte)

    def test_la_page_du_panel_est_servie(self):
        """compte.<domaine>/panel sert la page et son script ; la politique de la page admet l'urne et rien d'autre."""
        for chemin, attendu in (("/panel", "text/html"), ("/aveugle-rsa.js", "application/javascript")):
            req = urllib.request.Request(self.url + chemin, headers={"Host": "compte.cadrages.test"})
            with urllib.request.urlopen(req, timeout=20) as r:
                self.assertEqual(r.status, 200)
                self.assertTrue(r.headers["Content-Type"].startswith(attendu))
                csp = r.headers["Content-Security-Policy"]
        self.assertIn("connect-src 'self' https://urne.cadrages.test;", csp)
        self.assertNotIn("umami", csp)
        self.assertEqual(self.appel("GET", "/api/compte/panel", hote="cadrages.test")[0], 404)   # le site ne répond pas pour le compte

    def bulletin_signe_hors_guichet(self, q, pk):
        return signature.preparer(q.encode() + b"\x00" + os.urandom(32)), b"\x00" * (BITS // 8)

    @staticmethod
    def valeurs_communes(a, b):
        def valeurs(chemin):
            out = set()
            with sqlite3.connect(chemin) as db:
                for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
                    for ligne in db.execute(f"SELECT * FROM {t}"):
                        out.update(str(x) for x in ligne if x is not None and len(str(x)) > 3)
            return out
        return valeurs(a) & valeurs(b)

    def test_carte_de_votant(self):
        os.makedirs(os.path.join(config.public(), "aveugle"), exist_ok=True)
        with open(os.path.join(config.public(), "aveugle", "lots.json"), "w", encoding="utf-8") as f:
            json.dump({"lots": [{"id": i, "titres": ["Un titre"]} for i in (7, 8, 9)]}, f)
        cookie = self.membre("votant@exemple.fr")
        etat = self.appel("GET", "/api/compte/panel", cookie=cookie)[2]
        carte = etat["carte"]
        self.assertEqual((carte["id"], carte["retiree"]), (urne.carte_id(ceremonie.trimestre()), False))
        pk = signature.de_hex(carte["cle"])
        s, prep, sig = self.bulletin(cookie, carte["id"], pk, extra=b"\x02")                # bord 0, inscrit dans la carte
        self.assertEqual(s, 200)
        self.assertEqual(self.bulletin(cookie, carte["id"], pk, extra=b"\x02")[0], 409)     # une carte par trimestre
        avis = lambda lot, note=1, bord=0: self.appel("POST", "/api/urne/avis", {"trimestre": carte["trimestre"], "carte": prep.hex(),
                                                                                  "signature": sig.hex(), "lot": lot, "note": note, "bord": bord},
                                                      hote="urne.cadrages.test", entetes={"Origin": "https://compte.cadrages.test"})
        self.assertEqual(avis(7)[0], 201)
        s, e, _ = avis(7)
        self.assertEqual(s, 409)                                                             # un avis par lot et par carte
        self.assertEqual(e["Access-Control-Allow-Origin"], "https://compte.cadrages.test")  # un refus se lit dans la page
        self.assertEqual(avis(8, note=3)[0], 400)
        for lot in (6, 10, 999999, 2 ** 70, True):                                           # seulement les lots proposés
            self.assertEqual(avis(lot)[0], 400, lot)
        self.assertEqual(avis(9, bord=-2)[0], 201)                                           # le bord de la requête est ignoré
        s, _, r = self.appel("POST", "/api/urne/lots-juges", {"trimestre": carte["trimestre"], "carte": prep.hex()}, hote="urne.cadrages.test")
        self.assertEqual(r["lots"], [7, 9])
        agg = ceremonie.clore_trimestre(carte["trimestre"])
        self.assertEqual(agg["lots"]["7"]["c"], [1, 1])
        self.assertEqual(agg["lots"]["9"], {"g": [0, 0], "c": [1, 1], "d": [0, 0]})
        self.assertEqual(agg["cartes_delivrees"], 1)
        self.assertNotIn(urne.empreinte(prep), json.dumps(agg))                              # jamais une carte publiée


class PagePanel(unittest.TestCase):
    """compte/panel.html, le parcours du votant : un h1 par écran, rien d'extérieur, le bord jamais au guichet, l'urne
    appelée sans cookie, aucun texte du serveur par innerHTML (premier cadrage, règles 4, 11 et 15)."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(config.ICI, "compte", "panel.html"), encoding="utf-8") as f:
            cls.page = f.read()
        cls.script = "\n".join(re.findall(r"<script>(.*?)</script>", cls.page, re.S))
        cls.html = re.sub(r"<script.*?</script>|<style.*?</style>", "", cls.page, flags=re.S)

    @staticmethod
    def appels(source, nom):
        """Le texte des arguments de chaque appel `nom(...)`, parenthèses équilibrées (hors définition de la fonction)."""
        out = []
        for m in re.finditer(r"(?<![\w.])%s\(" % re.escape(nom), source):
            if source[max(0, m.start() - 9):m.start()] == "function ":
                continue
            i, n = m.end(), 1
            while n:
                n += {"(": 1, ")": -1}.get(source[i], 0)
                i += 1
            out.append(source[m.end():i - 1])
        return out

    def test_structure(self):
        p = self.page
        self.assertIn('<html lang="fr">', p)
        self.assertIn('name="viewport"', p)
        self.assertIn('<script src="/aveugle-rsa.js"></script>', p)
        self.assertIn("prefers-color-scheme: dark", p)
        sections = re.findall(r'<section id="([\w-]+)" hidden>(.*?)</section>', self.html, re.S)
        self.assertEqual({s for s, _ in sections}, {"hors", "accueil", "membre", "quitter", "bord", "question", "envoi",
                                                     "envoye", "lot", "lots-fini"})
        for nom, corps in sections:   # un h1 par écran, que le script peut focaliser
            self.assertEqual(len(re.findall(r'<h1 tabindex="-1"', corps)), 1, nom)
        self.assertEqual(self.html.count("<h1"), len(sections))
        self.assertIn("h.focus()", self.script)

    def test_rien_d_exterieur(self):
        self.assertNotRegex(self.page, r"https?://")                  # ni script, ni police, ni mesure d'audience
        self.assertNotIn("umami", self.page.lower())
        self.assertEqual(re.findall(r"<script[^>]*\bsrc=\"([^\"]+)\"", self.page), ["/aveugle-rsa.js"])

    def test_aucun_texte_du_serveur_par_innerhtml(self):
        self.assertNotIn("innerHTML", self.page)
        self.assertNotIn("outerHTML", self.page)
        self.assertNotIn("insertAdjacentHTML", self.page)
        self.assertNotIn("document.write", self.page)

    def test_deux_interlocuteurs(self):
        """Deux fetch, pas un de plus : le guichet sur la même origine ; l'urne sur la sienne, sans cookie."""
        fetchs = self.appels(self.script, "fetch")
        self.assertEqual(len(fetchs), 2)
        guichet, urne_ = sorted(fetchs, key=lambda a: "etat.urne" in a)
        self.assertIn("credentials: 'same-origin'", guichet)
        self.assertNotIn("etat.urne", guichet)
        self.assertTrue(urne_.startswith("etat.urne + chemin"))
        self.assertIn("credentials: 'omit'", urne_)
        self.assertIn("referrerPolicy: 'no-referrer'", urne_)

    def test_le_bord_ne_part_jamais_au_guichet(self):
        appels = self.appels(self.script, "guichet")
        self.assertGreaterEqual(len(appels), 5)
        for a in appels:
            self.assertTrue(re.match(r"'(GET|POST)', '/api/compte/", a), a)
            self.assertNotRegex(a.lower(), r"bord", a)
        self.assertIn("{ code: code, consentement: true }", self.script)
        self.assertIn("'cadrages.bord'", self.script)
        # le bord ne quitte l'appareil que vers l'urne avec les réponses, ou aveuglé dans la carte du trimestre
        envois_du_bord = [a for a in self.appels(self.script, "urne") if "bord" in a]
        self.assertEqual(sorted(a.split("'")[1] for a in envois_du_bord), ["/api/urne/depot"])
        self.assertIn("retirer(e.id, e.cle, bord + 2)", self.script)
        self.assertIn("message[nom.length + 1] = octet", self.script)

    def test_le_retrait_comme_le_test_python(self):
        """Message : identifiant, octet nul, 32 octets au hasard ; préparé, aveuglé, finalisé ; gardé avant toute question."""
        s = self.script
        for geste in ("A.hasard(32)", "A.preparer(message)", "A.aveugler(cle, prepare)", "A.finaliser(cle, prepare",
                      "'/api/compte/bulletin', { questionnaire: id, aveugle: A.hex(x.aveugle) }"):
            self.assertIn(geste, s)
        self.assertLess(s.index("ecrire(CLE_BULLETINS, t)"), s.index("debuter(q, t[q.id])"))
        for cle in ("cadrages.bulletins", "cadrages.recus", "cadrages.carte"):
            self.assertIn(cle, s)

    def test_les_textes_du_cadrage(self):
        h = self.html
        for phrase in ("ce site ne peut pas savoir lesquelles sont les vôtres",
                       "Ce choix reste sur cet appareil. Il part avec chacune de vos réponses, jamais avec votre nom.",
                       "J’accepte que mes réponses et le bord que j’indique servent aux résultats publiés par ce site.",
                       "Code d’invitation", "15 ans", "Rejoindre le panel", "Envoyer mes réponses",
                       "Une fois parties, elles ne portent pas votre nom. Vous pourrez les effacer depuis cet appareil seulement.",
                       "C’est envoyé", "Quitter et effacer mes réponses", "Mes réponses envoyées", "Ce média est plutôt…",
                       "Ce site ne garde aucun lien entre une personne et ses réponses ; il ne peut pas en reconstituer un après "
                       "coup ; il ne protège pas contre un serveur piraté au moment même où la réponse est envoyée.",
                       "Ce n’est pas un sondage."):
            self.assertIn(phrase, h)
        self.assertIn("Vous avez déjà commencé ce questionnaire sur un autre appareil. Finissez-le là-bas.", self.script)
        textes = h + "".join(re.findall(r"'([^']*)'", self.script))
        self.assertNotIn("—", textes)                                   # aucun tiret long
        self.assertNotRegex(textes.lower(), r"\b(nous|nos|notre|anonyme)\b")

    def test_le_compte_mene_au_panel(self):
        with open(os.path.join(config.ICI, "compte", "compte.html"), encoding="utf-8") as f:
            compte = f.read()
        self.assertIn("plus.href = '/panel'", compte)
        self.assertIn("'En savoir plus'", compte)
        self.assertIn("c.disabled = !t.ouvert || panel", compte)       # la case reste désactivée


class MigrationDuVote(unittest.TestCase):
    """Phase 3 : le vieux vote à l'aveugle (votants, avis_aveugle, avis_note, invitations dans comparateur.db) passe
    dans une urne close, urnes/aveugle-historique.db, et seules ses sommes sont publiées. Sur des données d'essai :
    jamais lancée ici sur une vraie base."""
    VOTANTS = {"temoin-votant-gauche-0001": -2, "temoin-votant-gauche-0002": -1, "temoin-votant-centre-0003": 0,
               "temoin-votant-droite-0004": 1, "temoin-votant-droite-0005": 2}

    def setUp(self):
        for c in (migrations.chemin_historique(), urne.chemin(urne.HISTORIQUE)):
            if os.path.exists(c):
                os.remove(c)
        self.db = base.connexion()
        base.charger_medias(self.db)
        self.db.executescript(migrations.ANCIEN_VOTE)
        for t in migrations.TABLES_DU_VOTE:
            self.db.execute(f"DELETE FROM {t}")
        self.db.execute("DELETE FROM lots_aveugle")
        ids = {r["nom"]: r["id"] for r in self.db.execute("SELECT id, nom FROM medias")}
        self.lots = {}
        for nom in ("Le Monde", "Le Figaro", "Libération"):
            self.lots[nom] = self.db.execute("INSERT INTO lots_aveugle (media_id, jour, titres, cree) VALUES (?, '2026-05-02', '[]', ?)",
                                             (ids[nom], base.iso())).lastrowid
        hasard = __import__("random").Random(3)
        self.avis = []   # (votant, bord, lot, note)
        for v, bord in self.VOTANTS.items():
            self.db.execute("INSERT INTO votants (id, bord, cree) VALUES (?, ?, '2026-05-01')", (v, bord))
            for nom, lot in self.lots.items():
                if hasard.random() < .85:
                    note = hasard.randint(-2, 2)
                    self.db.execute("INSERT INTO avis_aveugle (votant_id, lot_id, note, cree) VALUES (?, ?, ?, '2026-05-03')", (v, lot, note))
                    self.avis.append((v, bord, lot, note))
            self.db.execute("INSERT INTO avis_note (votant_id, media_id, accord, cree) VALUES (?, ?, ?, '2026-05-03')",
                            (v, ids["Le Monde"], int(bord <= 0)))
        self.db.execute("INSERT INTO invitations (code, cree, utilisee_le) VALUES ('temoin-invitation-01', '2026-05-01', '2026-05-01')")
        self.db.commit()

    def tearDown(self):
        for t in migrations.TABLES_DU_VOTE:
            self.db.execute(f"DROP TABLE IF EXISTS {t}")
        self.db.execute("DELETE FROM lots_aveugle")
        self.db.commit()
        self.db.close()

    def test_verser_puis_oublier(self):
        n = len(self.avis)
        self.assertGreater(n, 8)
        refus = migrations.oublier_votes(self.db)                       # rien de versé : rien n'est oublié
        self.assertEqual((refus["retrouves"], refus["effaces"]), (0, {}))
        self.assertGreaterEqual(refus["manquants"], n)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM avis_aveugle").fetchone()[0], n)

        bilan = migrations.verser_votes(self.db)
        self.assertEqual((bilan["lues"], bilan["versees"], bilan["deja"], bilan["accords"], bilan["publie"]), (n, n, 0, 5, True))
        self.assertEqual(migrations.verser_votes(self.db)["versees"], 0)  # relancée : rien en double
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM avis_aveugle").fetchone()[0], n)   # versée sans rien ôter

        # l'urne : les avis, sous une empreinte, sans date ; close ; aucun identifiant de votant, aucune date
        u = urne.ouvrir_aveugle(urne.HISTORIQUE)
        try:
            self.assertEqual(u.execute("SELECT COUNT(*) FROM avis").fetchone()[0], n)
            self.assertEqual(urne._meta(u)["etat"], "clos")
            self.assertEqual([c[1] for c in u.execute("PRAGMA table_info(avis)")], ["carte", "lot", "note", "bord"])
        finally:
            u.close()
        with open(urne.chemin(urne.HISTORIQUE), "rb") as f:
            brut = f.read()
        for v in self.VOTANTS:
            self.assertNotIn(v.encode(), brut)
        self.assertNotIn(b"2026-05-0", brut)
        with self.assertRaises(urne.Refus):                             # aucune route n'y mène
            urne.donner_avis("historique", "00", "00", 1, 0, 0)

        # ce qui est publié : des sommes par lot et par bord, les accords comptés par média
        with open(migrations.chemin_historique(), encoding="utf-8") as f:
            texte = f.read()
        pub = json.loads(texte)
        for v in self.VOTANTS:
            self.assertNotIn(v, texte)
        self.assertNotIn(migrations.pseudonyme(next(iter(self.VOTANTS))), texte)
        attendu = {}
        for _, bord, lot, note in self.avis:
            g = attendu.setdefault(str(lot), {"g": [0, 0], "c": [0, 0], "d": [0, 0]})[urne.groupe(bord)]
            g[0] += 1
            g[1] += note
        self.assertEqual(pub["lots"], attendu)
        self.assertEqual(pub["accords"], {"Le Monde": {"oui": 3, "votes": 5}})
        self.assertEqual((pub["mesure"], pub["trimestre"], pub["cartes_delivrees"]), ("aveugle", "historique", 5))

        # la lecture à l'aveugle, sur les sommes publiées, est celle que compter donne sur les avis eux-mêmes
        lecture = aveugle.resultats(self.db)
        self.assertEqual(lecture["trimestres"], ["historique"])
        for nom, lot in self.lots.items():
            brut_avis = [(b, note) for _, b, l, note in self.avis if l == lot]
            self.assertEqual(lecture["medias"].get(nom), aveugle.compter(brut_avis, config.min_par_bord()), nom)

        # une ligne perdue dans l'urne : l'oubli refuse, et le versement suivant la rend
        u = urne.ouvrir_aveugle(urne.HISTORIQUE)
        carte, lot = u.execute("SELECT carte, lot FROM avis ORDER BY carte, lot LIMIT 1").fetchone()
        u.execute("DELETE FROM avis WHERE carte = ? AND lot = ?", (carte, lot))
        u.commit()
        u.close()
        self.assertGreater(migrations.oublier_votes(self.db)["manquants"], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM votants").fetchone()[0], 5)
        self.assertEqual(migrations.verser_votes(self.db)["versees"], 1)

        # la publication perdue : l'oubli refuse (les accords et le nombre de votants n'existent que là et dans l'urne)
        with open(migrations.chemin_historique(), encoding="utf-8") as f:
            sauve = f.read()
        os.remove(migrations.chemin_historique())
        self.assertEqual(migrations.oublier_votes(self.db)["manquants"], 1)
        with open(migrations.chemin_historique(), "w", encoding="utf-8") as f:
            f.write(sauve.replace('"cartes_delivrees":5', '"cartes_delivrees":4'))
        self.assertEqual(migrations.oublier_votes(self.db)["manquants"], 1)
        migrations.verser_votes(self.db)

        fait = migrations.oublier_votes(self.db)
        self.assertEqual((fait["retrouves"], fait["manquants"]), (n, 0))
        self.assertEqual(fait["effaces"], {"avis_note": 5, "avis_aveugle": n, "votants": 5, "invitations": 1})
        for t in migrations.TABLES_DU_VOTE:
            self.assertEqual(self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], 0, t)
        for nom in ("comparateur.db", "comparateur.db-wal"):            # compactée, journal compris
            c = os.path.join(config.donnees(), nom)
            if os.path.exists(c):
                with open(c, "rb") as f:
                    brut = f.read()
                for v in list(self.VOTANTS) + ["temoin-invitation-01"]:
                    self.assertNotIn(v.encode(), brut, nom)

        self.assertIs(fait["journal_vide"], True)

        # après l'oubli : une copie d'avant de la base ne retrouve plus les avis d'un votant
        u = urne.ouvrir_aveugle(urne.HISTORIQUE)
        try:
            cartes = {r[0] for r in u.execute("SELECT carte FROM avis")}
        finally:
            u.close()
        self.assertEqual(len(cartes), 5)                                 # un tirage par ancien votant
        self.assertFalse(cartes & {migrations.pseudonyme(v) for v in self.VOTANTS})
        # le fichier publié se refait depuis l'urne seule, à l'identique, même perdu
        os.remove(migrations.chemin_historique())
        self.assertEqual(migrations.verser_votes(self.db)["publie"], True)
        with open(migrations.chemin_historique(), encoding="utf-8") as f:
            self.assertEqual(f.read(), texte)
        self.assertEqual(aveugle.resultats(self.db), lecture)
        self.assertEqual(migrations.oublier_votes(self.db)["manquants"], 0)   # relancée : rien à faire

    def test_un_avis_hors_lecture_bloque_l_oubli(self):
        """Un avis sur un lot disparu échappe à la jointure : l'oubli refuse plutôt que de l'effacer sans l'avoir compté."""
        self.db.execute("PRAGMA foreign_keys=OFF")
        self.db.execute("INSERT INTO avis_aveugle (votant_id, lot_id, note, cree) VALUES (?, 99999, 1, '2026-05-03')",
                        (next(iter(self.VOTANTS)),))
        self.db.commit()
        migrations.verser_votes(self.db)
        self.assertEqual(migrations.oublier_votes(self.db)["manquants"], 1)
        self.assertGreater(self.db.execute("SELECT COUNT(*) FROM avis_aveugle").fetchone()[0], 0)

    def test_un_trimestre_clos_s_ajoute_a_l_historique(self):
        migrations.verser_votes(self.db)
        lot = self.lots["Le Figaro"]
        dossier = os.path.join(config.public(), "panel", "aveugle")
        with open(os.path.join(dossier, "2026T3.json"), "w", encoding="utf-8") as f:
            json.dump({"v": 1, "mesure": "aveugle", "trimestre": "2026T3", "lots": {str(lot): {"g": [2, -3], "c": [0, 0], "d": [1, 2]}}}, f)
        try:
            lecture = aveugle.resultats(self.db)
            self.assertEqual(lecture["trimestres"], ["historique", "2026T3"])
            brut_avis = [(b, note) for _, b, l, note in self.avis if l == lot] + [(-1, -1), (-1, -2), (1, 2)]
            self.assertEqual(lecture["medias"]["Le Figaro"], aveugle.compter(brut_avis, config.min_par_bord()))
            self.assertEqual((lecture["mesure"], lecture["version"]), ("aveugle", aveugle.VERSION))
        finally:
            os.remove(os.path.join(dossier, "2026T3.json"))


class LigneDeCommande(unittest.TestCase):
    """python -m comparateur panel-inviter et questionnaire ouvrir|fermer|resultats (docs/deploiement-phase-3.md)."""

    @classmethod
    def setUpClass(cls):
        cls._vraie = signature.nouvelle_cle
        signature.nouvelle_cle = lambda bits=2048: cls._vraie(BITS)

    @classmethod
    def tearDownClass(cls):
        signature.nouvelle_cle = cls._vraie

    def lancer(self, *args):
        from comparateur import __main__ as cli
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            code = cli.main(["comparateur", *args])
        return code, sortie.getvalue()

    def fichier(self, q):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=DOSSIER, encoding="utf-8")
        json.dump(q, f, ensure_ascii=False)
        f.close()
        return f.name

    def test_panel_inviter(self):
        code, texte = self.lancer("panel-inviter", "2")
        self.assertEqual(code, 0)
        codes = re.findall(r"^(\S+)  https://compte\.cadrages\.test/panel#code=(\S+)$", texte, re.M)
        self.assertEqual(len(codes), 2)
        self.assertTrue(all(a == b for a, b in codes))
        ident = comptes.connexion()
        try:
            for c, _ in codes:   # seule l'empreinte est gardée
                self.assertTrue(ident.execute("SELECT 1 FROM invitations_panel WHERE empreinte = ?", (comptes.empreinte(c),)).fetchone())
        finally:
            ident.close()
        self.assertEqual(self.lancer("inviter")[0], 2)                                       # l'ancienne commande

    def test_ouvrir_fermer_resultats(self):
        q = dict(Questionnaire.BON, id="essai-commande")
        self.assertEqual(self.lancer("questionnaire")[0], 2)
        self.assertEqual(self.lancer("questionnaire", "ouvrir", os.path.join(DOSSIER, "absent.json"))[0], 2)
        for fin in (None, "2020-01-01", "31/12/2099", 20991231):                             # une date à venir, au bon format
            self.assertEqual(self.lancer("questionnaire", "ouvrir", self.fichier(dict(q, fermeture=fin)))[0], 2, fin)
        libre = json.loads(json.dumps(q)); libre["questions"][0]["type"] = "texte"
        code, texte = self.lancer("questionnaire", "ouvrir", self.fichier(libre))
        self.assertEqual(code, 2)
        self.assertIn("refusé", texte)
        self.assertFalse(os.path.exists(urne.chemin("essai-commande")))

        code, texte = self.lancer("questionnaire", "ouvrir", self.fichier(q))
        self.assertEqual(code, 0, texte)
        self.assertIn("jusqu'au 2099-01-01", texte)
        for d in ("cles", "questionnaires"):
            self.assertTrue(os.path.isfile(os.path.join(config.public(), "panel", d, "essai-commande.json")))
        self.assertEqual(self.lancer("questionnaire", "ouvrir", self.fichier(q))[0], 2)      # pas deux fois
        self.assertEqual(self.lancer("questionnaire", "resultats", "essai-commande")[0], 1)   # pas avant la clôture

        code, texte = self.lancer("questionnaire", "fermer", "essai-commande")
        self.assertEqual(code, 0, texte)
        self.assertIn("bulletins délivrés : 0, réponses reçues : 0", texte)
        self.assertIn("gauche moins de 5", texte)
        with open(os.path.join(config.public(), "panel", "resultats", "essai-commande.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["questionnaire"], "essai-commande")
        self.assertFalse(os.path.exists(os.path.join(config.public(), "panel", "cles", "essai-commande.json")))
        ident = comptes.connexion()
        try:
            self.assertNotIn("essai-commande", [r["questionnaire"] for r in comptes.cles_ouvertes(ident)])
        finally:
            ident.close()
        self.assertEqual(self.lancer("questionnaire", "fermer", "essai-commande")[0], 1)      # déjà clos
        self.assertEqual(self.lancer("questionnaire", "fermer", "inconnu-du-panel")[0], 1)
        self.assertEqual(self.lancer("questionnaire", "fermer", "carte-2026t4")[0], 2)        # pas une carte
        code, texte = self.lancer("questionnaire", "resultats", "essai-commande")
        self.assertEqual(code, 0, texte)
        self.assertIn("recompté", texte)
        self.assertEqual(self.lancer("questionnaire", "resultats", "inconnu-du-panel")[0], 1)

    def test_sans_mail_rien(self):
        avant = os.environ.pop("COMPARATEUR_SMTP_MOT_DE_PASSE")
        try:
            self.assertEqual(self.lancer("questionnaire", "fermer", "essai-x")[0], 1)
            self.assertEqual(self.lancer("panel-inviter")[0], 1)
        finally:
            os.environ["COMPARATEUR_SMTP_MOT_DE_PASSE"] = avant


class Separation(unittest.TestCase):
    """Premier cadrage, règle 1 : aucun module n'importe l'autre côté ; l'urne ne lit que ses fichiers et les clés
    publiques ; pas d'ATTACH."""

    def source(self, nom):
        with open(os.path.join(config.ICI, nom), encoding="utf-8") as f:
            return f.read()

    def imports(self, nom):
        """Les modules du paquet qu'un module importe (from . import a, b)."""
        return {m.strip() for l in re.findall(r"^\s*from \. import ([^\n]+)", self.source(nom), re.M) for m in l.split(",")}

    def test_aucun_module_n_importe_l_autre_cote(self):
        self.assertEqual(self.imports("urne.py"), {"config", "signature"})
        self.assertNotIn("urne", self.imports("comptes.py"))
        self.assertEqual(self.imports("signature.py"), set())
        for nom in ("comptes.py", "abonnements.py"):
            self.assertNotIn("urne", self.imports(nom))

    def test_l_urne_ne_lit_que_ses_fichiers_et_les_cles_publiques(self):
        s = self.source("urne.py")
        for interdit in ("config.base", "identites", "comptes", "base.connexion", "abonnes", "ATTACH"):
            self.assertNotIn(interdit, s)
        ouvertures = re.findall(r"\bopen\((.+?), encoding", s) + re.findall(r"sqlite3\.connect\((\w+)", s)
        self.assertEqual(sorted(ouvertures), sorted(['os.path.join(config.public(), "panel", "cles", questionnaire + ".json")', "c",
                                                     'os.path.join(config.public(), "aveugle", "lots.json")']))

    def test_les_mots_de_l_ecran(self):
        for nom in os.listdir(os.path.join(config.ICI, "compte")):
            if nom.endswith(".html"):
                with open(os.path.join(config.ICI, "compte", nom), encoding="utf-8") as f:
                    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", f.read(), flags=re.S).lower()
                for mot in ("jeton", "signature", "clé", "anonymisation"):           # premier cadrage, règle 15
                    self.assertNotIn(mot, page, nom)


if __name__ == "__main__":
    unittest.main()
