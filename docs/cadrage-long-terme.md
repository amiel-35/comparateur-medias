# Cadrage de long terme

Cadrage du 16/11/2026. Rien n'est construit, rien n'est décidé ici : ce fichier recommande. Sa commande est
`docs/brief-long-terme.md`, section 9. Il reprend `docs/cadrage-panel-comptes.md` (« le premier cadrage ») sans
refaire sa recherche, et dit ce qui en change.

C'est une feuille de route : des états cibles par phase, des déclencheurs, des coutures à poser tôt. Ni durées,
ni tâches. Les sources sont en section 13, avec ce qui a été lu et ce qui ne l'a pas été.

Décision d'Amiel prise en compte (16/11/2026) : aucune monétisation prévue ; l'affichage reste le titre, le nom
du média et le lien. Le droit voisin et le modèle économique ne sont donc le prérequis d'aucune phase. Ils se
rouvrent à un déclencheur (section 8.5).

### Décisions d'Amiel du 16/11/2026, sur les cinq points prioritaires

Elles priment sur les recommandations du document là où elles diffèrent.

| # | Point | Décision |
|---|---|---|
| 1 | Domaine (question 8, 5.2) | **Pas de domaine payant pour l'instant.** Le site reste sur un sous-domaine d'`inflexion.me`, déjà détenu. Les noms d'hôte séparés s'y construisent sans coût (`compte.compare-media.inflexion.me`, `urne.compare-media.inflexion.me`). La question se rouvre avant l'ouverture des comptes (phase 2) : c'est le dernier moment où changer ne coûte rien aux lecteurs. |
| 2 | Collaborateurs (question 2, 5.4) | **Peut-être un jour.** La règle de la grille 5.4 s'applique telle quelle : dès qu'une seconde personne doit avoir accès au serveur, l'urne part sur une autre machine, tenue par un autre administrateur, avant son arrivée. |
| 3 | Alertes par sujet (question 6, 3.5) | **« Mes sujets » sur l'appareil et flux par sujet, en phase 2.** Pas de suivi par mail ; il ne s'envisage que sur demande répétée de lecteurs. |
| 4 | Prototype (section 9) | **Périmètre validé** : les six preuves (signature aveugle sans dépendance, séparation tenue par des tests, parcours sans jargon, compte générique à deux types plus un type factice, noms d'hôte séparés essayés depuis l'application installée sur iPhone, une urne par questionnaire scellée à la clôture). Branche `proto/panel-comptes`, données d'essai, rien de déployé. |
| 5 | Classement (7.1) | **FrIdéo seule source, statut « non classé » pour les autres médias.** La piste d'une méthode de classement propre est abandonnée. La lecture à l'aveugle du panel s'affiche à côté, jamais fondue. |

## 1. Ce que ce cadrage avance

1. **Quatre tiroirs, pas trois.** Public, identité, urne, appareil. L'urne ne partage plus son fichier avec les
   données publiques.
2. **Le compte générique tient**, à une correction près : ce qui se classe n'est pas le type d'abonnement, c'est
   le couple (type, cible), et le cumul.
3. **Le bon découpage n'est pas « public, authentification, panel ».** C'est public, identité, urne. Et la
   première coupe utile est ailleurs : sortir la fabrique du processus qui répond au public.
4. **Trois noms d'hôte dès l'ouverture des comptes, un seul processus.** Le découpage de la phase 6 devient un
   réglage de proxy.
5. **Le domaine se tranche en phase 0.** Ce que l'appareil garde est attaché au nom du site.
6. **L'extension ne reçoit et n'envoie aucune adresse.** Avant elle, une fonction sans installation : coller
   l'adresse d'un article sur le site.
7. **Élargir sans classer.** Un média hors FrIdéo entre comme « non classé ». La gouvernance ne bloque plus la
   phase 1.
8. **Le droit de réponse existe déjà dans la loi.** Il s'organise, il ne s'invente pas.

## 2. L'architecture cible

### 2.1 Quatre tiroirs

