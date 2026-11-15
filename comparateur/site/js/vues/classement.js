/* classement */
function vClass(){
  var min=-3.2,max=2.8,span=max-min;
  function pos(v){return (v-min)/span*100;}
  var h='<p class="crumb"><a href="#/">Sujets</a> / Classement</p><h1 tabindex="-1" id="h1">Le classement vient de FrIdéo, pas d’un modèle</h1>'+
  '<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:56ch">Les '+MEDIAS.length+' médias du panel, situés les uns par rapport aux autres. Ce classement range les médias par bord. Lui seul.</p>';
  h+='<div class="src"><p><b>Source.</b> FrIdéo v1.0, French News Lab, Amr Sobhy, ICNLSP 2026, licence CC BY 4.0. <a href="https://frenchnewslab.org/fr/publications/frideo-french-news-ideology-scale" target="_blank" rel="noopener noreferrer">frenchnewslab.org ↗</a>. Scores et intervalles du jeu de données officiel publié sur data.gouv.fr.</p>'+
  '<p><b>Réserve.</b> Un journal classé « à gauche » est plus à gauche que les autres journaux du panel. Ça ne veut pas dire qu’il est de gauche. Ce classement peut ne pas correspondre à l’idée que vous vous faites d’un journal. Classer les journaux n’est pas le but de ce site.</p>'+
  '<p><b>Comment lire les scores.</b> Zéro est la moyenne des '+MEDIAS.length+' médias. Les sept bandes, leurs noms et leurs seuils sont ceux de FrIdéo : '+esc(String(C.seuils).replace(/^[^:]*: /,''))+'. Ce site n’y ajoute rien.</p>'+
  '<p><b>Intervalles de confiance.</b> Le trait fin autour de chaque barre : l’intervalle à 95 % publié par FrIdéo. Plus il est long, moins la place du journal est sûre. Pour '+MEDIAS.filter(function(m){return m.ic&&m.ic[0]<0&&m.ic[1]>0;}).length+' médias sur '+MEDIAS.length+', il traverse la moyenne : le classement ne dit pas de quel côté ils sont.</p></div>';
  h+='<div class="legend">'+BORDS.map(function(b){return '<span><i class="b-'+b+'"></i>'+BL[b]+'</span>';}).join('')+'</div>';
  h+='<div class="axis"><div class="scale"><div></div><div><span style="left:0">← gauche</span><span style="right:0;text-align:right">droite →</span><span style="left:'+pos(0)+'%;transform:translateX(-50%);top:1.5em">moy. panel</span></div><div></div></div>';
  h+='<ul class="cl">'+MEDIAS.slice().sort(function(a,b){return a.score-b.score;}).map(function(m){
    var z=pos(0),p=pos(m.score),l=Math.min(z,p),w=Math.abs(p-z);
    var tk=SEUILS.map(function(t){return '<span class="tick" style="left:'+pos(t)+'%"></span>';}).join('');
    return '<li'+(m.lu?'':' class="off"')+'><div><a href="#/media/'+enc(m.nom)+'">'+esc(m.nom)+'</a>'+'</div><div class="track" role="img" aria-label="'+esc(m.nom)+', score '+fs(m.score)+', '+BL[m.bord]+'">'+tk+'<span class="bar b-'+m.bord+'" style="left:'+l+'%;width:'+w+'%"></span>'+(m.ic?'<span class="ci" style="left:'+pos(m.ic[0])+'%;width:'+(pos(m.ic[1])-pos(m.ic[0]))+'%"></span>':'')+'<span class="zero" style="left:calc('+z+'% - 1px)"></span></div><div class="sc">'+fs(m.score)+'</div></li>';
  }).join('')+'</ul></div>';
  h+='<p class="note">Traits pointillés : les seuils de bord. Trait plein : zéro, la moyenne du panel ; à gauche de ce trait, plus à gauche que cette moyenne. Le nom d’un média ouvre sa fiche.</p>';
  return h;
}
