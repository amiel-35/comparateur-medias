/* médias */
function vMedias(){
  var h='<h1 tabindex="-1" id="h1">Les médias</h1>'+
  '<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:56ch">Pour chaque média : sa place dans le classement, ses titres du jour, les sujets qu’il couvre. Et ceux où il manque.</p>';
  BORDS.forEach(function(b){
    var l=MEDIAS.filter(function(m){return m.bord===b;}).sort(function(x,y){return x.score-y.score;});
    if(!l.length)return;
    h+='<h2>'+bchip(b)+'</h2><ul class="mlist">'+l.map(function(m){
      return '<li><a class="l-'+m.bord+'" href="#/media/'+enc(m.nom)+'"><b>'+esc(m.nom)+'</b><small>'+fs(m.score)+(m.lu?'':' · illisible')+'</small></a></li>';
    }).join('')+'</ul>';
  });
  /* les non classés : lus, hors de FrIdéo, sans score ni bord */
  if(NC.length){
    h+='<h2>'+bchip(null)+'</h2><p class="note">FrIdéo ne couvre pas ces médias, et ce site ne classe aucun média lui-même. Leurs titres comptent dans la couverture d’un sujet, dans aucun bord ni aucun silence.</p><ul class="mlist">'+NC.slice().sort(function(x,y){return x.nom.localeCompare(y.nom,'fr');}).map(function(m){
      return '<li><a class="l-nc" href="#/media/'+enc(m.nom)+'"><b>'+esc(m.nom)+'</b><small>non classé'+(m.lu?'':' · illisible')+'</small></a></li>';
    }).join('')+'</ul>';
  }
  return h;
}
function vMedia(nom){
  var m=BY[nom];if(!m)return vMedias();
  var h='<p class="crumb"><a href="#/medias">Médias</a> / '+esc(m.nom)+'</p><h1 tabindex="-1" id="h1">'+esc(m.nom)+'</h1>';
  if(m.nc){
    h+='<p style="margin:14px 0 0">'+bchip(null)+'</p>';
    h+='<dl class="kv"><div><dt>Pourquoi non classé</dt><dd>FrIdéo ne couvre pas ce média, et ce site ne classe aucun média lui-même. Il n’a ni score ni bord. <a href="#/classement">Voir le classement</a>.</dd></div>'+
    '<div><dt>Ce qu’il compte</dt><dd>Ses titres comptent dans la couverture d’un sujet (combien de médias en parlent). Ils ne comptent dans aucun bord et ne font aucun silence.</dd></div>';
  }else{
  h+='<p style="margin:14px 0 0"><span class="score">'+fs(m.score)+'</span> '+bchip(m.bord)+'</p>';
  var pos=(m.score+2.6)/4.8*100;
  h+='<div class="mini" role="img" aria-label="Position sur l’axe du panel"><i style="left:calc('+pos+'% - 2px)"></i></div><p class="note" style="display:flex;justify-content:space-between"><span>← plus à gauche que la moyenne</span><span>plus à droite →</span></p>';
  h+='<dl class="kv"><div><dt>D’où vient la note</dt><dd>Classement FrIdéo v1.0 (French News Lab, Amr Sobhy, ICNLSP 2026, CC BY 4.0). Le zéro est la moyenne du panel, pas un centre politique. <a href="#/classement">Voir le classement</a>.</dd></div>'+
  '<div><dt>D’où vient le bord</dt><dd>C’est la bande que FrIdéo donne à ce média. Ce site ne l’a pas choisie.</dd></div>'+
  '<div><dt>Intervalle de confiance</dt><dd>'+(m.ic?'De '+fs(m.ic[0])+' à '+fs(m.ic[1])+' (à 95 %).'+(m.ic[0]<0&&m.ic[1]>0?' Il traverse la moyenne du panel : le classement ne dit pas de quel côté se trouve ce journal.':'')+(m.sources?' Score établi sur '+m.sources+' familles d’indices sur 9'+(m.peu?', ce qui est peu : à lire avec prudence.':'.'):''):'<span class="soon">à venir</span>')+'</dd></div>'+
  '';}
  h+='<div><dt>Propriétaire</dt><dd><span class="soon">à venir</span> <span class="mute">(absent des données)</span></dd></div>'+
  (m.note?'<div><dt>Note sur le flux</dt><dd>'+esc(m.note)+'</dd></div>':'')+
  '<div><dt>Flux du jour</dt><dd>'+(m.lu?'Lu.':'Flux illisible aujourd’hui. Rien à dire de ses titres.')+'</dd></div></dl>';
  /* titres du jour */
  var its=[];rounds.forEach(function(r){r.arts.forEach(function(a){if(a.media===m.nom)its.push({r:r,a:a});});});
  h+='<h2>Ses titres du jour</h2><p class="note">Seulement ceux rangés sous un sujet ou parmi les titres sans jumeau, pas les '+D.total+' récoltés.</p>';
  if(!m.lu)h+='<p class="masked">Aucun : flux illisible.</p>';
  else if(!its.length)h+='<p class="masked">Aucun titre de ce média dans les sujets du jour.</p>';
  else{
    h+='<ul class="tlist">'+its.map(function(x){return '<li><span class="mono mute">'+esc(x.r.titre)+(x.r.kind==='sujet'?mdl():'')+'</span><a class="t" href="'+url(x.a.lien)+'" target="_blank" rel="noopener noreferrer">'+esc(x.a.titre)+' ↗</a></li>';}).join('')+'</ul>';
  }
  /* couverture */
  if(m.lu){
    var cov=[],mute=[];
    var mine={};rounds.forEach(function(r){if(r.kind==='sujet'&&r.arts.some(function(a){return a.media===m.nom;}))mine[r.id]=1;});
    rounds.forEach(function(r){if(r.kind!=='sujet')return;(mine[r.id]?cov:mute).push(r);});
    h+='<h2>Les sujets qu’il couvre</h2>'+(cov.length?'<ul class="tags">'+cov.map(function(r){return '<li><a href="#/sujet/'+r.id+'">'+esc(r.titre)+'</a></li>';}).join('')+'</ul>':'<p class="masked">Aucun parmi les sujets du jour.</p>');
    h+='<h2>Les sujets où il ne figure pas</h2>'+(mute.length?'<ul class="tags">'+mute.map(function(r){return '<li><a href="#/sujet/'+r.id+'">'+esc(r.titre)+'</a></li>';}).join('')+'</ul><p class="note">« Ne figure pas » : aucun titre de ce média n’est rangé sous ce sujet. Ça ne prouve pas qu’il n’en a pas parlé.</p>':'<p class="masked">Aucun parmi les sujets du jour.</p>');
  }else{h+='<h2>Les sujets qu’il couvre</h2><p class="masked">Impossible à dire : son flux n’a pas pu être lu.</p>';}
  return h;
}