| Tiroir | Contient | Ne contient jamais | Qui l'ouvre |
|---|---|---|---|
| **Public** (`comparateur.db`, `public/`) | médias, classements versionnés, articles, sujets, éditions, pages, exports | une adresse, une session, une réponse | la fabrique écrit ; tout le monde lit |
| **Identité** (`identites.db`) | comptes, abonnements, sessions, codes, retraits de bulletin, clés des questionnaires ouverts | bord, réponse, média suivi, lecture, date plus fine que le jour | le guichet seul |
| **Urne** (`urnes/<questionnaire>.db`) | une ligne par réponse, sous l'empreinte du bulletin | adresse, compte, session, IP, heure, rang | l'urne seule |
| **Appareil** (stockage du navigateur, de l'extension) | bord, bulletins, reçus, journaux suivis ou masqués, sujets suivis, thème | rien qui doive survivre à la perte de l'appareil | la personne |

Le premier cadrage faisait de `comparateur.db` l'urne. C'est le point à corriger : ce fichier porte les données
publiques, celles qu'un chercheur demandera, qu'un export copiera, que la fabrique réécrit toute la journée.
Une urne n'a rien à y faire. Une urne par questionnaire, dans son propre fichier : la clôture le scelle,
l'effacement à douze mois est la suppression d'un fichier, et aucune sauvegarde du tiroir public n'emporte une
réponse.

### 2.2 Ce qui traverse

```
                 fabrique ──écrit──▶ PUBLIC ──lu par──▶ site, extension, flux, chercheurs
                                        │
              (la synthèse de la semaine, déjà calculée, sans adresse)
                                        ▼
  personne ──adresse, code──▶ IDENTITÉ (guichet) ──mails──▶ prestataire d'envoi
      │                          │
      │  bulletin aveuglé ──────▶│ signe sans voir
      │◀───── signature ─────────│
      │
      └── bulletin, signature, bord, réponses ──▶ URNE        (sans session, sans cookie)
                                                   │
                                  comptages par bord, après clôture ──▶ PUBLIC
```

Cinq passages, pas un de plus. Chacun est tenu par un test.

| Passage | Ce qui passe | Ce qui ne passe jamais |
|---|---|---|
| Public → identité | la synthèse à envoyer, la liste fermée des cibles d'abonnement | rien dans l'autre sens : la fabrique n'ouvre pas `identites.db` |
| Appareil → identité | adresse, code, cases d'abonnement, bulletin aveuglé | bord, médias suivis, sujets suivis, adresse d'un article |
| Appareil → urne | bulletin, signature, bord, réponses | cookie, en-tête d'identité |
| Urne → public | effectifs et moyennes par bord, au-dessus du seuil, après clôture | une ligne brute |
| Public → appareil | pages, index, flux | rien de personnalisé : la même réponse pour tous |

La dernière ligne est la plus féconde. Tant que le tiroir public répond la même chose à tout le monde, il se
met en cache, se copie, se donne à un tiers, sans rien dire de personne.

### 2.3 Trois horizons

| Horizon | Phases | Forme |
|---|---|---|
| **H1. Un site qui dit vrai et qui tient** | 0, 1 | Un conteneur. Le tiroir public est le seul qui grossit. Un export et un index publics. Aucun compte nouveau. |
| **H2. Des services autour du noyau** | 2, 3, 4 | Trois noms d'hôte, deux processus (fabrique, guichet), quatre tiroirs. L'extension lit le tiroir public. |
| **H3. Une institution** | 5, 6 | Une structure, des tiers (chercheurs, rédactions), l'urne chez un autre administrateur si un déclencheur le demande. |

## 3. Le compte générique

### 3.1 La piste tient, avec trois corrections

La piste : un compte stable, une liste d'abonnements typés, un nouveau service = un nouveau type sans toucher au
schéma, chaque type classé selon ce qu'il révèle. Vérifiée sur les services nommés par le brief, elle tient.

**Correction 1 : on classe le couple (type, cible), pas le type.** « Alerte sur un sujet » ne dit rien tant
qu'on ne sait pas lequel. La donnée sensible est la cible. D'où une règle de structure : une cible est vide, ou
tirée d'une liste fermée et large écrite dans le code. Jamais un texte libre. Jamais un média, un bord, un
parti, une personne.

**Correction 2 : on classe aussi le cumul.** Un sujet suivi dit peu. Dix sujets suivis dessinent quelqu'un. La
règle « un peu, au cas par cas » ne suffit pas : il faut un plafond par compte et une extinction.

**Correction 3 : on ne classe pas d'après le thème.** Le brief suggère qu'un sujet « retraites » serait peu
sensible et un sujet « immigration » davantage. C'est un jugement éditorial sur les sujets, à refaire chaque
jour, que personne ne peut tenir et qu'aucun modèle ne doit faire. Le classement se fait sur la forme de la
cible, pas sur son contenu.

### 3.2 Le test d'entrée d'un type

Trois questions, dans l'ordre. La première réponse « oui » arrête.

1. La cible est-elle libre, ou désigne-t-elle un média, un bord, un côté, un parti, une personne, un sujet
   précis ? **Oui : sur l'appareil.**
2. Si la liste des abonnés à cette cible fuyait avec son intitulé, apprendrait-on le bord probable de
   quelqu'un ? **Oui : sur l'appareil.**
3. Sinon : **dans le compte**, sous quatre bornes. Cible prise dans une liste fermée. Plafond par compte.
   Sortie en un clic. Ligne visible dans « Ce que ce site sait de vous ».

### 3.3 Le classement

| Service | Cible | Ce qu'il révèle | Où |
|---|---|---|---|
| Synthèse de la semaine | aucune | rien | compte |
| Alerte d'édition (« l'édition du jour est parue ») | aucune | rien | compte |
| Panel (accepter d'être recontacté) | aucune | un peu : un intérêt pour la question, pas un bord | compte, consentement |
| Alerte par rubrique | liste fermée des rubriques larges du site | un peu | compte, trois au plus |
| Suivi d'un sujet | identifiant de sujet | peu à l'unité, une opinion par cumul | **appareil** d'abord (3.5) |
| Silences d'un côté | côté | une opinion | appareil |
| Journaux suivis ou masqués | média | une opinion (C-184/20, C-252/21) | appareil |
| Bord déclaré | aucune | une opinion | appareil ; voyage avec la réponse, jamais avec le compte |
| Adresse d'un article lu (extension) | adresse | une opinion par cumul | nulle part hors de l'appareil |
| Accès aux données (chercheur, rédaction) | organisation | rien sur une personne | pas un compte : une clé d'organisation, phase 5 |

### 3.4 Le schéma

```
comptes      (id, adresse UNIQUE, cree_jour, vu_mois)
abonnements  (compte, type, cible, etat, cree_jour, fin_jour, dernier_envoi, sortie,
              UNIQUE (compte, type, cible))
sessions, codes, retraits, cles          comme dans le premier cadrage
```

Les types ne sont pas en base. Ils vivent dans un registre du code (`abonnements.py`) : nom, classe, liste des
cibles admises, plafond, base légale, phrase d'écran. Un nouveau service est une entrée du registre.

- `sortie` : le jeton de désinscription en un clic, propre à chaque abonnement (RFC 8058, déjà en place).
- `fin_jour` : un abonnement peut s'éteindre seul.
- Aucune colonne libre. Pas de JSON, pas de « réglages ». C'est par là que des préférences reviendraient.

**Ce que le schéma change pour le lecteur : rien.** Un abonné à la lettre est un compte avec une ligne. Il ne se
connecte jamais ; il se désinscrit par le lien du mail, comme aujourd'hui. Le compte n'apparaît à l'écran que le
jour où quelqu'un veut gérer deux choses. Le brief demande « pas de compte à gérer » : c'est tenu.

**Les règles, chacune avec son test** (elles s'ajoutent aux quinze du premier cadrage) :

16. *Un type inconnu du registre est refusé.* Un type de classe « opinion » ne peut pas être enregistré.
17. *Une cible hors de la liste fermée de son type est refusée.* Test : un mot libre, un nom de média.
18. *Ajouter un type ne change pas le schéma.* Test : un type factice ajouté dans le test, parcours complet,
    `PRAGMA table_info` identique avant et après.
19. *L'écran « Ce que ce site sait de vous » est engendré depuis les lignes du compte.* Test : ce que l'écran
    montre est exactement ce que la base contient. La promesse ne peut plus dériver du code.
20. *La fabrique n'ouvre pas le tiroir identité.* Test : aucun import de `comptes` ou d'`abonnements` dans
    `fabrique.py`, `llm.py`, `publier.py`.

**Durée de vie.** Le premier cadrage efface un compte « après 24 mois sans connexion ». Un lecteur fidèle de la
lettre ne se connecte jamais : il serait effacé. Règle corrigée : un compte vit tant qu'un abonnement est actif
et que les mails partent sans rejet. Sans abonnement actif, effacement après 24 mois. Pas de mail de relance :
une ligne en pied de lettre, une fois l'an, suffit (« Vous recevez ce mail depuis… Se désinscrire »).

**Changer d'adresse** est le seul parcours nouveau qu'un compte durable exige : un code à l'ancienne adresse,
un code à la nouvelle. L'identifiant interne ne change pas.

### 3.5 Les alertes par sujet, sans que le serveur le sache

Trois voies, de la plus sobre à la moins sobre.

- **« Mes sujets », sur l'appareil.** Le site garde la liste dans le navigateur. À l'ouverture, la page compare
  cette liste à l'édition du jour, qu'elle a déjà. Rien ne part. C'est une alerte qu'on vient chercher.
- **Un flux par sujet et par rubrique.** `/<…>/s45.atom`. Le lecteur de flux de la personne fait le travail. Le
  site consomme des flux ; il peut en produire. Le serveur voit une lecture du tiroir public, sans compte.
- **Le suivi court, par mail.** Seulement si la question 6 du brief reçoit un oui. L'abonnement s'éteint quand
  le sujet n'a plus de titres, trois au plus par compte, effacé à l'extinction. Le profil ne s'épaissit pas.
  Il entre dans l'AIPD.

Recommandation : les deux premières en phase 2, la troisième seulement sur demande répétée de lecteurs.

## 4. Les phases

Pour chacune : l'état cible, ce qui doit déjà être posé pour la suivante, ce qui reste absent exprès.

### Phase 0. Assise

- **État cible.** Un conteneur, une base. Le README et les mentions disent ce que le code fait. Les journaux du
  proxy sont vérifiés et coupés sur `/api/`. Le suivi des clics de Brevo est vérifié. La page de méthode est le
  document de référence, datée. Une mesure d'accessibilité existe. Le vote à l'aveugle reste ouvert à son
  cercle, tel quel, avec une phrase corrigée : « pseudonyme », pas « aucun lien ».
- **Posé pour la suite.** Le domaine définitif (question 8, voir 5.2). Le nom de la marque dans les mails et le
  manifeste. La règle écrite : un export n'est jamais une copie de `comparateur.db`.
- **Absent exprès.** Toute fonction nouvelle. Tout compte. Toute question de droit voisin.

### Phase 1. Le public solide

- **État cible.** Toujours un conteneur. Le tiroir public grossit : plus de médias, dont des « non classés »
  (section 7), un regroupement meilleur. Trois sorties publiques, identiques pour tous : les pages, un export
  daté de chaque édition, un **index** (6.3). Une fonction « situer un article » : on colle une adresse, la page
  répond avec l'index qu'elle a déjà, rien ne part. Cache, compression, code hors des pages : l'ordre de
  `DOCTRINE.md` reste le bon.
- **Posé pour la suite.** L'index et sa règle de normalisation des adresses, avec des vecteurs d'essai : c'est
  le contrat de l'extension, écrit trois phases avant elle. La version de la méthode et du classement inscrite
  dans chaque édition gardée. Les statuts « classé » et « non classé ». La règle : pas de cache tiers devant un
  nom d'hôte qui porte `/api/` ; si un cache arrive ici, les noms d'hôte de la phase 2 arrivent avec lui.
- **Absent exprès.** PostgreSQL, ASGI. Un classement maison. Un compte. Une personnalisation côté serveur.

### Phase 2. Le compte durable

- **État cible.** Trois noms d'hôte : le site, `compte.`, `urne.` (ce dernier muet jusqu'à la phase 3). Deux
  processus du même dépôt : la **fabrique**, qui n'écoute aucun port et tient la clé des modèles ; le
  **guichet**, qui répond au public et tient la clé d'envoi. `identites.db` existe, avec `comptes` et
  `abonnements`. `abonnes` y est versée. Types ouverts : lettre, alerte d'édition, rubriques. « Mes sujets » et
  les flux côté public. Un cookie, un seul, sur `compte.`.
- **Posé pour la suite.** Le type « panel » déjà déclaré au registre, fermé. Les tables `retraits` et `cles`
  prévues. Le partage du travail : la fabrique calcule la synthèse et l'écrit dans le tiroir public ; le
  guichet l'envoie. Aujourd'hui `lettre.py` fait les deux depuis la boucle de la fabrique : c'est la seule
  vraie reprise de code de cette phase.
- **Absent exprès.** Préférences sur le serveur. Mot de passe, passkey, connexion par un tiers. Push. Liste des
  appareils connectés. Tout abonnement dont la cible n'est pas dans une liste fermée.

### Phase 3. Le panel

- **État cible.** `urne.` répond. Une urne par questionnaire. La signature aveugle entre guichet et urne, comme
  dans le premier cadrage, sans changement. AIPD faite. Cercle invité d'abord. Le vote à l'aveugle passe à la
  carte de votant et quitte `comparateur.db` : à partir de là, le tiroir public ne contient plus rien de
  personnel.
- **Posé pour la suite.** Les résultats publiés comme une mesure à part, versionnée, dans le tiroir public, à
  côté du classement et jamais fondue en lui. L'urne ne lit rien d'autre que ses fichiers et les clés
  publiques : elle est déjà déplaçable.
- **Absent exprès.** Suivi d'un répondant d'un questionnaire à l'autre. Texte libre. Ouverture à tout compte
  avant un premier questionnaire en cercle. Tout moyen payant contre les comptes multiples.

### Phase 4. L'extension

- **État cible.** Une extension Chrome et Firefox qui ne parle qu'au tiroir public : elle télécharge l'index à
  heure fixe et répond sur l'appareil. Elle ne connaît ni le compte ni l'urne. Sur téléphone, où les extensions
  sont rares, la fonction « situer un article » du site tient le même rôle.
- **Posé pour la suite.** Rien que la phase 1 n'ait déjà posé : c'est le signe que la couture est bonne.
- **Absent exprès.** Connexion au compte. Envoi d'adresse. Bandeau dans la page du journal. Lecture des réseaux
  sociaux. Safari.

### Phase 5. L'ouverture

- **État cible.** Des jeux de données datés et citables, tirés du tiroir public. Des clés d'organisation pour
  un accès régulier, hors des comptes de personnes. Un registre public des contestations. Une structure
  (section 8.4). Un second pays, s'il vient, est une seconde fabrique et un second tiroir public : rien n'est
  partagé que le code.
- **Posé pour la suite.** La méthode refaisable par un tiers. Les identifiants de médias et de sujets stables.
- **Absent exprès.** Comptes d'élèves. Contributions publiques. Un partenariat qui touche au classement.

### Phase 6. Les services séparés

- **État cible.** Seulement ce qu'un déclencheur exige (5.4). La coupe qui compte : l'urne sur une autre
  machine, tenue par une autre personne ou une autre entité. C'est la séparation « dans l'espace » de la
  RFC 9576, la seule qui réponde à l'administrateur curieux.
- **Absent exprès.** Un service « authentification » commun à d'autres sites. Il relierait des comptes entre
  eux, ce que tout le reste s'emploie à empêcher.

## 5. Le découpage

### 5.1 La position

Le brief propose « site public, authentification, panel ». Deux objections.

- **Le panel n'est pas un service, il est à cheval.** Le guichet du panel (qui est membre, qui a retiré un
  bulletin, la signature) a besoin de l'identité. L'urne ne doit jamais la voir. La frontière passe au milieu
  du panel. Les bons blocs sont : **public, identité (avec le guichet), urne**.
