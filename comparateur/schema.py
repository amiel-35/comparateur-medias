"""Un petit validateur de JSON Schema, en bibliothèque standard, pour le sous-ensemble que ce dépôt utilise :
type (un nom ou une liste de noms), properties, required, additionalProperties, items, enum, pattern, minimum,
maximum, et $ref local vers $defs ("#/$defs/nom"). Un mot-clé hors de cette liste est ignoré : le schéma de
l'export est écrit à la main avec ceux-là seulement.

`erreurs(doc, schema)` rend la liste des défauts (vide si le document est valide), chacun avec son chemin.
`verifier(doc, schema)` lève `ErreurSchema` s'il y en a.
"""
import re


class ErreurSchema(ValueError):
    pass


def _type_ok(valeur, nom):
    # En Python, True est un entier : un booléen n'est ni un entier ni un nombre.
    if nom == "null":
        return valeur is None
    if nom == "boolean":
        return isinstance(valeur, bool)
    if nom == "integer":
        return isinstance(valeur, int) and not isinstance(valeur, bool)
    if nom == "number":
        return isinstance(valeur, (int, float)) and not isinstance(valeur, bool)
    if nom == "string":
        return isinstance(valeur, str)
    if nom == "array":
        return isinstance(valeur, list)
    if nom == "object":
        return isinstance(valeur, dict)
    raise ValueError(f"type inconnu dans le schéma : {nom}")


def _egal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def _resoudre(ref, racine):
    if not ref.startswith("#/"):
        raise ValueError(f"seule une référence locale est permise : {ref}")
    noeud = racine
    for morceau in ref[2:].split("/"):
        noeud = noeud[morceau]
    return noeud


def _valider(doc, schema, racine, chemin, sortie):
    if "$ref" in schema:
        schema = _resoudre(schema["$ref"], racine)
    types = schema.get("type")
    if types is not None:
        noms = [types] if isinstance(types, str) else types
        if not any(_type_ok(doc, n) for n in noms):
            sortie.append(f"{chemin} : type attendu {'/'.join(noms)}, reçu {type(doc).__name__}")
            return
    if "enum" in schema and not any(_egal(doc, v) for v in schema["enum"]):
        sortie.append(f"{chemin} : valeur hors de la liste permise")
    if isinstance(doc, str) and "pattern" in schema and not re.search(schema["pattern"], doc):
        sortie.append(f"{chemin} : ne respecte pas le motif {schema['pattern']}")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            sortie.append(f"{chemin} : {doc} est sous le minimum {schema['minimum']}")
        if "maximum" in schema and doc > schema["maximum"]:
            sortie.append(f"{chemin} : {doc} dépasse le maximum {schema['maximum']}")
    if isinstance(doc, dict):
        props = schema.get("properties", {})
        for cle in schema.get("required", []):
            if cle not in doc:
                sortie.append(f"{chemin} : champ requis absent : {cle}")
        autres = schema.get("additionalProperties", True)
        for cle, valeur in doc.items():
            if cle in props:
                _valider(valeur, props[cle], racine, f"{chemin}.{cle}", sortie)
            elif autres is False:
                sortie.append(f"{chemin} : clé non prévue : {cle}")
            elif isinstance(autres, dict):
                _valider(valeur, autres, racine, f"{chemin}.{cle}", sortie)
    if isinstance(doc, list) and "items" in schema:
        for i, valeur in enumerate(doc):
            _valider(valeur, schema["items"], racine, f"{chemin}[{i}]", sortie)


def erreurs(doc, schema):
    sortie = []
    _valider(doc, schema, schema, "$", sortie)
    return sortie


def verifier(doc, schema):
    fautes = erreurs(doc, schema)
    if fautes:
        raise ErreurSchema("; ".join(fautes[:5]) + (f" (et {len(fautes) - 5} autres)" if len(fautes) > 5 else ""))
