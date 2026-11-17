/* Mentions légales et données personnelles. D.mesure (facultatif) : "umami" si la fréquentation est mesurée.
   D.mail (facultatif) : réglé si la synthèse de la semaine part par mail. */
function vMentions(){
  var UM=D.mesure==='umami';
  var mail='<a href="mailto:amiel@inflexion.me">amiel@inflexion.me</a>';
  var CP=D.compte||null;   /* facultatif : l'adresse de la page du compte, si le mail est réglé */
  return '<h1 tabindex="-1" id="h1">'+(CP?'Ce site ne dépose qu’un cookie, sur la page du compte, pour rester connecté':'Ce site ne dépose aucun cookie')+'</h1>'+
  '<div class="prose"><p>Ce site est personnel et non commercial. Il n’est pas une activité d’Inflexion.</p></div>'+
  '<h2>Éditeur</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Éditeur et directeur de la publication :</b> Amiel Lavon, à titre personnel.</li>'+
  '<li><b>Contact :</b> '+mail+'.</li></ul>'+
  '<h2>Hébergement</h2><ul class="lim" style="max-width:68ch">'+
  '<li>Hetzner Online GmbH, Industriestr. 25, 91710 Gunzenhausen, Allemagne. Téléphone : +49 9831 505-0.</li></ul>'+
  '<h2>Données personnelles</h2><ul class="lim" style="max-width:68ch">'+
  (CP?'<li><b>Un seul cookie.</b> La page du compte (<a href="'+url(CP)+'/">'+esc(CP.replace(/^https?:\/\//,''))+'</a>) en pose un, pour garder la connexion jusqu’à un an. Il est réservé à cette page : le site et ses autres pages ne le reçoivent pas. Il est strictement nécessaire, d’où l’absence de bandeau. Se déconnecter l’efface.</li>':'<li><b>Aucun cookie.</b></li>')+
  '<li><b>Dans votre navigateur.</b> Le navigateur garde le choix du thème et les sujets que vous suivez (« Mes sujets »). Il garde aussi une copie des pages et des données du site déjà ouvertes, pour les montrer hors connexion. Rien de cela ne quitte l’appareil.</li>'+
  (UM?'<li><b>Fréquentation.</b> Elle est mesurée avec Umami, un outil hébergé par l’éditeur, sans cookie, sans identifiant et sans donnée personnelle. Umami compte des pages vues, pas des personnes.</li>'
     :'<li><b>Fréquentation.</b> Elle n’est pas mesurée.</li>')+
  (D.mail?'<li><b>Compte et mails.</b> Si vous vous inscrivez à un mail (la synthèse de la semaine, l’alerte du matin, des rubriques), une base à part, celle des comptes, garde votre adresse mail, le jour de sa création et le mois de votre dernière visite à la page du compte. Pour chaque abonnement : son type, sa rubrique s’il y en a une, le jour de l’inscription, celui du dernier envoi, et un code aléatoire pour le lien de désinscription. Pour chaque appareil connecté : une empreinte de la connexion et sa date de fin. Rien d’autre : ni bord, ni sujet suivi, ni lecture. L’adresse sert aux mails demandés, rien d’autre.</li>'+
     '<li><b>Durées.</b> Le code de connexion vit dix minutes. Une inscription non confirmée sous 7 jours est effacée. Un compte sans abonnement ni appareil connecté est effacé. La page du compte montre tout ce que la base garde, et un bouton efface le compte.</li>'+
     '<li><b>Envoi du mail.</b> Il passe par Brevo (Brevo SAS, 17 rue Salneuve, 75017 Paris, France), prestataire d’envoi. Brevo reçoit l’adresse pour chaque envoi.</li>'+
     '<li><b>Suivi par Brevo.</b> Brevo ajoute à chaque mail une image invisible et fait passer les liens par ses serveurs. Il compte ainsi les ouvertures et les clics. Ce suivi est imposé par Brevo : ce site ne peut pas le couper. Bloquer les images dans votre messagerie empêche le comptage des ouvertures.</li>'+
     '<li><b>Se désinscrire.</b> Le lien en bas de chaque mail mène à une page avec un bouton. Un clic supprime l’adresse de la base. Les logiciels de messagerie qui proposent « se désabonner » le font aussi, en un clic. L’inscription ne dépose aucun cookie.</li>':'')+
  '<li><b>Adresse IP.</b> Le programme du site la garde en mémoire, pour limiter les abus, et l’oublie au plus tard une heure après la dernière visite. Il ne l’écrit ni dans un fichier ni dans la base. Le relais placé devant le site par l’hébergement (Traefik, sous Coolify) peut tenir son propre journal des accès, avec l’adresse IP et l’heure de chaque page demandée. Ce point n’est pas encore vérifié.</li>'+
  '<li><b>Vote à l’aveugle.</b> Il est réservé aux invités. Chaque votant a un pseudonyme : un jeton aléatoire, gardé dans son navigateur. La base garde l’empreinte de ce jeton, le bord déclaré par le votant et ses avis, datés au jour. Elle ne garde ni nom ni adresse. Ce n’est pas un anonymat : l’éditeur sait à qui il a remis chaque invitation, et le jour où une invitation sert est aussi le jour où le votant s’inscrit. Avec peu d’inscrits, un votant peut être retrouvé, et ses avis avec lui.</li>'+
  '<li><b>Vos droits.</b> Pour toute question sur vos données : '+mail+'. Vous pouvez aussi saisir la <a href="https://www.cnil.fr/fr/plaintes" target="_blank" rel="noopener noreferrer">CNIL ↗</a>.</li></ul>'+
  '<h2>Contenus</h2><ul class="lim" style="max-width:68ch">'+
  '<li><b>Les titres</b> appartiennent à leurs journaux. Chaque titre renvoie à l’article.</li>'+
  '<li><b>Le classement</b> est celui de FrIdéo v1.0, du French News Lab, sous licence CC BY 4.0. <a href="#/classement">Voir le classement</a>.</li>'+
  '<li><b>Les textes signalés</b> <span class="mdl" style="margin:0">écrit par un modèle</span> sont rédigés par un modèle de langage.</li>'+
  '<li><b>Le code</b> est public, sous licence AGPL-3.0 : <a href="https://github.com/amiel-35/comparateur-medias" target="_blank" rel="noopener noreferrer">github.com/amiel-35/comparateur-medias ↗</a>.</li></ul>';
}
