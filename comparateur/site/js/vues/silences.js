/* les silences de l'édition : les sujets repris par MIN médias ou plus où tout un côté (g, c, d) n'a aucun titre */
function vSilences(){
  var tus=LARGES.filter(function(r){return r.sil.length;});
  var h='';
  h+='<nav class="ed" aria-label="Éditions">'+(ED.precedent?'<a class="btn sm" href="'+edUrl(ED.precedent)+'#/silences" rel="prev">← '+esc(jourCourt(ED.precedent))+'</a>':'<span class="btn sm off" aria-hidden="true">←</span>')+
     '<span class="ed-j">Édition du '+esc(jourLong(ED.jour))+'</span>'+
     (ED.suivant?'<a class="btn sm" href="'+edUrl(ED.suivant)+'#/silences" rel="next">'+esc(jourCourt(ED.suivant))+' →</a>':'<span class="btn sm off" aria-hidden="true">→</span>')+'</nav>';
  h+='<h1 tabindex="-1" id="h1">Les silences</h1>';
  h+='<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:58ch">Les sujets repris par '+MIN+' médias ou plus sur lesquels tout un côté n’a aucun titre : la gauche, le centre ou la droite. Les plus couverts d’abord.</p>';
  h+='<p class="note">Tout est compté par formule, sans modèle. Seuls les titres des sujets sont écrits par un modèle.</p>';
  h+='<div class="nums"><div><b>'+LARGES.length+'</b><span>'+(LARGES.length>1?'sujets repris':'sujet repris')+' par '+MIN+' médias ou plus</span></div><div><b>'+tus.length+'</b><span>avec un côté entier silencieux</span></div></div>';
  h+=legende()+'<div class="cols">';
  COTES.forEach(function(x){
    var l=LARGES.filter(function(r){return r.sil.indexOf(x)>=0;}).sort(parOrdre);
    h+='<section class="col s-'+x+'"><header><span>'+GL3[x]+'</span><span class="mono" style="font-weight:400">'+pl(LUSC[x],'journal lu','journaux lus')+(LUSC[x]?' · '+pl(l.length,'silence','silences')+' sur '+LARGES.length:'')+'</span></header><div class="body">';
    if(!LUSC[x])h+='<p class="vide">Aucun journal de ce côté n’a été lu ce jour-là. Ses silences ne sont pas comptés.</p>';
    else if(!l.length)h+='<p class="vide">Aucun silence : ce côté a au moins un titre sur chaque sujet repris par '+MIN+' médias ou plus.</p>';
    else h+='<ul class="pl">'+l.map(function(r){
      return '<li><a href="#/sujet/'+r.id+'">'+esc(r.titre)+'</a>'+mdl()+'<span class="pm mono mute" style="display:block;margin:4px 0 6px;font-size:.72rem">'+pl(r.nmed,'média en parle','médias en parlent')+' ailleurs · '+pl(r.arts.length,'titre','titres')+'</span>'+bar5(r.par)+'</li>';
    }).join('')+'</ul>';
    h+='</div></section>';
  });
  h+='</div>';
  h+='<h2>Comment lire cette page</h2><ul class="lim" style="max-width:68ch"><li><b>Un silence n’est pas une preuve.</b> Il dit une chose : aucun titre de ce côté n’est rangé sous ce sujet. Un journal a pu en parler ailleurs. Ou son titre n’a pas été rattaché.</li>'+
  '<li><b>Trois côtés, sept bords.</b> Les barres comptent les titres sur les sept bandes de FrIdéo. Le silence se juge sur trois côtés : les bandes de gauche (extrême gauche, gauche, centre gauche), le centre, les bandes de droite (centre droit, droite, extrême droite). Sur sept bords, presque chaque sujet aurait un absent : le repère ne dirait plus rien.</li>'+
  '<li><b>Les côtés n’ont pas le même nombre de journaux.</b> '+COTES.map(function(x){return GL[x].toLowerCase()+' : '+LUSC[x];}).join(' ; ')+'. Un côté qui compte moins de journaux se tait plus souvent.</li>'+
  '<li><b>Un seul jour.</b> Un silence dans cette édition n’est pas un silence habituel. Pour la durée : <a href="#/semaine">la semaine</a>, <a href="#/mois">le mois</a>.</li>'+
  (D.absents&&D.absents.length?'<li><b>Flux illisibles :</b> '+D.absents.map(esc).join(', ')+'. Ces journaux ne comptent ni comme présents ni comme silencieux.</li>':'')+'</ul>';
  return h;
}
