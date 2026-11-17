# Doctrine du site

Comment le site est découpé, et les règles à suivre pour le faire grandir sans le casser. Ce fichier se lit
avant de toucher à `comparateur/site/`.

## Le principe

Le lecteur reçoit **une page**, sans dépendance, qui porte son HTML et les données de l'édition, et deux fichiers
partagés : un CSS et un JavaScript, nommés par leur empreinte (`public/actifs/site-<empreinte>.css` et `.js`). Cette
page n'est écrite par personne : `publier.gabarit()` assemble la page entière à partir de morceaux,
`publier.gabarit_en_actifs()` en sort le CSS et le JavaScript, puis `publier.ecrire_pages` injecte les données.
Il n'y a pas d'outil de construction : l'assemblage tient en quelques dizaines de lignes de Python.

```
comparateur/site/
  gabarit.html        le squelette : en-tête, navigation, et la liste ordonnée des morceaux
  styles/base.css     couleurs, thèmes, typographie, en-tête, étiquettes
  styles/commun.css   ce que plusieurs vues partagent
  styles/<vue>.css    une feuille par vue
  js/socle.js         constantes, petites fonctions
  js/donnees.js       les données de l'édition, préparées une fois
  js/commun.js        les briques d'affichage partagées
  js/adresse.js       la normalisation d'une adresse d'article et sa clé (même règle que comparateur/index.py)
  js/vues/<vue>.js    une vue par fichier
  js/routage.js       les routes #/…, le thème, le pied de page
  (publiés dans public/actifs/ sous des noms d'empreinte : le CSS en un fichier, le JavaScript en un fichier)
  aveugle.html        la page du vote à l'aveugle, à part
  mail.html           la page qui confirme ou supprime une inscription au mail de la semaine, à part
  manifest.webmanifest, sw.js, icone-*.png, apple-touch-icon.png   l'application installable (essais/icones.py)
```

Le squelette nomme chaque morceau par une ligne `/*INCLURE chemin*/`. L'ordre des lignes est l'ordre de la page.

## Les règles

1. **Une vue, un fichier.** Une vue a son fichier dans `js/vues/` et, si elle a des styles propres, sa feuille
   dans `styles/`. Modifier une vue ne demande d'ouvrir que ces deux fichiers.
2. **Ce qui sert deux fois va dans le commun.** Une brique utilisée par deux vues (barre sur sept bords,
   étiquette « écrit par un modèle », légende, navigation des éditions) vit dans `js/commun.js` et
   `styles/commun.css`. Une vue ne la réécrit pas.
3. **Les morceaux JavaScript sont les fragments d'une même fonction.** Ils partagent leurs variables et ne
   sont pas des modules. Deux conséquences : un nom déclaré dans un morceau est visible partout, donc il doit
   être unique ; une vue ne s'exécute pas au chargement, elle déclare une fonction `vNom()` que le routage
   appelle.
4. **Les données se préparent une fois.** Tout ce qui se calcule à partir de l'édition (comptages, silences,
   médias lus) se fait dans `js/donnees.js`. Une vue lit, elle ne recompte pas.
5. **Les calculs en Python, l'affichage en JavaScript.** Un comptage qui existe dans `syntheses.py` n'est pas
   refait dans le site : il est injecté dans la page. Reste à faire : les silences d'une édition sont encore
   calculés des deux côtés.
6. **Tout champ nouveau des données est facultatif.** Une édition gardée n'est jamais réécrite. Une vue qui
   lit un champ ajouté après coup prévoit le cas où il manque (`D.suivi||{}`, `D.ecartes`). Une édition
   d'avant doit toujours s'afficher.
7. **Aucun modèle ne compte ni ne note.** Les comptages se font par du code. Tout texte écrit par un modèle
   porte l'étiquette « écrit par un modèle » (`mdl()`).
8. **Le ton.** Phrases courtes, sobres, sans humour, sans « nous » : écrire « ce site ». Un journal classé
   « à gauche » est « plus à gauche que les autres journaux du panel », pas « de gauche ».
9. **Le dessin.** Fond crème, cadres noirs épais, serif, pas de carte arrondie ni d'ombre. Thèmes clair et
   sombre. Lisible à 375 px sans défilement horizontal. Les couleurs passent par les variables de
   `styles/base.css`, jamais par une valeur écrite dans une vue. Tout texte garde un contraste de 4,5:1 au moins
   sur son fond, et tout élément atteint au clavier montre un contour de focus.
10. **Un export n'est jamais une copie de `comparateur.db`.** La base ne porte pas que des données publiques :
   les adresses des abonnés, les votants, le journal de la fabrique y sont aussi. Un export, un index, un jeu de
   données se construit champ par champ à partir de ce qui est déjà publié (les éditions), jamais en copiant le
   fichier ou une table. Une sauvegarde est une copie, et c'est pour cela qu'elle n'est jamais publiée. Seul
   `base.py` ouvre la base. *Test : `Assise.test_un_export_n_est_jamais_une_copie_de_la_base`.* Exemple :
   `comparateur/export.py` lit l'édition gardée, champ par champ, et valide chaque fichier contre son schéma.
