# Cadrages, comparateur de cadrages médiatiques

Comment les médias français titrent-ils un même sujet, de la gauche à la droite ? Ce dépôt récolte les titres
de 30 médias, les regroupe en sujets, décrit le traitement de chaque bord et signale les angles morts.

Trois blocs, un seul paquet Python (`comparateur/`), aucune dépendance hors bibliothèque standard
sauf le SDK Anthropic (mode `api` seulement).

| Bloc | Fichiers | Rôle |
|---|---|---|
| **Fabrique** | `fabrique.py`, `llm.py`, `aveugle.py`, `publier.py`, `chaine.py` | Récolte les flux RSS, regroupe les titres en sujets (Haiku), analyse les cadrages (Sonnet), fabrique les lots à l'aveugle, écrit le site statique. |
| **Vitrine** | `site/` (morceaux, voir [DOCTRINE.md](DOCTRINE.md)) → `<données>/public/` | `index.html` + `data/jour.json`, régénérés par la fabrique. Une visite ne touche ni la base ni un modèle. |
| **Guichet des votes** | `serveur.py` | Sert la vitrine et l'API des votes (`/api/…`), contrôle de santé sur `/sante`. |


## En local

```bash
python3 -m unittest discover -s tests          # sans réseau ni modèle
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
   `COMPARATEUR_UMAMI_ID` (le `data-website-id` du site dans Umami, stats.inflexion.me) active la mesure de
   fréquentation, sans cookie ; la page `#/mentions` et la politique de sécurité suivent d'elles-mêmes.
   `COMPARATEUR_SMTP_UTILISATEUR` et `COMPARATEUR_SMTP_MOT_DE_PASSE` (secret : la clé SMTP de Brevo) allument la
   synthèse de la semaine par mail ; sans eux, ni formulaire ni envoi. Le nom de l'expéditeur est toujours
   « Cadrages » (`config.MARQUE`) : `COMPARATEUR_MAIL_NOM` n'est plus lu. Réglages facultatifs : `COMPARATEUR_SMTP_HOTE`
   (`smtp-relay.brevo.com`), `COMPARATEUR_SMTP_PORT` (587, STARTTLS), `COMPARATEUR_MAIL_EXPEDITEUR`
   (`no-reply@inflexion.me`, adresse à valider dans Brevo), `COMPARATEUR_SITE_URL` (`https://compare-media.inflexion.me`, pour les liens des mails).
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
envoyer est `https://<domaine>/aveugle.html#code=<code>` : dans le fragment, le code n'arrive ni au serveur ni au
journal du proxy. L'ancienne forme `?code=` marche encore.

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
- Un export n'est jamais une copie de `comparateur.db` (règle 10 de [DOCTRINE.md](DOCTRINE.md)) : la base porte
  aussi les adresses des abonnés et les votants.

## L'export de chaque édition

Chaque édition gardée est aussi publiée en JSON, la même pour tout le monde (aucun paramètre, aucune heure de
génération : mêmes octets d'un passage à l'autre).

- `/export/editions.json` : la liste des jours.
- `/export/editions/<jour>.json` : l'édition du jour (version 1 du format).
- `/export/schema.json` : le schéma JSON (2020-12) de ces fichiers, écrit à la main dans
  `comparateur/export_schema.json`.

Un export contient : les versions de la méthode et du classement, les licences (code AGPL-3.0 ; classement FrIdéo,
French News Lab, CC BY 4.0 ; les titres appartiennent à leurs journaux), la liste des champs écrits par un modèle,
les médias lus (nom, statut, score, bande), les absents, les non classés, les sujets (titre, fait, divergence,
angles, mots, titres, comptage par bande, côtés silencieux) et les titres restés seuls. Il ne contient ni
résultats de votes, ni rien qui touche un abonné ou un votant. Une édition d'avant les statuts ou la version 1.0
s'exporte aussi : un champ manquant reçoit une valeur par défaut. `comparateur/export.py` le construit champ par
champ à partir de l'édition gardée, jamais depuis la base, et `comparateur/schema.py` (un validateur de la
bibliothèque standard) le vérifie contre le schéma avant de l'écrire.

## La méthode, versionnée

La page Démarche (`#/demarche`) est le document de référence de la méthode. Elle porte une ligne de version
(`comparateur/methode.py`) et l'historique des changements de
règle, relevé dans l'historique du dépôt. Une version change quand une règle de comptage change.

## Le service des fichiers

