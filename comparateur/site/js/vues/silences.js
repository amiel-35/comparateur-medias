/* les silences de l'édition : les sujets repris par MIN médias ou plus où un bord n'a aucun titre */
function vSilences(){
  var tus=LARGES.filter(function(r){return r.sil.length;});
  var h='<p class="crumb"><a href="#/">Sujets</a> / Silences</p>';
  h+='<nav class="ed" aria-label="Éditions">'+(ED.precedent?'<a class="btn sm" href="'+edUrl(ED.precedent)+'#/silences" rel="prev">← '+esc(jourCourt(ED.precedent))+'</a>':'<span class="btn sm off" aria-hidden="true">←</span>')+
     '<span class="ed-j">Édition du '+esc(jourLong(ED.jour))+'</span>'+
     (ED.suivant?'<a class="btn sm" href="'+edUrl(ED.suivant)+'#/silences" rel="next">'+esc(jourCourt(ED.suivant))+' →</a>':'<span class="btn sm off" aria-hidden="true">→</span>')+'</nav>';
  h+='<h1 tabindex="-1" id="h1">Les silences</h1>';
  h+='<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:58ch">Les sujets repris par '+MIN+' médias ou plus sur lesquels un bord n’a aucun titre. Bord par bord, les plus couverts d’abord.</p>';
  h+='<p class="note">Tout est compté par une formule fixe, sans modèle de langage. Seuls les titres des sujets sont écrits par un modèle.</p>';
  h+='<div class="nums"><div><b>'+LARGES.length+'</b><span>'+(LARGES.length>1?'sujets repris':'sujet repris')+' par '+MIN+' médias ou plus</span></div><div><b>'+tus.length+'</b><span>avec au moins un bord silencieux</span></div></div>';
  h+=legende()+'<div class="cols cinq">';
  BORDS.forEach(function(b){
    var l=LARGES.filter(function(r){return r.sil.indexOf(b)>=0;}).sort(parOrdre);
    h+='<section class="col k-'+b+'"><header><span>'+BL[b]+'</span><span class="mono" style="font-weight:400">'+pl(LUS[b],'journal lu','journaux lus')+(LUS[b]?' · '+pl(l.length,'silence','silences')+' sur '+LARGES.length:'')+'</span></header><div class="body">';
    if(!LUS[b])h+='<p class="vide">Aucun journal de ce bord n’a été lu ce jour-là. Ses silences ne sont pas comptés.</p>';
    else if(!l.length)h+='<p class="vide">Aucun silence : ce bord a au moins un titre sur chaque sujet repris par '+MIN+' médias ou plus.</p>';
    else h+='<ul class="pl">'+l.map(function(r){
      return '<li><a href="#/sujet/'+r.id+'">'+esc(r.titre)+'</a>'+mdl()+'<span class="pm mono mute" style="display:block;margin:4px 0 6px;font-size:.72rem">'+pl(r.nmed,'média en parle','médias en parlent')+' ailleurs · '+pl(r.arts.length,'titre','titres')+'</span>'+bar5(r.par)+'</li>';
    }).join('')+'</ul>';
    h+='</div></section>';
  });
  h+='</div>';
  h+='<h2>Comment lire cette page</h2><ul class="lim" style="max-width:68ch"><li><b>Un silence n’est pas une preuve.</b> Il veut dire : aucun titre de ce bord n’a été rangé sous ce sujet dans les flux récoltés. Un journal a pu en parler ailleurs, ou son titre n’a pas été rattaché au sujet.</li>'+
  '<li><b>Les bords n’ont pas le même nombre de journaux.</b> '+BORDS.map(function(b){return bl(b)+' : '+LUS[b];}).join(' ; ')+'. Un bord de trois journaux se tait plus souvent qu’un bord de douze.</li>'+
  '<li><b>Cinq bords, '+MIN+' médias.</b> Sur un sujet repris par '+MIN+' médias seulement, un bord au moins est forcément absent. Un silence pèse plus quand le sujet est très repris.</li>'+
  '<li><b>Un seul jour.</b> Un silence dans cette édition n’est pas un silence habituel. Pour la durée : <a href="#/semaine">la semaine</a>, <a href="#/mois">le mois</a>.</li>'+
  (D.absents&&D.absents.length?'<li><b>Flux illisibles :</b> '+D.absents.map(esc).join(', ')+'. Ces journaux ne comptent ni comme présents ni comme silencieux.</li>':'')+'</ul>';
  return h;
}
