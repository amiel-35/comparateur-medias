# Brief de long terme

Brief du 16/11/2026. Rien n'est décidé ici, rien n'est construit. Ce fichier dit le besoin : où aller, pour qui, sous
quelles contraintes, dans quel ordre, et ce qui reste à trancher. L'architecture viendra dans un cadrage écrit à partir
de ce brief. Quand une solution a déjà été discutée, elle est notée comme **piste** ou comme **contrainte**, jamais
comme décision.

C'est une feuille de route de haut niveau : des phases à enclencher, pas des sprints ni des tâches. La section 5 en est
le cœur. Le reste la sert.

Les sources sont en fin de document (section 10), avec ce qui a été lu et ce qui ne l'a pas été. Une affirmation
juridique marquée « question » n'est pas un avis : elle demande une vérification par un juriste avant toute décision.

## 1. La vision

Dans cinq ans, ce site est **l'outil de référence en français pour voir comment les médias traitent un même sujet, et
ce qu'ils taisent**. Il se lit sans compte, gratuitement, sur un téléphone, sans rien savoir de la politique des
médias. Il montre, il ne juge pas : un média n'est jamais « bon » ou « mauvais », il est « plus à gauche que les autres
journaux du panel », avec la méthode et les chiffres à portée de clic.

Autour de ce noyau public, des fonctions facultatives : la synthèse de la semaine, des alertes, une extension de
navigateur qui situe l'article qu'on lit, un panel de lecteurs volontaires dont les réponses ne portent pas le nom.
Chacune est utile sans les autres. Aucune n'est nécessaire pour lire.

Ce que le site refuse d'être :

- **Un juge de la vérité.** Il ne dit pas qu'un article est vrai ou faux. Il compare des cadrages.
- **Un profileur.** Il ne garde aucune trace de ce que quelqu'un lit, suit ou masque, rattachée à une personne. Ces
  données révèlent une opinion politique (voir 4.1) : elles restent sur l'appareil.
- **Une plateforme d'attention.** Pas de fil sans fin, pas de notification pour revenir, pas de publicité ciblée.
- **Une source qui se cache.** Code, méthode, classement et limites sont publics.
- **Un clone américain.** La gauche et la droite américaines ne sont pas les françaises. Le classement, les mots et le
  droit sont ceux d'ici.

## 2. Les publics et leurs besoins

| Public | Ce qu'il attend | Ce qu'il ne doit jamais subir |
|---|---|---|
| **Lecteur occasionnel** | Arriver par un lien ou un moteur de recherche, comprendre en trente secondes qui parle d'un sujet et qui se tait. Aucune inscription. | Un mur d'inscription, un bandeau de cookies, du jargon. |
| **Abonné** (lettre, alertes) | Recevoir sans y penser ce qui l'intéresse : la semaine, un sujet suivi, une édition. Se désinscrire en un clic. | Un mail de relance, un compte à gérer, un mot de passe. |
| **Membre du panel** | Répondre à quelques questions quand il veut. Savoir, en une phrase, ce que le site garde et ne garde pas. Pouvoir partir. | Qu'une réponse soit rattachée à son nom, ou à son adresse mail. |
| **Utilisateur de l'extension** | Voir, sur l'article qu'il lit, le bord du média et le traitement du même sujet ailleurs. Sans que sa navigation parte quelque part. | Que la liste de ses lectures soit envoyée au site. |
| **Chercheur** | Des données ouvertes, une méthode citable, des versions datées, des limites écrites. | Des chiffres sans méthode, des définitions qui changent sans trace. |
| **Journaliste, rédaction** | Un outil pour repérer les angles morts et citer une source stable. Un droit de réponse clair sur le classement de son propre média. | Un classement opaque, un média jugé sans pouvoir répondre. |
| **École, enseignant** | Une page qui s'explique seule, sans compte d'élève, avec des exemples du jour. | Des données sur des mineurs. |

L'âge compte : le seuil de consentement pour un service en ligne est de 15 ans en France (cité de mémoire dans le
premier cadrage, non relu).

## 3. Le paysage

Résumé de ce qui existe. Les sources sont en 10.1. « Non vérifié » signale ce qui n'a pas pu être lu.

### 3.1 Ground News

- **Ce qu'il fait.** Fusionne les articles de plusieurs médias sur un même événement et montre qui couvre quoi, avec
  la répartition gauche, centre, droite. Environ 60 000 articles par jour, plus de 50 000 sources (chiffres de la
  page « À propos », lue). Fondé en 2017, basé à Kitchener (Ontario), détenu par ses fondateurs, avec des
  investisseurs nommés (page lue).
- **Comment il classe.** Il ne classe pas lui-même : il moyenne les notes de trois tiers, AllSides, Ad Fontes Media et
  Media Bias Fact Check, sur sept niveaux, et précise que l'analyse est faite « dans le contexte du système politique
  américain » (page « Rating system », lue). Il a ajouté sa propre catégorisation de la propriété (2 276 médias
  codés à la main). Il a une édition Europe, mais la page ne dit pas comment les médias non américains sont notés.
- **Son modèle économique.** L'abonnement. Un seul forfait payant visible : « Vantage », 8,50 € par mois facturé à
  l'année, qui ouvre notamment les angles morts, la comparaison complète, la propriété et les notes de fiabilité
  (page lue le 16/11/2026). L'article du Columbia Journalism Review ajoute : sponsoring de YouTubeurs de tous bords,
  nombre d'abonnés non communiqué, résumés produits par IA.
- **Ses fragilités, d'après la même source.** AllSides dit que ses notes ont été utilisées sans autorisation formelle ni
  paiement ; Media Bias Fact Check dit n'avoir aucun accord ; Ad Fontes dit être payé. Les trois méthodes diffèrent.
  Une étude citée montre un effet limité des « angles morts » sur les opinions. Le CJR rappelle qu'un étiquetage de
  biais ne mesure pas la vérité.
