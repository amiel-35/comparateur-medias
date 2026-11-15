/* La semaine et le mois : des comptages sur les éditions gardées, sans modèle. */
function perTitre(p,type){
  if(type==='mois')return 'Le mois de '+new Date(p.debut+'T12:00:00Z').toLocaleDateString('fr-FR',{timeZone:'UTC',month:'long',year:'numeric'});
  return 'La semaine du '+jourNum(p.debut)+' au '+jourNum(p.fin)+' '+p.fin.slice(0,4);
}
function vPeriode(type){
  var nomV=type==='mois'?'Mois':'Semaine';
  if(!PER)return '<p class="crumb"><a href="#/">Sujets</a> / '+nomV+'</p><h1 tabindex="-1" id="h1">'+nomV+'</h1><p class="vide">Pas encore de synthèse.</p>';
  var p=type==='mois'?PER.mois:PER.semaine, liste=type==='mois'?PER.mois_liste:PER.semaines;
  var i=liste.map(function(x){return x.cle;}).indexOf(p.cle), av=i>0?liste[i-1]:null, ap=i>=0&&i<liste.length-1?liste[i+1]:null;
  var h='<p class="crumb"><a href="#/">Sujets</a> / '+nomV+'</p>';
  h+='<nav class="ed" aria-label="Périodes">'+(av?'<a class="btn sm" href="'+edUrl(av.jour)+'#/'+type+'" rel="prev">← précédent</a>':'<span class="btn sm off" aria-hidden="true">←</span>')+
     '<span class="ed-j">'+(type==='mois'?'Synthèse du mois':'Synthèse de la semaine')+'</span>'+
     (ap?'<a class="btn sm" href="'+edUrl(ap.jour)+'#/'+type+'" rel="next">suivant →</a>':'<span class="btn sm off" aria-hidden="true">→</span>')+'</nav>';
  h+='<h1 tabindex="-1" id="h1">'+esc(perTitre(p,type))+'</h1>';
  h+='<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:58ch">Ce que les éditions de la période disent, mises bout à bout : les sujets les plus couverts, ce que chaque bord a traité, et ce qu’il a laissé de côté.</p>';
  h+='<p class="note">'+pl(p.jours.length,'édition gardée','éditions gardées')+' sur la période'+(p.jours.length<(type==='mois'?28:7)?' : la synthèse est partielle':'')+'. Tout est compté par une formule fixe, sans modèle de langage. Seuls les titres des sujets sont écrits par un modèle.</p>';
  h+='<div class="nums"><div><b>'+p.jours.length+'</b><span>'+(p.jours.length>1?'éditions':'édition')+'</span></div><div><b>'+p.sujets+'</b><span>sujets</span></div><div><b>'+p.titres+'</b><span>titres rangés</span></div><div><b>'+p.larges+'</b><span>sujets repris par '+p.min_medias+' médias ou plus</span></div></div>';
  /* les sujets les plus couverts */
  h+='<h2>Les sujets les plus couverts</h2><ol class="ptop">'+p.top.map(function(x){
    return '<li><a href="'+sujLien(x)+'">'+esc(x.titre)+'</a>'+mdl()+'<span class="pm mono mute">'+pl(x.medias,'média','médias')+' · '+pl(x.titres,'titre','titres')+(x.jours>1?' · '+x.jours+' jours':'')+(x.ecart!=null?' · écart '+x.ecart+' sur 5':'')+'</span>'+
      bar5(x.par)+'</li>';
  }).join('')+'</ol>'+legende();
  /* par bord */
  h+='<h2>Par bord</h2><p class="note">Cinq bords, tirés du score FrIdéo par ce site. Un silence : un sujet repris par '+p.min_medias+' médias ou plus, sans aucun titre de tout un côté (gauche et centre gauche, centre, ou centre droit et droite). Il est compté pour chaque bord de ce côté.</p><div class="cols cinq">';
  BORDS.forEach(function(c){
    var b=p.bords[c];if(!b)return;
    h+='<section class="col k-'+c+'"><header><span>'+BL[c]+'</span><span class="mono" style="font-weight:400">'+pl(b.medias,'journal lu','journaux lus')+' · '+pl(b.titres,'titre','titres')+'</span></header><div class="body">';
    if(!b.medias){h+='<p class="vide">Aucun journal de ce bord n’a été lu sur la période. Ses silences ne sont pas comptés.</p></div></section>';return;}
    h+='<p class="pk"><b>'+b.sujets+' sur '+b.sur+'</b> grands sujets couverts · <b>'+b.silences+'</b> '+(b.silences>1?'silences':'silence')+'</p>';
    h+='<p class="lab mono mute">Ce qu’il a le plus traité</p>'+(b.plus_couverts.length?'<ul class="pl">'+b.plus_couverts.map(function(x){return '<li><a href="'+sujLien(x)+'">'+esc(x.titre)+'</a> <span class="mono mute">'+pl(x.titres,'titre','titres')+'</span></li>';}).join('')+'</ul>':'<p class="vide">Rien relevé.</p>');
    h+='<p class="lab mono mute">Ce qu’il a laissé de côté</p>'+(b.tus.length?'<ul class="pl">'+b.tus.map(function(x){return '<li><a href="'+sujLien(x)+'">'+esc(x.titre)+'</a> <span class="mono mute">'+x.medias+' médias ailleurs</span></li>';}).join('')+'</ul>':'<p class="vide">Aucun silence sur les grands sujets.</p>');
    h+='</div></section>';
  });
  h+='</div>';
  /* par journal */
  h+='<h2>Par journal</h2><p class="note">« Grands sujets » : ceux repris par '+p.min_medias+' médias ou plus. « Dans le top » : présence parmi les '+p.top.length+' sujets les plus couverts.</p>';
  h+='<div class="ptw"><table class="pt"><thead><tr><th scope="col">Journal</th><th scope="col">Bord</th><th scope="col">Titres rangés</th><th scope="col">Grands sujets</th><th scope="col">Dans le top</th></tr></thead><tbody>'+p.medias.map(function(m){
    return '<tr><th scope="row"><a href="#/media/'+enc(m.nom)+'">'+esc(m.nom)+'</a></th><td>'+(BL[m.bord]||GL[m.cote]||'')+'</td><td>'+m.titres+'</td><td>'+m.sujets+' sur '+p.larges+'</td><td>'+m.top+' sur '+p.top.length+'</td></tr>';
  }).join('')+'</tbody></table></div>';
  h+='<p class="note">Limites. Un journal absent d’un sujet n’en a peut-être pas parlé, ou son titre n’a pas été rangé sous ce sujet. Deux sujets ouverts séparément sur le même fait sont comptés deux fois. Les journaux dont le flux est illisible n’apparaissent pas.</p>';
  return h;
}