11. **La méthode a une version.** Changer une règle de comptage (bords, silences, fenêtre, rubriques) change la
   version de `comparateur/methode.py` et ajoute une ligne à son historique. La page Démarche l'affiche : c'est
   le document de référence.

## Ajouter une vue

1. Écrire `js/vues/<vue>.js` : une fonction `vNom()` qui rend le HTML de la vue, avec un `<h1 id="h1">`.
2. Si besoin, écrire `styles/<vue>.css`.
3. Ajouter les deux lignes `/*INCLURE …*/` dans `gabarit.html`.
4. Ajouter la route dans `js/routage.js` et, si la vue a sa place dans le menu, le lien dans `gabarit.html`.
5. Ajouter la vue aux listes de `essais/rendu.js` et `essais/accessibilite.js`.

Un test refuse un morceau présent dans `site/` mais oublié dans le squelette, et un morceau nommé deux fois.

## Vérifier un changement

```bash
python3 -m unittest discover -s tests
```

```bash
COMPARATEUR_DONNEES=/tmp/essai python3 essais/editions_essai.py
```

```bash
COMPARATEUR_DONNEES=/tmp/essai PORT=8765 python3 -m comparateur servir
```

```bash
node essais/rendu.js http://127.0.0.1:8765 /tmp/empreintes.txt
```

```bash
node essais/accessibilite.js http://127.0.0.1:8765
```

`essais/accessibilite.js` est la mesure d'accessibilité, écrite à la main : sur chaque vue, un seul `h1` et aucun
niveau de titre sauté, un titre d'onglet qui reprend le `h1`, un nom lisible pour chaque lien, bouton, champ et
figure, le contraste de chaque texte contre son fond réel (WCAG 2.2, 4,5:1), celui de la bordure des champs (3:1),
et un contour de focus d'au moins 2 px et 3:1 sur tout ce qu'atteint la touche Tab, dans les deux thèmes. Elle
passe aussi sur `aveugle.html` et `mail.html`, avec leurs états d'après un geste (réponses du serveur simulées).
Pour voir l'encart du mail de la page Semaine, écrire les pages d'essai avec des réglages SMTP factices
(`COMPARATEUR_SMTP_UTILISATEUR=essai COMPARATEUR_SMTP_MOT_DE_PASSE=essai python3 -m comparateur pages`) : rien ne
part. Elle ne voit ni le survol ni les contenus `::before`. Le 17/11/2026, elle a trouvé : sur `aveugle.html`, un
focus sans contour, le message d'erreur à 4,2:1, deux étiquettes sans champ, des bordures de champ à 1,3:1 ; sur
tout le site, un contour de focus jaune à 1,4:1 sur le fond clair. Tout est corrigé (jeton `--focus`).

`essais/rendu.js` ouvre chaque vue de chaque édition à 375 px et 1280 px, en clair et en sombre. Il échoue sur
une erreur de console, un défilement horizontal ou un « undefined » à l'écran, et écrit l'empreinte de chaque
capture. Pour un changement qui ne doit rien changer à l'écran (un rangement, un découpage), on compare le
fichier d'empreintes avant et après : il doit être identique. C'est ainsi que le découpage du gabarit a été
vérifié, sur 252 pages, puis la sortie du CSS et du JavaScript hors des pages, sur 300.

## Monter en puissance

Ce qui tient déjà : une visite ne touche ni la base ni un modèle, et le coût de la fabrique ne dépend pas du
nombre de lecteurs. Ce qui reste à faire, par ordre d'utilité, quand l'audience le demandera :

1. **Un cache devant le serveur.** Fait côté serveur (17/11/2026) : pages et données en `Cache-Control: public,
   max-age=300`, `sw.js` en `no-cache`, actifs d'empreinte en `public, max-age=31536000, immutable`, API en
   `no-store`. Chaque fichier a un `ETag` et répond `304`. Reste : mettre un CDN ou le cache du proxy devant, sans
   changement de code.
2. **La limite de débit sur l'API seulement.** Fait : les 300 requêtes par minute et par adresse ne valent plus
   que pour `/api/`. Les fichiers publics et `/sante` ne sont pas limités. Reste : le compteur est en mémoire,
   par processus.
3. **La compression.** Fait : `gzip` pour le texte de plus de 1 Ko si le navigateur l'accepte (`q=0` compris),
   `Vary: Accept-Encoding`, version compressée gardée en mémoire (bornée). Reste : `br` (pas dans la bibliothèque
   standard), et la compression à la publication plutôt qu'à la première demande.
4. **Le code hors des pages.** Fait : une page d'édition ne porte plus que son HTML et ses données ; le CSS et le
   JavaScript sont deux fichiers d'empreinte, partagés par toutes les éditions. Mesuré le 17/11/2026 sur une
   édition d'essai : 142 Ko avant, 53 Ko après ; actifs 89 Ko. Les captures des 300 vues sont identiques avant et
   après. Reste : `aveugle.html` et `mail.html` gardent leur code en ligne (une page, peu de visites).
5. **Les votes.** SQLite et un seul conteneur suffisent pour un cercle invité. Ouvrir le vote demande
   PostgreSQL et une limite de débit partagée : voir « Limites connues » du `README.md`.