- **L'extension.** « Media Bias Checker » : montre comment les médias couvrent la même histoire, y compris sur les
  articles partagés sur Facebook, Twitter et Reddit (page « À propos », lue). Sa fiche sur la boutique Chrome
  déclare ne collecter aucune donnée (d'après un résultat de recherche, fiche non lue). Des avis sur la boutique
  Firefox affirment que chaque adresse visitée est envoyée à Ground News : **non vérifié**, témoignages seulement.

### 3.2 Les autres

| Acteur | Ce qu'il fait | Modèle | À reprendre | À ne pas reprendre |
|---|---|---|---|---|
| **AllSides** (États-Unis) | Note le biais des médias par panel équilibré, enquête à l'aveugle, revue éditoriale, retours de lecteurs (méthode d'après la page citée par le README, **non relue** : refus 403 du robot). Montre les trois titres gauche, centre, droite. | Selon ses propres pages (vues par un résumé de recherche, **non vérifié par lecture**) : services aux organisations environ 72 %, abonnements et dons 23 %, publicité 4 % en 2022. | L'idée d'un panel équilibré, la transparence du modèle économique. | Le cadre américain. |
| **Ad Fontes Media** (États-Unis) | Analystes humains aux opinions variées, notation de contenus. Société à mission, à but lucratif, Colorado. | Vente de produits à individus, enseignants, marques, régies, agrégateurs, réseaux sociaux. 6,4 M$ levés depuis 2018 (page lue). | La notation par contenu, le principe d'analystes de tous bords. | La dépendance à un cadre américain et à un financement par la publicité et les plateformes. |
| **Media Bias / Fact Check** (États-Unis) | Notation par vérificateurs humains. | Non lu. | Rien de précis. | Non évalué. |
| **NewsGuard** (États-Unis) | Journalistes notent la fiabilité de plus de 6 500 sites ; couvre États-Unis, Royaume-Uni, Italie, France, Allemagne. | Licence de ses données à plateformes, régies, marques, gouvernements, chercheurs (page lue). | Les fiches détaillées, les langues européennes. | Le jugement de fiabilité : ce site ne le fera pas. |
| **FrIdéo / French News Lab** (France) | Position gauche-droite continue de 30 médias français, fusion de neuf familles de preuves, intervalles de confiance ; CC BY 4.0 ; association loi 1901 à Paris (page lue). | Non indiqué. | Tout : c'est déjà la base du site. | Sa limite : 30 médias, fréquence de mise à jour non indiquée, zéro est la moyenne du panel et non un point neutre. |
| **Décodex** (Le Monde, France) | Extension et base de sites rangés de « plutôt fiable » à « très peu fiable », lancée en 2017. | Initiative d'un seul journal. | Le format d'extension simple. | La critique d'origine : un journal qui note les autres. **État actuel non vérifié.** |
| **Freepress, NEXA** (Europe) | Agrégateurs européens à résumés produits par IA. | Non lu. | À regarder. | Résultat d'une seule recherche : **non vérifié**. |

**Constat honnête.** La recherche faite pour ce brief n'a trouvé aucun équivalent français de Ground News qui compare
les titres par bord. Ce n'est pas une preuve d'absence : la recherche était courte et en ligne seulement. À reprendre
par une veille plus soigneuse avant tout message public du type « le premier ».

**Ce qui se transpose mal en Europe.** Le classement gauche-droite américain, qui porte sur un bipartisme. Les médias
régionaux et la presse locale, absents des classements. Une multiplicité de langues et de paysages politiques, avec
des partis qui ne se rangent pas sur un seul axe. Le droit : droits voisins des éditeurs, protection de données plus
stricte, sensibilité particulière des opinions politiques.

**Ce qui se reprend.** La page de sujet qui montre les couvertures en parallèle. Les angles morts, déjà au cœur du site.
L'extension comme point d'entrée. Un modèle par abonnement léger pour les fonctions avancées, sans fermer le noyau.

## 4. Les contraintes françaises et européennes

Chaque ligne dit ce que la règle impose au produit. Les textes ont été lus à partir d'une base de textes juridiques
(miroir des textes officiels) pour les articles cités ; les points qui n'ont pas été lus sont marqués.

### 4.1 RGPD, données sensibles, AIPD

- **Article 9.** Le traitement de données qui « révèlent » les opinions politiques est interdit, sauf exception ; le
  consentement explicite en est une (premier alinéa lu ; l'alinéa 2 est cité par le premier cadrage, non relu ici).
  La CJUE, dans l'arrêt C-184/20 (1er août 2022), a jugé que l'article 9 couvre aussi les données qui dévoilent
  une opinion « indirectement, au terme d'une opération intellectuelle de déduction ou de recoupement » (point lu
  dans le premier cadrage). **Imposé au produit :** les médias suivis ou masqués, l'historique de lecture et le bord
  déclaré sont à traiter comme des données sensibles. Principe retenu : elles ne quittent pas l'appareil, ou ne sont
  jamais liées à un compte. L'application à un comparateur de médias est une **inférence** du premier cadrage, non
  tranchée par un texte : question pour un juriste.
- **Article 35, AIPD.** Obligatoire en cas de traitement à grande échelle de catégories de l'article 9 (alinéa 3, b,
  lu). **Imposé :** une AIPD avant le panel élargi et avant l'extension si elle envoie quoi que ce soit. Question : à
  partir de quelle taille « grande échelle » vaut-il pour ce site ? Le premier cadrage retient deux critères sur neuf
  de la CNIL ; la liste complète des critères n'a pas été relue.
- **Anonymat réel ou pseudonymat.** L'état de l'art est dans `docs/cadrage-panel-comptes.md` (section 4) : CNIL, G29,
  CEPD 01/2025, CJUE C-413/23 P. À retenir : un pseudonyme reste une donnée personnelle ; le mot « anonyme » ne
  s'écrit qu'avec sa limite.