Les pages d'édition ne portent que leur HTML et leurs données. Le CSS et le JavaScript sont écrits dans
`public/actifs/site-<empreinte>.css` et `.js` (12 caractères du SHA-256 du contenu) ; un ancien actif reste un jour après
la dernière publication qui le citait (`actifs/retires.json`), pour les pages encore en cache. Le serveur envoie les pages et les données avec `Cache-Control: public, max-age=300`, `sw.js` avec
`no-cache`, les actifs avec `public, max-age=31536000, immutable`, et l'API avec `no-store`. Chaque fichier a un
`ETag` et répond `304` à un `If-None-Match` qui correspond. Si le navigateur accepte `gzip`, le texte (HTML, CSS,
JS, JSON, SVG, manifest) de plus de 1 Ko part compressé, avec `Vary: Accept-Encoding` ; la version compressée est
gardée en mémoire (512 fichiers et 32 Mo au plus). Une page d'édition de l'essai passe de 142 Ko à 53 Ko (31 Ko à
6 Ko compressée), et les deux actifs, 89 Ko, ne se chargent qu'une fois (25 Ko compressés).

## L'application

Le site s'installe comme une application, sans magasin : `manifest.webmanifest`, icônes PNG (192, 512, 512
« maskable », `apple-touch-icon.png` en 180), et un service worker `sw.js` servi depuis la racine. Le service
worker passe toujours par le réseau d'abord : quand le réseau répond, c'est sa réponse qui est servie, jamais une
copie. La dernière copie gardée ne sert que hors ligne. La page `#/installer` explique la marche à suivre sur
iPhone, Mac, Android, Windows et Firefox, avec en tête la section de l'appareil de la personne. Les chemins de
menu y ont été relevés dans l'aide d'Apple, de Google et de Microsoft le 15/11/2026 ; ceux de Firefox n'ont pas
pu l'être (pages de Mozilla illisibles par un robot) et sont écrits avec prudence. Les icônes se refont avec
`python3 essais/icones.py`.

## Le compte et les mails (phase 2)

Allumés par les deux réglages SMTP du guichet, éteints sans eux : ni formulaire, ni page de compte, ni route
`/api/mail/` ou `/api/compte/`. Le détail du déploiement : [docs/deploiement-phase-2.md](docs/deploiement-phase-2.md).

