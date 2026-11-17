"""Publication : la fabrique écrit le site statique (HTML + JSON) dans <données>/public/.

Les lecteurs ne lisent que ces fichiers : ni la base ni les modèles ne sont sollicités par une visite.
Écriture atomique (fichier temporaire puis renommage) : un lecteur ne voit jamais un fichier à moitié écrit.
"""
import hashlib, json, os, re, shutil

from . import aveugle, base, config, methode, syntheses
from .fabrique import hors_ecartees, sujets_du_jour


_REF = json.load(open(os.path.join(config.ICI, "medias.json"), encoding="utf-8"))
SEUILS = _REF["seuils"]
VERSION_CLASSEMENT = _REF["version"]   # « FrIdéo v1.0 » : inscrite dans chaque édition gardée


def _ecrire(chemin, texte):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texte)
    os.replace(tmp, chemin)


SITE = os.path.join(config.ICI, "site")
INCLURE = re.compile(r"/\*INCLURE ([\w./-]+)\*/")
STYLE = re.compile(r"<style>\n(.*?)</style>", re.S)
SCRIPT = re.compile(r'<script id="app-js">\n(.*?)</script>', re.S)
ACTIF = re.compile(r"site-[0-9a-f]{12}\.(css|js)$")   # un actif nommé par son empreinte : jamais modifié, donc immuable


def gabarit():
    """Assemble la page unique du site. gabarit.html est le squelette ; il nomme, dans l'ordre, les morceaux à
    y coller (/*INCLURE styles/base.css*/, /*INCLURE js/vues/sujet.js*/). Une vue = un fichier : voir DOCTRINE.md.
    Un morceau nommé mais absent arrête la publication : mieux vaut pas de page qu'une page à moitié faite."""
    def morceau(m):
        with open(os.path.join(SITE, m.group(1)), encoding="utf-8") as f:
            return f.read().rstrip("\n")
    with open(os.path.join(SITE, "gabarit.html"), encoding="utf-8") as f:
        page = INCLURE.sub(morceau, f.read())
    return page.replace("<!--MESURE-->", balise_mesure())


def gabarit_en_actifs():
    """La même page, mais le CSS et le JavaScript en sont sortis : (page, {chemin: contenu}). La page garde son HTML
    et ses données, et cite actifs/site-<empreinte>.css et .js (12 hexadécimaux du SHA-256 du contenu). Les données
    (<script id="donnees">, const DONNEES) sont déclarées avant le script : un script classique les voit.
    gabarit() reste la page entière, d'un seul tenant : c'est elle que les tests lisent."""
    page, actifs = gabarit(), {}

    def sortir(m, ext, balise):
        corps = m.group(1)
        nom = "actifs/site-" + hashlib.sha256(corps.encode("utf-8")).hexdigest()[:12] + "." + ext
        actifs[nom] = corps
        return balise % ("/" + nom)
    page = STYLE.sub(lambda m: sortir(m, "css", '<link rel="stylesheet" href="%s">'), page, count=1)
    page = SCRIPT.sub(lambda m: sortir(m, "js", '<script src="%s"></script>'), page, count=1)
    return page, actifs


def ecrire_actifs(pub, actifs):
    os.makedirs(os.path.join(pub, "actifs"), exist_ok=True)
    for nom, corps in actifs.items():
        _ecrire(os.path.join(pub, nom), corps)


def retirer_anciens_actifs(pub, actifs):
    """Supprime les site-*.css/js que les pages ne citent plus. À faire une fois les pages écrites : un lecteur
    ne tombe jamais sur une page dont l'actif manque."""
    dossier = os.path.join(pub, "actifs")
    for ancien in os.listdir(dossier):
        if ACTIF.match(ancien) and "actifs/" + ancien not in actifs:
            os.remove(os.path.join(dossier, ancien))


def balise_mesure():
    """La balise d'Umami, si la mesure est réglée (config.umami) ; sinon rien. Umami ne dépose aucun cookie."""
    u = config.umami()
    if not u:
        return ""
    a = lambda s: s.replace("&", "&amp;").replace('"', "&quot;")
    return (f'<script defer src="{a(u["script"])}" data-website-id="{a(u["id"])}" '
            f'data-domains="{a(u["domaines"])}"></script>')