- **L'authentification seule n'est pas un service.** À cette taille, elle se réduit à un code par mail et une
  session. L'isoler ajoute un saut et un secret partagé, sans rien protéger de plus.

Et une coupe que le brief ne nomme pas vaut plus que les autres : **la fabrique hors du processus qui répond**.
Aujourd'hui un seul processus lit les flux de trente sites, appelle les modèles, tient la clé d'API, et répond
aux visiteurs. Le jour où ce processus ouvre aussi `identites.db`, une faille dans la lecture d'un flux touche
les adresses. Deux services du même fichier compose, la même image, deux commandes : la fabrique écrit
`public/`, le guichet le lit.

### 5.2 Les coutures à poser, et quand

| Couture | Quoi | Quand |
|---|---|---|
| **Domaine** | Un domaine propre au site, hors `inflexion.me`. | Phase 0 |
| **Noms d'hôte** | `<domaine>`, `compte.<domaine>`, `urne.<domaine>`, tous vers le même conteneur ; le serveur trie sur l'en-tête `Host`. | Entrée de la phase 2, ou plus tôt si un cache arrive |
| **Chemins** | `/api/compte/…` et `/api/urne/…`, comme dans le premier cadrage. Ils restent valables si l'on revient à un seul hôte. | Phase 2 |
| **Cookie** | Sans attribut `Domain`, préfixe `__Host-`, `HttpOnly`, `Secure`, `SameSite=Strict`. | Phase 2 |
| **Fichiers** | `comparateur.db` (public), `identites.db`, `urnes/<id>.db`. Trois sauvegardes distinctes ; une urne n'est sauvegardée qu'à sa clôture. | Phases 2 et 3 |
| **Modules** | `comptes.py`, `abonnements.py` (registre), `signature.py`, `urne.py`. Aucun n'importe l'autre côté ; `ATTACH` interdit. | Phases 2 et 3 |
| **Processus** | `fabrique` et `guichet`, deux services du compose. | Entrée de la phase 2 |
| **Sorties publiques** | Pages, export, index, flux : mêmes octets pour tous, aucun paramètre. | Phase 1 |