### 4.2 ePrivacy et traceurs

- **Directive 2002/58, article 5, paragraphe 3** (lu), transposée par l'article 82 de la loi Informatique et Libertés
  (page CNIL lue). Tout stockage ou accès sur l'appareil exige un accord, sauf s'il est strictement nécessaire à un
  service demandé. La mesure d'audience est exemptée sous conditions que la page lue ne détaille pas.
- **Imposé :** l'absence de cookie et de traceur reste un atout. Une session de compte par cookie serait « strictement
  nécessaire » (piste du premier cadrage). Le stockage local du bord ou des médias suivis, écrit par le site sur
  l'appareil, relève du même article 5 paragraphe 3 : question — suffit-il qu'il serve à un service demandé ? Une
  extension installée par l'utilisateur est-elle un « équipement terminal » au sens de cet article ? Question
  ouverte, non tranchée.

### 4.3 Droit voisin des éditeurs de presse

- **Directive 2019/790, article 15** (lu) : les éditeurs ont un droit sur l'utilisation en ligne de leurs publications
  par des fournisseurs de services de la société de l'information. Il ne s'applique pas aux actes d'hyperlien, ni à
  l'usage de « mots isolés ou de très courts extraits ». Il dure deux ans.
- **Droit français.** Code de la propriété intellectuelle, L218-2 (autorisation de l'éditeur requise avant reproduction
  ou communication au public, totale ou partielle) et L211-3-1 (l'éditeur ne peut interdire les hyperliens ni les mots
  isolés ou très courts extraits) ; loi du 24 juillet 2019 (articles lus).
- **Application.** L'Autorité de la concurrence a infligé 250 M€ à Google le 20 mars 2024 pour non-respect d'engagements
  sur ces droits (d'après la presse ; communiqué de l'Autorité **non lu**).
- **Imposé :** le site affiche des titres et ouvre vers l'article. La notion de « très court extrait » appliquée à un titre
  n'a pas été étudiée. Question : un titre entier, reproduit à côté de quatre autres, est-il un « très court
  extrait » ? Le site est-il un « fournisseur de services de la société de l'information » visé ? Tant que la
  réponse n'est pas écrite par un juriste, la pratique prudente reste : titre, nom du média, lien, rien d'autre.
  Un modèle économique payant renforce le risque. À régler avant toute monétisation.

### 4.4 Règlement européen sur la liberté des médias (EMFA, 2024/1083)

- Lu : l'article 3 (droit des destinataires à une pluralité de contenus indépendants), l'article 6 (bases de données
  nationales sur la propriété des médias, à la charge des régulateurs nationaux), l'article 18 (très grandes
  plateformes en ligne : fonctionnalité de déclaration des fournisseurs de services de médias). Seuls des extraits
  ont été lus ; les dates d'application sont **non vérifiées**.
- **Imposé :** presque rien directement. Le règlement vise les très grandes plateformes et les régulateurs. Indirectement,
  il crée des bases de propriété publiques, une source possible pour une page « à qui appartient ce média »
  (comme Ground News le fait de son côté). Question : ces bases sont-elles accessibles en France, sous quelle forme ?

### 4.5 DSA (2022/2065)

- Seulement si le site héberge des contributions de tiers (commentaires, annotations publiques, listes partagées). Un
  hébergeur doit un dispositif de signalement et des conditions claires (articles 14 et 16, **non lus**). L'article 19
  (lu) exclut les micro et petites entreprises des obligations propres aux plateformes en ligne, et non de celles des
  hébergeurs : **à confirmer**.
- **Imposé :** aujourd'hui, rien : les réponses du panel ne sont pas publiées. Dès qu'un contenu d'utilisateur devient
  public, la question se pose. Principe : ne pas héberger de contributions publiques tant que ce n'est pas
  nécessaire.

### 4.6 AI Act (2024/1689)

- **Article 50, paragraphe 4** (lu, version en vigueur depuis le 27 juillet 2026) : le déployeur d'un système d'IA qui
  génère ou manipule un texte publié pour informer le public sur des questions d'intérêt public doit indiquer que le
  texte a été généré par une IA, sauf si le texte a fait l'objet d'un examen humain ou d'un contrôle éditorial et
  qu'une personne assume la responsabilité éditoriale. L'information est claire, au plus tard à la première exposition,
  et conforme aux exigences d'accessibilité (paragraphe 5).
- **Imposé :** l'étiquette « écrit par un modèle » est déjà une règle du site (DOCTRINE, règle 7). Elle est à garder, y
  compris dans les mails, les alertes et l'extension. Question : si un humain relit systématiquement, l'exception de
  responsabilité éditoriale s'applique-t-elle, et le site veut-il l'assumer ? Réponse recommandée : non, garder
  l'étiquette. Date d'application de l'article 50 : **non vérifiée** (le texte du paquet « omnibus » de juillet 2026
  mentionne le 2 août 2026 et un délai au 2 décembre 2026 pour le marquage par les fournisseurs, article 50
  paragraphe 2 ; non relu en entier).

### 4.7 Accessibilité

