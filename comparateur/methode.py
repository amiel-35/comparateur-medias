"""La version de la méthode : la page Démarche est le document de référence, et elle porte cette ligne.

Une version change quand ce que le site compte ou montre change de règle : bords, silences, fenêtre, rubriques,
regroupement. Un changement d'affichage seul ne change pas la version. L'historique est relevé dans l'historique
du dépôt (git log), daté au jour.
"""

VERSION = "1.0"
DATE = "2026-11-17"   # jour où cette version est entrée en vigueur

# Du plus récent au plus ancien. Chaque ligne : (version, jour, ce qui a changé). Les éditions d'avant la
# version 1.0 n'ont pas de numéro : elles suivent les règles en vigueur le jour où elles ont été faites.
HISTORIQUE = (
    ("1.0", "2026-11-17", "Première version numérotée. Elle reprend les règles du 15/11/2026, sans changement de calcul."),
    ("", "2026-11-15", "Les bords deviennent les sept bandes de FrIdéo, avec ses noms et ses seuils. Les silences se jugent "
                       "sur trois côtés. Les dates des titres sont ramenées en temps universel."),
    ("", "2026-11-14", "Premières éditions, une par jour. Cinq bords, découpés par ce site dans le score FrIdéo. Le sport "
                       "et la culture sont écartés d'après l'adresse de l'article."),
)


def charge():
    """Ce que la page reçoit : la version en vigueur et son historique. Lu par la vue Démarche."""
    return {"version": VERSION, "date": DATE,
            "historique": [{"version": v, "jour": j, "texte": t} for v, j, t in HISTORIQUE]}