- **Deux processus, quatre tiroirs.** La `fabrique` (`python -m comparateur fabrique`) récolte, fait l'édition et
  écrit le tiroir public, sans port ni clé d'envoi. Le `guichet` (`python -m comparateur guichet`) sert le site,
  `compte.<domaine>` et `urne.<domaine>` (tri sur l'en-tête `Host`), tient `identites.db` et envoie les mails.
  `python -m comparateur servir` fait les deux dans un processus, pour un poste de développement. Un test vérifie
  qu'aucun module du côté de la fabrique n'importe le tiroir identité, et que son processus ne le charge pas.
- **Le tiroir identité** (`comptes.py`, `identites.db`) : comptes, abonnements, sessions, codes ; `retraits` et
  `cles` créées vides pour le panel. Dates au jour, dernière visite au mois. Ni bord, ni sujet, ni lecture.
- **Le registre** (`abonnements.py`) : lettre de la semaine, alerte du matin, rubriques larges (six, trois au plus),
  et le panel, déclaré et fermé. Un type inconnu, une classe « opinion », une cible hors liste sont refusés.
  Ajouter un type ne change pas le schéma.
- **La connexion** : un code de six chiffres par mail, dix minutes, cinq essais, gardé en empreinte salée ; puis un
  cookie, un seul, `__Host-cadrages` (`Secure`, `HttpOnly`, `SameSite=Strict`, sans `Domain`), sur `compte.` seulement,
  un an. Une requête d'un autre site est refusée (JSON exigé, `Origin` et `Sec-Fetch-Site` contrôlés). 5 codes par
  heure et par IP, 3 par adresse, 20 essais de connexion par heure et par IP.
- **La page du compte** (`comparateur/compte/compte.html`, servie sur `compte.` seulement, sans mesure d'audience) :
  cases d'abonnement, et « Ce que ce site sait de vous », engendré depuis les lignes du compte.
- **La lettre sans compte** : l'encart de la page Semaine marche comme avant (double confirmation, désinscription
  en un clic, RFC 8058). Un abonné est un compte avec une ligne ; il ne se connecte jamais. Une désinscription qui
  laisse le compte vide efface l'adresse.
- **Les envois** : la fabrique écrit `public/lettre/<semaine>.json` et `public/alertes/<jour>.json` (sujets du jour et
  rubriques lues dans l'adresse des articles) ; le guichet envoie la lettre le lundi et l'alerte chaque matin, un mail
  par compte, une fois (`abonnements.dernier_envoi`).
- **La migration d'`abonnes`** : `python -m comparateur verser-abonnes` puis `oublier-abonnes` (voir le document de
  déploiement). Écrite et testée sur des données d'essai, jamais lancée sur une vraie base.
- **« Mes sujets » et les flux** : suivre un sujet le garde dans le navigateur (`localStorage`, clé
  `cadrages.sujets`) ; l'accueil compare la liste à l'édition. Chaque sujet a un flux Atom,
  `/flux/sujets/<id>.xml`, le même pour tous. Pas de suivi par mail (décision 3).
- **Essai** : `python -m comparateur mail-essai <adresse>` envoie la synthèse de la dernière semaine écrite par la
  fabrique à cette seule adresse, sans l'inscrire.

## Sept bords, trois côtés

Ce site ne classe aucun média. Le bord d'un média est sa **bande FrIdéo** : sept bandes, avec les noms et les
seuils publiés par le French News Lab (extrême gauche, gauche, centre gauche, centre, centre droit, droite,
extrême droite ; seuils −1,5, −0,75, −0,25, +0,25, +0,75, +1,5). `base.bord(score)` applique ces seuils, et un
test vérifie que le résultat est la bande publiée par FrIdéo pour chacun des trente médias. Tous les comptages
du site se font sur ces sept bords : cartes de l'accueil, page d'un sujet, silences, semaine, mois.

Le seul regroupement fait par le site est celui des **trois côtés** (`base.COTE`) : les trois bandes de gauche,
le centre, les trois bandes de droite. Il sert aux textes d'angle écrits par le modèle (`analyse.g/c/d`) et aux
silences. Une édition gardée avant le passage aux sept bandes est réétiquetée à l'affichage, d'après le score.

## Les silences

Un **côté** est silencieux sur un sujet quand il n'a aucun titre, que le sujet est repris par
`syntheses.MIN_MEDIAS` médias ou plus (4) et que ce côté a au moins un média lu. Trois côtés : les trois bandes de gauche, le centre, les trois bandes de droite. Les comptages et les barres restent sur sept bords,
mais le silence se juge sur trois côtés : sur cinq bords, à l'époque où le site en comptait cinq, 21 sujets sur 23 avaient un absent dans l'édition du
15/11/2026, contre 7 sur trois côtés. Un repère présent partout ne dit plus rien. Tout est compté par formule,
sans modèle. La vue `#/silences` liste les silences de l'édition affichée, côté par côté, les sujets les plus
couverts d'abord ; dans les synthèses, le silence d'un côté est compté pour chacun de ses bords lus.

## Suivre un sujet

Un sujet garde son identifiant (`s45`) d'une édition à l'autre. À chaque écriture des pages,
`publier.ecrire_pages` calcule sa présence dans toutes les éditions gardées (`syntheses.suivi` : jour, titres,
médias, répartition sur sept bords, côtés silencieux) et l'injecte dans la page (`suivi`). Quand un sujet figure
dans plus d'une édition, sa page montre une frise jour par jour ; chaque jour mène à
`/editions/<jour>.html#/sujet/<id>`. Rien n'est ajouté aux éditions gardées en base.

## Le sport et la culture sont écartés

`fabrique.rubrique` lit la rubrique d'un article dans son adresse, sans modèle : un segment entier du chemin
(`/sport/`, `/sports/`, `/culture/`, `/loisirs/`, `/people/`, `/cinema/`, `/musique/`, `/tele/`...) ou un
sous-domaine (`sport24.lefigaro.fr`). Le dernier segment, qui porte le titre, n'est pas lu. La rubrique est
gardée dans la colonne `articles.rubrique` ; une base existante reçoit la colonne au démarrage (`ALTER TABLE`,
puis lecture des adresses déjà en base), sans rien perdre.

Les articles des rubriques écartées ne sont ni proposés au regroupement ni comptés dans les sujets, ni montrés
parmi les titres sans jumeau. Ils restent en base. La liste se règle par `COMPARATEUR_RUBRIQUES_ECARTEES`
(défaut `sport,culture` ; `aucune` pour ne rien écarter). Rubriques reconnues : sport, culture, politique,
international, economie, societe, faits-divers, sciences, environnement, opinions. Un article dont l'adresse
ne dit rien de sa rubrique n'est pas écarté.

## La semaine et le mois

`syntheses.py` met bout à bout les éditions gardées : les sujets les plus couverts, ce que chacun des sept bords
a traité et laissé de côté, la présence de chaque journal. Ce sont des comptages, sans modèle. Un sujet qui dure garde
le même identifiant d'un jour à l'autre, ce qui permet de le suivre ; deux sujets ouverts séparément sur le
même fait sont comptés deux fois. Les synthèses sont recalculées à chaque publication et s'ouvrent depuis
l'accueil (« la semaine », « le mois »).

## L'index et « Situer un article »

`public/index.json` est un fichier unique, à une seule adresse, sans paramètre : les mêmes octets pour tous
(`comparateur/index.py`, écrit par `publier.ecrire_pages`, atomiquement). Il se construit à partir des éditions
gardées des sept derniers jours, jamais de la base. Format `v: 1` : `genere_le` (le jour de la dernière édition),
`methode`, `classement`, `medias` (domaine, puis nom, statut, bande, score, intervalle ; un média non classé n'a
que son nom et son statut), `sujets` (titre, jour, titres par bande, côtés silencieux, page) et `articles` (clé,
puis identifiant de sujet). Le domaine d'un média est déduit des adresses de ses articles ; un domaine vu chez
deux médias n'est pas retenu. Un champ facultatif `domaines` d'une entrée de `medias.json` s'ajouterait aux
domaines vus.

La clé d'un article est les 16 premiers caractères hexadécimaux du SHA-256 de son adresse normalisée. La règle
de normalisation est écrite deux fois, en Python (`index.normaliser`) et en JavaScript (`js/adresse.js`), et
essayée avec les mêmes vecteurs (`tests/vecteurs-adresses.json`, calculés par Python) :

1. les espaces des bords sont retirés ;
2. le schéma doit être `http` ou `https`, sinon rien ; il est ensuite oublié ;
3. l'hôte est mis en minuscules, sans point final, sans port, sans identifiants ;
4. un préfixe d'usage est retiré une fois en tête d'hôte (`www.`, `m.`, `mobile.`, `amp.`), si l'hôte garde au
   moins deux étiquettes ;
5. le chemin est gardé tel quel (casse et `%xx` conservés) ; vide, il devient `/` ; une barre finale est retirée,
   sauf pour `/` ;
6. les paramètres (`?…`) et le fragment (`#…`) sont retirés.

Le résultat est l'hôte suivi du chemin. Une adresse sans hôte, ou dont l'hôte est une adresse IPv6, n'a pas de
forme normalisée.

La vue `#/situer` télécharge `/index.json` une fois, puis cherche sur l'appareil : l'adresse collée n'est envoyée
à personne. Elle dit le média (bande FrIdéo ou « non classé », ou « ce site ne lit pas ce média ») et, si
l'article est dans l'index, le sujet, la répartition sur sept bords, les côtés silencieux et le lien vers la page
du sujet. Un test refuse tout autre appel réseau dans la vue. Le contrat : `docs/cadrage-long-terme.md`, 6.3.

## L'API des votes

| Route | Corps | Réponse |
|---|---|---|
| `POST /api/inscription` | `{code, bord}` (bord déclaré du votant, de −2 à +2) | `201 {jeton}` ; le code est à usage unique |
| `GET /api/lot` | en-tête `Authorization: Bearer <jeton>` | `{lot: {id, titres[10]} \| null, restants}` |
| `POST /api/avis-aveugle` | `{lot, note}` (de −2 à +2) | `201` ; `409` si le lot est déjà jugé |
| `POST /api/avis-note` | `{media, accord}` | `201` ; simple alerte, ne change aucune note |
| `GET /api/resultats` | | note à l'aveugle par média, effectifs par bord, statut `indicatif` ou `publiable` |
| `GET /sante` | | `{ok, derniere_publication}` |
| `POST /api/mail/inscription` | `{adresse}` | `202 {ok}`, toujours ; seulement si le mail est réglé |
| `POST /api/mail/confirmation` | `{jeton}` | `200` ; `404` si le lien est inconnu ou expiré |
| `POST /api/mail/desinscription` | `{jeton}`, ou `?jeton=` en un clic (RFC 8058) | `200`, toujours |
| `POST /api/compte/code` (sur `compte.`) | `{adresse}` | `202`, toujours |
| `POST /api/compte/connexion` | `{adresse, code}` | `200` et le cookie ; `403` si le code est faux ou expiré |
| `GET /api/compte` | cookie | `{sait, registre}` ; `401` sans session |
| `POST /api/compte/abonnement` | `{type, cible, actif}` | `{sait, registre}` ; `400` si le registre refuse |
| `POST /api/compte/deconnexion`, `/suppression` | | `200`, le cookie effacé |

**Un pseudonyme, pas un anonymat.** La base garde l'empreinte du jeton, le bord déclaré et les avis, sans nom ni
adresse ; les dates sont arrondies au jour. Le jeton relie entre eux les avis d'un même votant : c'est un
pseudonyme. Et l'éditeur sait à qui il a remis chaque code, tandis que `invitations.utilisee_le` et `votants.cree`
portent le même jour : avec une ou deux inscriptions par jour, le rapprochement se fait à la main. Les pages le
disent. Le journal du serveur n'écrit pas l'adresse du visiteur. La phase 3 de `docs/cadrage-long-terme.md`
remplace ce vote par la carte de votant.

**Comptage.** Moyenne par bord déclaré (gauche, centre, droite), puis moyenne des bords : un bord nombreux ne
pèse pas plus qu'un autre. `publiable` seulement si chaque bord atteint `COMPARATEUR_MIN_PAR_BORD` votants.

**Abus.** Un vote par lot et par jeton ; 10 essais d'inscription par heure et par adresse ; 300 requêtes d'API par
minute et par adresse (les fichiers publics ne sont pas limités) ; corps limité à 4 Ko.

## Garde-fous de la fabrique

- Un modèle ne note jamais un média : les notes viennent de `medias.json` (FrIdéo, CC BY 4.0) et, plus tard, des votes.
- Les scores et leurs intervalles de confiance viennent du jeu de données officiel FrIdéo (data.gouv.fr). Une
  nouvelle version du classement s'ajoute en base sans effacer l'ancienne.
- À l'aveugle, la typographie maison est effacée (guillemets, apostrophes, tirets, milliers) : le French News Lab
  a montré qu'on reconnaît un journal à ces détails plus qu'à ses mots.
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
- **Quatre journaux absents de la récolte** : Le Figaro, Marianne, Le Point et Les Echos refusent le lecteur.
  Marianne, Le Point et Les Echos répondent 403 à un lecteur RSS déclaré (14/11/2026). Ce site ne contourne pas
  un refus : ils restent absents, et les pages le disent (« flux illisibles »). Ils ne comptent ni comme présents
  ni comme silencieux.
- Un titre resté seul n'est pas reproposé aux sujets ouverts après lui.
- **Rubriques lues dans l'adresse seulement.** Un article de sport dont l'adresse ne porte pas de rubrique passe.
  Les lots à l'aveugle ne tiennent pas compte des rubriques.
- **Les côtés n'ont pas le même nombre de journaux** : un côté de sept journaux se tait plus souvent qu'un côté de douze. Voir « Les silences ».

## Essais

`essais/coloration.py` mesure la stabilité de l'analyse : second tirage, consigne colorée à gauche ou à droite,
autre modèle, noms des médias masqués, bords échangés. Sur 20 sujets (14/11/2026), aucune de ces variantes ne
change plus la description qu'un simple second tirage.

`essais/rendu.js` ouvre chaque vue de chaque édition dans un navigateur (375 px et 1280 px, clair et sombre) et
échoue sur une erreur de console, un défilement horizontal ou un « undefined » à l'écran.

`essais/accessibilite.js` est la mesure d'accessibilité : titres, contrastes, noms des liens, boutons et champs,
contour de focus, sur chaque vue et sur les pages à part. Écrite à la main, sans bibliothèque d'audit. Un test
(`Assise`) tient, sans navigateur, les contrastes des couples de couleurs qu'il liste (texte et fond, focus). Mode d'emploi et
règles du site : [DOCTRINE.md](DOCTRINE.md).

`essais/editions_essai.py` fabrique quatre éditions factices (dont une au format d'avant les rubriques et le
suivi) et écrit le site, sans réseau ni modèle, pour voir le rendu en local. Il efface les éditions de la base
visée : `COMPARATEUR_DONNEES=/tmp/essai python3 essais/editions_essai.py`, puis `python3 -m comparateur servir`
avec la même variable.

## Sources et remerciements

- **L'idée** de comparer la couverture par bord et de signaler les angles morts vient de
  [Ground News](https://ground.news/rating-system).
- **Le classement des médias** est FrIdéo v1.0, du French News Lab (<https://frenchnewslab.org/en/medias>), sous
  licence CC BY 4.0. Les scores de `comparateur/medias.json` en sont relevés. Les sept bandes, leurs noms et leurs
  seuils sont ceux de FrIdéo. Ce site ne classe aucun média ; il regroupe seulement les bandes en trois côtés.
- **Le jugement à l'aveugle** par un panel équilibré s'inspire de la méthode publiée par
  [AllSides](https://www.allsides.com/about/media-bias-rating-methods).

Ce projet n'est affilié à aucun de ces organismes.

## Licence

Code sous [AGPL-3.0](LICENSE).
