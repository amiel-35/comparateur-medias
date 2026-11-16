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
  else if(v==='semaine'||v==='mois')html=vPeriode(v);
  else if(v==='silences')html=vSilences();
  else if(v==='pourquoi'){html=vPourquoi();nav='';}
  else if(v==='mentions'){html=vMentions();nav='';}
  else if(v==='installer')html=vInstaller();
  else{html=vHome();nav='home';}
  var y=window.scrollY;
  app.innerHTML=html;
  document.querySelectorAll('nav.main a,nav.aide a').forEach(function(a){if(a.getAttribute('data-nav')===nav)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  if(opt&&opt.keep){window.scrollTo(0,y);if(opt.focus){var f=app.querySelector(opt.focus);if(f)f.focus({preventScroll:true});}}
  else{window.scrollTo(0,0);var h1=document.getElementById('h1')||app.querySelector('h1');if(h1){h1.setAttribute('tabindex','-1');h1.focus({preventScroll:true});}}
  if(v==='semaine'&&parts[1]==='mail'){var em=document.getElementById('mailAdr');if(em){em.scrollIntoView({block:'center'});em.focus({preventScroll:true});}}
  document.title=(app.querySelector('h1')?app.querySelector('h1').textContent.replace(/écrit par un modèle/,'').trim()+' · ':'')+'Cadrages';
}
window.addEventListener('hashchange',function(){route();});
/* « Par mail » dans l'en-tête : vers l'inscription de la page Semaine, seulement si le mail est en service */
(function(){var m=document.getElementById('btnMail');if(!m||!DONNEES.mail)return;m.hidden=false;
  m.addEventListener('click',function(){if(location.hash==='#/semaine/mail')route();});})();

/* L'application installable. Le service worker est enregistré s'il existe dans ce navigateur, sans erreur sinon.
   L'invitation à installer (beforeinstallprompt, Chrome, Edge, Android) est gardée pour le bouton de #/installer :
   le site n'affiche aucune invitation ailleurs. */
if('serviceWorker' in navigator){try{navigator.serviceWorker.register('/sw.js').catch(function(){});}catch(_){}}
window.addEventListener('beforeinstallprompt',function(e){e.preventDefault();INVITE=e;if(/^#\/installer/.test(location.hash))route({keep:true});});
window.addEventListener('appinstalled',function(){INVITE=null;if(/^#\/installer/.test(location.hash))route({keep:true});});
/* Inscription au mail de la semaine (encart de #/semaine). La réponse du serveur est toujours la même. */
app.addEventListener('submit',function(e){
  if(e.target.id!=='fMail')return;
  e.preventDefault();
  var f=e.target,msg=document.getElementById('mailMsg'),b=f.querySelector('button');
  if(!f.adresse.value.trim()){msg.textContent='Saisissez une adresse mail.';f.adresse.focus();return;}
  b.disabled=true;msg.textContent='Un instant…';
  fetch('/api/mail/inscription',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({adresse:f.adresse.value.trim(),site:f.site.value})})
    .then(function(r){
      if(r.status===202){f.adresse.value='';msg.textContent='Si l’adresse est valide, un mail de confirmation est parti. Le lien qu’il contient finit l’inscription. Pensez à regarder dans les indésirables.';}
      else msg.textContent=r.status===429?'Trop d’essais depuis cette connexion. Réessayez dans une heure.':'L’inscription n’a pas abouti. Réessayez plus tard.';
    },function(){msg.textContent='Pas de réseau. Réessayez plus tard.';})
    .then(function(){b.disabled=false;});
});
app.addEventListener('click',function(e){
  var b=e.target.closest&&e.target.closest('#btnInstaller');if(!b||!INVITE)return;
  var inv=INVITE;INVITE=null;inv.prompt();
  Promise.resolve(inv.userChoice).catch(function(){}).then(function(){route({keep:true});});
});

function effDark(){return S.theme?S.theme==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;}
function applyTheme(){var d=document.documentElement;if(S.theme)d.setAttribute('data-theme',S.theme);else d.removeAttribute('data-theme');
  var b=document.getElementById('btnTheme');var t=effDark()?'Thème : sombre':'Thème : clair';b.innerHTML='<span class="th-i" aria-hidden="true">◐</span><span class="th-t">'+t+'</span>';b.title=t;}
document.getElementById('btnTheme').addEventListener('click',function(){S.theme=effDark()?'light':'dark';save();applyTheme();});
try{window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',applyTheme);}catch(_){}

document.getElementById('foot').innerHTML='<p><span class="mdl" style="margin:0">écrit par un modèle</span> signale tout texte rédigé par un modèle de langage (sujets, faits, angles, mots). Les scores viennent de FrIdéo v1.0 (French News Lab, CC BY 4.0), les comptages d’une formule fixe. Données du '+esc(new Date(D.recolte).toLocaleDateString('fr-FR',{timeZone:'Europe/Paris'}))+'. '+(D.mesure==='umami'?'Aucun cookie. La fréquentation est mesurée sans cookie ni donnée personnelle.':'Aucun cookie. Seul le choix du thème reste dans votre navigateur.')+(D.mail?' <a href="#/semaine/mail">La synthèse de la semaine par mail</a>.':'')+' <a href="#/mentions">Mentions légales et données personnelles</a>. <a href="#/installer">Installer Cadrages comme une application</a>.</p>';
applyTheme();route();
