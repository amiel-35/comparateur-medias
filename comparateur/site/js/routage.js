/* routage */
var app=document.getElementById('app');
function route(opt){
  var hsh=location.hash.replace(/^#\/?/,'');var parts=hsh.split('/');var v=parts[0]||'home';var html,nav=v;
  if(v==='sujet'){html=vRound(parts[1]);nav='home';}
  else if(v==='media'){html=vMedia(decodeURIComponent(parts.slice(1).join('/')));nav='medias';}
  else if(v==='medias')html=vMedias();
  else if(v==='classement')html=vClass();
  else if(v==='demarche')html=vDemarche();
  else if(v==='origine')html=vOrigine();
  else if(v==='editions'){html=vEditions();nav='home';}
  else if(v==='semaine'||v==='mois'){html=vPeriode(v);nav='home';}
  else if(v==='silences'){html=vSilences();nav='home';}
  else if(v==='pourquoi'){html=vPourquoi();nav='home';}
  else if(v==='mentions'){html=vMentions();nav='home';}
  else{html=vHome();nav='home';}
  var y=window.scrollY;
  app.innerHTML=html;
  document.querySelectorAll('nav.main a').forEach(function(a){if(a.getAttribute('data-nav')===nav)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  if(opt&&opt.keep){window.scrollTo(0,y);if(opt.focus){var f=app.querySelector(opt.focus);if(f)f.focus({preventScroll:true});}}
  else{window.scrollTo(0,0);var h1=document.getElementById('h1')||app.querySelector('h1');if(h1){h1.setAttribute('tabindex','-1');h1.focus({preventScroll:true});}}
  document.title=(app.querySelector('h1')?app.querySelector('h1').textContent.replace(/écrit par un modèle/,'').trim()+' · ':'')+'Cadrages';
}
window.addEventListener('hashchange',function(){route();});

function effDark(){return S.theme?S.theme==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;}
function applyTheme(){var d=document.documentElement;if(S.theme)d.setAttribute('data-theme',S.theme);else d.removeAttribute('data-theme');
  var b=document.getElementById('btnTheme');b.textContent=effDark()?'Thème : sombre':'Thème : clair';}
document.getElementById('btnTheme').addEventListener('click',function(){S.theme=effDark()?'light':'dark';save();applyTheme();});
try{window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',applyTheme);}catch(_){}

document.getElementById('foot').innerHTML='<p><span class="mdl" style="margin:0">écrit par un modèle</span> signale tout texte rédigé par un modèle de langage (sujets, faits, angles, mots). Les scores viennent de FrIdéo v1.0 (French News Lab, CC BY 4.0), les comptages d’une formule fixe. Données du '+esc(new Date(D.recolte).toLocaleDateString('fr-FR',{timeZone:'Europe/Paris'}))+'. '+(D.mesure==='umami'?'Aucun cookie. La fréquentation est mesurée sans cookie ni donnée personnelle.':'Aucun cookie. Seul le choix du thème reste dans votre navigateur.')+' <a href="#/mentions">Mentions légales et données personnelles</a>.</p>';
applyTheme();route();
