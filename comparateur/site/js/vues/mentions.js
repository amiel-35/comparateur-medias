/* Mentions légales et données personnelles. D.mesure (facultatif) : "umami" si la fréquentation est mesurée.
   D.mail (facultatif) : réglé si la synthèse de la semaine part par mail. */
function vMentions(){
  var UM=D.mesure==='umami';
  var mail='<a href="mailto:amiel@inflexion.me">amiel@inflexion.me</a>';
  return '<h1 tabindex="-1" id="h1">Ce site ne dépose aucun cookie</h1>'+
  '<div class="prose"><p>Ce site est personnel et non commercial. Il n’est pas une activité d’Inflexion.</p></div>'+
  '<h2>Éditeur</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Éditeur et directeur de la publication :</b> Amiel Lavon, à titre personnel.</li>'+
  '<li><b>Contact :</b> '+mail+'.</li></ul>'+
  '<h2>Hébergement</h2><ul class="lim" style="max-width:68ch">'+
  '<li>Hetzner Online GmbH, Industriestr. 25, 91710 Gunzenhausen, Allemagne. Téléphone : +49 9831 505-0.</li></ul>'+
  '<h2>Données personnelles</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Aucun cookie.</b> Le navigateur garde le choix du thème. Il garde aussi une copie des pages et des données du site déjà ouvertes, pour les montrer hors connexion. Rien de cela ne quitte l’appareil.</li>'+
  (UM?'<li><b>Fréquentation.</b> Elle est mesurée avec Umami, un outil hébergé par l’éditeur, sans cookie, sans identifiant et sans donnée personnelle. Umami compte des pages vues, pas des personnes.</li>'
     :'<li><b>Fréquentation.</b> Elle n’est pas mesurée.</li>')+
  (D.mail?'<li><b>Mail de la semaine.</b> Si vous vous y inscrivez, la base garde votre adresse mail, un jeton aléatoire pour les liens de confirmation et de désinscription, la date d’inscription, celle de la confirmation et la semaine du dernier envoi. L’adresse sert au mail de la semaine, rien d’autre. Elle est gardée jusqu’à la désinscription. Une inscription non confirmée sous 7 jours est effacée.</li>'+
     '<li><b>Envoi du mail.</b> Il passe par Brevo (Brevo SAS, 17 rue Salneuve, 75017 Paris, France), prestataire d’envoi. Brevo reçoit l’adresse pour chaque envoi.</li>'+
     '<li><b>Suivi par Brevo.</b> Brevo ajoute à chaque mail une image invisible et fait passer les liens par ses serveurs. Il compte ainsi les ouvertures et les clics. Ce suivi est imposé par Brevo : ce site ne peut pas le couper. Bloquer les images dans votre messagerie empêche le comptage des ouvertures.</li>'+
     '<li><b>Se désinscrire.</b> Le lien en bas de chaque mail mène à une page avec un bouton. Un clic supprime l’adresse de la base. Les logiciels de messagerie qui proposent « se désabonner » le font aussi, en un clic. L’inscription ne dépose aucun cookie.</li>':'')+
  '<li><b>Adresse IP.</b> Le programme du site la garde en mémoire, pour limiter les abus, et l’oublie au plus tard une heure après la dernière visite. Il ne l’écrit ni dans un fichier ni dans la base. Le relais placé devant le site par l’hébergement (Traefik, sous Coolify) ne tient pas de journal des accès : il est désactivé. Vérifié le 17 novembre 2026. Aucun autre service ne se place entre le lecteur et le site.</li>'+
  '<li><b>Vote à l’aveugle.</b> Il est réservé aux invités. Chaque votant a un pseudonyme : un jeton aléatoire, gardé dans son navigateur. La base garde l’empreinte de ce jeton, le bord déclaré par le votant et ses avis, datés au jour. Elle ne garde ni nom ni adresse. Ce n’est pas un anonymat : l’éditeur sait à qui il a remis chaque invitation, et le jour où une invitation sert est aussi le jour où le votant s’inscrit. Avec peu d’inscrits, un votant peut être retrouvé, et ses avis avec lui.</li>'+
  '<li><b>Vos droits.</b> Pour toute question sur vos données : '+mail+'. Vous pouvez aussi saisir la <a href="https://www.cnil.fr/fr/plaintes" target="_blank" rel="noopener noreferrer">CNIL ↗</a>.</li></ul>'+
  '<h2>Contenus</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Les titres</b> appartiennent à leurs journaux. Chaque titre renvoie à l’article.</li>'+
  '<li><b>Le classement</b> est celui de FrIdéo v1.0, du French News Lab, sous licence CC BY 4.0. <a href="#/classement">Voir le classement</a>.</li>'+
  '<li><b>Les textes signalés</b> <span class="mdl" style="margin:0">écrit par un modèle</span> sont rédigés par un modèle de langage.</li>'+
  '<li><b>Le code</b> est public, sous licence AGPL-3.0 : <a href="https://github.com/amiel-35/comparateur-medias" target="_blank" rel="noopener noreferrer">github.com/amiel-35/comparateur-medias ↗</a>.</li></ul>';
}
