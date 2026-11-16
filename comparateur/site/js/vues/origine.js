/* origine */
function vOrigine(){
  var L=' target="_blank" rel="noopener noreferrer"';
  /* Trois sources, à place égale, dans l'ordre où ce site les a rencontrées. */
  function bloc(pour,nom,intro,points,liens){
    return '<article><span class="for">'+pour+'</span><h2>'+nom+'</h2><p>'+intro+'</p><p class="lab mono mute">Ce que ce site leur doit</p><ul class="lim">'+points.map(function(x){return '<li>'+x+'</li>';}).join('')+'</ul><p class="liens">'+liens.map(function(x){return '<a href="'+x[1]+'"'+L+'>'+x[0]+' ↗</a>';}).join(' · ')+'</p></article>';
  }
  return '<h1 tabindex="-1" id="h1">D’où vient ce site</h1>'+
  '<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:56ch">D’abord une idée, celle de Ground News. Ensuite un classement et une méthode, ceux du French News Lab. Et une exigence, celle d’AllSides. Ce site n’invente aucune des trois.</p>'+
  '<div class="origin">'+
  bloc('L’idée','Ground News',
    'Un site nord-américain qui met côte à côte ce que des médias de bords différents font d’un même sujet. Ce geste de lecture, ils l’ont rendu simple et courant.',
    ['<b>La comparaison par bord.</b> Un sujet, et les titres de chaque bord en regard.',
     '<b>Les silences.</b> Montrer ce qu’un bord laisse de côté. <a href="#/silences">Les silences de l’édition</a>.',
     '<b>Aucune note maison.</b> Ground News ne classe pas les médias lui-même : il s’appuie sur des classements publiés par d’autres. Ce site fait pareil.'],
    [['ground.news/rating-system','https://ground.news/rating-system']])+
  bloc('Le classement et la méthode','Le French News Lab',
    'Une association de recherche française, fondée par Amr Sobhy, qui étudie la presse avec des données ouvertes.',
    ['<b>Le classement.</b> Ce n’est pas ce site qui classe les journaux. C’est FrIdéo, leur échelle de trente médias, avec ses sept bandes et ses intervalles de confiance. <a href="#/classement">Voir le classement</a>.',
     '<b>La leçon principale.</b> Sur un même événement, les journaux écrivent souvent à peu près la même chose. Ce qui les sépare, c’est surtout ce qu’ils choisissent de couvrir.',
     '<b>Une prudence.</b> On reconnaît un journal à sa typographie plus qu’à ses mots, et deux lecteurs sérieux ne jugent pas un titre de la même façon. Les descriptions de ce site sont à lire avec la même réserve.'],
    [['frenchnewslab.org','https://frenchnewslab.org/fr'],['FrIdéo','https://frenchnewslab.org/fr/publications/frideo-french-news-ideology-scale'],['Cadrage par les mots, cadrage par la sélection','https://frenchnewslab.org/fr/publications/framing-by-wording-framing-by-selection'],['Qui a publié ce titre ?','https://frenchnewslab.org/fr/publications/who-published-this-headline']])+
  bloc('La transparence','AllSides',
    'Un organisme américain qui évalue le positionnement des médias et publie comment il s’y prend, plutôt que d’asséner une note.',
    ['<b>Dire d’où vient chaque chose.</b> Ici, chaque classement cite sa source, et chaque texte écrit par un modèle porte son étiquette.',
     '<b>Croiser plusieurs approches.</b> Une note unique cache ses raisons. Ce site sépare ce qui est compté par formule de ce qui est écrit par un modèle. <a href="#/demarche">La démarche</a>.',
     '<b>Juger à l’aveugle.</b> AllSides fait lire des contenus sans le nom du média à des lecteurs de bords différents. C’est le modèle du vote à l’aveugle prévu sur ce site.'],
    [['allsides.com/about/media-bias-rating-methods','https://www.allsides.com/about/media-bias-rating-methods']])+
  '</div>'+
  '<p class="note">Données FrIdéo v1.0 sous licence CC BY 4.0. Les sept bandes affichées ici, de l’extrême gauche à l’extrême droite, sont celles de FrIdéo. Le regroupement en trois côtés, pour les silences, est de ce site. Ce site n’est affilié à aucun des organismes cités.</p>'+
  '<h2>Ce que ce site fait de son côté</h2><ul class="lim" style="max-width:68ch"><li>Il publie une édition par jour : chaque fait en regard, bord par bord, avec les silences et les mots qui diffèrent.</li><li>Il garde chaque édition, et en tire une synthèse par semaine et par mois.</li><li>Il ne note aucun média lui-même (<a href="#/classement">le classement</a>).</li></ul>';
}
