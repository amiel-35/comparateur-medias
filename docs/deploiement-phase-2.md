# Déploiement de la phase 2 : deux services, trois noms d'hôte

Ce que le code fait, et ce qui reste à régler à la main, dans Coolify et le DNS. Rien de cela n'a été essayé sur le
serveur : tout est à vérifier en local d'abord, sur une copie de la vraie base.

## Ce qui change

| Avant | Après |
|---|---|
| Un service `comparateur` : fabrique et guichet dans un processus | Deux services du même compose, même image : `fabrique` (aucun port) et `guichet` (port interne 8080) |
| Un volume `comparateur-donnees` | Le même, partagé ; plus `comparateur-identites`, monté sur le guichet seul |
| La lettre part de la boucle de la fabrique | La fabrique écrit `public/lettre/<semaine>.json` et `public/alertes/<jour>.json` ; le guichet envoie |
| Les abonnés dans `comparateur.db` (table `abonnes`) | Les comptes et abonnements dans `identites.db` |
| Un nom d'hôte | Trois : `compare-media.inflexion.me`, `compte.compare-media.inflexion.me`, `urne.compare-media.inflexion.me` (décision 8) |

## Les réglages de chaque service

- **fabrique** : `ANTHROPIC_API_KEY`, les réglages de récolte, `COMPARATEUR_SITE_URL`, `COMPARATEUR_UMAMI_ID`, et
  rien pour le mail : elle lit `public/guichet.json`, écrit par le guichet. Pas de clé SMTP.
- **guichet** : `COMPARATEUR_SMTP_UTILISATEUR`, `COMPARATEUR_SMTP_MOT_DE_PASSE` (secret), `COMPARATEUR_SITE_URL`,
  `COMPARATEUR_UMAMI_ID`. Pas de clé des modèles. `COMPARATEUR_IDENTITES=/identites` est écrit dans le compose.

Coolify montre les variables d'un compose pour toute la ressource : vérifier dans son interface qu'une variable
peut n'être donnée qu'à un service. Sinon, la clé des modèles est visible du guichet par l'environnement, même si
son code ne la lit pas (non vérifié dans la documentation de Coolify).

## DNS

Deux enregistrements de plus, vers le même serveur que le site : `compte.compare-media.inflexion.me` et
`urne.compare-media.inflexion.me` (A/AAAA, ou CNAME vers `compare-media.inflexion.me`). Rien d'autre.

## Coolify et Traefik

1. Service `guichet` : trois domaines, chacun avec le port interne 8080 (forme `https://<nom>:8080`, comme
   aujourd'hui) : le site, `compte.`, `urne.`. Coolify obtient un certificat pour chacun.
2. Service `fabrique` : aucun domaine.
3. Traefik doit transmettre l'en-tête `Host` tel quel (c'est son comportement par défaut) : le guichet trie sur lui.
   Un hôte inconnu est servi comme le site.
4. Aucun cache tiers devant `compte.` et `urne.` (cadrage, phase 1 : « pas de cache tiers devant un nom d'hôte qui
   porte `/api/` »).
5. Les journaux d'accès de Traefik sont désactivés (vérifié le 17/11/2026, voir les Mentions) : les garder ainsi
   pour les trois noms d'hôte, `compte.` et `urne.` compris.

## L'ordre, le jour du passage

1. Sauvegarder le volume `comparateur-donnees` (il porte `comparateur.db`, donc la table `abonnes`).
2. Sur une copie, en local : lancer le guichet une fois (ou `python -m comparateur verser-abonnes`), lire le bilan
   (`lues` = `abonnements` + `deja` + `invalides`), puis faire le parcours d'un abonné : le lien de désinscription
   d'un mail déjà reçu doit marcher.
3. Déployer les deux services. Au démarrage, le guichet crée `identites.db` et y déplace les abonnés d'`abonnes`,
   ligne par ligne : chaque abonné est écrit dans `identites.db`, puis retiré d'`abonnes`. Il n'y a pas de moment
   où une désinscription se perd, et un désinscrit ne revient pas au démarrage suivant. Les liens de désinscription
   déjà envoyés marchent encore (le jeton d'`abonnes` devient le jeton de sortie).
4. Ajouter les volumes `comparateur-identites` (et, en phase 3, `comparateur-urnes`) aux sauvegardes, à part de
   `comparateur-donnees`. Les copies de `comparateur-donnees` d'avant le passage contiennent encore `abonnes` : les
   garder le moins longtemps possible.

Le guichet écrit `public/guichet.json` à son démarrage (`{"mail": true, "compte": "<adresse du compte>"}`) : la
fabrique, qui n'a pas la clé SMTP, y lit si le mail est en service et l'adresse du compte. Le réglage
`COMPARATEUR_MAIL_EN_SERVICE=1` n'est utile que pour forcer ce choix.

## En local

```bash
COMPARATEUR_DONNEES=/tmp/essai python3 essais/editions_essai.py
```

```bash
COMPARATEUR_DONNEES=/tmp/essai COMPARATEUR_SITE_URL=http://localhost:8765 PORT=8765 COMPARATEUR_SMTP_UTILISATEUR=essai COMPARATEUR_SMTP_MOT_DE_PASSE=essai python3 -m comparateur guichet
```

Le site sur <http://localhost:8765>, le compte sur <http://compte.localhost:8765> (les navigateurs envoient
`*.localhost` sur la machine). Sans vrai SMTP, le code ne part pas : l'envoi échoue et le journal le compte. Les tests
(`tests/test_compte.py`) font le parcours entier avec un faux SMTP.

## Non vérifié

- L'application installée sur iPhone qui ouvre `compte.` : s'ouvre-t-elle dans l'application ou dans Safari, et la
  session tient-elle ? (cadrage, 5.2 et prototype, preuve 5). En cas d'échec, repli sur un seul hôte et les chemins
  `/api/compte/…`, sans autre changement de code que le tri sur l'hôte.
- Le cookie `__Host-` sur `http://compte.localhost` : les navigateurs récents traitent `localhost` comme sûr ;
  Safari est à vérifier.
