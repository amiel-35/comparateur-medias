# Comparateur de cadrages médiatiques

Comment les médias français titrent-ils un même sujet, de la gauche à la droite ? Ce dépôt récolte les titres
de 30 médias, les regroupe en sujets, décrit le traitement de chaque bord et signale les angles morts.

Trois blocs, un seul paquet Python (`comparateur/`), aucune dépendance hors bibliothèque standard
sauf le SDK Anthropic (mode `api` seulement).

| Bloc | Fichiers | Rôle |
|---|---|---|
| **Fabrique** | `fabrique.py`, `llm.py`, `aveugle.py`, `publier.py`, `chaine.py` | Récolte les flux RSS, regroupe les titres en sujets (Haiku), analyse les cadrages (Sonnet), fabrique les lots à l'aveugle, écrit le site statique. |
| **Vitrine** | `site/` → `<données>/public/` | `index.html` + `data/jour.json`, régénérés par la fabrique. Une visite ne touche ni la base ni un modèle. |
| **Guichet des votes** | `serveur.py` | Sert la vitrine et l'API des votes (`/api/…`), contrôle de santé sur `/sante`. |


## En local

```bash
python3 -m unittest discover -s tests          # 18 tests, sans réseau ni modèle
python3 -m comparateur init                    # base SQLite + 30 médias (scores FrIdéo)
python3 -m comparateur tout                    # l'édition du jour : récolte, regroupement, analyse, lots, publication
python3 -m comparateur inviter 3               # trois codes d'invitation
python3 -m comparateur servir                  # http://localhost:8080
python3 -m comparateur jetons                  # appels aux modèles, jetons, coût
```

En local la fabrique appelle les modèles par `claude -p` (abonnement Claude Code, pas de clé) :
`COMPARATEUR_LLM=cli`, la valeur par défaut hors Docker. Les données vivent dans `donnees/` (hors git).

## Sur Coolify

1. Nouvelle ressource → **Docker Compose**, ce dépôt Git, dossier de base à la racine.
2. **Environment Variables** : `ANTHROPIC_API_KEY` (secret), et au besoin les réglages de `.env.example`.
3. **Domaine** : Domains → Add domain, service `comparateur`, port interne `8080` (forme `https://mon-domaine:8080` : le
   suffixe dit au proxy quel port du conteneur viser, le public reste en 443 ; Coolify n'affiche plus
   le suffixe ensuite mais le garde pour son proxy). Coolify fournit le HTTPS. Aucun `ports:` dans le compose.
4. **Stockage** : le volume `comparateur-donnees` (monté sur `/data`) porte la base, le cache des appels et le
   site généré. C'est lui qu'il faut sauvegarder.
5. Déployer. Le conteneur crée la base, réécrit le site depuis les éditions gardées, sert, puis lance la
   fabrique : récolte des flux toutes les `COMPARATEUR_FABRIQUE_MINUTES` minutes (180 par défaut) et une édition
   par jour à `COMPARATEUR_EDITION_HEURE` heures, heure de Paris (6 par défaut).

Variante, si ta version de Coolify propose des tâches planifiées sur une ressource Compose (non vérifié dans sa
documentation) : `COMPARATEUR_FABRIQUE_MINUTES=0` et une tâche `python -m comparateur tout`, par exemple `*/30 * * * *`.

Vérifié dans la documentation de Coolify le 14/11/2026 : domaine et port saisis dans l'interface, variables
`${VAR:-défaut}` et `${VAR:?}` (obligatoire, bloque le déploiement si vide), `healthcheck:` du compose pris comme
référence, Base Directory et emplacement du compose réglables. Coolify peut renommer le volume : vérifier son nom
dans Persistent Storage avant toute migration de données.

Créer des invitations : terminal du conteneur dans Coolify, `python -m comparateur inviter 5`. Le lien à
envoyer est `https://<domaine>/aveugle.html?code=<code>`.

## Les éditions

La récolte et l'édition sont séparées. Les flux sont lus plusieurs fois par jour, sans modèle, pour ne rien
rater. Une fois par jour, à heure fixe, la fabrique regroupe et analyse les titres des 24 dernières heures et
publie **l'édition du jour**, qui ne bouge plus ensuite.

- Chaque édition est gardée entière dans la table `editions` (une ligne par jour, datée en heure de Paris).
- Le site a une page par édition (`/editions/2026-11-14.html`), la dernière servant de page d'accueil, avec une
  navigation jour par jour et la liste de toutes les éditions.