- **Directive 2019/882** (acte européen sur l'accessibilité), article 4 (lu) : les services doivent respecter les
  exigences de l'annexe I ; les **microentreprises** qui proposent des services sont exonérées (paragraphe 5). Décret
  du 9 octobre 2023 et arrêté du même jour pour la France (intitulés vus, **texte non lu**).
- **RGAA.** Loi du 11 février 2005, article 47, et décret du 24 juillet 2019 : obligation pour les organismes publics et
  pour les grandes entreprises (seuil de chiffre d'affaires **non relu**). Le site ne semble pas visé aujourd'hui. Question :
  l'est-il en devenant une société ou un service payant, et à quelle taille ?
- **Imposé :** viser quand même le RGAA et le WCAG comme règle de conception. Cela sert l'objectif « public non
  technicien » et protège la suite.

### 4.8 Boutiques d'extensions

- **Chrome Web Store** (politique lue). Politique de confidentialité obligatoire, même pour des données stockées
  localement. Pour l'activité de navigation et le contenu des sites : divulgation et consentement affichés dans
  l'interface de l'extension, par un geste explicite ; usage limité à une fonction décrite et qui a une interface qui en
  a besoin ; interdiction de la publicité ciblée et de toute lecture humaine sauf exceptions ; permissions minimales ;
  cohérence entre fiche, politique et comportement réel, sous peine de suspension.
- **Firefox** (documentation lue en grande partie). Depuis le 3 novembre 2025, les nouvelles extensions doivent
  déclarer dans le manifeste ce qu'elles collectent (`data_collection_permissions`) ; « none » est une déclaration
  valide ; Firefox 140 sur ordinateur et 142 sur Android pour le consentement intégré.
- **Safari / Apple** (lignes directrices lues en grande partie). Règle 4.4.2 : une extension Safari ne doit pas demander
  l'accès à plus de sites que le strict nécessaire. Règle 5.1.1 : politique de confidentialité, consentement pour toute
  collecte même anonyme, minimisation. Règle 5.1.2 : pas de profil caché. Distribution par une app Mac ou iOS et le
  programme développeur payant d'Apple (d'après la documentation d'Apple, résumé non confirmé ligne à ligne).
- **Imposé :** une extension qui ne reçoit aucune adresse visitée est de loin la plus simple à faire valider, sur les
  trois boutiques. Une extension qui envoie l'adresse de la page au site est une collecte d'activité de navigation :
  consentement, AIPD, et aucune adresse rattachée à un compte. Safari ajoute un coût fixe (app, compte développeur) et
  un chemin d'envoi distinct : à traiter après Chrome et Firefox.

## 5. Les grandes phases

Les phases ne sont pas des étapes obligatoires dans cet ordre : chacune a son déclencheur. Aucune durée n'est donnée.
Une phase peut être sautée, retardée ou faite en partie, tant que ses exigences sont tenues. Ce qui doit être tenu
dès la phase 0 est dit en 7 (principes non négociables).

```
0 Assise ── 1 Public ─┬─ 2 Comptes ── 3 Panel ──┐
                      ├─ 4 Extension            ├─ 6 Services séparés
                      └─ 5 Ouverture ───────────┘
        Fil transversal, en continu : pérennité, financement, indépendance
```

### Phase 0. Assise : dire vrai, tenir ce qui existe

**Ce qu'elle apporte.** Un site dont ce qu'il dit de lui est exact, et dont le noyau supporte une audience sans
réécriture. Aucune nouvelle fonction.

**Ce qu'elle exige d'avoir fait avant.** Rien. C'est le point de départ.

**Elle couvre.** Corriger l'écart connu entre le README et la réalité de l'anonymat du vote à l'aveugle (premier
cadrage, section 3). Décider du sort du vote à l'aveugle tant qu'il n'est ouvert qu'à un cercle. Vérifier et couper
les journaux d'accès du proxy sur les routes sensibles (premier cadrage, D9) : sans cela, toute promesse d'anonymat
est fausse. Vérifier le suivi des clics de Brevo. Poser la page de méthode et de limites comme document de référence.
Le droit voisin (4.3) n'en fait pas partie : aucune monétisation n'est prévue et l'affichage reste le titre et le
lien (décision d'Amiel, 16/11/2026). La question est renvoyée au fil transversal. Poser une mesure d'accessibilité.

**Déclencheur.** Immédiat. Rien ne doit s'ouvrir plus largement tant qu'elle n'est pas faite.

**À ne pas faire trop tôt.** Une nouvelle fonction qui reposerait sur une promesse non tenue. Un nom de marque ou un domaine
dont le changement coûterait cher plus tard, avant d'avoir répondu à la question 8 de la section 8.

### Phase 1. Le public solide : un noyau qui s'élargit sans se casser

**Ce qu'elle apporte.** Un site gratuit, rapide, citable, qui couvre plus de médias et plus de sujets, et qui se
partage. C'est la base d'audience dont toutes les phases suivantes dépendent.

**Ce qu'elle exige d'avoir fait avant.** La phase 0 faite : mentions et méthode exactes, journaux du proxy tenus.

**Elle couvre.** L'élargissement du périmètre (au-delà de 30 médias, y compris, avec leur accord, quatre journaux
aujourd'hui illisibles par la récolte : le site ne contourne pas un refus) ; la qualité du regroupement ; la mesure sans cookie ; le cache et la compression déjà prévus dans
`DOCTRINE.md` ; le partage d'une page de sujet ; un export ouvert, en lecture seule, des données de l'édition ; la
version datée de la méthode. Le classement des médias nouveaux pose la question de la gouvernance (section 6) : elle se
tranche ici, pas après.

**Déclencheur.** Immédiat après la phase 0. Un premier signal d'usage (visites par semaine, citations, partage) fixe le
rythme, mais ne conditionne pas le début.

**À ne pas faire trop tôt.** Une base PostgreSQL, un serveur ASGI, plusieurs services : ni la charge ni le besoin ne
le demandent encore (DOCTRINE, « Monter en puissance », point 5). Un classement des médias propre à ce site, avant d'avoir
tranché la gouvernance. Une traduction ou une extension à un autre pays, avant d'avoir fait tenir la méthode en France.

### Phase 2. Le compte durable : abonnements typés, sans opinion

**Ce qu'elle apporte.** Un compte stable par adresse, qui porte des abonnements : la synthèse de la semaine d'abord,
puis les alertes (sur un sujet, sur une édition) et tout ce qui viendra. Un nouveau service est un nouveau type
d'abonnement, sans changer le schéma. Un lecteur qui change de téléphone retrouve ses abonnements en trois gestes.

**Ce qu'elle exige d'avoir fait avant.** La phase 1 (une audience qui a une raison de s'abonner). La décision sur
l'identité (section 6) : durée de session, cookie ou stockage local, ce qu'un compte garde. La classification de chaque
type d'abonnement selon ce qu'il révèle : opinion (jamais dans le compte), un peu (au cas par cas), pas du tout (dans
le compte). Le premier cadrage (`docs/cadrage-panel-comptes.md`) a déjà posé cette règle et une piste : code à six chiffres
par mail, session longue ; passkeys et notifications web écartées pour l'instant.

**Déclencheur.** Un besoin de service au-delà de la lettre : un deuxième type d'abonnement demandé par des lecteurs, ou la
nécessité de retrouver ses réglages. Pas l'envie d'avoir des comptes.

**À ne pas faire trop tôt.** Des préférences gardées sur le serveur ; un mot de passe ; une connexion par un tiers (Google,
Apple, FranceConnect) qui introduit un tiers dans l'identité ; un parcours d'inscription obligatoire pour lire.
Les alertes sur un sujet disent, par définition, ce qui intéresse quelqu'un : elles sont à classer avec soin (un sujet
« réforme des retraites » est peu sensible, un sujet « immigration » l'est peut-être davantage). Question 6.

### Phase 3. Le panel : des lecteurs recontactables, des réponses sans nom

**Ce qu'elle apporte.** Une mesure par bord déclaré, par des lecteurs volontaires, qui complète le classement
documentaire. C'est ce qui distinguerait le site d'un simple agrégateur. Le premier cadrage en a étudié la construction :
un compte qui sait qui, une urne qui sait quoi sans savoir qui, une signature aveugle (RFC 9474) entre les deux.

**Ce qu'elle exige d'avoir fait avant.** La phase 2 (le compte). Une AIPD faite (4.1). Les journaux du proxy tenus
(phase 0). La réponse à la question du statut : « consultation de volontaires », jamais « sondage » (loi du
19 juillet 1977, citée par le premier cadrage, article 12 non relu ici). Un seuil de publication par bord.

**Déclencheur.** Une masse critique : assez de membres par bord pour publier sans désigner personne (le premier
cadrage propose 10 réponses par bord pour un résultat, rien sous 5). Un besoin précis de résultat que le classement
documentaire ne donne pas. Pas le simple désir d'avoir un panel.

**À ne pas faire trop tôt.** Ouvrir à tout compte avant d'avoir fait le premier questionnaire en cercle invité. Publier un
chiffre sous le seuil. Lier des questionnaires entre eux (pseudonymat, premier cadrage D6). Dire « anonyme » sans sa
limite. Pallier la limite des comptes multiples par un moyen payant (SMS, vérification d'identité) : c'est exclu
(section 7).

### Phase 4. L'extension : situer l'article qu'on lit

**Ce qu'elle apporte.** Le point d'entrée le plus utile pour un lecteur déjà informé : sur la page d'un article, le bord
du média et le traitement du même sujet ailleurs. C'est la fonction qui a installé Ground News dans les usages.

**Ce qu'elle exige d'avoir fait avant.** La phase 1 (un classement et un index de sujets assez larges pour avoir quelque
chose à dire sur la plupart des pages). Une réponse à la question centrale : l'extension fait-elle sa correspondance sur
l'appareil (elle télécharge un index et ne dit rien) ou envoie-t-elle l'adresse de la page au site ? La première option
ne demande ni compte, ni AIPD lourde, et passe le plus facilement les trois boutiques (4.8). La seconde est une collecte
d'activité de navigation, donc sensible (4.1). Piste, non décision : première version qui n'affiche que le bord du
média, d'après le domaine, sans rien envoyer ; une seconde qui rapproche l'article d'un sujet de l'index du jour, toujours
localement.

**Déclencheur.** Une audience du site assez grande pour que l'installation d'une extension soit un geste crédible, et
un index de sujets qui couvre assez de pages visitées pour ne pas décevoir. Pas de lien nécessaire avec le compte.

**À ne pas faire trop tôt.** Un envoi d'adresses au serveur « pour améliorer ». Un compte obligatoire. Safari avant Chrome et
Firefox (coût fixe d'une app et d'un compte développeur payant). Une extension qui change l'affichage des pages de
médias au-delà d'un bandeau. Des permissions larges « au cas où » (refusées par la politique de Chrome et d'Apple).

### Phase 5. L'ouverture : chercheurs, journalistes, écoles, autres pays

**Ce qu'elle apporte.** Des usages qui donnent de la crédibilité et des relais : jeux de données datés et citables pour la
recherche, fiches de sujet pour les rédactions, pages d'exemples pour les classes. Possiblement d'autres paysages
médiatiques européens, avec leur propre échelle.

**Ce qu'elle exige d'avoir fait avant.** La phase 1 (une méthode publique et versionnée). La gouvernance du classement
tranchée (section 6) : un chercheur ou une rédaction posera tôt ou tard la question « qui décide du bord de ce média ? ».
Un droit de réponse défini.

**Déclencheur.** Une demande venue du dehors : un laboratoire qui veut citer, une rédaction qui conteste un classement, un
enseignant qui veut un support. Pas un plan de couverture européen fait d'avance.

**À ne pas faire trop tôt.** Un deuxième pays avant que la méthode soit documentée au point qu'un tiers la refasse. Une
version « école » avec des comptes d'élèves (mineurs). Un partenariat qui engagerait l'indépendance du classement.

### Phase 6. Les services séparés : seulement quand le découpage se justifie

**Ce qu'elle apporte.** Deux ou trois services indépendants, par exemple le site public, l'authentification et le panel,
avec leurs propres données, leurs déploiements et leurs droits d'accès. Le gain principal est de sécurité : une brèche
du site public ne touche pas l'identité, et réciproquement. Le premier cadrage a déjà posé la séparation des données en deux
fichiers distincts comme première étape, avant tout découpage en services.

**Ce qu'elle exige d'avoir fait avant.** Les phases 2 et 3 conçues avec des frontières nettes (deux fichiers de données,
aucune jointure). Des tests qui tiennent ces frontières. Une idée claire de ce qui part d'un service à l'autre.

**Déclencheur.** L'un de ces trois : une exigence de sécurité ou de conformité qu'un seul conteneur ne tient plus (AIPD,
exigence d'une institution partenaire) ; une charge qui impose des échelles différentes ; plusieurs personnes qui
travaillent sur des parties différentes. Pas le goût de l'architecture.

**À ne pas faire trop tôt.** Découper avant d'avoir deux utilisateurs réels du panel et du compte. Ajouter un tiers (un
fournisseur d'identité, un relais) sans avoir mesuré ce qu'il voit. Passer à PostgreSQL « au cas où » : les limites
sont déjà décrites dans le README et sont levées quand le besoin se présente.

### Fil transversal : pérennité, financement, indépendance

Ce n'est pas une phase mais une question posée à chaque déclencheur. Le site est aujourd'hui un projet personnel qui
tourne sur un petit serveur et dont le coût principal est celui des modèles.

**Décision d'Amiel (16/11/2026) : aucune monétisation n'est prévue, et l'affichage reste le titre, le nom du média et le
lien.** La question du droit voisin (4.3) et celle du modèle économique sont donc renvoyées à plus tard. Elles se
rouvrent au premier projet de monétisation ou au premier affichage au-delà du titre (extrait, résumé d'article).

- **Pistes de financement vues au paysage.** Abonnement léger pour les fonctions avancées, avec noyau gratuit (Ground
  News, 8,50 € par mois à l'année) ; services aux organisations (AllSides, d'après ses propres pages non relues) ; licence
  de données (NewsGuard, Ad Fontes) ; dons, adhésions, subventions : pas étudiés dans ce brief.
- **Contrainte forte.** Un financement par ceux que le site classe, ou par la publicité ciblée, compromettrait la
  neutralité. À écrire avant le premier euro.
- **Forme juridique.** Association (comme le French News Lab, loi 1901), société, fondation, coopérative : choix non fait.
  Il conditionne la responsabilité, la fiscalité, la gouvernance, l'accessibilité (4.7) et le droit voisin (4.3).

**Déclencheur d'une décision :** le premier euro attendu, ou le premier coût qui dépasse ce qu'Amiel veut payer seul, ou
la première personne qui travaillerait sur le site.

## 6. Les décisions structurantes à prendre tôt

Ce sont celles dont le changement coûte cher : elles touchent des données déjà collectées, des promesses faites, des
outils installés chez les lecteurs. Chacune dit pourquoi, la piste connue, ce qu'elle bloque si elle est mal prise.

1. **L'identité et les comptes.**
   *Pourquoi tôt :* une adresse mail devient un compte, puis un abonnement, puis un lien vers un panel. Chaque lien posé est
   difficile à défaire.
   *Piste :* compte stable par adresse, abonnements typés, rien de sensible dedans, connexion par code, session longue.
   *Mal prise :* un compte qui garde le bord, des préférences, ou un historique devient une base de données sensibles
   (4.1).
2. **Le découpage en services ou en sites.**
   *Pourquoi tôt :* pas pour découper maintenant, mais pour que les frontières existent dans le code dès le début.
   *Piste :* deux fichiers de données sans jointure (identité, urne), un module par fichier, des tests qui tiennent la
   séparation. Découper en services plus tard, le long de ces coutures. Nom de domaine et noms de chemins à choisir de
   façon à pouvoir héberger plus tard sur un sous-domaine séparé.
   *Mal prise :* un noyau où comptes, panel et pages publiques se mélangent dans les mêmes tables.
3. **La séparation des données.**
   *Pourquoi tôt :* elle porte la promesse « le compte sait qui, l'urne sait quoi ».
   *Piste :* trois tiroirs (identité, urne, appareil), avec les réglages sensibles sur l'appareil.
   *Mal prise :* une promesse affichée et non tenue, plus grave qu'une promesse non faite.
4. **Le modèle économique et l'indépendance.**
   *Pourquoi tôt :* il fixe qui peut payer le site, donc qui peut l'influencer. Il conditionne aussi le droit voisin et
   l'accessibilité.
   *Piste :* noyau gratuit, abonnement léger pour les fonctions avancées, aucun financement par les médias classés, aucune
   publicité ciblée.
   *Mal pris :* un financement qui crée une dépendance, puis une pression sur le classement.
5. **La gouvernance de la classification des médias.**
   *Pourquoi tôt :* c'est ce qui fait la crédibilité. Aujourd'hui, les sept bandes et les 30 scores viennent d'un tiers
   (FrIdéo, CC BY 4.0) et le site ne classe rien. Élargir le périmètre exige de décider qui classe les médias qui n'y sont pas.
   *Pistes :* rester dépendant de FrIdéo et se limiter à son périmètre ; contribuer avec le French News Lab pour étendre
   le classement ; construire une méthode propre, documentée, ouverte, avec un droit de réponse et un comité ; compléter
   par le vote à l'aveugle du panel, dans l'esprit d'AllSides.
   *Mal prise :* un classement maison sans méthode publique, ou un site qui a l'air de classer en secret.
6. **Le périmètre du compte vis-à-vis des alertes.**
   *Pourquoi tôt :* un type d'abonnement mal classé crée une donnée sensible sans qu'on s'en aperçoive.
7. **Où tourne le code qui parle à l'appareil de l'utilisateur** (site, extension, application installée).
   *Pourquoi tôt :* le serveur sert le JavaScript. Tant que le code est public et la page comparable à celle du dépôt,
   l'anonymat tient. Une extension distribuée par les boutiques fixe en plus un état de code que le serveur ne contrôle
   plus.

## 7. Les principes

### 7.1 Non négociables

1. **Le compte sait qui est la personne, jamais ce qu'elle pense. L'urne sait ce qui est pensé, jamais par qui.**
2. **Ce qui révèle une opinion reste sur l'appareil**, ou n'est jamais lié à un compte : médias suivis ou masqués,
   historique de lecture, bord déclaré.
3. **Aucun canal payant pour l'identité.** Ni SMS, ni vérification payante. Les parades contre les comptes multiples
   sont gratuites ; le tort résiduel est borné et dit.
4. **Aucun modèle ne compte, ne note, ni ne lit une réponse.** Les comptages se font par du code. Tout texte écrit par un
   modèle porte l'étiquette (DOCTRINE, règle 7).
5. **Ce site ne classe aucun média selon ses propres goûts.** Le classement a une méthode publique, une version datée,
   des limites écrites.
6. **Code et méthode publics.** Code sous AGPL-3.0, méthode publiée. Ce que le site dit de lui-même est vérifiable.
7. **Pas de publicité ciblée, pas de suivi inter-sites.** La mesure d'audience se fait sans cookie.
8. **Le noyau est gratuit et sans compte.** Lire n'exige rien.
9. **Les mots simples.** « Jeton », « signature », « clé » n'apparaissent dans aucun écran (premier cadrage, règle 15).
   Lisible à 375 px, accessible.
10. **Honnêteté sur les limites.** « Ce site ne garde aucun lien entre une personne et ses réponses ; il ne peut pas en
    reconstituer un après coup ; il ne protège pas contre un serveur piraté au moment même où la réponse est envoyée »
    (phrase du premier cadrage).

### 7.2 À discuter

- **Un modèle économique avec abonnement payant** : compatible avec « noyau gratuit », mais pas encore arbitré (question 3).
- **L'ouverture du panel à tout compte** ou le maintien d'un cercle invité (premier cadrage D7).
- **L'utilisation de modèles hébergés hors d'Europe** (aujourd'hui Anthropic) : compatible avec le RGPD tant qu'aucune
  donnée personnelle n'y passe, ce que garantit la séparation ; question de souveraineté à poser, non traitée ici.
- **Le multilinguisme et les autres pays.**
- **Des contributions publiques** (annotations, commentaires) : exclues pour l'instant (4.5).
- **Le nom et le domaine** : un site qui veut être une référence doit un jour avoir un nom qui se retient.

## 8. Les questions ouvertes pour Amiel

Chacune se tranche en une phrase.

1. Dans cinq ans, le site reste-t-il un projet d'Amiel, ou une structure à plusieurs (association, société, fondation) ?
2. Des collaborateurs auront-ils un jour accès au serveur ? Si oui, l'architecture doit tenir contre eux comme contre
   l'éditeur, et les accès aux journaux et aux sauvegardes deviennent un sujet de gouvernance.
3. ~~Le site peut-il porter, un jour, un abonnement payant ?~~ Répondu le 16/11/2026 : aucune monétisation prévue,
   question renvoyée à plus tard.
4. Quels financeurs sont exclus d'avance (médias classés, partis, annonceurs, fonds liés à un parti) ?
5. Le site doit-il rester sur les médias français, ou prévoir des déclinaisons dans d'autres pays ?
6. Le site accepte-t-il les alertes par sujet, sachant qu'elles disent ce qui intéresse quelqu'un, ou les limite-t-il à des
   catégories larges ?
7. Qui doit pouvoir contester le classement d'un média (le média lui-même, un chercheur, tout lecteur) et par quelle voie ?
8. Le nom et le domaine actuels (`compare-media.inflexion.me`) conviennent-ils à un site public durable ?
9. Veut-on dépendre durablement de FrIdéo, ou s'en émanciper pour les médias qu'il ne couvre pas ?
10. L'extension doit-elle d'abord n'afficher que le bord du média (sans rien envoyer), même si cela fait moins que Ground News ?
11. Safari vaut-il le coût (app, compte développeur payant) au début, ou après Chrome et Firefox ?
12. Faut-il une AIPD faite par un tiers (DPO, juriste) plutôt qu'en interne ?
13. Le site assume-t-il d'être un « fournisseur de services de la société de l'information » pour le droit voisin, et
    accepte-t-il de demander un avis juridique avant d'élargir l'affichage de titres ?
14. Un abonnement ou un panel réservé aux membres d'une communauté (écoles, rédactions) serait-il bienvenu, ou contraire à l'idée
    de neutralité ?
15. Quel volume de lecteurs ou d'abonnés fait passer de « projet » à « service » (seuil pour la phase 6) ?

## 9. Ce que le cadrage suivant doit produire

**À produire.**

- Une architecture cible, en trois horizons correspondant aux phases, avec les frontières entre composants (site public,
  identité, urne, extension) et les données qui les traversent.
- Un schéma de compte générique et le classement de chaque type d'abonnement (révèle une opinion, un peu, pas du tout).
- Un modèle de menace mis à jour pour l'extension, avec l'option « sans envoi d'adresse » comparée à l'option « avec envoi ».
- Le contrat de données de l'index de sujets destiné à l'extension : taille, mise à jour, sécurité, et ce qu'il révèle.
- Une proposition de gouvernance du classement : méthode, versions, droit de réponse, rôle de FrIdéo.
- Une grille de décision pour le passage de la phase 6 (découper ou non), avec ses seuils.
- Une liste des consultations juridiques à demander, avec la question exacte.

**À trancher.**

- L'extension fait-elle sa correspondance sur l'appareil, et à quelle granularité ?
- Où est la frontière du compte : quels types d'abonnements y sont admis, lesquels restent sur l'appareil ?
- Comment les parades contre les comptes multiples se combinent sans canal payant ?
- Quelle forme prend le droit de réponse d'un média classé ?
- Quelle est la réponse à la question du titre et du « très court extrait » ?
- Comment la neutralité financière se garantit-elle, par la structure ou par un engagement écrit ?
- Quels critères de l'AIPD et quel seuil de « grande échelle » s'appliquent à ce site ?

## 10. Sources

Vérifiées le 16/11/2026. « Lu » : le texte de la page a été lu. « Résumé » : lu via un résumé automatique du contenu
(la restitution peut omettre ou déformer). « Non lu » : cité d'après une recherche, un autre document ou la mémoire.

### 10.1 Paysage

- Ground News, À propos (lu) : <https://ground.news/about>
- Ground News, Rating system (lu) : <https://ground.news/rating-system>
- Ground News, abonnement, 8,50 €/mois à l'année (lu) : <https://ground.news/subscribe>
- Columbia Journalism Review, « The business of balance » (lu) : <https://www.cjr.org/analysis/the-business-of-balance-ground-news.php>
- Ground News, fiche de l'extension sur la boutique Chrome (**non lue**, redirection vers un écran de consentement) :
  <https://chromewebstore.google.com/detail/ground-news-bias-checker/agleiimpggapjekcdhdjbmegjbbkleie>
- Ground News, avis sur l'extension Firefox, affirmant un envoi des adresses visitées (**non vérifié**) :
  <https://addons.mozilla.org/en-US/firefox/addon/ground-news-bias-checker/reviews/>
- Ad Fontes Media, À propos (lu) : <https://adfontesmedia.com/about/>
- NewsGuard, À propos (lu) : <https://www.newsguardtech.com/about/>
- French News Lab, FrIdéo (lu) : <https://frenchnewslab.org/en/medias>
- AllSides, méthodes (**non lu**, HTTP 403) : <https://www.allsides.com/about/media-bias-rating-methods>
- AllSides, structure et revenus (**non lu**, vu par résultat de recherche) :
  <https://www.allsides.com/blog/allsides-biased-about-our-biases-partners-and-funding>
- Décodex, Le Monde (**état actuel non vérifié**, page non lisible par le robot) : <https://www.lemonde.fr/verification/>
- Freepress, NEXA (**non vérifiés**) : trouvés par recherche, sans page lue.

### 10.2 Droit

Les articles suivants ont été lus à travers un miroir de textes juridiques, version en vigueur. Le lien officiel d'EUR-Lex
n'est pas lisible par un robot : il est donné pour référence.

- Directive (UE) 2019/790, art. 15 : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32019L0790>
- Code de la propriété intellectuelle, L218-2 et L211-3-1 (lus) ; loi n° 2019-775 du 24 juillet 2019 (articles lus) :
  <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000038826732/2019-10-24>
- Règlement (UE) 2024/1083 (EMFA), art. 3, 6, 18 (extraits) : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32024R1083>
  (dates d'application **non vérifiées**)
- Règlement (UE) 2022/2065 (DSA), art. 19 (lu), art. 14 et 16 (**non lus**) :
  <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32022R2065>
- Règlement (UE) 2024/1689 (AI Act), art. 50 (lu, version en vigueur depuis le 27/07/2026) :
  <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32024R1689> ; règlement (UE) 2026/1744 du 8 juillet 2026 (« omnibus
  numérique sur l'IA », cité à propos de l'article 50, **non relu en entier**) :
  <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32026R1744> (adresse composée, non testée)
- Directive (UE) 2019/882, art. 4 (lu) : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32019L0882> ; décret n° 2023-931
  du 9 octobre 2023 (intitulé vu, **texte non lu**)
- Loi n° 2005-102 du 11 février 2005, art. 47, et décret n° 2019-768 du 24 juillet 2019 (extraits ; seuil de chiffre d'affaires
  **non lu**) : <https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000809647>
- RGPD, art. 9 (premier alinéa), 35 (lu) : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32016R0679>
- Directive 2002/58, art. 5 § 3 (lu) : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32002L0058>
- CNIL, cookies et autres traceurs, ce que dit la loi (lu) :
  <https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies/que-dit-la-loi>
- CJUE, 1er août 2022, C-184/20 (cité depuis le premier cadrage) :
  <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:62020CJ0184>
- Autorité de la concurrence, décision du 20 mars 2024 sur Google (**communiqué non lu**, faits d'après la presse, par exemple
  <https://siecledigital.fr/2024/03/20/google-ecope-dune-amende-de-250-millions-deuros-pour-non-respect-des-droits-voisins/>)

### 10.3 Boutiques d'extensions

- Chrome Web Store, politique de données utilisateur (lu) : <https://developer.chrome.com/docs/webstore/program-policies/user-data-faq>
- Firefox, consentement intégré aux données (lu aux 100 000 premiers caractères sur 102 912) :
  <https://extensionworkshop.com/documentation/develop/firefox-builtin-data-consent/>
- Apple, App Review Guidelines (lu aux 100 000 premiers caractères sur 114 384, via un résumé) :
  <https://developer.apple.com/app-store/review/guidelines/>
- Apple, conversion d'une extension web pour Safari (**non lu**, la page n'a rendu que son titre) :
  <https://developer.apple.com/documentation/safariservices/converting-a-web-extension-for-safari>

### 10.4 Premier cadrage

`docs/cadrage-panel-comptes.md` : sources sur les signatures aveugles (RFC 9474, 9576, 9578), Kagi, ANONIZE, Helios,
Belenios, CNIL, G29, CEPD 01/2025, CJUE C-413/23 P, NIST SP 800-63B-4, WebKit, Brevo. Non reprises ici : elles se lisent
là-bas, avec leur état de vérification.
