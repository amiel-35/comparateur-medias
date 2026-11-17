"""Le registre des abonnements : chaque service du compte est une entrée de ce registre, pas une colonne de la base.

Un abonnement est une ligne (compte, type, cible). Ce qui se classe, c'est le couple (type, cible), et le cumul
(docs/cadrage-long-terme.md, section 3). Les règles, chacune tenue par un test :

  16. un type inconnu du registre est refusé ; un type de classe « opinion » ne peut pas être enregistré ;
  17. une cible hors de la liste fermée de son type est refusée (un mot libre, un nom de média) ;
  18. ajouter un type ne change pas le schéma de identites.db ;
  19. l'écran « Ce que ce site sait de vous » est engendré depuis les lignes du compte.

Une cible est vide, ou tirée d'une liste fermée et large écrite ici. Jamais un texte libre, jamais un média, un
bord, un parti, une personne, un sujet précis : ceux-là restent sur l'appareil (« Mes sujets », journaux suivis).
Ce module ne connaît ni la base publique ni l'urne : il n'importe rien du paquet.
"""
from collections import namedtuple

# Ce qu'un abonnement révèle de quelqu'un, d'après la forme de sa cible (jamais d'après son thème).
CLASSES = ("rien", "un peu")          # « opinion » n'entre pas dans le compte : sa place est l'appareil
CLASSES_REFUSEES = ("opinion",)

Type = namedtuple("Type", "nom classe cibles plafond base_legale phrase ouvert rythme")

# Les rubriques larges du site, lues dans l'adresse des articles par la fabrique (fabrique.RUBRIQUES). Le sport et
# la culture sont écartés des sujets ; faits-divers et opinions ne sont pas proposés.
RUBRIQUES = ("politique", "international", "economie", "societe", "sciences", "environnement")
NOMS_RUBRIQUES = {"politique": "Politique", "international": "International", "economie": "Économie",
                  "societe": "Société", "sciences": "Sciences", "environnement": "Environnement"}

REGISTRE = {
    "lettre": Type("La synthèse de la semaine", "rien", None, 1,
                   "consentement, avec double confirmation (RGPD, art. 6-1-a)",
                   "Chaque lundi, les sujets les plus couverts de la semaine et les silences de chaque bord.", True, "semaine"),
    "alerte-edition": Type("L’édition du jour est parue", "rien", None, 1, "consentement (RGPD, art. 6-1-a)",
                           "Chaque matin, un mail court quand l’édition du jour est en ligne.", True, "jour"),
    "rubrique": Type("Rubrique", "un peu", RUBRIQUES, 3, "consentement (RGPD, art. 6-1-a)",
                     "Chaque matin, les sujets du jour d’une rubrique large. Trois rubriques au plus.", True, "jour"),
    # Déclaré, fermé : il s'ouvrira avec le panel (phase 3), après l'AIPD.
    "panel": Type("Le panel", "un peu", None, 1, "consentement exprès (RGPD, art. 9-2-a)",
                  "Être recontacté, de temps en temps, pour répondre à des questionnaires sans votre nom.", False, None),
}


class Refus(Exception):
    """Un abonnement que le registre n'admet pas. Le message se lit à l'écran."""


def verifier_registre(registre=None):
    """Lève une erreur si une entrée du registre enfreint ses règles. Appelée à l'import, et par les tests."""
    for nom, t in (registre or REGISTRE).items():
        if t.classe in CLASSES_REFUSEES or t.classe not in CLASSES:
            raise ValueError(f"type {nom} : classe {t.classe!r} refusée dans le compte")
        if t.cibles is not None and (not t.cibles or any(not isinstance(c, str) or not c for c in t.cibles)):
            raise ValueError(f"type {nom} : liste de cibles vide ou mal formée")
        if not isinstance(t.plafond, int) or t.plafond < 1:
            raise ValueError(f"type {nom} : plafond invalide")


verifier_registre()


def type_de(nom, registre=None):
    t = (registre or REGISTRE).get(nom)
    if t is None:
        raise Refus("type d’abonnement inconnu")
    return t


def verifier(nom, cible, registre=None, ouvert_requis=True):
    """Rend la cible normalisée ('' pour un type sans cible), ou lève Refus."""
    t = type_de(nom, registre)
    if ouvert_requis and not t.ouvert:
        raise Refus("ce service n’est pas encore ouvert")
    cible = "" if cible is None else cible
    if not isinstance(cible, str):
        raise Refus("cible invalide")
    if t.cibles is None:
        if cible:
            raise Refus("ce service ne prend pas de cible")
        return ""
    if cible not in t.cibles:
        raise Refus("cible hors de la liste")
    return cible


def ecran(registre=None):
    """Ce que la page du compte propose : les types ouverts, leurs cibles, leur phrase. Mêmes octets pour tous."""
    return [{"type": nom, "nom": t.nom, "phrase": t.phrase, "ouvert": t.ouvert, "plafond": t.plafond,
             "cibles": [{"cible": c, "nom": NOMS_RUBRIQUES.get(c, c)} for c in t.cibles] if t.cibles else None}
            for nom, t in (registre or REGISTRE).items()]