def donnees_du_jour(db):
    notes = base.scores(db)
    fiche = {m["nom"]: m for m in json.load(open(os.path.join(config.ICI, "medias.json"), encoding="utf-8"))["medias"]}
    # Un média sans note FrIdéo est non classé : ni score, ni bord. Il n'est jamais rangé au centre par défaut.
    medias = [{"nom": r["nom"], "score": notes.get(r["id"]),
               "bord": base.bord(notes[r["id"]]) if r["id"] in notes else None, "statut": base.statut(notes.get(r["id"])),
               "proprietaire": r["proprietaire"], "id": r["id"], "ic": fiche.get(r["nom"], {}).get("ic"),
               "sources": fiche.get(r["nom"], {}).get("sources"),
               "peu_documente": bool(fiche.get(r["nom"], {}).get("peu_documente"))}
              for r in db.execute("SELECT id, nom, proprietaire FROM medias WHERE actif = 1").fetchall()]
    presents = {r["media_id"] for r in db.execute(
        "SELECT DISTINCT media_id FROM articles WHERE COALESCE(date, recolte) >= ?", (base.depuis(),))}
    analyses = {r["sujet_id"]: r for r in db.execute("SELECT * FROM analyses")}
    sujets, ranges = [], set()
    for s in sujets_du_jour(db):
        a = analyses.get(s["id"])
        if a is None and s["medias"] < 3:
            continue
        vide = "Sujet non analysé (trop peu couvert)."
        sujets.append({
            "id": f"s{s['id']}", "titre": a["titre"] if a else s["libelle"], "fait": a["fait"] if a else "",
            "divergence": a["ecart"] if a else None,
            "analyse": {k: a[k] for k in "gcd"} if a else {"g": vide, "c": vide, "d": vide},
            "mots": json.loads(a["mots"]) if a else [],
            "articles": [{"media": x["media"], "titre": x["titre"], "lien": x["lien"]} for x in s["articles"]]})
        ranges.update(x["id"] for x in s["articles"])
    # Titres de la fenêtre rangés sous aucun sujet publié : montrés à part, jamais comptés dans un bord.
    # Ceux des rubriques écartées (sport, culture) ne sont montrés nulle part : seul leur nombre est publié.
    garde, rubs = hors_ecartees("a")
    seuls = [{"media": r["nom"], "titre": r["titre"], "lien": r["lien"]} for r in db.execute(
        f"""SELECT a.id, a.titre, a.lien, m.nom FROM articles a JOIN medias m ON m.id = a.media_id
            WHERE COALESCE(a.date, a.recolte) >= ? AND m.actif = 1 AND {garde} ORDER BY m.nom, a.id""",
        (base.depuis(),) + rubs) if r["id"] not in ranges]
    total = db.execute("SELECT COUNT(*) AS n FROM articles WHERE COALESCE(date, recolte) >= ?", (base.depuis(),)).fetchone()["n"]
    ecartes = db.execute(f"SELECT COUNT(*) AS n FROM articles a WHERE COALESCE(a.date, a.recolte) >= ? AND NOT ({garde})",
                         (base.depuis(),) + rubs).fetchone()["n"]
    source = db.execute("SELECT source FROM notes_media WHERE methode = 'etude tierce' ORDER BY cree DESC, id DESC LIMIT 1").fetchone()
    return {"recolte": base.iso(), "heures": config.heures(), "total": total, "mode": "auto",
            "ecartes": {"rubriques": config.rubriques_ecartees(), "titres": ecartes},
            "medias": sorted(({k: m[k] for k in ("nom", "score", "bord", "statut", "proprietaire")} for m in medias if m["id"] in presents),
                             key=lambda m: (m["score"] is None, m["score"] or 0, m["nom"])),
            "absents": [m["nom"] for m in medias if m["id"] not in presents],
            "source_classement": source["source"] if source else "",
            "classement": {"source": source["source"] if source else "", "seuils": SEUILS,
                           "medias": sorted(({k: m[k] for k in ("nom", "score", "ic", "sources", "peu_documente")}
                                             for m in medias if m["statut"] == "classe"), key=lambda m: m["score"])},
            # Les médias lus hors de FrIdéo : comptés dans la couverture d'un sujet, dans aucun bord ni aucun silence.
            "non_classes": sorted(m["nom"] for m in medias if m["statut"] == "non-classe"),
            "sujets": sujets, "seuls": seuls,
            "aveugle": aveugle.resultats(db)}


def enregistrer_edition(db, jour=None):
    """Photographie l'état du jour et la garde : une édition par jour, datée en heure de Paris.
    Refaire l'édition d'un jour déjà fait la remplace."""
    charge = donnees_du_jour(db)
    charge["rythme"] = {"recolte_minutes": config.fabrique_minutes(), "edition_heure": config.edition_heure()}
    jour = jour or base.paris().strftime("%Y-%m-%d")
    # Les versions qui produisent l'édition sont gardées avec elle : un changement de méthode ou de classement ne
    # réécrit rien, et chaque édition dit sous quelles règles elle a été faite.
    db.execute("""INSERT INTO editions (jour, cree, donnees, methode, classement) VALUES (?, ?, ?, ?, ?)
                  ON CONFLICT(jour) DO UPDATE SET cree = excluded.cree, donnees = excluded.donnees,
                    methode = excluded.methode, classement = excluded.classement""",
               (jour, base.iso(), json.dumps(charge, ensure_ascii=False), methode.VERSION, VERSION_CLASSEMENT))
    db.commit()
    return jour, charge


