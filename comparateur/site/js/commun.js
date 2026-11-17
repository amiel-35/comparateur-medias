/* Les briques d'affichage partagées par plusieurs vues. */
function edNav(){
  var h='<nav class="ed" aria-label="Éditions">';
  h+=ED.precedent?'<a class="btn sm" href="'+edUrl(ED.precedent)+'" rel="prev">← '+esc(jourCourt(ED.precedent))+'</a>':'<span class="btn sm off" aria-hidden="true">←</span>';
  h+='<span class="ed-j">Édition du '+esc(jourLong(ED.jour))+'</span>';
  h+=ED.suivant?'<a class="btn sm" href="'+edUrl(ED.suivant)+'" rel="next">'+esc(jourCourt(ED.suivant))+' →</a>':'<span class="btn sm off" aria-hidden="true">→</span>';
  h+='</nav><p class="mono mute ed-s">'+(ED.suivant?'Vous lisez une édition passée. <a href="/">Dernière édition</a> · ':'Dernière édition · ')+'<a href="#/editions">toutes les éditions</a></p>';
  return h;
}
/* éléments communs */
function mdl(){return '<span class="mdl" title="Écrit par un modèle de langage">écrit par un modèle</span>';}
function bchip(b){return b?'<span class="bchip b-'+b+'">'+BL[b]+'</span>':'<span class="bchip b-nc">Non classé</span>';}
function bl(b){return b?BL[b].toLowerCase():'non classé';}
function legende(){return '<div class="legend">'+BORDS.map(function(b){return '<span><i class="b-'+b+'"></i>'+BL[b]+'</span>';}).join('')+'<span>Les sept bandes du classement FrIdéo</span></div>';}
/* la répartition des titres sur sept bords : une case par bord, hachurée quand le bord n'a aucun titre */
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
function silChip(r){return r.sil.length?'<span class="am">Silence : '+r.sil.map(function(x){return GL[x].toLowerCase();}).join(', ')+'</span>':'';}
/* La lecture à l'aveugle du panel (AV), pour la page Classement et la fiche d'un média : une seconde mesure, à côté
   du classement FrIdéo, jamais fondue en lui. Ni bande ni couleur de bord : un point sur une échelle neutre, de −2 à +2. */
var AVT='Perçu à l’aveugle par le panel, titres masqués';
function avTrim(t){var m=/^(\d{4})T([1-4])$/.exec(t);return t==='historique'?'les avis d’avant la carte de votant':m?(m[2]==='1'?'1er':m[2]+'e')+' trimestre '+m[1]:esc(t);}
function avSource(){return 'Version : '+esc(AV.version||'')+'. Avis pris en compte : '+(AV.trimestres||[]).map(avTrim).join(', ')+'.';}
function avRegle(){return 'Des volontaires lisent dix titres d’un même média, sans son nom, et le placent de −2 (gauche) à +2 (droite). La note est la moyenne des avis par bord déclaré des lecteurs (gauche, centre, droite), puis la moyenne des bords : un bord nombreux ne pèse pas plus qu’un autre. Statut « publiable » quand chaque bord compte au moins '+(AV.min_par_bord||5)+' avis, « indicatif » sinon.';}
function avStatut(a){return a.statut==='publiable'?'publiable':'indicatif';}
function avEff(a){var e=a.effectifs||{};return 'gauche '+(e.g||0)+', centre '+(e.c||0)+', droite '+(e.d||0);}
function avPiste(nom,a){var p=Math.max(0,Math.min(100,(a.note+2)/4*100));
  return '<div class="avp" role="img" aria-label="'+esc(nom)+' : perçu à '+fs(a.note)+', sur une échelle de −2 (gauche) à +2 (droite)"><span class="avz"></span><i style="left:calc('+p+'% - 3px)"></i></div>';}
