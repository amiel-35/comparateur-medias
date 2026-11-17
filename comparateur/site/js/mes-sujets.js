/* « Mes sujets » : les sujets suivis, gardés dans ce navigateur seulement (localStorage, clé à part). Rien ne part
   au serveur : à l'ouverture, la page compare la liste à l'édition qu'elle a déjà. Pas de suivi par mail. */
var CLE_MES='cadrages.sujets',MES_MAX=50;
function mesSujets(){
  try{var l=JSON.parse(localStorage.getItem(CLE_MES)||'[]');
    return Array.isArray(l)?l.filter(function(x){return x&&typeof x.id==='string'&&/^[\w-]{1,40}$/.test(x.id)&&typeof x.titre==='string';}).slice(0,MES_MAX):[];}
  catch(_){return [];}
}
function estSuivi(id){return mesSujets().some(function(x){return x.id===id;});}
function basculerSujet(id,titre){
  var l=mesSujets(),reste=l.filter(function(x){return x.id!==id;});
  if(reste.length===l.length)reste.unshift({id:id,titre:String(titre).slice(0,200)});
  try{if(reste.length)localStorage.setItem(CLE_MES,JSON.stringify(reste.slice(0,MES_MAX)));else localStorage.removeItem(CLE_MES);}catch(_){}
}
function fluxSujet(id){return '/flux/sujets/'+encodeURIComponent(id)+'.xml';}
function boutonSuivre(r){
  var oui=estSuivi(r.id);
  return '<p class="suivre"><button class="btn sm" type="button" id="btnSuivre" data-id="'+esc(r.id)+'" aria-pressed="'+oui+'">'+(oui?'Suivi sur cet appareil':'Suivre ce sujet sur cet appareil')+'</button> '+
    '<a href="'+fluxSujet(r.id)+'">Flux Atom de ce sujet</a></p>'+
    '<p class="note">Le suivi reste dans ce navigateur : ce site ne sait pas quels sujets vous suivez. Le flux est le même pour tous.</p>';
}
/* à l'accueil : les sujets suivis présents dans cette édition, puis ceux qui n'y sont pas */
function blocMesSujets(){
  var l=mesSujets();if(!l.length)return '';
  var ici=l.filter(function(x){return RB[x.id];}),ailleurs=l.filter(function(x){return !RB[x.id];});
  var h='<section class="mes" aria-labelledby="hMes"><h2 id="hMes">Mes sujets</h2><p class="note">Gardés dans ce navigateur seulement.</p><ul class="pl">';
  h+=ici.map(function(x){var r=RB[x.id];return '<li><a href="#/sujet/'+esc(r.id)+'">'+esc(r.titre)+'</a>'+mdl()+' <span class="mono mute">dans cette édition · '+pl(r.nmed,'média','médias')+'</span></li>';}).join('');
  h+=ailleurs.map(function(x){return '<li>'+esc(x.titre)+mdl()+' <span class="mono mute">absent de cette édition</span> <a href="'+fluxSujet(x.id)+'">flux</a></li>';}).join('');
  return h+'</ul></section>';
}
