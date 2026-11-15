/* Mentions légales et données personnelles. D.mesure (facultatif) : "umami" si la fréquentation est mesurée. */
function vMentions(){
  var UM=D.mesure==='umami';
  var mail='<a href="mailto:amiel@inflexion.me">amiel@inflexion.me</a>';
  return '<p class="crumb"><a href="#/">Sujets</a> / Mentions légales</p><h1 tabindex="-1" id="h1">Ce site ne dépose aucun cookie</h1>'+
  '<div class="prose"><p>Ce site est personnel et non commercial. Il n’est pas une activité d’Inflexion.</p></div>'+
  '<h2>Éditeur</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Éditeur et directeur de la publication :</b> Amiel Lavon, à titre personnel.</li>'+
  '<li><b>Contact :</b> '+mail+'.</li></ul>'+
  '<h2>Hébergement</h2><ul class="lim" style="max-width:68ch">'+
  '<li>Hetzner Online GmbH, Industriestr. 25, 91710 Gunzenhausen, Allemagne. Téléphone : +49 9831 505-0.</li></ul>'+
  '<h2>Données personnelles</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Aucun cookie.</b> Le navigateur garde seulement le choix du thème. Ce choix ne quitte pas l’appareil.</li>'+
  (UM?'<li><b>Fréquentation.</b> Elle est mesurée avec Umami, un outil hébergé par l’éditeur, sans cookie, sans identifiant et sans donnée personnelle. Umami compte des pages vues, pas des personnes.</li>'
     :'<li><b>Fréquentation.</b> Elle n’est pas mesurée.</li>')+
  '<li><b>Adresse IP.</b> Le serveur la garde en mémoire, pour limiter les abus. Il ne l’écrit ni dans un fichier ni dans la base.</li>'+
  '<li><b>Vote à l’aveugle.</b> Il est réservé aux invités. La base garde l’empreinte d’un jeton anonyme, le bord déclaré par le votant et ses avis, datés au jour. Aucun nom, aucune adresse, aucun lien entre une invitation et un votant. Le jeton reste dans le navigateur du votant.</li>'+
  '<li><b>Vos droits.</b> Pour toute question sur vos données : '+mail+'. Vous pouvez aussi saisir la <a href="https://www.cnil.fr/fr/plaintes" target="_blank" rel="noopener noreferrer">CNIL ↗</a>.</li></ul>'+
  '<h2>Contenus</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Les titres</b> appartiennent à leurs journaux. Chaque titre renvoie à l’article.</li>'+
  '<li><b>Le classement</b> est celui de FrIdéo v1.0, du French News Lab, sous licence CC BY 4.0. <a href="#/classement">Voir le classement</a>.</li>'+
  '<li><b>Les textes signalés</b> <span class="mdl" style="margin:0">écrit par un modèle</span> sont rédigés par un modèle de langage.</li>'+
  '<li><b>Le code</b> est public, sous licence AGPL-3.0 : <a href="https://github.com/amiel-35/comparateur-medias" target="_blank" rel="noopener noreferrer">github.com/amiel-35/comparateur-medias ↗</a>.</li></ul>';
}
