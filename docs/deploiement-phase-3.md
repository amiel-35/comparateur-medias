# Le panel (phase 3) : ce que le code fait, ce qui reste à faire à la main

Rien n'a été essayé sur le serveur ni sur la vraie base. Tout est à essayer en local d'abord, sur une copie.

## Les pièces

| Pièce | Où | Ce qu'elle sait |
|---|---|---|
| Guichet (`comptes.py`, `compte.<domaine>`) | `identites.db` | qui est membre du panel, qui a retiré son bulletin (jusqu'à la clôture), la clé privée de chaque questionnaire ouvert |
| Urne (`urne.py`, `urne.<domaine>`) | `urnes/<questionnaire>.db` | les réponses, chacune sous l'empreinte de son bulletin, avec le bord déclaré ; ni date, ni rang, ni compte |
| Appareil (`compte/panel.html`) | stockage du navigateur | le bord, les bulletins, les reçus, la carte de votant |
| Tiroir public | `public/panel/` | les clés publiques, les questionnaires ouverts, les résultats après clôture |

La signature aveugle (RFC 9474, `signature.py` et `compte/aveugle-rsa.js`) fait que le guichet signe un bulletin
sans le voir : il ne peut pas rapprocher un retrait d'un dépôt, même en lisant tout.

## Les commandes

- `python -m comparateur panel-inviter 5` : cinq codes d'invitation au panel (le lien est
  `https://compte.compare-media.inflexion.me/panel#code=<code>`). Seule l'empreinte du code est gardée ; un code
  servi est effacé.
- `python -m comparateur questionnaire ouvrir <fichier.json>` : un questionnaire (format : `tests/test_panel.py`,
  `Questionnaire.BON`). Il se refuse lui-même s'il a un texte libre, plus de deux questions de profil ou une question
  de profil trop fine. Le panel est figé : seuls les membres inscrits sept jours avant l'ouverture peuvent répondre.
- `python -m comparateur questionnaire fermer <id>` : la clôture. Clé détruite, retraits effacés, urne close,
  compactée et scellée, résultats publiés dans `public/panel/resultats/<id>.json` avec deux effectifs. Le guichet la
  fait seul le lendemain du jour de fermeture inscrit dans le questionnaire.
- La carte de votant du vote à l'aveugle : une clé par trimestre, créée à la première demande, détruite au début du
  trimestre suivant, quand le guichet publie les agrégats par lot (`public/panel/aveugle/<trimestre>.json`).

## Ce qui reste à Amiel

- **Le questionnaire, le cercle invité, l'AIPD.** Seul un questionnaire factice existe (dans les tests).
- **Les journaux du proxy** (Traefik) : à couper pour `urne.` et `compte.` avant toute ouverture (cadrage D9). Sans
  cela, l'adresse IP et l'heure d'un retrait et d'un dépôt se rapprochent dans le journal, et la signature aveugle
  ne sert à rien.
- **Le DNS et Coolify** : `urne.compare-media.inflexion.me` sur le service `guichet`, port 8080, comme `compte.`
  (docs/deploiement-phase-2.md). Le volume `comparateur-urnes` est dans le compose.
- **Brevo** : l'annonce d'un questionnaire, en texte seul, sans lien (le suivi des clics ne se coupe pas).
- **La migration du vote à l'aveugle** : voir le README (commandes `verser-votes`, `oublier-votes`), sur une copie
  d'abord.

## À essayer avant tout déploiement

- Le parcours entier depuis l'application installée sur iPhone, Chrome Android et Firefox (cadrage, prototype,
  preuve 5) : la page du panel sur `compte.`, l'envoi vers `urne.`, le reçu, l'effacement. Si l'iPhone ouvre
  `compte.` hors de l'application ou perd la session, le repli prévu est un seul hôte et les chemins `/api/compte/`
  et `/api/urne/`, ce qui demande de changer le tri sur l'hôte et la politique CORS.
- Qu'aucune requête vers `urne.` ne porte de cookie (outils du navigateur, onglet Réseau).
- Une personne qui n'a jamais entendu le mot « jeton » fait le parcours sans aide. Noter ses hésitations.
