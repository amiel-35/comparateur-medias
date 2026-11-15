/* Le socle : constantes, réglages gardés dans le navigateur, petites fonctions. */
var D=DONNEES,C=CLASSEMENT;
var GRP={'gauche':'g','centre-gauche':'g','centre':'c','centre-droit':'d','droite':'d'};
var GL={g:'Gauche',c:'Centre',d:'Droite'};
/* Les textes d'angle écrits par le modèle n'existent que pour trois côtés ; les comptages se font sur cinq bords. */
var GL3={g:'Gauche et centre gauche',c:'Centre',d:'Centre droit et droite'};
var BL={'gauche':'Gauche','centre-gauche':'Centre gauche','centre':'Centre','centre-droit':'Centre droit','droite':'Droite'};
var BORDS=['gauche','centre-gauche','centre','centre-droit','droite'];
var KEY='cadrages.v1';
var S={theme:null};
try{var raw=localStorage.getItem(KEY);if(raw){var p=JSON.parse(raw);if(p&&typeof p==='object'){S.theme=p.theme||null;}}}catch(_){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S));}catch(_){}}

function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function url(u){return /^https?:\/\//i.test(u)?esc(u):'#';}
function fs(n){return (n>0?'+':n<0?'−':'')+Math.abs(n).toFixed(2).replace('.',',');}
function pl(n,a,b){return n+' '+(n>1?b:a);}
function bordOf(s){return s<=-1?'gauche':s<=-0.5?'centre-gauche':s>=1?'droite':s>=0.5?'centre-droit':'centre';}
function hash(s){var h=5381;for(var i=0;i<s.length;i++){h=((h<<5)+h+s.charCodeAt(i))|0;}return h>>>0;}
function enc(s){return encodeURIComponent(s);}
