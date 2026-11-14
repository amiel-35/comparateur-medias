"""Essai : la description des cadrages bouge-t-elle selon la consigne et selon le modèle ?

Sur les sujets déjà analysés, mêmes titres, cinq lectures :
  neutre    Sonnet, consigne de la fabrique
  neutre2   Sonnet, même consigne, second tirage : c'est le bruit de fond, l'étalon
  gauche    Sonnet, consigne précédée d'un regard de lecteur de gauche
  droite    Sonnet, consigne précédée d'un regard de lecteur de droite
  opus      Opus, consigne de la fabrique

Ne touche ni la base (lecture seule) ni le cache de la fabrique : tout va dans donnees/essais/coloration/.
  python3 essais/coloration.py lancer     # appels (claude -p), repris là où ils se sont arrêtés
  python3 essais/coloration.py mesurer    # tableau des écarts
"""
import difflib, hashlib, json, os, statistics, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("COMPARATEUR_HEURES", "400")   # l'essai porte sur les sujets analysés, quel que soit leur âge
from comparateur import base, config, fabrique, llm  # noqa: E402

REGARD = ("Pour cet exercice, tu lis ces titres avec le regard d'un lecteur français nettement de {bord} : ce que tu "
          "remarques et les mots que tu choisis sont ceux de ce lecteur. Tu restes exact sur ce que disent les titres.\n\n")
LECTURES = {
    "neutre": ("sonnet", ""),
    "neutre2": ("sonnet", "\n"),          # un saut de ligne en tête : même consigne, autre tirage
    "gauche": ("sonnet", REGARD.format(bord="gauche")),
    "droite": ("sonnet", REGARD.format(bord="droite")),
    "opus": ("opus", ""),
    # Sans étiquettes : le nom des médias est remplacé par un code (M1, M2…).
    "masque": ("sonnet", "", "prompt_masque"),
    # Sans étiquettes ET bords échangés : les titres de gauche sont présentés comme de droite, et l'inverse.
    # Si la description suit les titres et non l'étiquette, « d » ici doit ressembler à « g » de la lecture masquée.
    "inverse": ("sonnet", "", "prompt_inverse"),
}
DOSSIER = os.path.join(config.donnees(), "essais", "coloration")


def sujets():
    db = base.connexion()
    try:
        faits = {r["sujet_id"] for r in db.execute("SELECT sujet_id FROM analyses")}
        out = []
        for s in fabrique.sujets_du_jour(db):
            if s["id"] not in faits:
                continue
            codes = {}

            def bloc(masquer, inverser):
                lignes, n = [], 0
                for cote in "gcd":
                    lignes.append(f"--- {fabrique.NOM_COTE[cote]} ---")
                    vrai = {"g": "d", "d": "g"}.get(cote, cote) if inverser else cote
                    for a in s["articles"]:
                        if a["cote"] == vrai:
                            n += 1
                            nom = codes.setdefault(a["media"], f"M{len(codes) + 1}") if masquer else a["media"]
                            lignes.append(f"{n}. {nom} : {a['titre']}")
                    if lignes[-1].startswith("---"):
                        lignes.append("(aucun titre)")
                return fabrique.CONSIGNE_ANALYSE.format(libelle=s["libelle"], titres="\n".join(lignes)), n

            prompt, n = bloc(False, False)
            out.append({"id": s["id"], "libelle": s["libelle"], "titres": n, "prompt": prompt,
                        "prompt_masque": bloc(True, False)[0], "prompt_inverse": bloc(True, True)[0]})
        return out
    finally:
        db.close()


def chemin(sid, lecture):
    return os.path.join(DOSSIER, f"{sid}-{lecture}.json")


def appeler(tache):
    s, lecture = tache
    if os.path.exists(chemin(s["id"], lecture)):
        return None
    modele, tete = LECTURES[lecture][:2]
    prompt = s[LECTURES[lecture][2] if len(LECTURES[lecture]) > 2 else "prompt"]
    vide = tempfile.mkdtemp(prefix="comparateur-")
    cmd = ["claude", "-p", "--model", modele, "--output-format", "json", "--system-prompt", llm.SYSTEME,
           "--tools", "", "--strict-mcp-config", "--setting-sources", "project",
           "--disable-slash-commands", "--no-session-persistence"]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, input=tete + prompt, capture_output=True, text=True, cwd=vide, timeout=400)
    finally:
        os.rmdir(vide)
    try:
        env = json.loads(r.stdout)
        rendu = llm._json(env["result"])
    except Exception as e:
        return f"{s['id']}/{lecture} : échec ({type(e).__name__}) {(r.stderr or r.stdout)[:200]}"
    u = env.get("usage", {})
    rendu["_mesure"] = {"modele": modele, "secondes": round(time.time() - t0, 1), "cout_usd": env.get("total_cost_usd"),
                        "entree": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                        + u.get("cache_read_input_tokens", 0), "sortie": u.get("output_tokens", 0)}
    with open(chemin(s["id"], lecture), "w", encoding="utf-8") as f:
        json.dump(rendu, f, ensure_ascii=False, indent=1)
    return None