**Pourquoi le domaine d'abord.** Le navigateur attache à l'origine tout ce que l'appareil garde : bord,
bulletins, reçus, journaux suivis, sujets suivis, l'application installée. Changer de domaine après la phase 2
efface tout cela chez chaque lecteur, sans recours, puisque rien n'est sur le serveur. S'y ajoutent les liens
cités, les flux, l'expéditeur des mails, la fiche de l'extension. Et la page des mentions dit que le site
« n'est pas une activité d'Inflexion », sous un nom en `inflexion.me` : c'est une phrase à ne pas laisser
vieillir. Le brief range le nom parmi les choses à ne pas faire trop tôt. Position inverse ici : c'est la
décision la moins chère aujourd'hui et la plus chère demain.

**Pourquoi des noms d'hôte plutôt qu'un chemin.** Le premier cadrage limite le cookie au chemin
`/api/compte`. C'est une précaution que le navigateur n'impose qu'à l'envoi. Trois gains à passer au nom
d'hôte :

- Le cookie posé sans attribut `Domain` n'est renvoyé qu'à l'hôte qui l'a posé, pas aux sous-domaines (MDN, lu).
  L'urne ne peut pas le recevoir, par construction et non par un test.
- Une page publique affiche des titres venus de trente sites et des textes écrits par un modèle. Un défaut
  d'échappement y reste possible. Sur une autre origine, il ne peut ni lire le stockage du compte, ni appeler
  le guichet avec la session.
- Le cache, les journaux, la mesure d'audience se règlent par hôte. Le site public peut passer derrière un
  cache tiers sans que ce tiers voie un retrait ou un dépôt.

Le prix : les écrans du compte et du panel vivent sur `compte.`, et leur stockage (bord, bulletins, reçus) aussi.
Depuis l'application installée sur iPhone, l'ouverture d'un autre hôte et la tenue de sa session sont **non
vérifiées** : à prouver dans le prototype. En cas d'échec, repli sur un seul hôte et les chemins, sans autre
changement.

### 5.3 L'ordre des coupes

| | Coupe | Déclencheur | Coût |
|---|---|---|---|
| C1 | Trois noms d'hôte, un processus | ouverture des comptes, ou premier cache tiers | réglage du proxy, tri sur `Host` |
| C2 | Fabrique et guichet en deux processus | ouverture des comptes | deux services du compose |
| C3 | Site public derrière un cache | la charge (DOCTRINE, point 1) | aucun code, si C1 est faite |
| C4 | Urne sur une autre machine, autre administrateur | grille 5.4 | une machine, une convention avec un tiers |
| C5 | Identité sur PostgreSQL, guichet en plusieurs copies | grille 5.4 | réécriture de l'accès aux données d'un seul tiroir |