- Les pages sont réécrites depuis les éditions gardées à chaque publication et à chaque démarrage : un
  changement du gabarit vaut aussi pour les archives.
- `python -m comparateur tout` refait l'édition du jour ; `python -m comparateur pages` réécrit seulement le site.

## L'API des votes

| Route | Corps | Réponse |
|---|---|---|
| `POST /api/inscription` | `{code, bord}` (bord déclaré du votant, de −2 à +2) | `201 {jeton}` ; le code est à usage unique |
| `GET /api/lot` | en-tête `Authorization: Bearer <jeton>` | `{lot: {id, titres[10]} \| null, restants}` |
| `POST /api/avis-aveugle` | `{lot, note}` (de −2 à +2) | `201` ; `409` si le lot est déjà jugé |
| `POST /api/avis-note` | `{media, accord}` | `201` ; simple alerte, ne change aucune note |
| `GET /api/resultats` | | note à l'aveugle par média, effectifs par bord, statut `indicatif` ou `publiable` |
| `GET /sante` | | `{ok, derniere_publication}` |

**Anonymat.** La base ne garde que l'empreinte du jeton et le bord déclaré : ni nom, ni adresse, ni lien entre
une invitation et un votant ; les dates sont arrondies au jour. Le journal du serveur n'écrit pas l'adresse du visiteur.

**Comptage.** Moyenne par bord déclaré (gauche, centre, droite), puis moyenne des bords : un bord nombreux ne
pèse pas plus qu'un autre. `publiable` seulement si chaque bord atteint `COMPARATEUR_MIN_PAR_BORD` votants.

**Abus.** Un vote par lot et par jeton ; 10 essais d'inscription par heure et par adresse ; 300 requêtes par
minute et par adresse ; corps limité à 4 Ko.

## Garde-fous de la fabrique

- Un modèle ne note jamais un média : les notes viennent de `medias.json` (FrIdéo, CC BY 4.0) et, plus tard, des votes.
- Au regroupement, le modèle ne voit pas le nom des médias.
- Toute citation entre « » absente des titres est retirée par le code (`verifier_citations`).
- Chaque appel est mis en cache par empreinte : relancer la fabrique ne repaie pas ce qui est déjà fait.
- Un sujet n'est réanalysé que si ses titres ont changé.
- Plafond de dépense par jour (`COMPARATEUR_BUDGET_JOUR_USD`) : au-delà, la fabrique saute les étapes à modèle et publie quand même.

## Limites connues

- **SQLite, un seul conteneur.** Suffisant pour un cercle invité. Pour la charge : PostgreSQL et plusieurs copies
  du guichet ; le SQL est gardé simple pour ça, mais `base.py` et la limite de débit en mémoire sont à adapter.
- **Serveur HTTP de la bibliothèque standard.** Correct derrière le proxy de Coolify à petite échelle ; à
  remplacer par un serveur ASGI pour la charge.
- **Mode `api` non essayé** tant qu'il n'y a pas de clé : seul le mode `cli` a tourné.
- **Le Point et Les Echos** refusent même un lecteur RSS déclaré (403) : absents de la récolte.
- Un titre resté seul n'est pas reproposé aux sujets ouverts après lui.

## Essais

`essais/coloration.py` mesure la stabilité de l'analyse : second tirage, consigne colorée à gauche ou à droite,
autre modèle, noms des médias masqués, bords échangés. Sur 20 sujets (14/11/2026), aucune de ces variantes ne
change plus la description qu'un simple second tirage.

## Sources et remerciements

- **Classement des médias : FrIdéo v1.0**, French News Lab (<https://frenchnewslab.org/en/medias>), sous licence
  CC BY 4.0. Les scores de `comparateur/medias.json` en sont relevés ; les bords (gauche, centre, droite) sont
  dérivés ici par des seuils fixes et n'engagent pas ses auteurs.
- **L'idée** de comparer la couverture par bord et de signaler les angles morts vient de
  [Ground News](https://ground.news/rating-system).
- **Le jugement à l'aveugle** par un panel équilibré s'inspire de la méthode publiée par
  [AllSides](https://www.allsides.com/about/media-bias-rating-methods).

Ce projet n'est affilié à aucun de ces organismes.

## Licence

Code sous [AGPL-3.0](LICENSE).