def lancer():
    os.makedirs(DOSSIER, exist_ok=True)
    ss = sujets()
    json.dump(ss,
              open(os.path.join(DOSSIER, "sujets.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    taches = [(s, l) for s in ss for l in LECTURES]
    print(f"{len(ss)} sujets, {len(taches)} lectures", flush=True)
    with ThreadPoolExecutor(5) as pool:
        for i, err in enumerate(pool.map(appeler, taches), 1):
            if err:
                print(err, flush=True)
            if i % 10 == 0:
                print(f"{i}/{len(taches)}", flush=True)
    print("fini", flush=True)


def proche(a, b):
    """Ressemblance de deux textes, de 0 à 1, sur les mots (sans casse ni ponctuation)."""
    return difflib.SequenceMatcher(None, fabrique.norm_strict(a).split(), fabrique.norm_strict(b).split()).ratio()


def mesurer():
    ss = json.load(open(os.path.join(DOSSIER, "sujets.json"), encoding="utf-8"))
    lignes, couts = [], {}
    for s in ss:
        lus = {}
        for l in LECTURES:
            try:
                lus[l] = json.load(open(chemin(s["id"], l), encoding="utf-8"))
            except FileNotFoundError:
                pass
        for l, r in lus.items():
            m = r["_mesure"]
            c = couts.setdefault(l, {"appels": 0, "cout": 0.0, "entree": 0, "sortie": 0, "secondes": 0.0})
            c["appels"] += 1
            c["cout"] += m["cout_usd"] or 0
            c["entree"] += m["entree"]
            c["sortie"] += m["sortie"]
            c["secondes"] += m["secondes"]
        if "neutre" not in lus:
            continue
        ref = lus["neutre"]
        for l, r in lus.items():
            if l == "neutre":
                continue
            mots_ref = {fabrique.norm_strict(m.get("terme", "")) for m in ref.get("mots") or []}
            mots = {fabrique.norm_strict(m.get("terme", "")) for m in r.get("mots") or []}
            lignes.append({
                "sujet": s["id"], "libelle": s["libelle"], "lecture": l,
                "ecart_ref": ref.get("ecart"), "ecart": r.get("ecart"),
                "texte": round(statistics.mean(proche(str(ref.get(k, "")), str(r.get(k, ""))) for k in "gcd"), 2),
                "mots_communs": f"{len(mots & mots_ref)}/{len(mots | mots_ref)}",
                "hors_sujet_identique": sorted(map(str, ref.get("hors_sujet") or [])) == sorted(map(str, r.get("hors_sujet") or [])),
            })
    json.dump(lignes, open(os.path.join(DOSSIER, "ecarts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("lecture   sujets  |écart de note| moyen  notes identiques  texte proche (0-1)  hors-sujet identique")
    for l in [x for x in LECTURES if x != "neutre"]:
        ls = [x for x in lignes if x["lecture"] == l]
        if not ls:
            continue
        dn = [abs(x["ecart"] - x["ecart_ref"]) for x in ls if isinstance(x["ecart"], int) and isinstance(x["ecart_ref"], int)]
        sens = statistics.mean(x["ecart"] - x["ecart_ref"] for x in ls if isinstance(x["ecart"], int) and isinstance(x["ecart_ref"], int))
        print(f"{l:9} {len(ls):6}  {statistics.mean(dn):.2f} (sens {sens:+.2f})        {sum(d == 0 for d in dn)}/{len(dn)}"
              f"             {statistics.mean(x['texte'] for x in ls):.2f}                {sum(x['hors_sujet_identique'] for x in ls)}/{len(ls)}")
    print()
    for l, c in couts.items():
        print(f"{l:9} {c['appels']} appels, {c['entree']} jetons en entrée, {c['sortie']} en sortie, "
              f"{c['cout']:.2f} $, {c['secondes'] / max(1, c['appels']):.0f} s par appel")


if __name__ == "__main__":
    {"lancer": lancer, "mesurer": mesurer}[sys.argv[1] if len(sys.argv) > 1 else "mesurer"]()
