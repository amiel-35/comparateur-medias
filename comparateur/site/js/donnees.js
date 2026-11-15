/* Les données de l'édition, préparées une fois : médias, sujets, comptages sur cinq bords, silences, dates. */
/* médias */
var lus={};D.medias.forEach(function(m){lus[m.nom]=m;});
var MEDIAS=C.medias.map(function(m){var l=lus[m.nom];return {nom:m.nom,score:m.score,note:m.note||null,lu:!!l,bord:l?l.bord:bordOf(m.score),ic:m.ic||null,sources:m.sources||null,peu:!!m.peu_documente};});
var BY={};MEDIAS.forEach(function(m){BY[m.nom]=m;});

/* sujets */
var rounds=D.sujets.map(function(s){return {id:s.id,kind:'sujet',titre:s.titre,fait:s.fait,div:s.divergence,analyse:s.analyse,mots:s.mots,arts:s.articles};});
rounds.push({id:'seuls',kind:'seuls',titre:'Les titres sans jumeau',fait:null,div:null,analyse:null,mots:[],arts:D.seuls});
var RB={};
/* seuil des silences (syntheses.MIN_MEDIAS) et nombre de médias lus par bord, pour cette édition */
var MIN=D.min_medias||(D.periodes&&D.periodes.semaine&&D.periodes.semaine.min_medias)||4;
var LUS={};BORDS.forEach(function(b){LUS[b]=0;});
MEDIAS.forEach(function(m){if(m.lu&&LUS[m.bord]!=null)LUS[m.bord]++;});
rounds.forEach(function(r,i){
  r.n=i+1;RB[r.id]=r;
  r.arts=r.arts.map(function(a,k){var m=BY[a.media];return {media:a.media,titre:a.titre,lien:a.lien,k:k,bord:m.bord,grp:GRP[m.bord],score:m.score};});
  r.count={g:0,c:0,d:0};r.med={g:{},c:{},d:{}};r.par={};r.medb={};
  BORDS.forEach(function(b){r.par[b]=0;r.medb[b]={};});
  r.arts.forEach(function(a){r.count[a.grp]++;r.med[a.grp][a.media]=1;r.par[a.bord]++;r.medb[a.bord][a.media]=1;});
  r.nmed=Object.keys(Object.assign({},r.med.g,r.med.c,r.med.d)).length;
  /* angle mort : un bord qui a au moins un média lu et aucun titre sous ce sujet. Un silence : un angle mort
     sur un sujet repris par MIN médias ou plus. */
  r.mortes=BORDS.filter(function(b){return LUS[b]>0&&r.par[b]===0;});
  r.large=r.kind==='sujet'&&r.nmed>=MIN;
  r.sil=r.large?r.mortes:[];
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