C1 et C2 ne sont pas la phase 6. Elles appartiennent à la phase 2 : elles coûtent peu et donnent l'essentiel
du gain de sécurité que le brief attend de la phase 6 (une faille du public ne touche pas l'identité). La
phase 6 proprement dite, ce sont C4 et C5.

### 5.4 La grille de la phase 6

Par défaut : ne pas découper. Les seuils chiffrés sont des conventions proposées, pas des normes.

| Question | Mesure | Seuil | Coupe |
|---|---|---|---|
| Une seconde personne a-t-elle accès au serveur ? | oui ou non | dès la première | C4, avant qu'elle n'arrive |
| L'AIPD, ou un partenaire, juge-t-il insuffisant qu'un seul opérateur tienne guichet et urne ? | conclusion écrite | une seule suffit | C4 |
| Le panel est-il ouvert à tout compte ? | oui ou non | à l'ouverture | C4 recommandée, sinon le dire dans la limite affichée |
| Le guichet sature-t-il ? | part des réponses 429 ou 5xx sur `/api/`, délai d'arrivée des codes | plus de 1 % sur une semaine | C5 |
| Plusieurs personnes travaillent-elles sur des parties différentes ? | oui ou non | deux contributeurs réguliers | dépôts ou déploiements séparés, le long des modules |
| Le site public sature-t-il ? | — | — | jamais une coupe : c'est C3, un cache |

Une ligne à garder en tête : avec un seul administrateur et une seule machine, séparer des services ne protège
pas de l'administrateur. La réponse à la question 2 du brief décide donc de presque toute la phase 6.

**De « projet » à « service » (question 15).** Proposition : le premier atteint de ces trois repères. Mille
comptes. Deux cents membres du panel. Environ 250 abonnés à la lettre, parce que l'offre gratuite de Brevo
plafonnerait à 300 mails par jour (chiffre du premier cadrage, **non vérifié**) : c'est le premier coût réel,
donc le premier déclencheur du fil sur le financement, bien avant tout autre.

## 6. L'extension

### 6.1 Les deux options

| | Sans envoi (correspondance sur l'appareil) | Avec envoi (l'adresse part au site) |
|---|---|---|
| Ce que le site apprend | qu'une adresse IP télécharge l'index, à heure fixe | chaque article ouvert, par IP et par instant |
| Statut | rien de personnel au-delà d'un accès au tiroir public | historique de lecture : opinion par déduction (C-184/20, C-252/21) |
| Obligations | politique de confidentialité ; déclaration « aucune collecte » | consentement dans l'interface, déclaration d'activité de navigation, AIPD, journaux à couper |
| Couverture | les articles de l'index (quelques jours) et les médias classés | toutes les archives |
| Panne du site | l'extension répond avec le dernier index | l'extension ne répond plus |
| Coût pour le site | un fichier de plus | un service de plus, à tenir à la charge de la navigation de tous |

**Tranché : sans envoi, et sans retour possible par une mise à jour discrète.** L'option avec envoi n'achète
que les archives. Si le besoin vient un jour, il passe par un geste (« chercher cet article dans les
archives »), jamais par la navigation.

### 6.2 La granularité, et le modèle de menace

**Deux paliers, tous deux locaux.** D'abord le média : d'après le domaine de l'onglet, sa bande FrIdéo, ou « non
classé ». Ensuite l'article : s'il figure dans l'index, son sujet, la répartition sur sept bords, les côtés
silencieux, un lien vers la page du sujet.

**Affichage dans la fenêtre de l'extension, pas dans la page.** Le brief admet un bandeau. Position plus
stricte : rien n'est injecté dans la page du journal. Cela évite toute permission sur des sites, tout script
dans la page d'autrui, et toute querelle avec les rédactions dont le site a besoin par ailleurs.

**Une seule permission : `activeTab`.** Elle donne l'adresse de l'onglet au moment où la personne clique sur
l'icône, s'éteint quand elle quitte la page, et n'affiche aucun avertissement à l'installation (documentation
de Chrome, lue). Un affichage automatique sans clic demanderait davantage : faisabilité **non vérifiée**, à ne
pas promettre.

| Menace | Couvert | Pas couvert |
|---|---|---|
| **Le site, ou qui le pirate** | Il ne reçoit aucune adresse. Il ne peut pas pousser de code : celui de l'extension vient de la boutique. | Il peut servir un index faux : un média mal étiqueté. Parade : l'extension affiche la date et la version de l'index, valide son format, n'en injecte aucun HTML. |
| **Une mise à jour malveillante** (compte de développeur volé) | Avec `activeTab` seul, elle ne lit que l'onglet où la personne clique. | Ce qu'elle lit là. C'est la raison de ne jamais demander plus. |
| **La boutique** | — | Google, Mozilla savent qui a installé. À dire dans la fiche. |
| **Le réseau, l'hébergeur, un cache** | L'index est le même pour tous, demandé à heure fixe, sans cookie ni identifiant. | L'adresse IP et le fait d'avoir l'extension. |
| **Le recoupement avec le compte** | Aucun lien : l'extension ne se connecte pas. | Rien, tant que cette règle tient. |
| **La dérive** (« envoyons l'adresse pour améliorer ») | Une règle et un test : l'extension n'appelle que l'adresse de l'index. | Une décision future contraire, qui devra alors se dire en clair. |

### 6.3 Le contrat de l'index

C'est une sortie de la phase 1, pas un objet de la phase 4. Le site s'en sert le premier (« situer un article »).

- **Adresse.** Une seule, sur l'hôte public, sans paramètre. Les mêmes octets pour tous.
- **Contenu.** `v` (version du format), `genere_le`, `methode`, `classement` (par exemple « FrIdéo v1.0 »),
  `medias` (domaine → nom, bande, score, intervalle, ou « non classé »), `sujets` (identifiant → titre,
  répartition sur sept bords, côtés silencieux, adresse de la page), `articles` (clé → identifiant de sujet).
- **Clé d'un article.** L'adresse normalisée (hôte en minuscules sans préfixe d'usage, chemin, ni paramètres
  ni fragment), puis une empreinte tronquée. La normalisation est écrite une fois en Python, une fois en
  JavaScript, avec les mêmes vecteurs d'essai des deux côtés : la méthode déjà retenue pour la signature.
- **Fenêtre et taille.** Les éditions des sept derniers jours. Ordre de grandeur attendu : quelques milliers
  d'articles, moins de 200 Ko une fois compressé. **Estimation, non mesurée** : aucune donnée locale n'a permis
  de compter. Plafond à écrire dans le code de l'extension.
- **Mise à jour.** À chaque publication d'édition. L'extension le redemande à intervalle fixe, jamais au moment
  d'une visite, avec une demande conditionnelle.
- **Ce qu'il révèle.** Rien que le site ne publie déjà. Les empreintes ne cachent rien : elles réduisent la
  taille.
- **Compatibilité.** Règle 6 de `DOCTRINE.md` : tout champ nouveau est facultatif, un index d'avant doit se lire.
- **Étiquette.** Les titres de sujet sont écrits par un modèle : l'extension l'affiche, comme le site.

## 7. La gouvernance du classement

### 7.1 La proposition

- **Le principe ne bouge pas.** Ce site ne classe aucun média. Le brief garde pourtant, parmi ses pistes,
  « construire une méthode propre ». Les deux ne tiennent pas ensemble : cette piste est à écarter, pas à
  différer.
- **Trois statuts.** « Classé » (FrIdéo, version citée). « Peu documenté » (déjà dans les données FrIdéo).
  « Non classé » : le média est lu, ses titres apparaissent dans les sujets, il compte dans la couverture ; il
  ne compte dans aucun bord ni aucun silence. La phase 1 s'élargit ainsi sans attendre personne.
- **Le rôle de FrIdéo.** Source unique du classement. Deux demandes à faire au French News Lab : le rythme de
  mise à jour, et la voie pour proposer un média. Si la réponse est non ou silence, les médias concernés
  restent « non classés ». C'est une limite, écrite, et non un problème à résoudre par un classement maison.
- **Une seconde mesure, à côté.** La lecture à l'aveugle par le panel (phase 3) se publie comme telle :
  « perçu, titres masqués, plus à gauche que… ». La table `notes_media` porte déjà une ligne par méthode. Les
  deux mesures s'affichent côte à côte ; aucune formule ne les fond.
- **Les versions.** Chaque édition gardée cite la version du classement et de la méthode qui l'a produite. Un
  changement de version ne réécrit rien : la règle existe déjà pour les éditions.
- **Un comité** n'a de sens qu'avec une structure (phase 5). Avant, ce serait un décor.

### 7.2 Le droit de réponse

**Il existe déjà.** La loi pour la confiance dans l'économie numérique, article 1-1, III (lu) : toute personne
nommée ou désignée dans un service de communication au public en ligne dispose d'un droit de réponse ; la
demande va au directeur de la publication, dans les trois mois ; l'insertion se fait dans les trois jours, sous
peine de 3 750 € d'amende ; elle est gratuite. Le décret du 24 octobre 2007 (lu) : réponse écrite, de la
longueur du message en cause, 200 lignes au plus, publiée à la suite du message ou accessible depuis lui ; et,
pour un courrier périodique non quotidien, insérée dans la parution suivante. La lettre de la semaine est
donc concernée.

Ce que le site a à trancher n'est pas l'existence de ce droit, c'est sa forme :

- **Qui.** Le média classé : droit de réponse, au sens de la loi. Un chercheur : une contestation de méthode,
  transmise au French News Lab et inscrite au registre. Un lecteur : un signalement, sans suite promise.
- **Par quelle voie.** Une adresse dédiée, affichée sur la fiche de chaque média et sur la page de méthode.
- **Ce qui se passe.** Le site ne change pas un score qui n'est pas le sien. Il publie la réponse du média sur
  sa fiche, datée, présentée comme telle. Il transmet à FrIdéo. Il tient un **registre public** : date, média,
  objet, suite donnée.
- **Ce qui ne se passe pas.** Aucun formulaire qui publierait seul. La réponse est insérée par le directeur de
  la publication : ce n'est pas un contenu stocké à la demande d'un utilisateur. La définition de l'hébergement
  dans le DSA (article 3, g, iii, lu) vise ce dernier cas. Lecture à confirmer par un juriste.

Un point voisin, que le brief ne nomme pas : l'article 1-1, V rend la loi de 1881 applicable au site. Afficher
qu'un journal est « d'extrême droite » ou « d'extrême gauche », même repris d'une étude, engage le directeur
de la publication. La règle 8 de `DOCTRINE.md` (« plus à gauche que les autres journaux du panel ») est aussi
une protection. À faire relire.

## 8. Ce que le brief demande de trancher

### 8.1 Extension, frontière du compte

Tranchés en 6.1, 6.2 et 3.2. En une ligne chacun : correspondance sur l'appareil, au média puis à l'article ;
entre dans le compte ce dont la cible est vide ou prise dans une liste fermée et large, sous plafond.

### 8.2 Les comptes multiples, sans canal payant

Aucun moyen gratuit ne prouve qu'une personne est unique. Les parades s'empilent par couche ; aucune ne
suffit seule.

| Couche | Parade | Ce qu'elle coûte au tricheur |
|---|---|---|
| Entrée | Cercle invité, codes donnés par l'éditeur ; à l'ouverture, une ancienneté minimale du compte | des invitations, ou du temps |
| Unicité | Une adresse, un compte, après normalisation ; domaines jetables refusés | de vraies boîtes mail |
| Calendrier | Panel figé à l'ouverture du questionnaire, délai de carence | de l'anticipation, sans connaître les questions |
| Comptage | Moyenne par bord, puis moyenne des bords | bourrer un bord ne le fait pas peser plus ; à l'intérieur d'un bord, le bourrage déplace la moyenne |
| Signal | Afflux d'adhésions avant une ouverture ; écart entre les deux urnes ci-dessous | — |
| Parole | « Panel de volontaires. Ce n'est pas un sondage. » | — |

**Une idée de plus, pour le jour de l'ouverture à tout compte : deux urnes par ancienneté.** Le guichet signe
avec une clé pour les membres anciens, une autre pour les récents. L'urne connaît alors un seul fait de plus
par réponse : ancienne ou récente. Les deux résultats se publient côte à côte. Un afflux de comptes neufs se
voit à l'écart entre les deux, sans rien savoir de personne. Prix : l'ensemble d'anonymat est coupé en deux ;
à n'employer qu'au-dessus du seuil dans chaque moitié.

Le tort résiduel, à écrire tel quel : une personne patiente, avec plusieurs vraies adresses inscrites
longtemps à l'avance, répond plusieurs fois.

### 8.3 L'AIPD

- **Critères.** La CNIL en liste neuf et demande l'analyse dès deux (page lue) : évaluation ou notation ;
  décision automatique ; surveillance systématique ; données sensibles ; large échelle ; croisement ;
  personnes vulnérables ; usage innovant ; exclusion d'un droit ou d'un contrat. Pour le panel : données
  sensibles, sûrement ; usage innovant, plausible. Le croisement est exclu par construction. Les personnes
  vulnérables n'entrent que par des mineurs : raison de plus pour tenir les écoles hors des comptes.
- **Grande échelle.** Aucun seuil chiffré, ni dans l'article 35, ni sur la page de la CNIL, qui ne donne qu'un
  exemple à « plusieurs millions ». Chercher le seuil est une fausse piste : la règle des deux critères
  s'applique avant.
- **Tranché.** Panel : AIPD avant le premier questionnaire hors du cercle invité, avec l'outil de la CNIL.
  Extension sans envoi, alertes par rubrique : une note d'une page qui dit pourquoi il n'y en a pas. Suivi
  court par mail : il entre dans l'AIPD du compte. Relecture par un tiers (question 12) à l'ouverture du
  panel à tout compte ; avant, la faire soi-même vaut mieux que l'attendre.

### 8.4 La neutralité financière

**Par un engagement écrit maintenant, par la structure au premier euro.** Une charte courte dans le dépôt et
sur le site : financeurs exclus (médias classés, leurs propriétaires, partis, annonceurs), publication de toute
recette, aucune publicité. Elle ne coûte rien et lie déjà. Le jour d'un premier euro ou d'une seconde
personne, une association reprend la charte dans ses statuts. La garantie de dernier recours existe déjà : code
sous AGPL, classement sous CC BY, tiroir public exportable. N'importe qui peut repartir sans le site.

Deux remarques pour le jour où la question se rouvrira. L'abonnement individuel à la manière de Ground News vend
surtout des fonctions personnalisées, celles que ce site refuse de garder sur un serveur : il aurait peu à
vendre. Et les « services aux rédactions » sont un financement par ceux que le site classe : exclus par la
charte. Restent l'adhésion, le don, et les services aux organisations qui ne sont pas des médias.

### 8.5 Le titre et le « très court extrait »

**Renvoyé, par décision.** Pratique tenue : titre, nom du média, lien, rien d'autre. Trois déclencheurs
rouvrent la question et appellent un avis écrit avant d'agir : un projet de recette ; un affichage au-delà du
titre (chapô, extrait, image, résumé d'un article) ; une réclamation d'un éditeur. Aucune phase n'en dépend.
Les sources du brief sur ce point n'ont pas été relues.

## 9. Le sort du premier cadrage

**Reste valable, sans retouche.** La règle « le compte sait qui, l'urne sait quoi ». La signature aveugle
(D1, D2, D15) et ses limites dites. Le bord sur l'appareil (D4). Pas de lien entre questionnaires (D6). Le
cercle invité (D7). Les seuils (D8). Les journaux du proxy et Brevo (D9, D10). Le retrait au début (D12).
L'AIPD (D14). Les quinze règles de code. Les huit flux. Le modèle de menace. Les écrans du panel. Le refus du
push, des passkeys, du chiffrement des adresses.

**Change.**

| Premier cadrage | Ici |
|---|---|
| Le compte est « une adresse et deux cases » | Un compte et une liste d'abonnements typés (section 3) |
| L'urne est `comparateur.db` | Une urne par questionnaire, dans son fichier ; `comparateur.db` est le tiroir public |
| Trois tiroirs | Quatre |
| Cookie limité au chemin `/api/compte` (D3, règle 4) | Cookie d'hôte sur `compte.` ; le chemin reste le repli |
| Fusion d'`abonnes` « après le prototype » (D5) | Le schéma générique dès le prototype ; la fusion devient une copie de lignes |
| Effacement après 24 mois sans connexion | Un compte vit tant qu'un abonnement est actif |
| 300 mails par jour « à accepter » (D11) | Premier déclencheur du fil sur le financement |
| La fabrique envoie la lettre | La fabrique écrit la synthèse, le guichet l'envoie |
| « Gardé par le site : votre adresse, vos deux cases » | L'écran est engendré depuis les lignes du compte |

**Le prototype `proto/panel-comptes`.** Il garde ses trois preuves et ses critères de fin. Il en gagne trois.

4. *Le compte générique tient avec deux types.* « Lettre » et « panel » passent par la même table et le même
   registre. Un troisième type, factice, est ajouté dans un test sans toucher au schéma (règles 16 à 19).
5. *La couture des noms d'hôte tient.* `compte.localhost` et `urne.localhost` sur un seul processus ; le
   cookie n'arrive jamais à l'urne ; le parcours « répondre » est refait depuis l'application installée sur
   iPhone. Si ce dernier point échoue, le repli sur un seul hôte est noté et le reste ne change pas.
6. *L'urne est un fichier par questionnaire.* Après clôture : fichier scellé, plus de clé, plus de retraits.

Il construit en plus `abonnements.py`. Il laisse toujours de côté : la migration réelle d'`abonnes`, les
alertes, les flux, la séparation fabrique-guichet, le vote à l'aveugle, l'AIPD. Le critère « les 31 tests
actuels passent » et celui des empreintes de rendu identiques restent.

## 10. Désaccords avec le brief

1. **Le nom et le domaine ne sont pas « à ne pas faire trop tôt ».** C'est la première décision (5.2).
2. **Le découpage « public, authentification, panel »** n'est pas le bon (5.1). Et l'essentiel du gain de
   sécurité que le brief place en phase 6 s'obtient en phase 2, pour presque rien.
3. **Classer un abonnement d'après la sensibilité de son thème** n'est pas tenable (3.1).
4. **L'extension comme « point d'entrée ».** Le brief veut un site lu « sur un téléphone », où les extensions
   sont rares. Le point d'entrée y est le partage d'un lien et le champ « situer un article ». L'extension
   vient après, pour l'ordinateur. Et sans bandeau dans la page.
5. **La gouvernance comme prérequis de l'élargissement.** Le statut « non classé » les découple (7.1).
6. **« Construire une méthode propre »** contredit le principe 7.1.5 du même brief. À écarter.
7. **Le droit de réponse « à définir ».** Il est défini par la loi ; reste sa mise en forme (7.2). Et le brief
   ne dit rien du risque de la loi de 1881 sur les étiquettes de bord.
8. **Le seuil de « grande échelle »** n'est pas la bonne question pour l'AIPD (8.3).
9. **L'abonnement payant léger** comme piste de financement : faible pour ce site (8.4). Sans objet
   aujourd'hui, après la décision d'Amiel.

## 11. Les questions ouvertes du brief

| | Question | Recommandation | Bloque, sans réponse |
|---|---|---|---|
| 1 | Projet d'Amiel ou structure à plusieurs ? | Projet personnel sous charte ; association au premier euro ou à la première personne. | Phase 5 |
| 2 | Des collaborateurs sur le serveur ? | Supposer que oui un jour. Donc l'urne déplaçable dès la phase 3. | Phase 6 ; l'ouverture du panel à tout compte |
| 3 | Abonnement payant ? | Répondu : aucune monétisation. | Rien |
| 4 | Financeurs exclus ? | Médias classés et leurs propriétaires, partis et fonds liés, annonceurs. L'écrire dans la charte. | Le premier euro, pas une phase |
| 5 | France seule ? | France seule. Un autre pays serait une autre fabrique, pas une option du site. | Phase 5, en partie |
| 6 | Alertes par sujet ? | Oui sur l'appareil et par flux. Par mail : rubriques larges ; le suivi court seulement sur demande. | Phase 2 (la liste des types ouverts) |
| 7 | Qui conteste le classement ? | Le média : droit de réponse légal. Chercheur : contestation de méthode. Lecteur : signalement. Registre public. | Phase 1 dès qu'un média est ajouté ; phase 5 |
| 8 | Nom et domaine ? | Non. Un domaine propre, choisi maintenant. | Phase 1 (liens cités), phase 2 (stockage de l'appareil), phase 4 (fiche de l'extension) |
| 9 | Dépendre de FrIdéo ? | Oui, en le disant. Les autres médias sont « non classés ». | Rien, grâce au statut ; sinon la phase 1 |
| 10 | Extension d'abord limitée au bord du média ? | Oui, puis l'article, toujours sur l'appareil. | Phase 4 |
| 11 | Safari ? | Après Chrome et Firefox, sur demande. | Rien |
| 12 | AIPD par un tiers ? | Soi-même pour le cercle invité ; relecture par un tiers à l'ouverture. | L'ouverture du panel, pas la phase 3 |
| 13 | Droit voisin, avis juridique ? | Renvoyé (8.5). | Rien, tant que l'affichage ne change pas |
| 14 | Panel ou abonnement réservé à une communauté ? | Non pour un panel réservé : il ferait un résultat de communauté sous le nom du site. Oui pour des pages d'exemples destinées aux classes, sans compte. | Phase 5 |
| 15 | Seuil de « projet » à « service » ? | Mille comptes, deux cents membres du panel, ou le plafond d'envoi gratuit : le premier atteint. | Phase 6 |

## 12. Les consultations juridiques à demander

Dans l'ordre où une phase en a besoin.

1. **Avant la phase 1 élargie.** Un journal dont le site affiche la bande FrIdéo est-il « nommé ou désigné » au
   sens de l'article 1-1, III de la loi du 21 juin 2004 ? Reprendre l'étiquette « extrême droite » ou « extrême
   gauche » d'une étude publiée expose-t-il le directeur de la publication au titre de la loi de 1881, et la
   formule relative (« plus à droite que les autres journaux du panel ») change-t-elle l'analyse ?
2. **Avant la phase 2.** L'appartenance au panel et un abonnement à une rubrique large sont-ils des données
   « révélant » une opinion politique au sens de l'article 9 du RGPD, lu avec l'arrêt C-184/20 ? Le stockage,
   dans le navigateur et à la demande de la personne, de son bord et de ses journaux suivis est-il exempté de
   consentement au titre de l'article 82 de la loi Informatique et Libertés ?
3. **Avant la phase 3.** L'étiquette « consultation de volontaires » suffit-elle au regard de la loi du
   19 juillet 1977, y compris en période électorale ? L'exercice des droits par le reçu satisfait-il
   l'article 11 du RGPD ? L'âge de quinze ans (article 45 de la loi Informatique et Libertés) appelle-t-il plus
   qu'une déclaration ?
4. **Avant la phase 4.** Le téléchargement et le stockage de l'index par une extension installée par la
   personne relèvent-ils de l'article 5, paragraphe 3 de la directive 2002/58, et sont-ils « strictement
   nécessaires » au service demandé ?
5. **Avant la phase 5.** La publication, par le directeur de la publication, de la réponse d'un média
   fait-elle du site un fournisseur d'hébergement au sens du DSA ? Quelle forme (association, fonds de
   dotation) porte le mieux une charte d'indépendance ?
6. **Au déclencheur seulement.** Le titre entier comme « très court extrait » ; le site comme fournisseur de
   services de la société de l'information ; l'envoi des titres à un modèle au regard de la fouille de textes
   (ce dernier point **non vérifié**, aucun texte lu).

## 13. Sources

Vérifiées le 16/11/2026. « Lu » : le texte a été lu, à travers un miroir de textes juridiques pour le droit,
à travers un résumé automatique de la page pour le web (la restitution peut omettre).

**Lues pour ce cadrage**

- Loi n° 2004-575 du 21 juin 2004, art. 1-1 (I à V), version en vigueur depuis le 23/05/2024 (lu) :
  <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049568614/2024-05-23>
- Décret n° 2007-1527 du 24 octobre 2007, art. 1 à 6 (lu ; il renvoie encore à l'ancien numéro, IV de
  l'article 6) : <https://librejustice.fr/norm/fr/decret-n-2007-1527-du-24-octobre-2007-relatif-au-droit-de-reponse-applicable-aux> (miroir lu)
- Règlement (UE) 2022/2065 (DSA), art. 3, 14 et 16 (lus). L'article 16 est dans la section 2, applicable à
  tout hébergeur ; l'exemption des petites entreprises (art. 19, lu par le brief) porte sur la section 3.
- Règlement (UE) 2024/1689 (AI Act), version consolidée au 27/07/2026 : art. 50 (lu), art. 113 (lu :
  application générale au 2 août 2026, sans exception pour l'article 50), art. 111, paragraphe 4 (lu : délai au
  2 décembre 2026 pour l'article 50, paragraphe 2, qui vise les fournisseurs). Le site est déployeur :
  l'article 50, paragraphe 4 s'applique à lui depuis le 2 août 2026. L'étiquette « écrit par un modèle » y
  répond, mails et extension compris.
- Règlement (UE) 2024/1083 (EMFA), art. 29 (lu : applicable au 8 août 2025 ; l'article 6, paragraphe 2, sur les
  bases nationales de propriété, n'a pas de date différée) et art. 6 (lu).
- Loi n° 78-17 du 6 janvier 1978, art. 45 (lu en extrait : consentement seul à partir de quinze ans).
- CNIL, « Ce qu'il faut savoir sur l'AIPD » (lu, résumé) :
  <https://www.cnil.fr/fr/ce-quil-faut-savoir-sur-lanalyse-dimpact-relative-la-protection-des-donnees-aipd>
- MDN, `Set-Cookie` : cookie sans `Domain`, préfixes `__Host-` et `__Secure-` (lu, résumé) :
  <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie>
- Chrome, permission `activeTab` (lu, résumé) :
  <https://developer.chrome.com/docs/extensions/develop/concepts/activeTab>
- MDN, `share_target` (lu, résumé : fonction expérimentale, disponibilité limitée ; le tableau par navigateur
  n'a pas été restitué) : <https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/share_target>
- Dans le dépôt : `comparateur/base.py` (schéma), `comparateur/serveur.py` (routes), `comparateur/site/js/vues/mentions.js`.

**Non vérifiées**

- Le règlement (UE) 2026/1744 lui-même : seuls ses effets dans la version consolidée de l'AI Act ont été lus.
- L'existence et l'accès, en France, de la base de propriété des médias prévue par l'EMFA.
- Le comportement d'une application installée sur iPhone qui ouvre un autre nom d'hôte, et la tenue d'une
  session dans ce cas.
- Le partage d'un lien vers une application web installée, navigateur par navigateur.
- L'affichage automatique d'une extension sans permission sur des sites, sur Chrome et sur Firefox.
- La taille réelle de l'index.
- Le plafond de 300 mails par jour de Brevo et la coupure de son suivi des clics (déjà signalés par le
  premier cadrage).
- Qu'un journal, personne morale, soit bien « nommé ou désigné » au sens du droit de réponse : lecture du
  texte, sans jurisprudence consultée.
- Le rythme de mise à jour de FrIdéo et sa voie d'ajout d'un média.
- La disponibilité d'un nom de domaine.
- Tout le droit voisin et la fouille de textes : renvoyés, non relus.
- Les sources que le brief marque lui-même non lues et qui ne pèsent sur aucune décision d'ici : accessibilité
  (décret du 9 octobre 2023, seuil du RGAA), Décodex, AllSides, fiches des boutiques pour Ground News.
