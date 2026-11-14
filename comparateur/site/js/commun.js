/* Les briques d'affichage partagées par plusieurs vues. */
function edNav(){
  var h='<nav class="ed" aria-label="Éditions">';
  h+=ED.precedent?'<a class="btn sm" href="'+edUrl(ED.precedent)+'" rel="prev">← '+esc(jourCourt(ED.precedent))+'</a>':'<span class="btn sm off" aria-hidden="true">←</span>';
  h+='<span class="ed-j">Édition du '+esc(jourLong(ED.jour))+'</span>';
  h+=ED.suivant?'<a class="btn sm" href="'+edUrl(ED.suivant)+'" rel="next">'+esc(jourCourt(ED.suivant))+' →</a>':'<span class="btn sm off" aria-hidden="true">→</span>';
  h+='</nav><p class="mono mute ed-s">'+(ED.suivant?'Vous lisez une édition passée. <a href="/">Dernière édition</a> · ':'Dernière édition · ')+'<a href="#/editions">toutes les éditions</a> · <a href="#/semaine">la semaine</a> · <a href="#/mois">le mois</a> · <a href="#/silences">les silences</a></p>';
  return h;
}
/* éléments communs */
function mdl(){return '<span class="mdl" title="Écrit par un modèle de langage">écrit par un modèle</span>';}
function bchip(b){return '<span class="bchip b-'+b+'">'+BL[b]+'</span>';}
function bl(b){return BL[b].toLowerCase();}
function legende(){return '<div class="legend">'+BORDS.map(function(b){return '<span><i class="b-'+b+'"></i>'+BL[b]+'</span>';}).join('')+'<span>Cinq bords, tirés du score FrIdéo par ce site</span></div>';}
/* la répartition des titres sur cinq bords : une case par bord, hachurée quand le bord n'a aucun titre */
function bar5(par){
  return '<span class="pbar" role="img" aria-label="Titres par bord : '+BORDS.map(function(b){return bl(b)+' '+(par[b]||0);}).join(', ')+'">'+BORDS.map(function(b){
    var n=par[b]||0;
    return '<i class="'+(n?'b-'+b:'nul z-'+b)+'" style="flex:'+Math.max(n,0.35)+'" title="'+BL[b]+' : '+pl(n,'titre','titres')+'"><b>'+n+'</b></i>';
  }).join('')+'</span>';
}
/* la même, sans chiffres, à une largeur donnée (frise) */
function barFine(par,pct){
  return '<span class="pbar fin" style="width:'+pct+'%" role="img" aria-label="Titres par bord : '+BORDS.map(function(b){return bl(b)+' '+(par[b]||0);}).join(', ')+'">'+BORDS.map(function(b){
    var n=par[b]||0;return n?'<i class="b-'+b+'" style="flex:'+n+'" title="'+BL[b]+' : '+pl(n,'titre','titres')+'"></i>':'';
  }).join('')+'</span>';
}
function silChip(r){return r.sil.length?'<span class="am">Silence : '+r.sil.map(bl).join(', ')+'</span>':'';}
