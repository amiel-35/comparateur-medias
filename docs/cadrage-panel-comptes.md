# Cadrage : comptes et panel

Cadrage du 16/11/2026. Rien n'est construit. Ce fichier se lit avant d'ouvrir la branche du prototype.
Les sources sont en fin de document, avec la date de vérification. Ce qui n'a pas pu être vérifié est dit.

## 1. L'intention

Deux choses, qui ne doivent jamais se toucher.

- **Un compte**, pour tout le monde : une adresse, la synthèse de la semaine, l'adhésion au panel.
- **Un panel** : des titulaires de compte qui acceptent d'être recontactés pour répondre à des questionnaires,
  une fois chacun, en donnant leur bord politique.

La règle qui tient tout : **le compte sait qui est la personne, jamais ce qu'elle pense. L'urne sait ce qui est
pensé, jamais par qui.** Ni l'éditeur, ni un voleur de la base ne doit pouvoir rapprocher les deux.

Contraintes : des mots simples, aucun matériel requis, aucun canal payant, bibliothèque standard de Python, pas
d'outil de construction côté site.

## 2. Périmètre

| Dans le chantier | Hors sujet |
|---|---|
| Compte par adresse mail, connexion par code | Mot de passe, connexion par Google ou Apple, FranceConnect |
| Adhésion au panel, sortie du panel | Échantillon représentatif, redressement, quotas |
| Questionnaires à réponse unique, bord joint à la réponse | Suivi d'une même personne d'un questionnaire à l'autre |
| Résultats par bord, au-dessus d'un seuil | Champs de texte libre, export des lignes brutes |
| Fusion de la synthèse par mail dans le compte | Préférences gardées sur le serveur, synchronisation entre appareils |
| Reprise du vote à l'aveugle (phase 2, après le prototype) | Vote vérifiable de bout en bout (Belenios, Helios) |

Le mot « sondage » est hors sujet aussi, au sens propre. La loi du 19 juillet 1977 le réserve aux enquêtes sur
un échantillon choisi pour être représentatif (art. 1er), et punit de 75 000 € son emploi pour une enquête liée au
débat électoral qui ne l'est pas (art. 12). Un panel de volontaires publie une **consultation**, jamais un sondage.

## 3. Ce qui existe, et ce qu'on en fait

| Existant | Sort |
|---|---|
| `abonnes` (adresse en clair, jeton, double confirmation), `lettre.py` | **Devient le compte.** Un abonné confirmé est un compte dont la case « synthèse de la semaine » est cochée. L'envoi du lundi, la désinscription en un clic (RFC 8058) et les journaux sans adresse sont gardés tels quels. |
| `lettre.Envoi`, `FauxSMTP` des tests, `config.mail()` | **Réutilisés.** Sans réglage SMTP, ni compte ni panel : même convention que la lettre. |
| `Debit`, réponse identique quelle que soit l'adresse, champ caché contre les robots | **Réutilisés** pour la demande de code. |
| `invitations` (codes à usage unique) | **Gardées**, pour l'entrée au panel tant qu'il reste un cercle invité. |
| `votants`, `avis_aveugle`, `avis_note`, `aveugle.html` | **Intacts pendant le prototype.** Remplacés en phase 2 (voir plus bas). |
| `aveugle.compter` (moyenne par bord, puis moyenne des bords), `COMPARATEUR_MIN_PAR_BORD` | **Réutilisés** pour les résultats des questionnaires. |
| Page `#/mentions` : « Ce site ne dépose aucun cookie » | **À réécrire** si la session passe par un cookie (décision D3). |

**Une faiblesse de l'existant, à dire.** Le README annonce « aucun lien entre une invitation et un votant ».
C'est vrai dans le schéma, pas dans les faits. L'éditeur sait à qui il a envoyé chaque code. `invitations.utilisee_le`
et `votants.cree` portent le même jour. Avec une ou deux inscriptions par jour, le rapprochement code → votant → bord
se fait à la main. Et un votant garde le même identifiant de lot en lot : c'est un pseudonyme, pas un anonymat.
La signature aveugle corrige le premier point. Le second est un choix (décision D6).

**Migration des votants actuels.** Ils n'ont pas d'adresse en base : aucune conversion automatique n'est possible,
et c'est bien ainsi. Leur jeton continue de marcher. La page du vote leur propose de créer un compte ; cette
création n'envoie jamais leur jeton de votant. En phase 2, l'inscription au vote à l'aveugle accepte, à la place
du code d'invitation, une « carte de votant » signée à l'aveugle, délivrée une fois par membre du panel et par
trimestre. Les anciens votants s'éteignent avec leur jeton. Aucune ligne n'est réécrite.

## 4. État de l'art

**Signatures aveugles.** Le signataire signe un message qu'il ne voit pas ; la signature, une fois dévoilée par
le client, est valide et ne peut pas être rapprochée de la demande. L'idée est de Chaum (1982). La RFC 9474
(IRTF, octobre 2023) en fixe la version RSA : quatre variantes, toutes en SHA-384 et PSS ; les variantes
« Randomized » sont recommandées. Le résultat se vérifie comme une signature RSA-PSS ordinaire. Deux exigences
utiles ici : la clé ne sert à rien d'autre (§6.2, §7.2), et le signataire se protège des attaques par mesure du
temps, par exemple en masquant ses calculs (§7.1).

