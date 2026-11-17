"""Ce que la fabrique dépose dans le tiroir public pour les mails et les lecteurs de flux. Aucune adresse, aucun compte :
les mêmes octets pour tous.

  public/lettre/<semaine>.json   la synthèse de chaque semaine (syntheses.periode), que le guichet envoie le lundi
  public/alertes/<jour>.json     les sujets de chaque édition et leurs rubriques, pour l'alerte du matin
  public/flux/sujets/<id>.xml    un flux Atom par sujet : une entrée par édition où il figure

La rubrique d'un sujet est lue dans l'adresse de ses articles (fabrique.rubrique), par un programme : une rubrique
compte pour un sujet quand un tiers au moins de ses titres la portent. Aucun modèle n'y touche.
"""
import json, os, re
from xml.sax.saxutils import escape, quoteattr

from . import base, config, syntheses
from .fabrique import rubrique

GARDE_FLUX = 30   # entrées par flux, les plus récentes


def _ecrire(chemin, texte):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texte)
    os.replace(tmp, chemin)


def _json(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def rubriques_du_sujet(articles):
    """Les rubriques qu'un tiers au moins des titres du sujet portent dans leur adresse."""
    compte = {}
    for a in articles:
        r = rubrique(a.get("lien") or "")
        if r:
            compte[r] = compte.get(r, 0) + 1
    return sorted(r for r, n in compte.items() if 3 * n >= len(articles))


def alerte(jour, charge):
    """L'alerte d'une édition : ses sujets, les plus couverts d'abord, avec leurs rubriques."""
    bord = syntheses.bords_des_medias(charge)
    lus = syntheses.medias_lus(bord)
    sujets = []
    for s in charge.get("sujets", []):
        noms = [a["media"] for a in s["articles"]]
        par = syntheses.repartition(noms, bord)
        sujets.append({"id": s["id"], "titre": s["titre"], "medias": len(set(noms)), "titres": len(noms),
                       "rubriques": rubriques_du_sujet(s["articles"]),
                       "silences": syntheses.silencieux(par, lus, syntheses.classes(noms, bord)),
                       "page": f"/editions/{jour}.html#/sujet/{s['id']}"})
    sujets.sort(key=lambda s: (-s["medias"], -s["titres"], s["id"]))
    return {"jour": jour, "page": f"/editions/{jour}.html", "titres_ecrits_par_un_modele": True, "sujets": sujets}


def atom(id_sujet, entrees, site):
    """Le flux Atom d'un sujet. entrees : [(jour, titre, ligne de suivi)], du plus ancien au plus récent."""
    entrees = entrees[-GARDE_FLUX:]
    dernier = entrees[-1]
    lignes = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="fr">',
              f"<title>{escape(config.MARQUE + ' : ' + dernier[1])}</title>",
              f"<subtitle>Ce sujet, édition après édition. Les titres de sujet sont écrits par un modèle ; les comptages, par une formule.</subtitle>",
              f"<id>{escape(site)}/flux/sujets/{escape(id_sujet)}.xml</id>",
              f"<link rel=\"self\" href={quoteattr(site + '/flux/sujets/' + id_sujet + '.xml')}/>",
              f"<link rel=\"alternate\" href={quoteattr(site + '/editions/' + dernier[0] + '.html#/sujet/' + id_sujet)}/>",
              f"<updated>{dernier[0]}T06:00:00Z</updated>", f"<author><name>{escape(config.MARQUE)}</name></author>"]
    noms = {"g": "gauche", "c": "centre", "d": "droite"}
    for jour, titre, x in reversed(entrees):
        sil = [noms[c] for c in x.get("silences", []) if c in noms]
        resume = (f"{x['titres']} titres, {x['medias']} médias. "
                  + ("Côté silencieux : " + ", ".join(sil) + ". " if sil else "")
                  + "Titre du sujet écrit par un modèle.")
        lien = f"{site}/editions/{jour}.html#/sujet/{id_sujet}"
        lignes += ["<entry>", f"<title>{escape(jour + ' : ' + titre)}</title>", f"<id>{escape(lien)}</id>",
                   f"<link href={quoteattr(lien)}/>", f"<updated>{jour}T06:00:00Z</updated>",
                   f"<summary>{escape(resume)}</summary>", "</entry>"]
    return "\n".join(lignes + ["</feed>", ""])


def ecrire(pub, charges, semaines):
    """Écrit les synthèses de semaine, les alertes et les flux par sujet. charges : [(jour, charge)] de toute la base,
    déjà préparées par publier.ecrire_pages (bords relus, suivi calculé)."""
    for cle, p in semaines.items():
        _ecrire(os.path.join(pub, "lettre", cle + ".json"), _json(p))
    titres = {}
    for jour, charge in charges:
        _ecrire(os.path.join(pub, "alertes", jour + ".json"), _json(alerte(jour, charge)))
        for s in charge.get("sujets", []):
            titres[(s["id"], jour)] = s["titre"]
    suivi = syntheses.suivi(charges)
    site = config.site_url()
    for id_sujet, lignes in suivi.items():
        if not re.fullmatch(r"[\w-]{1,40}", id_sujet):   # l'identifiant devient un nom de fichier
            continue
        entrees = [(x["jour"], titres[(id_sujet, x["jour"])], x) for x in lignes]
        _ecrire(os.path.join(pub, "flux", "sujets", id_sujet + ".xml"), atom(id_sujet, entrees, site))
