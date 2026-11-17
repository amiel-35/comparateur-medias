/* classement */
function vClass(){
  var min=-3.2,max=2.8,span=max-min;
  function pos(v){return (v-min)/span*100;}
  var h='<h1 tabindex="-1" id="h1">Le classement vient de FrIdéo, pas d’un modèle</h1>'+
  '<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:56ch">Les '+CLASSES.length+' médias du panel, situés les uns par rapport aux autres. Ce classement range les médias par bord. Lui seul.</p>';
  h+='<div class="src"><p><b>Source.</b> FrIdéo v1.0, French News Lab, Amr Sobhy, ICNLSP 2026, licence CC BY 4.0. <a href="https://frenchnewslab.org/fr/publications/frideo-french-news-ideology-scale" target="_blank" rel="noopener noreferrer">frenchnewslab.org ↗</a>. Scores et intervalles du jeu de données officiel publié sur data.gouv.fr.</p>'+
  '<p><b>Réserve.</b> Un journal classé « à gauche » est plus à gauche que les autres journaux du panel. Ça ne veut pas dire qu’il est de gauche. Ce classement peut ne pas correspondre à l’idée que vous vous faites d’un journal. Classer les journaux n’est pas le but de ce site.</p>'+
  '<p><b>Comment lire les scores.</b> Zéro est la moyenne des '+CLASSES.length+' médias. Les sept bandes, leurs noms et leurs seuils sont ceux de FrIdéo : '+esc(String(C.seuils).replace(/^[^:]*: /,''))+'. Ce site n’y ajoute rien.</p>'+
  '<p><b>Intervalles de confiance.</b> Le trait fin autour de chaque barre : l’intervalle à 95 % publié par FrIdéo. Plus il est long, moins la place du journal est sûre. Pour '+CLASSES.filter(function(m){return m.ic&&m.ic[0]<0&&m.ic[1]>0;}).length+' médias sur '+CLASSES.length+', il traverse la moyenne : le classement ne dit pas de quel côté ils sont.</p></div>';
  h+='<div class="legend">'+BORDS.map(function(b){return '<span><i class="b-'+b+'"></i>'+BL[b]+'</span>';}).join('')+'</div>';
  h+='<div class="axis"><div class="scale"><div></div><div><span style="left:0">← gauche</span><span style="right:0;text-align:right">droite →</span><span style="left:'+pos(0)+'%;transform:translateX(-50%);top:1.5em">moy. panel</span></div><div></div></div>';
  h+='<ul class="cl">'+CLASSES.slice().sort(function(a,b){return a.score-b.score;}).map(function(m){
    var z=pos(0),p=pos(m.score),l=Math.min(z,p),w=Math.abs(p-z);
    var tk=SEUILS.map(function(t){return '<span class="tick" style="left:'+pos(t)+'%"></span>';}).join('');
    return '<li'+(m.lu?'':' class="off"')+'><div><a href="#/media/'+enc(m.nom)+'">'+esc(m.nom)+'</a>'+'</div><div class="track" role="img" aria-label="'+esc(m.nom)+', score '+fs(m.score)+', '+BL[m.bord]+'">'+tk+'<span class="bar b-'+m.bord+'" style="left:'+l+'%;width:'+w+'%"></span>'+(m.ic?'<span class="ci" style="left:'+pos(m.ic[0])+'%;width:'+(pos(m.ic[1])-pos(m.ic[0]))+'%"></span>':'')+'<span class="zero" style="left:calc('+z+'% - 1px)"></span></div><div class="sc">'+fs(m.score)+'</div></li>';
  }).join('')+'</ul></div>';
  if(NC.length)h+='<p class="note">'+(NC.length>1?NC.length+' médias lus ne sont pas classés':'Un média lu n’est pas classé')+' : '+NC.map(function(m){return '<a href="#/media/'+enc(m.nom)+'">'+esc(m.nom)+'</a>';}).join(', ')+'. FrIdéo ne les couvre pas, et ce site ne classe aucun média lui-même. Leurs titres comptent dans la couverture d’un sujet, dans aucun bord ni aucun silence.</p>';
  h+='<p class="note">Traits pointillés : les seuils de bord. Trait plein : zéro, la moyenne du panel ; à gauche de ce trait, plus à gauche que cette moyenne. Le nom d’un média ouvre sa fiche.</p>';
  /* À côté, jamais fondue : la lecture à l'aveugle du panel (AV, facultatif). Ni score ni bande n'en viennent. */
  if(AV){
    var av=Object.keys(AV.medias).map(function(n){return {nom:n,a:AV.medias[n]};}).sort(function(x,y){return x.a.note-y.a.note||x.nom.localeCompare(y.nom,'fr');});
    h+='<h2 id="aveugle">'+AVT+'</h2><p class="etq">'+esc(AV.etiquette||'Panel de volontaires. Ce n’est pas un sondage.')+'</p>'+
    '<p class="note">Une seconde mesure, à côté du classement FrIdéo. Elle ne change ni les scores ni les bandes ci-dessus, et aucune formule ne mêle les deux. '+avRegle()+' '+avSource()+'</p>';
    h+='<ul class="avl">'+av.map(function(x){
      return '<li><a href="#/media/'+enc(x.nom)+'">'+esc(x.nom)+'</a>'+avPiste(x.nom,x.a)+'<div class="sc">'+fs(x.a.note)+'</div><p class="avd">Avis : '+avEff(x.a)+' · '+avStatut(x.a)+'</p></li>';
    }).join('')+'</ul>';
    h+='<p class="note">Le point : la note du panel. Trait pointillé : zéro, le milieu de l’échelle proposée aux lecteurs. Ce n’est pas la moyenne des médias, comme dans le classement FrIdéo.</p>';
  }
  return h;
}