**Privacy Pass.** Les RFC 9576, 9577 et 9578 (IETF, juin 2024) décrivent des jetons anonymes à usage unique. Le
type 2 est une signature RSA aveugle de 2048 bits, vérifiable par tous (RFC 9578, §6). La RFC 9576 nomme
exactement le cas de ce site, où un seul opérateur tient tous les rôles (§4.1) : l'anonymat ne repose alors plus
sur la non-collusion, mais sur la séparation de la délivrance et de l'usage « dans le temps » ou « dans l'espace »
(service d'anonymisation). Elle prévient que l'adresse IP partitionne les clients (§3.3) et que la corrélation
temporelle réduit l'ensemble d'anonymat (§6.3). Kagi applique ce schéma depuis février 2025 pour séparer le compte
payant des recherches, et écrit les mêmes limites : l'adresse IP reste visible, la délivrance n'est pas anonyme.

**Questionnaires anonymes.** ANONIZE (Hohenberger, Myers, Pass, shelat, IEEE S&P 2014) traite le même problème :
une autorité désigne des inscrits par leur adresse, chacun répond une fois, anonymement. La construction est plus
lourde (preuves à divulgation nulle). Elle confirme que le besoin est classique et que la réponse est toujours la
même : un jeton délivré à l'identité, dépensé sans elle.

**Vote en ligne.** Helios (Adida, USENIX Security 2008) et Belenios (LORIA, Inria, CNRS, AGPL-3.0) ajoutent la
vérifiabilité : chacun contrôle que son bulletin est compté. C'est plus que ce qu'il faut ici. La CNIL demande
pour le vote par correspondance électronique un niveau de sécurité gradué en trois niveaux de risque
(délibération 2019-053, remplacée par la délibération 2026-045 du 19 mars 2026, texte non lu). Ses avis anciens
répètent une exigence qui vaut pour une urne : l'émargement et les bulletins sur des systèmes « distincts et
isolés ».

**Dans un navigateur, sans dépendance.** `crypto.subtle` vérifie une signature RSA-PSS (avec `saltLength`) mais
n'offre aucune opération RSA brute : l'aveuglement se fait en `BigInt`, disponible partout depuis septembre 2020.
MDN prévient que `BigInt` n'est pas à temps constant. Ici c'est sans gravité : le client ne manipule aucun secret
durable, seulement un aléa jetable. Cloudflare publie `blindrsa-ts`, conforme à la RFC 9474, qui s'appuie sur
WebCrypto : la chose est faite ailleurs. Mesuré sur ce poste le 16/11/2026 : aveuglement et inverse modulaire en
1 ms (Node, `BigInt`) ; côté Python, signature en 17 ms par `pow(m, d, n)`, génération d'une clé de 2048 bits en
1,5 s. Compter 150 lignes de JavaScript et 120 de Python.

**Anonymisation, pseudonymisation, données sensibles.**
- CNIL : une donnée est anonyme si l'on ne peut ni individualiser, ni corréler, ni inférer. Si un critère manque,
  le responsable doit démontrer que le risque de réidentification est négligeable. Le G29 (avis 05/2014) dit la
  même chose et rappelle que la pseudonymisation n'est pas une anonymisation.
- CEPD, lignes directrices 01/2025 (adoptées le 16 janvier 2025, version de consultation ; version finale non
  trouvée) : une donnée pseudonymisée reste personnelle, même quand l'information de rattachement est chez un
  autre, et même effacée tant que les conditions de l'anonymat ne sont pas réunies.
- CJUE, 4 septembre 2025, C-413/23 P, CEPD c. CRU : le caractère identifiable s'apprécie du point de vue de celui
  qui détient la donnée et de ses moyens. Lecture prudente : cela ne dispense de rien un responsable qui tient
  les deux tiroirs.
- CJUE, 1er août 2022, C-184/20, OT : la piste était juste. L'article 9 couvre les données qui dévoilent
  « indirectement, au terme d'une opération intellectuelle de déduction ou de recoupement » une information
  sensible (points 120 à 123 et suivants). L'arrêt du 4 juillet 2023, C-252/21, Meta, l'applique à la
  consultation de sites. Les médias suivis ou masqués sur un comparateur politique en relèvent.
- CNIL : les opinions politiques sont des données sensibles ; l'exception utilisable est le consentement exprès.
  Une AIPD s'impose dès deux critères sur neuf.

**Connexion par mail.** Les antivirus de messagerie ouvrent les liens : des liens à usage unique sont consommés
avant le clic (témoignages nombreux sur Safe Links, peu de documentation officielle). Le site y répond déjà par
un bouton. Le NIST (SP 800-63B-4, §3.1.3.1) interdit le mail comme second facteur : un code par mail ne prouve
que l'accès à la boîte. C'est acceptable à une condition, qui est la doctrine elle-même : le compte ne garde rien
de sensible.

**Notifications.** Sur iPhone, le web push exige iOS 16.4 et une application ajoutée à l'écran d'accueil
(WebKit, 2023). Côté serveur, VAPID impose une signature ECDSA P-256 (RFC 8292, §2), absente de la bibliothèque
standard de Python.

**Stockage sur l'appareil.** Safari efface le stockage écrit par script (dont `localStorage`) après sept jours
d'usage sans visite du site ; les applications installées ont leur propre compteur (WebKit, 2020).

**Brevo.** 300 mails par jour sur l'offre gratuite (chiffre lu dans un résultat de recherche, page Brevo non relue : à vérifier dans le compte). Le suivi des clics et des
ouvertures des mails transactionnels ne se coupe pas message par message, et sa coupure complète serait réservée
à certaines offres (forum Brevo, messages anciens : à vérifier dans le compte).

## 5. Doctrine d'architecture

### Trois tiroirs

| Tiroir | Où | Contient | Ne contient jamais |
|---|---|---|---|
| **Identité** | `identites.db`, nouveau fichier | adresse, case « lettre », case « panel », sessions, codes de connexion, liste « a retiré son bulletin » par questionnaire ouvert, clés privées des questionnaires ouverts | bord, réponse, média suivi, historique de lecture, date plus fine que le jour |
| **Urne** | `comparateur.db`, l'actuel | par réponse : empreinte du bulletin, questionnaire, bord, réponses. Les questionnaires et leurs clés publiques. | adresse, identifiant de compte, session, IP, date, ordre d'arrivée |
| **Appareil** | `localStorage` du navigateur | bord déclaré, bulletins non dépensés, reçus des réponses envoyées, médias suivis ou masqués, thème | rien qui doive survivre à la perte de l'appareil |

Deux fichiers SQLite, et non deux groupes de tables : aucune jointure n'est possible sans un `ATTACH`, qu'un test
interdit. Les deux fichiers se sauvegardent à part.

### Qui sait quoi

| | Qui est membre | Qui a retiré un bulletin | Le bord d'une personne | La réponse d'une personne |
|---|---|---|---|---|
| Guichet (`comptes.py`) | oui | oui, jusqu'à la clôture | non | non |
| Urne (`urne.py`) | non | non | non : un bord par réponse, sans nom | non |
| Brevo | oui (il envoie les mails) | non | non | non |
| L'appareil | le sien | le sien | le sien | les siennes |

### Les flux

1. **Compte.** Adresse → code à 6 chiffres par mail → session. Première connexion et connexions suivantes : le
   même écran. Le compte naît à la première saisie d'un bon code.
2. **Panel.** Case cochée dans le compte, avec le consentement exprès. Le bord est demandé à ce moment, gardé sur
   l'appareil, et n'est pas envoyé au guichet.
3. **Ouverture d'un questionnaire.** En ligne de commande, comme `inviter` : une paire de clés RSA 2048 propre au
   questionnaire, la liste des membres figée (seuls les membres d'avant l'ouverture peuvent retirer un bulletin),
   un mail identique pour tous, sans lien personnel.
4. **Retrait du bulletin.** L'appareil tire 32 octets au hasard, les aveugle, les envoie au guichet avec la
   session. Le guichet vérifie : membre, pas encore de retrait. Il signe sans voir, note « retiré », répond.
   L'appareil dévoile la signature et la vérifie avec `crypto.subtle`.
5. **Dépôt.** Requête sans session, sans cookie, sans en-tête d'identité : bulletin, signature, bord, réponses.
   L'urne vérifie la signature avec la clé publique, refuse un bulletin déjà vu, écrit la ligne sous l'empreinte
   du bulletin. Table `WITHOUT ROWID` : l'ordre physique est celui des empreintes, pas des arrivées.
6. **Effacement.** L'appareil qui garde son reçu (le bulletin) peut faire effacer sa ligne. Personne d'autre.
7. **Clôture.** La clé privée est détruite. La liste des retraits est supprimée. L'urne est compactée (`VACUUM`).
   Les effectifs « bulletins délivrés » et « réponses reçues » sont publiés. Après cela, plus personne ne peut
   fabriquer un bulletin, ni savoir qui a participé.
8. **Résultats.** Calculés par formule (`aveugle.compter`). Rien n'est montré avant la clôture, ni sous le seuil
   par bord.

### Modèle de menace

| Menace | Couvert | Pas couvert |
|---|---|---|
| **Vol de la base** (un fichier, les deux, une sauvegarde) | Aucune ligne ne relie une adresse à un bord ou à une réponse. La clé privée volée permet de bourrer une urne ouverte, jamais de lever un anonymat. | La liste des adresses et des membres du panel fuit. Deux sauvegardes successives montrent qui a retiré un bulletin et quelles réponses sont arrivées entre les deux : avec peu de monde, cela rapproche. |
| **Administrateur curieux** qui lit les fichiers | Comme ci-dessus. La signature aveugle l'empêche de rapprocher un retrait d'un dépôt, même en lisant tout. | S'il observe l'urne en continu pendant un questionnaire, il voit une ligne naître juste après un retrait. Parade partielle : résultats et lecture seulement après clôture, par discipline, pas par construction. |
| **Serveur compromis en direct** | Les réponses déjà déposées restent sans nom. | Tout ce qui passe pendant la compromission : même adresse IP et instants voisins pour le retrait et le dépôt (RFC 9576, §3.3 et §6.3). Et surtout : le serveur sert le JavaScript. Un code modifié peut tout dévoiler. Seule parade : code public, page servie comparable à celle du dépôt. |
| **Journaux du proxy** (Coolify, Traefik) | Le serveur Python n'écrit ni IP ni paramètres. | Si le proxy journalise les accès (IP, heure, chemin), le rapprochement est immédiat. À vérifier et couper avant toute ouverture (décision D9). |
| **Brevo** | Ne voit que des adresses, des codes et un mail d'annonce identique pour tous. | Sait qui est membre. Si le suivi des clics reste actif, sait qui a cliqué sur l'annonce. Parade : annonce en texte seul, sans lien. |
| **Recoupement** | Pas de texte libre. Deux questions de profil au plus, à modalités larges. Aucun croisement publié sous le seuil. Pas de lien entre questionnaires. | Dans un petit cercle, un bord rare plus une réponse rare désignent quelqu'un. Le seuil réduit le risque à la publication, pas dans la base. |
| **Comptes multiples** | Voir section 9. Le tort est borné, pas empêché. | Une personne décidée, avec dix adresses et dix invitations, répond dix fois. |
| **Vol d'un compte** (boîte mail lue par un tiers) | Le voleur ne lit rien : ni bord, ni réponse passée. | Il peut désinscrire, quitter le panel, ou retirer le bulletin à la place du membre. |

En une phrase honnête, à écrire telle quelle sur le site : *ce site ne garde aucun lien entre une personne et ses
réponses ; il ne peut pas en reconstituer un après coup ; il ne protège pas contre un serveur piraté au moment
même où la réponse est envoyée.*

## 6. Doctrine de code

Dans l'esprit de `DOCTRINE.md` : des règles courtes, chacune tenue par un test.

1. **Deux fichiers, aucune jointure.** `comptes.py` n'ouvre que `identites.db`. `urne.py` n'ouvre que
   `comparateur.db`. *Tests : aucun des deux modules n'importe l'autre ; le mot `ATTACH` n'apparaît nulle part
   dans le paquet.*
2. **Aucune colonne commune.** Hors `questionnaire`, aucun nom de colonne n'existe à la fois dans une table
   d'identité et dans une table de l'urne. Aucune clé étrangère ne traverse. *Test : lecture de `PRAGMA
   table_info` des deux fichiers.*
3. **Le mot « bord » n'existe pas côté identité.** Ni colonne, ni clé JSON, ni paramètre de route. *Test : recherche
   dans `comptes.py` et dans le schéma d'`identites.db`.*
4. **L'urne refuse l'identité.** Une requête vers `/api/urne/` qui porte un en-tête `Cookie` ou `Authorization`
   reçoit 400, avant toute lecture du corps. Le cookie de session est limité au chemin `/api/compte`. *Tests : le
   refus ; l'attribut `Path` du cookie.*
5. **L'urne n'a ni heure ni rang.** Tables `WITHOUT ROWID`, clé = empreinte du bulletin, aucune colonne de date,
   aucun `AUTOINCREMENT`. *Test : schéma ; cent dépôts dans un ordre, relus dans l'ordre des empreintes.*
6. **Une clé par questionnaire, un seul usage.** La clé ne signe que des bulletins de ce questionnaire. La
   clôture la détruit et vide les retraits. *Test : après clôture, plus de clé privée, plus de retraits, un
   retrait répond 410.*
7. **Une signature par compte et par clé.** Contrainte d'unicité, pas vérification applicative. Elle borne aussi
   les attaques par mesure du temps. *Test : deux retraits simultanés, un seul passe.*
8. **La cryptographie suit la RFC, vecteurs à l'appui.** `signature.py` et `js/aveugle-rsa.js` passent les
   vecteurs d'essai de l'annexe A de la RFC 9474 (variante RSABSSA-SHA384-PSS-Randomized). La signature du
   serveur est masquée et revérifiée avant d'être rendue (RFC 9474, §4.3 et §7.1). *Tests : les vecteurs, des deux
   côtés ; un bulletin signé en Python vérifié en JavaScript et l'inverse.*
9. **Rien d'écrit sur une personne.** Les journaux comptent, ils ne nomment pas : ni adresse, ni IP, ni empreinte
   de bulletin. *Test : la sortie standard d'un parcours complet ne contient aucune de ces chaînes.*
10. **Les dates de l'identité sont arrondies.** Au jour pour la création, au mois pour la dernière visite.
    *Test : format des colonnes.*
11. **Pas de mesure sur les pages du compte et du panel.** Ni Umami, ni script tiers. Le service worker ne touche
    pas `/api/`. *Test : la page publiée ne contient pas l'origine d'Umami ; `sw.js` laisse passer `/api/`.*
12. **Aucun modèle ne lit une réponse.** Les résultats sont des comptages (règle 7 de `DOCTRINE.md`).
13. **Un questionnaire se refuse lui-même.** À l'ouverture, le code rejette un champ de texte libre, plus de deux
    questions de profil, une modalité de profil trop fine. *Test : trois questionnaires fautifs refusés.*
14. **Éteint sans mail.** Sans réglage SMTP : aucune route `/api/compte/`, aucun écran. *Test : comme
    `MailEteint`.*
15. **Le ton.** Les mots « jeton », « signature », « clé », « anonymisation » n'apparaissent dans aucun écran.
    *Test : recherche dans les pages publiées du compte et du panel.*

## 7. Les parcours, écran par écran

Une page à part, `compte.html`, comme `aveugle.html` et `mail.html`. Lisible à 375 px.

**Créer un compte, se connecter (le même parcours).**
1. « Votre adresse mail ». Un champ, un bouton : « Recevoir un code ».
2. « Un code vient de partir à cette adresse. Tapez-le ici. » Six cases. Sous les cases : « Le code vaut dix
   minutes. Rien reçu ? Regardez les indésirables, ou redemandez-le. »
3. « Vous êtes connecté sur cet appareil. » Trois lignes : la synthèse de la semaine (case), le panel (bouton
   « En savoir plus »), « Ce que ce site sait de vous ».

**Ce que ce site sait de vous.** Deux colonnes. « Gardé par le site : votre adresse, vos deux cases. » « Gardé
sur cet appareil seulement : votre bord, les journaux que vous suivez. » Un bouton : « Supprimer mon compte ».

**Rejoindre le panel.**
1. « De temps en temps, quelques questions. Vous répondez si vous voulez. Vos réponses partent sans votre nom :
   ce site ne peut pas savoir lesquelles sont les vôtres. »
2. « Où vous situez-vous ? » Cinq cases, de gauche à droite. « Ce choix reste sur cet appareil. Il part avec
   chacune de vos réponses, jamais avec votre nom. »
3. Case à cocher, non cochée : « J'accepte que mes réponses et le bord que j'indique servent aux résultats publiés
   par ce site. » Bouton : « Rejoindre le panel ». Tant que le panel est un cercle invité : un champ « Code
   d'invitation ».

**Répondre.**
1. Le mail : « Un nouveau questionnaire est ouvert jusqu'au 30 novembre. Ouvrez Cadrages, rubrique Panel. »
2. Dans l'application : « Trois questions sur la confiance dans les médias. Deux minutes. » Bouton : « Commencer ».
   Le bulletin est retiré à ce clic, sans rien montrer.
3. Le bord, déjà coché si l'appareil s'en souvient. Puis les questions, une par écran.
4. « Envoyer mes réponses. Une fois parties, elles ne portent pas votre nom. Vous pourrez les effacer depuis cet
   appareil seulement. »
5. « C'est envoyé. Les résultats seront publiés après le 30 novembre. »
6. Si un bulletin a déjà été retiré ailleurs : « Vous avez déjà commencé ce questionnaire sur un autre appareil.
   Finissez-le là-bas. »

**Changer de téléphone.** Sur le nouveau : adresse, code, c'est fait. Le compte et ses cases sont là. Le bord
est redemandé au prochain questionnaire, en un geste. Les journaux suivis sont à refaire, ou repris de l'ancien
téléphone par un code affiché à l'écran (plus tard, idée 9). Dit en une ligne : « Vos réglages personnels ne
sont pas sur nos serveurs. Ils ne suivent pas tout seuls. »

**Quitter le panel.** Dans le compte : « Quitter le panel ». Un écran : « Vous ne recevrez plus de questionnaire.
Vos réponses déjà envoyées ne portent pas votre nom : ce site ne peut pas les retrouver. Depuis cet appareil,
vous pouvez les effacer. » Deux boutons : « Quitter », « Quitter et effacer mes réponses ».

## 8. RGPD

**Responsable.** L'éditeur du site. Sous-traitants : Brevo (envoi), l'hébergeur du serveur. À inscrire au
registre.

| Traitement | Base légale | Conservation |
|---|---|---|
| Compte (adresse, session) | Exécution du service demandé (art. 6-1-b) | Jusqu'à suppression ; effacé après 24 mois sans connexion, un mail d'avertissement avant |
| Synthèse de la semaine | Consentement (art. 6-1-a), double confirmation gardée | Jusqu'à désinscription |
| Appartenance au panel, annonces | Consentement (art. 6-1-a) | Jusqu'à la sortie du panel |
| Liste des retraits de bulletin | Intérêt légitime : une réponse par membre (art. 6-1-f) | Jusqu'à la clôture du questionnaire |
| Réponses et bord | Consentement exprès (art. 9-2-a), case non cochée par défaut | Lignes : 12 mois après clôture. Résultats agrégés : sans limite |
| Codes de connexion | Exécution du service | 10 minutes |

**Article 9.** Le bord est une opinion politique. Les réponses le sont souvent. Les médias suivis ou masqués le
sont par déduction (C-184/20, C-252/21) : ils restent sur l'appareil, donc hors traitement. C'est le gain le plus
net de la doctrine.

**AIPD.** Deux critères sur neuf sont plausibles : données sensibles, usage innovant. Recommandation : la faire,
courte, avec l'outil PIA de la CNIL, avant d'ouvrir au-delà du cercle invité. Le modèle de menace de la section 5
en fournit l'essentiel.

**Droits.** Sur le compte : accès, rectification, effacement, depuis l'écran « Ce que ce site sait de vous »,
sans écrire à personne. Sur les réponses : l'éditeur ne peut pas identifier la personne (art. 11). Elle exerce
ses droits en présentant son reçu, que seul son appareil détient (art. 11-2). C'est dit avant l'envoi. Retrait du
consentement : sortie du panel pour l'avenir ; effacement par le reçu pour le passé.

**Urne anonyme ou urne pseudonyme : ce qui change.**

| | Sans lien entre questionnaires (proposé) | Avec un pseudonyme stable (le vote à l'aveugle actuel) |
|---|---|---|
| Statut | Vise l'anonymat. Traité comme sensible par prudence : dans un petit panel, l'individualisation reste possible. | Donnée personnelle sans discussion (CEPD 01/2025). Article 9 plein. |
| Droits | Par le reçu (art. 11) | Par le jeton, à organiser entièrement |
| Durée | Agrégats sans limite | Limitée, à justifier |
| Risque | Stable | Croît à chaque réponse : le profil s'épaissit |
| AIPD | Recommandée | Nécessaire |

Le mot « anonyme » ne s'écrit sur le site qu'avec sa limite. « Sans votre nom » est plus juste et plus simple.

**Âge.** 15 ans, seuil du consentement en France pour un service en ligne : une ligne sur l'écran d'adhésion.

## 9. Idées proposées

1. **Le bord voyage avec la réponse, jamais avec le compte.** Demandé une fois, gardé sur l'appareil, rejoué à
   chaque questionnaire. L'éditeur connaît le bord de chaque réponse et la répartition du panel, jamais le bord
   de quelqu'un.
2. **Le recensement.** Pour connaître la composition du panel sans la rattacher aux comptes : un questionnaire
   d'une seule question (le bord), ouvert à l'adhésion et refait chaque année. L'ancien est jeté. La dérive due
   aux départs se corrige d'elle-même.
3. **Le reçu.** Le bulletin gardé par l'appareil vaut droit d'effacement. Un droit RGPD exercé sans s'identifier.
4. **Le panel figé à l'ouverture.** Seuls les membres d'avant l'ouverture peuvent répondre. Créer dix comptes en
   découvrant les questions ne sert à rien. Gratuit, une ligne de code.
5. **La clôture comme cérémonie.** Clé détruite, retraits effacés, urne compactée, deux effectifs publiés. Chacun
   peut vérifier qu'il n'y a pas plus de réponses que de bulletins.
6. **« Ce que ce site sait de vous ».** La promesse devient un écran. Deux colonnes, rien d'autre.
7. **Deux fichiers.** La séparation la moins chère qui soit, et la seule qu'un test tient vraiment.
8. **La carte de votant** (phase 2). Le vote à l'aveugle passe par le même guichet. Renouvelée chaque trimestre,
   elle coupe aussi le pseudonyme en tranches : un profil ne s'épaissit pas au-delà de trois mois.
9. **Le passage de témoin** (plus tard). L'ancien téléphone affiche un code ; le nouveau le lit et reprend bord et
   journaux suivis. Rien ne passe par le serveur.
10. **Le facteur** (plus tard, si le panel grossit). Un relais tenu par un tiers reçoit les dépôts chiffrés pour
    l'urne et les transmet : le serveur ne voit plus l'adresse IP, le relais ne voit pas le contenu. C'est la
    séparation « dans l'espace » de la RFC 9576. Coût : un tiers de plus à nommer.

**Comptes multiples, sans SMS.** Aucun moyen gratuit ne prouve qu'une personne est unique. L'objectif est de
borner le tort et de le dire.
- Invitations : le panel reste un cercle invité au départ. Les codes sont donnés par l'éditeur, pas multipliés par
  les membres (un parrainage libre et sans trace laisserait un tricheur s'inviter lui-même sans fin).
- Une adresse, un compte, après normalisation (`+suffixe` retiré) et refus des domaines jetables (liste publique
  sous CC0).
- Panel figé à l'ouverture, plus un délai de carence de sept jours.
- Le comptage existant : moyenne par bord, puis moyenne des bords. Bourrer un bord ne le fait pas peser plus.
- La détection statistique dans l'urne est impossible par construction, et c'est voulu. Reste un seul signal
  licite : un afflux d'adhésions avant une ouverture.
- L'étiquette, sur chaque résultat : « Panel de volontaires. Ce n'est pas un sondage. »

## 10. Désaccords avec les pistes évoquées

1. **Les notifications web push à la place du mail : non.** Elles exigent l'installation sur iPhone, donc un
   prérequis. VAPID impose une signature ECDSA absente de la bibliothèque standard. Et le service de push
   d'Apple, Google ou Mozilla devient un tiers de plus. Le mail reste le canal.
2. **Adresses en empreinte HMAC, ou chiffrées avec une clé hors serveur : non, pas en première version.**
   Recontacter le panel et envoyer la lettre demandent l'adresse en clair, chaque lundi, sans intervention.
   Python n'a aucun chiffrement dans sa bibliothèque standard. Brevo voit les adresses de toute façon. La chose à
   protéger n'est pas l'adresse, c'est le lien entre l'adresse et l'opinion : l'effort va là.
3. **Passkey en option : pas maintenant.** Vérifier une passkey côté serveur demande ECDSA et CBOR, hors
   bibliothèque standard. Et le compte ne garde rien qui mérite un second moyen de connexion.
4. **« Le compte garde des préférences » : non, il ne garde presque rien.** Si les préférences restent sur
   l'appareil, le compte se réduit à une adresse et deux cases. C'est une bonne nouvelle : il se construit comme
   une extension de `abonnes`, pas comme un système de comptes.
5. **La signature aveugle : oui, mais elle promet moins qu'il n'y paraît.** Un seul opérateur tient le guichet et
   l'urne. Adresse IP, instants voisins, JavaScript servi par le serveur, journaux du proxy : rien de cela n'est
   couvert. La RFC 9576 le dit en toutes lettres. Elle couvre le vol de base et la lecture après coup, ce qui est
   déjà la demande.
6. **`WITHOUT ROWID` et pas d'heure : oui, et insuffisant.** Deux sauvegardes successives redonnent un ordre.
   D'où la clôture (idée 5) et la lecture de l'urne seulement après elle.
7. **Le code à 6 chiffres : oui**, à la condition écrite plus haut. Sans la règle « le compte ne sait rien », il
   serait trop faible.
8. **Détection statistique des doublons : contradictoire** avec une urne sans identité. À abandonner comme piste.

## 11. Décisions à trancher

| | Décision | Recommandation |
|---|---|---|
| D1 | Signature aveugle RFC 9474, ou simple séparation de tables sans cryptographie | **Signature aveugle.** C'est la seule réponse à « l'éditeur lui-même ne peut pas ». 270 lignes, vecteurs d'essai publics. |
| D2 | Tout en bibliothèque standard, ou une dépendance (`cryptography`) | **Bibliothèque standard.** Signature par `pow`. Clés engendrées par `openssl`, outil du système et non dépendance Python (présence dans l'image à vérifier), hors du chemin des requêtes. |
| D3 | Session par cookie (`HttpOnly`, chemin `/api/compte`) ou par jeton en `localStorage` comme `aveugle.html` | **Cookie.** Il survit à l'effacement de sept jours de Safari. Coût : réécrire « aucun cookie » en « un seul cookie, pour rester connecté » ; pas de bandeau, il est strictement nécessaire. |
| D4 | Bord gardé sur l'appareil et joint à chaque réponse, ou gardé dans une table à part | **Sur l'appareil.** Plus le recensement (idée 2) pour la composition du panel. |
| D5 | Fusionner `abonnes` dans les comptes, ou garder la lettre à part | **Fusionner**, après le prototype. Un abonné confirmé devient un compte, sans rien lui demander. |
| D6 | Questionnaires sans lien entre eux, ou suivi d'un même répondant | **Sans lien.** Le suivi fait de l'urne une donnée pseudonyme et épaissit les profils. À rouvrir seulement sur un besoin d'étude précis. |
| D7 | Panel ouvert à tout compte, ou cercle invité | **Cercle invité** d'abord, codes donnés par l'éditeur. Ouverture après l'AIPD et un premier questionnaire. |
| D8 | Seuil de publication | **10 réponses par bord** pour un résultat, rien sous 5. Rien avant la clôture. |
| D9 | Journaux d'accès du proxy de Coolify | **Les vérifier et les couper** pour ce site, ou au moins pour `/api/`. Sans cela, D1 ne sert à rien. Non vérifié : la page de Traefik n'a pas pu être lue. |
| D10 | Suivi des clics et des ouvertures de Brevo | **Vérifier dans le compte.** S'il ne se coupe pas : annonces en texte seul, sans lien. |
| D11 | Quota de 300 mails par jour | **L'accepter** : sessions de 12 mois pour limiter les codes, annonces étalées sur plusieurs jours au-delà de 250 membres. Payer Brevo est l'autre choix. |
| D12 | Bulletin retiré au début du questionnaire, ou à l'envoi | **Au début.** Quelques minutes d'écart valent mieux que zéro. Prix : un bulletin peut se perdre avec le stockage du navigateur. |
| D13 | Vote à l'aveugle : le laisser, ou le passer à la carte de votant | **Le laisser pendant le prototype**, le passer en phase 2. Corriger tout de suite la phrase du README sur l'absence de lien. |
| D14 | AIPD | **La faire** avant l'ouverture au-delà du cercle invité. |
| D15 | Variante RFC 9474 | **RSABSSA-SHA384-PSS-Randomized**, 2048 bits : celle que la RFC recommande, vérifiable par `crypto.subtle`. |

## 12. Le prototype

Branche `proto/panel-comptes`. Données dans un dossier d'essai (`COMPARATEUR_DONNEES=/tmp/essai`). Rien n'est
déployé, rien n'est fusionné.

**Ce qu'il doit prouver.**
1. La signature aveugle tient en bibliothèque standard côté serveur et sans dépendance côté navigateur.
2. La séparation est tenue par des tests, pas par une intention.
3. Une personne qui n'a jamais entendu le mot « jeton » va de l'adresse mail à la réponse envoyée sans aide.

**Ce qu'il construit.** `signature.py`, `comptes.py`, `urne.py`, les routes `/api/compte/…` et `/api/urne/…`,
`compte.html`, `js/aveugle-rsa.js`, trois commandes (`questionnaire ouvrir`, `fermer`, `resultats`), un
questionnaire d'essai de trois questions.

**Ce qu'il laisse de côté.** La fusion d'`abonnes`. Le vote à l'aveugle et la carte de votant. Le recensement.
Le passage de témoin, le facteur, les passkeys, le push. L'envoi réel par Brevo (`FauxSMTP` suffit). Le refus des
domaines jetables. La purge des comptes inactifs. L'AIPD.

**C'est fini quand.**
- [ ] `python3 -m unittest discover -s tests` passe, les 31 tests actuels compris.
- [ ] Les vecteurs de l'annexe A de la RFC 9474 passent en Python et en JavaScript (Node), et un bulletin signé
      d'un côté se vérifie de l'autre.
- [ ] Un test déroule le parcours entier avec `FauxSMTP` : code, session, adhésion, retrait, dépôt, clôture,
      résultats.
- [ ] Un second retrait répond 409 ; un second dépôt du même bulletin répond 409 ; un bulletin forgé répond 403.
- [ ] Un dépôt qui porte un cookie ou un en-tête `Authorization` répond 400.
- [ ] Les tests des règles 1, 2, 3, 5, 6, 9 et 15 de la section 6 existent et passent.
- [ ] Après la clôture : `identites.db` ne contient plus ni clé privée ni retrait ; un script d'essai qui reçoit
      les deux fichiers ne trouve aucune valeur commune hors les identifiants de questionnaire.
- [ ] Après cent dépôts, la sortie standard du serveur ne contient ni adresse, ni IP, ni empreinte.
- [ ] `essais/rendu.js` ouvre chaque écran de `compte.html` à 375 px et 1280 px, en clair et en sombre, sans
      erreur de console ni défilement horizontal.
- [ ] Le parcours « répondre » est fait à la main sur Safari iPhone, Chrome Android et Firefox, et noté dans la
      branche.
- [ ] Sans réglage SMTP, aucune route nouvelle ne répond, et les empreintes de rendu des pages existantes sont
      identiques à celles de `main`.
- [ ] Une personne non technicienne fait le parcours sans question. Ses hésitations sont notées.

## 13. Sources

Vérifiées le 16/11/2026, sauf mention.

**Signatures aveugles, jetons**
- RFC 9474, RSA Blind Signatures, octobre 2023 : <https://www.rfc-editor.org/rfc/rfc9474.html>
- RFC 9576, The Privacy Pass Architecture, juin 2024 : <https://www.rfc-editor.org/rfc/rfc9576.html>
- RFC 9578, Privacy Pass Issuance Protocols : <https://www.rfc-editor.org/rfc/rfc9578.html>
- RFC 9577, Privacy Pass HTTP Authentication Scheme (citée par Kagi, non lue) : <https://www.rfc-editor.org/rfc/rfc9577.html>
- Kagi, « Privacy Pass », 13 février 2025 : <https://blog.kagi.com/kagi-privacy-pass>
- Cloudflare, `blindrsa-ts` (Apache-2.0) : <https://github.com/cloudflare/blindrsa-ts>
- Google, `anonymous-tokens` (C++, Java, Apache-2.0) : <https://github.com/google/anonymous-tokens>
- D. Chaum, « Blind Signatures for Untraceable Payments », Crypto 1982 (référence de mémoire, non relue).

**Questionnaires et vote**
- ANONIZE, IEEE S&P 2014, version longue : <https://eprint.iacr.org/2015/681>
- Helios, USENIX Security 2008 : <https://www.usenix.org/conference/17th-usenix-security-symposium/helios-web-based-open-audit-voting>
- Belenios : <https://www.belenios.org/>
- CNIL, vote par correspondance électronique (page du 13/11/2025 ; la délibération 2026-045 n'a pas été lue) :
  <https://www.cnil.fr/fr/vote-electronique-par-correspondance-une-nouvelle-recommandation-en-2026>
- CNIL, délibération 2005-273 du 17 novembre 2005 (systèmes « distincts et isolés », lue en résumé) :
  <https://www.legifrance.gouv.fr/cnil/id/CNILTEXT000017652148>

**Navigateur**
- MDN, `BigInt` (disponibilité, avertissement sur le temps constant) : <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/BigInt>
- MDN, `SubtleCrypto.verify` : <https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/verify>
- WebKit, « Web Push for Web Apps on iOS and iPadOS », 2023 : <https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/>
- WebKit, « Full Third-Party Cookie Blocking and More », 24 mars 2020 : <https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/>
- RFC 8292, VAPID : <https://www.rfc-editor.org/rfc/rfc8292.html>

**Droit**
- CJUE, 1er août 2022, C-184/20, OT : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:62020CJ0184>
  (points 120 à 123 lus dans le texte)
- CJUE, 4 juillet 2023, C-252/21, Meta Platforms c. Bundeskartellamt (sommaire lu) : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:62021CJ0252>
- CJUE, 4 septembre 2025, C-413/23 P, CEPD c. CRU (sommaire lu) : <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:62023CJ0413>
- CEPD, lignes directrices 01/2025 sur la pseudonymisation (résumé lu) : <https://www.edpb.europa.eu/our-work-tools/documents/public-consultations/2025/guidelines-012025-pseudonymisation_en>
- G29, avis 05/2014 sur les techniques d'anonymisation (WP216, non relu) : <https://ec.europa.eu/justice/article-29/documentation/opinion-recommendation/files/2014/wp216_en.pdf>
- CNIL, l'anonymisation de données personnelles, 19 mai 2020 : <https://www.cnil.fr/fr/technologies/lanonymisation-de-donnees-personnelles>
- CNIL, donnée sensible : <https://www.cnil.fr/fr/definition/donnee-sensible>
- CNIL, ce qu'il faut savoir sur l'AIPD : <https://www.cnil.fr/fr/ce-quil-faut-savoir-sur-lanalyse-dimpact-relative-la-protection-des-donnees-aipd>
- Loi n° 77-808 du 19 juillet 1977, art. 1er et 12 : <https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032454569/2016-04-27>
- Le seuil de 15 ans et les articles 6, 9 et 11 du RGPD sont cités de mémoire, non relus ce jour.

**Connexion, envoi**
- NIST SP 800-63B-4, §3.1.3.1 : <https://pages.nist.gov/800-63-4/sp800-63b.html>
- Safe Links et liens à usage unique (forum Microsoft, témoignages) : <https://techcommunity.microsoft.com/discussions/microsoftdefenderforoffice365/possible-major-problem-with-ms-defender-scanningclicking-links/3874918>
- Brevo, offre SMTP : <https://www.brevo.com/fr/landing/smtp/>
- Brevo, suivi des mails transactionnels (forum, messages anciens) : <https://community.brevo.com/t/no-way-to-disable-by-option-tracking-in-transactional-e-mail/201>
- Liste de domaines jetables (CC0) : <https://github.com/disposable-email-domains/disposable-email-domains>
