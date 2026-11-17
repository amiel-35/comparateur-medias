/* La normalisation d'une adresse d'article, et sa clé. Même règle que comparateur/index.py (mêmes vecteurs d'essai :
   tests/vecteurs-adresses.json). Sans l'objet URL, dont les règles diffèrent de celles de Python (ports par défaut,
   encodage du chemin, hôtes). Les espaces des bords sont retirés ; le schéma doit être http ou https, puis il est
   oublié ; l'hôte est en minuscules, sans point final, sans port, sans identifiants ; un préfixe d'usage (www., m.,
   mobile., amp.) est retiré une fois si l'hôte garde deux étiquettes ; le chemin reste tel quel, « / » s'il est
   vide, sans barre finale ; paramètres et fragment sont retirés. Résultat : hôte + chemin, ou null. */
var ADR_SCHEMA=/^(https?):\/\/([^\/?#]*)([^?#]*)/i;
function normaliserAdresse(u){
  if(typeof u!=='string')return null;
  var m=ADR_SCHEMA.exec(u.replace(/^[ \t\n\r\f\v]+|[ \t\n\r\f\v]+$/g,''));
  if(!m)return null;
  var hote=m[2],chemin=m[3];
  hote=hote.slice(hote.lastIndexOf('@')+1).replace(/:[0-9]*$/,'').replace(/[A-Z]+/g,function(x){return x.toLowerCase();}).replace(/\.+$/,'');
  if(!hote||/[:\[\]]/.test(hote))return null;
  var et=hote.split('.');
  if(['www','m','mobile','amp'].indexOf(et[0])>=0&&et.length>2)hote=et.slice(1).join('.');
  if(chemin==='')chemin='/';
  else if(chemin.length>1&&chemin.charAt(chemin.length-1)==='/')chemin=chemin.slice(0,-1);
  return hote+chemin;
}
/* Les 16 premiers caractères hexadécimaux du SHA-256 de la forme normalisée (UTF-8). Rend une promesse : null si
   l'adresse n'a pas de forme normalisée. */
function cleAdresse(u){
  var n=normaliserAdresse(u);
  if(n===null)return Promise.resolve(null);
  return crypto.subtle.digest('SHA-256',new TextEncoder().encode(n)).then(function(b){
    return Array.prototype.map.call(new Uint8Array(b),function(x){return ('0'+x.toString(16)).slice(-2);}).join('').slice(0,16);
  });
}
