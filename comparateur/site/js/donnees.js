/* Les données de l'édition, préparées une fois : médias, sujets, comptages sur sept bords, silences, dates. */
/* médias */
var lus={};D.medias.forEach(function(m){lus[m.nom]=m;});
/* Classés : ceux de FrIdéo, avec une bande. Non classés (D.non_classes, facultatif) : lus, comptés dans la couverture
   d'un sujet, dans aucun bord ni aucun silence (nc, bord null). Ce site ne range jamais un média au centre par défaut. */
var MEDIAS=C.medias.map(function(m){var l=lus[m.nom];return {nom:m.nom,score:m.score,note:m.note||null,lu:!!l,bord:l&&l.bord?l.bord:bordOf(m.score),ic:m.ic||null,sources:m.sources||null,peu:!!m.peu_documente,nc:false};});
var BY={};MEDIAS.forEach(function(m){BY[m.nom]=m;});
(D.non_classes||[]).concat(D.medias.map(function(m){return m.nom;})).forEach(function(nom){
  if(!BY[nom]){var m={nom:nom,score:null,note:null,lu:!!lus[nom],bord:null,ic:null,sources:null,peu:false,nc:true};MEDIAS.push(m);BY[nom]=m;}
});
var CLASSES=MEDIAS.filter(function(m){return !m.nc;}),NC=MEDIAS.filter(function(m){return m.nc;});

/* sujets */
var rounds=D.sujets.map(function(s){return {id:s.id,kind:'sujet',titre:s.titre,fait:s.fait,div:s.divergence,analyse:s.analyse,mots:s.mots,arts:s.articles};});
rounds.push({id:'seuls',kind:'seuls',titre:'Les titres sans jumeau',fait:null,div:null,analyse:null,mots:[],arts:D.seuls});
var RB={};
/* seuil des silences (syntheses.MIN_MEDIAS) et nombre de médias lus par bord, pour cette édition */
var MIN=D.min_medias||(D.periodes&&D.periodes.semaine&&D.periodes.semaine.min_medias)||4;
var LUS={};BORDS.forEach(function(b){LUS[b]=0;});
MEDIAS.forEach(function(m){if(m.lu&&LUS[m.bord]!=null)LUS[m.bord]++;});
/* médias lus par côté : gauche = gauche et centre gauche, centre, droite = centre droit et droite */
var COTES=['g','c','d'],LUSC={g:0,c:0,d:0};BORDS.forEach(function(b){LUSC[GRP[b]]+=LUS[b];});
rounds.forEach(function(r,i){
  r.n=i+1;RB[r.id]=r;
  r.arts=r.arts.map(function(a,k){var m=BY[a.media]||{bord:null,score:null};return {media:a.media,titre:a.titre,lien:a.lien,k:k,bord:m.bord,grp:m.bord?GRP[m.bord]:null,score:m.score};});
  r.count={g:0,c:0,d:0};r.med={g:{},c:{},d:{}};r.par={};r.medb={};
  BORDS.forEach(function(b){r.par[b]=0;r.medb[b]={};});
  var tous={};
  r.arts.forEach(function(a){tous[a.media]=1;if(!a.grp)return;r.count[a.grp]++;r.med[a.grp][a.media]=1;r.par[a.bord]++;r.medb[a.bord][a.media]=1;});
  /* la couverture compte tous les médias lus, classés ou non ; les bords et les silences, les classés seulement */
  r.nmed=Object.keys(tous).length;
  r.nc=r.arts.filter(function(a){return !a.grp;});
  /* bord sans titre : un bord qui a au moins un média lu et aucun titre sous ce sujet (détail, sur sept bords).
     Un silence : tout un côté (g, c ou d) sans aucun titre, sur un sujet repris par MIN médias ou plus.
     Sur sept bords, presque chaque sujet aurait un absent : le repère ne dirait plus rien. */
  r.mortes=BORDS.filter(function(b){return LUS[b]>0&&r.par[b]===0;});
  r.large=r.kind==='sujet'&&r.nmed>=MIN;
  r.sil=r.large?COTES.filter(function(x){return LUSC[x]>0&&r.count[x]===0;}):[];
});
var LARGES=rounds.filter(function(r){return r.large;});
function parOrdre(a,b){return b.nmed-a.nmed||b.arts.length-a.arts.length;}
/* éditions : une par jour, chacune sur sa page */
var ED=D.edition||{jour:String(D.recolte).slice(0,10),precedent:null,suivant:null,toutes:[]};
function jourLong(j){return new Date(j+'T12:00:00Z').toLocaleDateString('fr-FR',{timeZone:'UTC',weekday:'long',day:'numeric',month:'long',year:'numeric'});}
function jourCourt(j){return new Date(j+'T12:00:00Z').toLocaleDateString('fr-FR',{timeZone:'UTC',day:'numeric',month:'long'});}
function edUrl(j){return '/editions/'+j+'.html';}
/* la semaine et le mois : des comptages sur les éditions gardées, sans modèle */
var PER=D.periodes||null;
function jourNum(j){return new Date(j+'T12:00:00Z').toLocaleDateString('fr-FR',{timeZone:'UTC',day:'numeric',month:'long'});}
function sujLien(x){return (x.dernier===ED.jour?'':edUrl(x.dernier))+'#/sujet/'+x.id;}
