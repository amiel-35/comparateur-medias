/* Page d'un sujet. */
/* un bord par ligne : qui en parle, sur sept bords */
function brows(r){
  var mx=1;BORDS.forEach(function(b){mx=Math.max(mx,r.par[b]);});
  return '<ul class="brows">'+BORDS.map(function(b){
    var n=r.par[b],nm=Object.keys(r.medb[b]).length;
    var txt=n?'<b>'+pl(n,'titre','titres')+'</b> · '+pl(nm,'média','médias'):(!LUS[b]?'<span class="mute">aucun média lu</span>':r.sil.indexOf(GRP[b])>=0?'<span class="ko">silence</span>':'<span class="mute">aucun titre</span>');
    return '<li><span class="bl">'+bchip(b)+'</span><span class="bt'+(n?'':' nul')+'">'+(n?'<i class="b-'+b+'" style="width:'+Math.max(2,Math.round(100*n/mx))+'%"></i>':'')+'</span><span class="bn">'+txt+'</span></li>';
  }).join('')+'</ul>';
}
/* un sujet suivi d'une édition à l'autre : une ligne par édition gardée, entre son premier et son dernier jour */
function jourFrise(j){return new Date(j+'T12:00:00Z').toLocaleDateString('fr-FR',{timeZone:'UTC',weekday:'long',day:'numeric',month:'long'});}
function frise(r){
  var su=(D.suivi||{})[r.id];if(!su||su.length<2)return '';
  var by={},mx=1;su.forEach(function(x){by[x.jour]=x;mx=Math.max(mx,x.titres);});
  var jours=(ED.toutes||[]).filter(function(j){return j>=su[0].jour&&j<=su[su.length-1].jour;});
  su.forEach(function(x){if(jours.indexOf(x.jour)<0)jours.push(x.jour);});jours.sort();
  var h='<h2>Ce sujet dans le temps</h2><p class="note">Ce sujet figure dans '+su.length+' éditions gardées. Chaque jour mène à sa page ce jour-là. La barre compte les titres par bord. Sa longueur dit combien. Compté par formule, sans modèle.</p><ol class="brows frise">';
  jours.forEach(function(j){
    var x=by[j],ici=j===ED.jour;
    var lab=ici?'<b aria-current="true">'+esc(jourFrise(j))+'</b> <span class="mono mute">cette édition</span>':x?'<a href="'+edUrl(j)+'#/sujet/'+esc(r.id)+'">'+esc(jourFrise(j))+'</a>':'<span class="mute">'+esc(jourFrise(j))+'</span>';
    if(!x){h+='<li><span class="bl">'+lab+'</span><span class="bt nul"></span><span class="bn mute">absent de cette édition</span></li>';return;}
    var sl=(x.silences||[]).filter(function(b){return GL[b];});
    h+='<li><span class="bl">'+lab+'</span><span class="bt">'+barFine(x.par||{},Math.max(4,Math.round(100*x.titres/mx)))+'</span><span class="bn">'+pl(x.titres,'titre','titres')+' · '+pl(x.medias,'média','médias')+(sl.length?' <span class="ko">silence : '+sl.map(function(x){return GL[x].toLowerCase();}).join(', ')+'</span>':'')+'</span></li>';
  });
  return h+'</ol>'+legende();
}
function titleLi(r,a){
  return '<li><div class="who"><a class="mname mchip" href="#/media/'+enc(a.media)+'">'+esc(a.media)+'</a>'+bchip(a.bord)+'</div><a class="t" href="'+url(a.lien)+'" target="_blank" rel="noopener noreferrer">'+esc(a.titre)+' ↗</a></li>';
}
function sujetView(r){
  var h='<div><p class="crumb"><a href="#/">Les sujets du jour</a> / Sujet '+r.n+'</p>'+
  '<p class="mono mute">Sujet '+r.n+' sur '+rounds.length+'</p><h1 tabindex="-1" id="h1">'+esc(r.titre)+(r.kind==='sujet'?mdl():'')+'</h1>';
  if(r.fait)h+='<div class="fait"><span class="mono">Le fait commun'+mdl()+'</span><p>'+esc(r.fait)+'</p></div>';
  /* qui en parle */
  h+='<h2>Qui en parle</h2><p class="note">Les titres, comptés sur les sept bandes de FrIdéo. Par formule, sans modèle.</p>'+brows(r);
  if(r.kind==='sujet')h+='<div class="chips">'+(r.sil.length?silChip(r)+'<span class="note">Aucun média de '+(r.sil.length>1?'ces côtés':'ce côté')+' n’a de titre rangé sous ce sujet, repris par '+r.nmed+' médias. <a href="#/silences">Tous les silences de l’édition</a>.</span>':r.large?'<span class="note">Gauche, centre et droite ont chacun au moins un titre sur ce sujet.</span>':'<span class="note">Sujet repris par moins de '+MIN+' médias : les silences n’y sont pas relevés.</span>')+'</div>';
  if(r.div!=null){h+='<p><span class="mono">Écart de cadrage</span> <span class="dots" aria-label="'+r.div+' sur 5">'+'●'.repeat(r.div)+'○'.repeat(5-r.div)+'</span> '+r.div+' sur 5'+mdl()+'</p>';}
  /* face à face */
  h+='<h2>'+(r.kind==='sujet'?'Le même fait, trois formulations':'Les titres, côté par côté')+'</h2>';
  h+='<p class="note">'+(r.analyse?'Le modèle écrit un angle par côté, pas par bord : ':'Les titres sont rangés ici en trois côtés : ')+'les bandes de gauche (extrême gauche, gauche, centre gauche), le centre, les bandes de droite (centre droit, droite, extrême droite). Les comptages ci-dessus se font sur sept bords, et chaque titre porte le bord de son journal.</p><div class="cols">';
  ['g','c','d'].forEach(function(x){
    var list=r.arts.filter(function(a){return a.grp===x;}).sort(function(a,b){return a.score-b.score;});
    var names=Object.keys(r.med[x]);
    h+='<section class="col s-'+x+'"><header><span>'+GL3[x]+'</span><span class="mono" style="font-weight:400">'+pl(list.length,'titre','titres')+(names.length?' · '+pl(names.length,'média','médias'):'')+'</span></header><div class="body">';
    /* un sujet trop peu repris n'est pas analysé : pas d'angle, donc pas d'étiquette « écrit par un modèle » */
    if(r.analyse&&r.div!=null)h+='<div class="angle"><span class="lab mono mute">Angle'+mdl()+'</span>'+esc(r.analyse[x])+'</div>';
    else if(r.kind==='sujet')h+='<div class="angle"><span class="lab mono mute">Angle</span><span class="mute">Sujet non analysé : trop peu repris.</span></div>';
    if(!list.length)h+='<div class="silence">Aucun titre de ce côté'+'<span>'+(r.kind==='sujet'?'Aucun média de ce côté n’apparaît sous ce sujet dans les flux récoltés.':'Aucun titre de ce côté parmi les titres sans jumeau.')+'</span></div>';
    else{
      var first=list.slice(0,5),rest=list.slice(5);
      h+='<ul class="tlist">'+first.map(function(a){return titleLi(r,a);}).join('')+'</ul>';
      if(rest.length)h+='<details><summary>Voir les '+rest.length+' autres titres</summary><ul class="tlist">'+rest.map(function(a){return titleLi(r,a);}).join('')+'</ul></details>';
    }
    h+='</div></section>';
  });
  h+='</div>';
  /* les titres des médias non classés : comptés dans la couverture du sujet, rangés sous aucun côté */
  if(r.nc&&r.nc.length){
    var ncm={};r.nc.forEach(function(a){ncm[a.media]=1;});
    h+='<section class="col nc-col"><header><span>Non classés</span><span class="mono" style="font-weight:400">'+pl(r.nc.length,'titre','titres')+' · '+pl(Object.keys(ncm).length,'média','médias')+'</span></header><div class="body">'+
      '<p class="note">FrIdéo ne classe pas ces médias. Leurs titres comptent dans la couverture du sujet, dans aucun bord ni aucun silence.</p>'+
      '<ul class="tlist">'+r.nc.map(function(a){return titleLi(r,a);}).join('')+'</ul></div></section>';
  }
  if(r.mots&&r.mots.length){
    h+='<h2>Les mots qui diffèrent'+mdl()+'</h2><ul class="mots">'+r.mots.map(function(m){return '<li><q>'+esc(m.terme)+'</q><br><span class="mute">'+esc(m.qui)+'</span></li>';}).join('')+'</ul>';
  }else if(r.kind==='sujet'){h+='<h2>Les mots qui diffèrent</h2><p class="note">Le modèle n’a repéré aucun mot qui diffère nettement sur ce sujet.</p>';}
  h+=frise(r);
  h+='<p class="note">Aller vérifier : <a href="#/classement">le classement des médias</a> · <a href="#/demarche">la démarche</a>.</p>';
  var pr=rounds[r.n-2],nx=rounds[r.n];
  h+='<div class="pn">'+(pr?'<a class="btn" href="#/sujet/'+pr.id+'">← Sujet '+pr.n+'</a>':'<span></span>')+(nx?'<a class="btn hl" href="#/sujet/'+nx.id+'">Sujet '+nx.n+' →</a>':'<a class="btn hl" href="#/">Retour aux sujets</a>')+'</div></div>';
  return h;
}
function vRound(id){var r=RB[id];if(!r)return vHome();return sujetView(r);}
