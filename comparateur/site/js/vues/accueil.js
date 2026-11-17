/* ====== vues ====== */
function vHome(){
  /* Le contenu d'abord : une ligne pour dire ce que c'est, le reste sur sa page (#/pourquoi). */
  var h='<section class="hero">'+edNav()+
  '<h1 tabindex="-1" id="h1">Qui en parle, avec quels mots. Et qui se tait.</h1>'+
  '<p class="lede">Les titres de la presse française, sujet par sujet, de la gauche à la droite. <a href="#/pourquoi">Pourquoi ce site</a></p></section>';
  h+=blocMesSujets();
  h+='<h2 class="h-suj">Les '+rounds.length+' sujets du jour</h2>';
  var nsil=LARGES.filter(function(r){return r.sil.length;}).length;
  if(LARGES.length)h+='<p class="note">'+(nsil?'<b>'+nsil+' sur '+LARGES.length+'</b> '+(LARGES.length>1?'sujets repris':'sujet repris')+' par '+MIN+' médias ou plus '+(nsil>1?'ont':'a')+' un côté entier silencieux. <a href="#/silences">Voir les silences</a>.':'Aucun silence sur les '+LARGES.length+' sujets repris par '+MIN+' médias ou plus.')+'</p>';
  h+=legende();
  h+='<ul class="grid">'+rounds.map(function(r){
    var t=r.kind==='sujet'?esc(r.titre)+mdl():esc(r.titre);
    return '<li class="card'+(r.sil.length?' sil':'')+'"><a class="cover" href="#/sujet/'+r.id+'"><span class="no">Sujet '+r.n+'</span><h3>'+t+'</h3>'+
      '<div class="chips">'+(r.sil.length?silChip(r):r.large?'<span class="mono mute">Aucun silence</span>':'')+'</div>'+bar5(r.par)+
      '<span class="mute" style="font-size:.82rem">'+pl(r.arts.length,'titre','titres')+', '+pl(r.nmed,'média','médias')+(r.div!=null?' · écart de cadrage '+r.div+' sur 5':'')+'</span>'+
      '</a></li>';
  }).join('')+'</ul>';
  return h;
}
