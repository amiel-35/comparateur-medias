"""L'ouverture et la clôture d'un questionnaire, et la carte de votant de chaque trimestre. C'est le seul module qui
touche aux deux côtés (le guichet, comptes.py ; l'urne, urne.py) : il ne fait qu'enchaîner leurs gestes, sans rien
garder. Il ne lit jamais une ligne de l'urne ni une ligne d'un compte.

  ouvrir     une paire de clés RSA neuve, propre au questionnaire ; la clé privée au guichet, la clé publique dans le
             tiroir public, l'urne créée avec ses questions ; le panel est figé (membres inscrits sept jours avant)
  fermer     la cérémonie : clé détruite, retraits effacés, urne close, compactée, scellée ; résultats publiés avec
             deux effectifs, bulletins délivrés et réponses reçues
  cartes     une clé par trimestre pour la carte de votant du vote à l'aveugle ; le trimestre fini, elle est
             détruite et les agrégats par lot publiés

Fichiers publics : public/panel/cles/<id>.json, public/panel/questionnaires/<id>.json (ce que l'appareil montre),
public/panel/resultats/<id>.json, public/panel/aveugle/<trimestre>.json.
"""
import json, os
from datetime import date

from . import comptes, config, signature, urne


def _public(*chemin):
    c = os.path.join(config.public(), "panel", *chemin)
    os.makedirs(os.path.dirname(c), exist_ok=True)
    return c


def _ecrire(chemin, x):
    with open(chemin + ".tmp", "w", encoding="utf-8") as f:
        f.write(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    os.replace(chemin + ".tmp", chemin)


def _effacer(chemin):
    try:
        os.remove(chemin)
    except FileNotFoundError:
        pass


def ouvrir(q, ident=None, bits=2048):
    """Ouvre un questionnaire. Lève ValueError avec les fautes s'il se refuse lui-même (urne.verifier_questionnaire).
    Rend la description publique du questionnaire."""
    fautes = urne.verifier_questionnaire(q)
    if fautes:
        raise ValueError("; ".join(fautes))
    if q["id"].startswith(("carte-", "aveugle-")):
        raise ValueError("identifiant réservé")
    cle = signature.nouvelle_cle(bits)
    pk = signature.publique(cle)
    propre = ident is None
    ident = ident or comptes.connexion()
    try:
        urne.creer(q, pk)
        comptes.ouvrir_cle(ident, q["id"], cle)
    finally:
        if propre:
            ident.close()
    _ecrire(_public("cles", q["id"] + ".json"), signature.en_hex(pk))
    public = {"v": 1, "id": q["id"], "titre": q["titre"], "intro": q.get("intro", ""), "fermeture": q.get("fermeture", ""),
              "questions": q["questions"], "cle": signature.en_hex(pk), "etiquette": urne.ETIQUETTE}
    _ecrire(_public("questionnaires", q["id"] + ".json"), public)
    return public


def fermer(questionnaire, ident=None):
    """La clôture comme cérémonie (premier cadrage, idée 5). Rend les résultats publiés."""
    propre = ident is None
    ident = ident or comptes.connexion()
    try:
        delivres = comptes.fermer_cle(ident, questionnaire)
    finally:
        if propre:
            ident.close()
    res = urne.fermer(questionnaire, delivres)
    _ecrire(_public("resultats", questionnaire + ".json"), res)
    _effacer(_public("questionnaires", questionnaire + ".json"))
    _effacer(_public("cles", questionnaire + ".json"))
    return res


def republier(questionnaire):
    """Recalcule les résultats d'un questionnaire clos (après un effacement par le reçu, par exemple)."""
    res = urne.resultats(questionnaire)
    _ecrire(_public("resultats", questionnaire + ".json"), res)
    return res


def trimestre(d=None):
    d = d or date.today()
    return f"{d.year}T{(d.month - 1) // 3 + 1}"


def assurer_carte(ident, t=None, bits=2048):
    """La clé de la carte de votant du trimestre, créée à la première demande. Rend l'identifiant (« carte-2026t4 »)."""
    cid = urne.carte_id(t or trimestre())
    if not ident.execute("SELECT 1 FROM cles WHERE questionnaire = ?", (cid,)).fetchone():
        cle = signature.nouvelle_cle(bits)
        try:
            comptes.ouvrir_cle(ident, cid, cle)
        except Exception:   # créée entre-temps par une autre requête
            ident.rollback()
            return cid
        _ecrire(_public("cles", cid + ".json"), signature.en_hex(signature.publique(cle)))
    return cid


def clore_trimestre(t, ident=None):
    """Le trimestre fini : clé de la carte détruite, retraits effacés, urne du vote close, agrégats publiés."""
    cid = urne.carte_id(t)
    propre = ident is None
    ident = ident or comptes.connexion()
    try:
        delivres = comptes.fermer_cle(ident, cid)
    finally:
        if propre:
            ident.close()
    agg = urne.clore_trimestre(t)
    agg["cartes_delivrees"] = delivres
    _ecrire(_public("aveugle", t + ".json"), agg)
    _effacer(_public("cles", cid + ".json"))
    return agg


def echeances(ident, aujourdhui=None):
    """Ce que le guichet fait seul, chaque minute : clore les trimestres passés et les questionnaires dont le jour de
    fermeture est passé. Rend la liste de ce qui a été clos."""
    aujourdhui = aujourdhui or date.today()
    fait = []
    courant = urne.carte_id(trimestre(aujourdhui))
    for r in comptes.cles_ouvertes(ident):
        q = r["questionnaire"]
        if q.startswith("carte-") and q != courant:
            clore_trimestre(q[6:].upper(), ident)
            fait.append(q)
        elif not q.startswith("carte-"):
            try:
                with open(_public("questionnaires", q + ".json"), encoding="utf-8") as f:
                    fin = json.load(f).get("fermeture") or ""
            except (OSError, ValueError):
                fin = ""
            if fin and fin < aujourdhui.isoformat():
                fermer(q, ident)
                fait.append(q)
    return fait
