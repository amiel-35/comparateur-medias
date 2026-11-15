/* Le socle : constantes, réglages gardés dans le navigateur, petites fonctions. */
var D=DONNEES,C=CLASSEMENT;
var GRP={'extreme-gauche':'g','gauche':'g','centre-gauche':'g','centre':'c','centre-droit':'d','droite':'d','extreme-droite':'d'};
var GL={g:'Gauche',c:'Centre',d:'Droite'};
/* Les textes d'angle écrits par le modèle et les silences n'existent que pour trois côtés ; les comptages se font
   sur les sept bandes de FrIdéo. Le regroupement en trois côtés est le seul fait par ce site. */
var GL3={g:'Côté gauche',c:'Centre',d:'Côté droit'};
/* Les sept bandes de FrIdéo, avec ses mots. Ce site ne classe aucun média. */
var BL={'extreme-gauche':'Extrême gauche','gauche':'Gauche','centre-gauche':'Centre gauche','centre':'Centre','centre-droit':'Centre droit','droite':'Droite','extreme-droite':'Extrême droite'};
var BORDS=['extreme-gauche','gauche','centre-gauche','centre','centre-droit','droite','extreme-droite'];
var SEUILS=[-1.5,-0.75,-0.25,0.25,0.75,1.5];
var KEY='cadrages.v1';
var S={theme:null};
try{var raw=localStorage.getItem(KEY);if(raw){var p=JSON.parse(raw);if(p&&typeof p==='object'){S.theme=p.theme||null;}}}catch(_){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S));}catch(_){}}

function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function url(u){return /^https?:\/\//i.test(u)?esc(u):'#';}
function fs(n){return (n>0?'+':n<0?'−':'')+Math.abs(n).toFixed(2).replace('.',',');}
function pl(n,a,b){return n+' '+(n>1?b:a);}
function bordOf(s){var n=0;SEUILS.forEach(function(x){if(s>=x)n++;});return BORDS[n];}
function hash(s){var h=5381;for(var i=0;i<s.length;i++){h=((h<<5)+h+s.charCodeAt(i))|0;}return h>>>0;}
function enc(s){return encodeURIComponent(s);}
