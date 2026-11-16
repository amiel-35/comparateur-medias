/* Pourquoi ce site : l'explication, sortie de l'accueil pour laisser la place aux sujets. */
function vPourquoi(){
  return '<h1 tabindex="-1" id="h1">Pourquoi ce site</h1>'+
  '<div class="prose"><p>Un même fait n’est pas titré de la même façon partout. Ce site met les titres côte à côte pour le montrer : qui en parle, avec quels mots, et qui n’en parle pas.</p>'+
  '<p>Il ne dit pas qui a raison. Il ne classe pas les journaux : le classement vient de FrIdéo, une étude publiée par le French News Lab. <a href="#/classement">Voir le classement</a>.</p>'+
  '<p>Un journal classé « à gauche » est plus à gauche que les autres journaux du panel. Ça ne veut pas dire qu’il est de gauche.</p></div>'+
  '<h2>Comment lire la page d’accueil</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Une édition par jour.</b> Chaque matin, les titres des 24 dernières heures sont regroupés par sujet. L’édition ne bouge plus ensuite.</li>'+
  '<li><b>Une carte par sujet.</b> La barre de couleurs compte les titres de chaque bord, de la gauche à la droite.</li>'+
  '<li><b>Un silence.</b> Un filet rouge signale un sujet repris par '+MIN+' médias ou plus sur lequel tout un côté n’a aucun titre. <a href="#/silences">Les silences de l’édition</a>.</li>'+
  '<li><b>Les titres du jour d’un média</b> sont ceux rangés dans les sujets ou parmi les titres sans jumeau.</li></ul>'+
  '<p class="note">Ce site doit son classement au French News Lab et son idée à Ground News : <a href="#/origine">d’où vient ce site</a>. Comment ça marche : <a href="#/demarche">la démarche</a>. Le code est public : <a href="https://github.com/amiel-35/comparateur-medias" target="_blank" rel="noopener noreferrer">github.com/amiel-35/comparateur-medias ↗</a>.</p>';
}
