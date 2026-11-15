/* ====== vues ====== */
function vHome(){
  var h='<section class="hero">'+edNav()+
  '<h1>Un même fait, titré autrement selon le bord.</h1>'+
  '<p class="lede">Chaque sujet du jour rassemble les titres des médias français qui en parlent : qui en parle à gauche, au centre ou à droite, avec quels mots, et qui se tait.</p>'+
  '<p class="note" style="margin-top:14px">Les « titres du jour » d’un média sont ceux rangés dans les sujets ci-dessous ou parmi les titres sans jumeau.</p></section>';
  h+='<details class="why"><summary><span class="why-t">Pourquoi ce site</span><span class="why-i" aria-hidden="true"></span></summary>'+
  '<p>Un même fait n’est pas titré de la même façon partout. Ce site met les titres côte à côte pour le montrer : qui en parle, avec quels mots, et qui n’en parle pas.</p>'+
  '<p>Il ne dit pas qui a raison. Il ne classe pas les journaux : le classement vient de FrIdéo, une étude publiée par le French News Lab. <a href="#/classement">Voir le classement</a>.</p>'+
  '<p>Un journal classé « à gauche » est plus à gauche que les autres journaux du panel. Ça ne veut pas dire qu’il est de gauche.</p>'+
  '<p class="note">Ce site doit son classement au French News Lab et son idée à Ground News : <a href="#/origine">d’où vient ce site</a>. Comment ça marche : <a href="#/demarche">la démarche</a>. Le code est public : <a href="https://github.com/amiel-35/comparateur-medias" target="_blank" rel="noopener noreferrer">github.com/amiel-35/comparateur-medias ↗</a>.</p></details>';
  h+='<h2 style="margin-top:28px">Les '+rounds.length+' sujets du jour</h2>';
  var nsil=LARGES.filter(function(r){return r.sil.length;}).length;
  if(LARGES.length)h+='<p class="note">'+(nsil?'<b>'+nsil+' sur '+LARGES.length+'</b> '+(LARGES.length>1?'sujets repris':'sujet repris')+' par '+MIN+' médias ou plus '+(nsil>1?'ont':'a')+' au moins un bord silencieux. <a href="#/silences">Voir les silences</a>.':'Aucun bord silencieux sur les '+LARGES.length+' sujets repris par '+MIN+' médias ou plus.')+'</p>';
  h+=legende();
  h+='<ul class="grid">'+rounds.map(function(r){
    var t=r.kind==='sujet'?esc(r.titre)+mdl():esc(r.titre);
    return '<li class="card'+(r.sil.length?' sil':'')+'"><a class="cover" href="#/sujet/'+r.id+'"><span class="no">Sujet '+r.n+'</span><h3>'+t+'</h3>'+
      '<div class="chips">'+(r.sil.length?silChip(r):r.large?'<span class="mono mute">Aucun bord silencieux</span>':'')+'</div>'+bar5(r.par)+
      '<span class="mute" style="font-size:.82rem">'+pl(r.arts.length,'titre','titres')+', '+pl(r.nmed,'média','médias')+(r.div!=null?' · écart de cadrage '+r.div+' sur 5':'')+'</span>'+
      '</a></li>';
  }).join('')+'</ul>';
  return h;
}
