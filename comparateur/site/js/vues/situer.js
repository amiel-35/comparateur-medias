/* Situer un article : la personne colle l'adresse d'un article, la page dit de quel média il vient (sa bande FrIdéo, ou
   « non classé ») et, s'il est dans l'index, sous quel sujet. La page télécharge /index.json (le même fichier pour tous,
   sans paramètre) puis cherche sur l'appareil : rien de ce qui est collé n'est envoyé. Une valeur de l'index n'entre
   dans la page que par esc(). */
var SIT_IX=null,SIT_ECOUTE=false;
function sitCharger(){
  if(!SIT_IX)SIT_IX=fetch('/index.json').then(function(r){
    if(!r.ok)throw new Error('http');
    return r.json();
  }).then(function(ix){
    if(!ix||ix.v!==1||typeof ix.medias!=='object'||typeof ix.sujets!=='object'||typeof ix.articles!=='object'||!ix.medias||!ix.sujets||!ix.articles)throw new Error('format');
    return ix;
  });
  return SIT_IX;
}
/* le média d'un hôte : l'hôte lui-même, puis ses domaines parents (abonnes.exemple.fr, puis exemple.fr) */
function sitMedia(ix,hote){
  var et=hote.split('.');
  for(var i=0;i<=et.length-2;i++){var m=ix.medias[et.slice(i).join('.')];if(m&&typeof m==='object')return m;}
  return null;
}
function sitDate(ix){return /^\d{4}-\d\d-\d\d$/.test(ix.genere_le)?jourLong(ix.genere_le):'date inconnue';}
function sitMeta(ix){
  return 'Index du '+esc(sitDate(ix))+(ix.methode?' · méthode '+esc(ix.methode):'')+(ix.classement?' · classement '+esc(ix.classement):'')+'.';
}
function sitReponse(ix,adresse,cle){
  var n=normaliserAdresse(adresse);
  if(n===null)return '<p><b>Cette adresse n’est pas celle d’une page web.</b> Il faut une adresse qui commence par http:// ou https://.</p>';
  var m=sitMedia(ix,n.split('/')[0]),h='';
  if(!m)h+='<p><b>Ce site ne lit pas ce média.</b> Il ne le connaît pas : aucune bande, aucun sujet.</p>';
  else if(m.statut==='classe'&&BL[m.bande]){
    h+='<p><b>'+esc(m.nom)+'</b> '+bchip(m.bande)+'</p>';
    h+='<p class="note">Bande du classement FrIdéo'+(typeof m.score==='number'?', score '+fs(m.score):'')+
       (m.ic&&m.ic.length===2&&typeof m.ic[0]==='number'&&typeof m.ic[1]==='number'?' (intervalle de '+fs(m.ic[0])+' à '+fs(m.ic[1])+')':'')+'. Ce site ne classe aucun média.</p>';
  }else h+='<p><b>'+esc(m.nom)+'</b> '+bchip(null)+'</p><p class="note">Ce site lit ce média, mais FrIdéo ne le classe pas : il n’a aucune bande ici.</p>';
  var s=cle?ix.sujets[ix.articles[cle]]:null;
  if(!s||typeof s!=='object')return m?h+'<p>Cet article n’est dans aucune édition des sept derniers jours.</p>':h;
  var par={};BORDS.forEach(function(b){par[b]=Number(s.par&&s.par[b])||0;});
  var sil=(Array.isArray(s.silences)?s.silences:[]).filter(function(x){return GL[x];});
  h+='<h2>Le sujet</h2><p class="sit-sujet">'+esc(s.titre)+' '+mdl()+'</p>'+bar5(par);
  h+='<p>'+(sil.length?'<b>Côtés silencieux :</b> '+sil.map(function(x){return esc(GL[x].toLowerCase());}).join(', ')+'. Aucun titre de ce côté n’est rangé sous ce sujet.':'Aucun côté silencieux sur ce sujet.')+'</p>';
  if(typeof s.page==='string'&&s.page.indexOf('/editions/')===0&&s.page.indexOf('//')<0)h+='<p><a href="'+esc(s.page)+'">Voir la page du sujet</a>'+(/^\d{4}-\d\d-\d\d$/.test(s.jour)?' (édition du '+esc(jourCourt(s.jour))+')':'')+'</p>';
  return h;
}
function vSituer(){
  if(!SIT_ECOUTE){
    SIT_ECOUTE=true;
    document.getElementById('app').addEventListener('submit',function(e){
      if(e.target.id!=='fSituer')return;
      e.preventDefault();
      var champ=e.target.adresse,sortie=document.getElementById('sitRep'),adresse=champ.value;
      if(!adresse.trim()){sortie.innerHTML='<p>Collez d’abord une adresse.</p>';champ.focus();return;}
      sortie.innerHTML='<p>Un instant…</p>';
      Promise.all([sitCharger(),cleAdresse(adresse)]).then(function(r){sortie.innerHTML=sitReponse(r[0],adresse,r[1]);},
        function(){sortie.innerHTML='<p><b>L’index n’a pas pu être lu.</b> Réessayez plus tard.</p>';});
    });
  }
  sitCharger().then(function(ix){var p=document.getElementById('sitMeta');if(p)p.innerHTML=sitMeta(ix);},function(){});
  var h='<h1 tabindex="-1" id="h1">Une adresse d’article, et ce site dit d’où elle vient, sans l’envoyer</h1>';
  h+='<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:58ch">Collez l’adresse d’un article. La page dit de quel média il vient et, s’il figure dans une édition des sept derniers jours, sous quel sujet.</p>';
  h+='<p class="note"><b>Rien de ce que vous collez ne quitte votre appareil.</b> La page télécharge un fichier identique pour tout le monde, puis cherche dedans.</p>';
  h+='<form id="fSituer" class="fsit"><label for="sitAdr">Adresse de l’article</label><span class="fl"><input id="sitAdr" type="text" name="adresse" inputmode="url" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="https://…" maxlength="2000">'+
     '<button class="btn hl" type="submit">Situer</button></span></form>';
  h+='<div id="sitRep" class="sit-rep" role="status" aria-live="polite"></div>';
  h+='<p id="sitMeta" class="note"></p>';
  h+='<h2>Comment lire cette page</h2><ul class="lim" style="max-width:68ch"><li><b>Le média se reconnaît à son domaine.</b> Ce site ne connaît que les domaines vus dans les liens des articles qu’il a lus. Un domaine vu chez deux médias n’est pas retenu.</li>'+
     '<li><b>L’article se reconnaît à son adresse.</b> Les paramètres, le fragment, www. et le port sont ignorés ; le reste du chemin compte.</li>'+
     '<li><b>Sept jours seulement.</b> Un article plus ancien, ou jamais rangé sous un sujet, n’est pas retrouvé. Cela ne dit rien de lui.</li>'+
     '<li><b>Le titre du sujet est écrit par un modèle.</b> La bande vient de FrIdéo, les comptages d’une formule fixe.</li></ul>';
  return h;
}