def ecrire_pages(db):
    """Écrit le site à partir des éditions gardées : une page par jour (editions/<jour>.html), la dernière en
    page d'accueil. Tout est réécrit à chaque fois : un changement du gabarit vaut aussi pour les archives."""
    pub = config.public()
    os.makedirs(os.path.join(pub, "editions"), exist_ok=True)
    os.makedirs(os.path.join(pub, "data", "editions"), exist_ok=True)
    modele, actifs = gabarit_en_actifs()
    ecrire_actifs(pub, actifs)
    lignes = db.execute("SELECT jour, donnees, methode, classement FROM editions ORDER BY jour").fetchall()
    jours = [r["jour"] for r in lignes]
    charges = [(r["jour"], json.loads(r["donnees"])) for r in lignes]
    # Une édition faite avant que les intervalles de confiance soient connus les reçoit ici, sans rien réécrire d'autre.
    fiche = {m["nom"]: m for m in json.load(open(os.path.join(config.ICI, "medias.json"), encoding="utf-8"))["medias"]}
    for _, charge in charges:
        # Le bord d'un média est sa bande FrIdéo, relue dans son score : les éditions gardées avant le passage
        # aux sept bandes sont réétiquetées à l'affichage, rien n'est réécrit en base.
        for m in charge.get("medias", []):
            if m.get("score") is not None:
                m["bord"] = base.bord(m["score"])
            m["statut"] = base.statut(m.get("score"))   # une édition d'avant les statuts : tous ses médias sont classés
        charge.setdefault("classement", {})["seuils"] = SEUILS
        for m in charge.get("classement", {}).get("medias", []):
            if m.get("ic") is None and m["nom"] in fiche:
                m.update({k: fiche[m["nom"]].get(k) for k in ("ic", "sources")},
                         peu_documente=bool(fiche[m["nom"]].get("peu_documente")))
    semaines, mois = syntheses.toutes(charges)
    # pour passer d'une période à l'autre : la dernière édition de chacune porte sa synthèse
    liste_s = [{"cle": k, "jour": v["jours"][-1]} for k, v in sorted(semaines.items())]
    liste_m = [{"cle": k, "jour": v["jours"][-1]} for k, v in sorted(mois.items())]
    suivi = syntheses.suivi(charges)
    for i, (r, (_, charge)) in enumerate(zip(lignes, charges)):
        # Le suivi d'un sujet : sa présence dans toutes les éditions gardées, s'il y figure plus d'un jour.
        charge["suivi"] = {s["id"]: suivi[s["id"]] for s in charge["sujets"] if len(suivi.get(s["id"], [])) > 1}
        charge["min_medias"] = syntheses.MIN_MEDIAS
        # Les versions de cette édition : celles du jour où elle a été faite. methode '' : avant la version 1.0.
        charge["versions"] = {"methode": r["methode"] or "", "classement": r["classement"] or ""}
        charge["methode"] = methode.charge()   # la version de la méthode et son historique, lus par la page Démarche
        charge["mesure"] = "umami" if config.umami() else None   # lu par la page Mentions et le pied de page
        # La synthèse de la semaine par mail : null quand le SMTP n'est pas réglé (ni formulaire, ni mention).
        charge["mail"] = {"prestataire": "Brevo"} if config.mail() else None
        charge["periodes"] = {"semaine": semaines[syntheses.cle_semaine(r["jour"])], "mois": mois[r["jour"][:7]],
                              "semaines": liste_s, "mois_liste": liste_m}
        charge["edition"] = {"jour": r["jour"], "precedent": jours[i - 1] if i else None,
                             "suivant": jours[i + 1] if i + 1 < len(jours) else None, "toutes": jours}
        texte = json.dumps(charge, ensure_ascii=False)
        page = modele.replace("/*DONNEES*/null", texte.replace("</", "<\\/"))
        _ecrire(os.path.join(pub, "editions", r["jour"] + ".html"), page)
        _ecrire(os.path.join(pub, "data", "editions", r["jour"] + ".json"), texte)
        if i + 1 == len(jours):   # la dernière édition est la page d'accueil
            _ecrire(os.path.join(pub, "index.html"), page)
            _ecrire(os.path.join(pub, "data", "jour.json"), texte)
    _ecrire(os.path.join(pub, "data", "editions.json"), json.dumps(jours))
    retirer_anciens_actifs(pub, actifs)   # les pages citent les nouveaux : les anciens ne servent plus
    for nom in os.listdir(SITE):   # les autres pages (aveugle.html) ; les morceaux du gabarit ne sont pas publiés
        if nom != "gabarit.html" and os.path.isfile(os.path.join(SITE, nom)):
            shutil.copyfile(os.path.join(SITE, nom), os.path.join(pub, nom))
    return jours


def publier(db, jour=None):
    """Fait l'édition du jour et réécrit le site."""
    with base.Etape(db, "publication") as etape:
        jour, charge = enregistrer_edition(db, jour)
        jours = ecrire_pages(db)
        etape.detail = {"edition": jour, "editions": len(jours), "sujets": len(charge["sujets"]),
                        "medias": len(charge["medias"]), "titres": charge["total"]}
        return etape.detail


def pages(db):
    """Au démarrage : réécrit le site depuis les éditions gardées, sans en refaire une. S'il n'y en a aucune
    (première mise en route), en fait une avec ce que la base contient."""
    if not db.execute("SELECT 1 FROM editions LIMIT 1").fetchone():
        return publier(db)
    return {"editions": len(ecrire_pages(db))}
