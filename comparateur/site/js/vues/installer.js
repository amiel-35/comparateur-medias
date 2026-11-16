/* Installer Cadrages comme une application. Chemins de menu relevés le 15/11/2026 dans l'aide d'Apple, de Google,
   de Microsoft et de Mozilla. L'appareil est deviné d'après le navigateur (user agent), sans rien envoyer : sa
   section passe en tête. INVITE (routage) : l'invitation à installer de Chrome et Edge, quand elle existe. */
function appareil(){
  var u=navigator.userAgent||'';
  if(/iPhone|iPad|iPod/.test(u)||(/Macintosh/.test(u)&&navigator.maxTouchPoints>1))return 'ios';
  if(/Android/.test(u))return /Firefox/.test(u)?'firefox':'android';
  if(/Firefox/.test(u))return 'firefox';
  if(/Macintosh|Mac OS X/.test(u))return 'mac';
  return 'ordi';
}
function installe(){
  try{if(window.matchMedia('(display-mode: standalone)').matches||window.matchMedia('(display-mode: window-controls-overlay)').matches)return true;}catch(_){}
  return navigator.standalone===true;
}
function pas(l){return '<ol class="pas">'+l.map(function(x){return '<li>'+x+'</li>';}).join('')+'</ol>';}
function vInstaller(){
  var ici=appareil();
  var S_={
    ios:['iPhone et iPad','<h3>Safari</h3>'+pas([
      'Touchez le bouton <b>Partager</b>. Selon la disposition des onglets, il est dans la barre, ou derrière le bouton <b>…</b> (puis <b>Partager</b>).',
      'Faites défiler les options, puis touchez <b>Sur l’écran d’accueil</b>. Si elle manque : <b>Modifier les actions</b>, pour l’ajouter.',
      'Activez <b>Ouvrir comme app web</b> si l’option s’affiche.',
      'Touchez <b>Ajouter</b>.'])+
      '<h3>Chrome</h3>'+pas(['Touchez <b>Partager</b>, à droite de la barre d’adresse.','Touchez <b>Ajouter à l’écran d’accueil</b>, puis <b>Ajouter</b>.'])+
      '<p class="note">Depuis iOS 16.4, les autres navigateurs (Edge, Firefox) peuvent aussi proposer l’ajout à l’écran d’accueil, dans leur menu de partage. Le libellé dépend du navigateur.</p>'],
    mac:['Mac','<h3>Safari (macOS Sonoma 14 ou plus récent)</h3>'+pas([
      'Dans la barre des menus, choisissez <b>Fichier</b>, puis <b>Ajouter au Dock</b>. Ou cliquez sur le bouton <b>Partager</b> de la barre d’outils, puis <b>Ajouter au Dock</b>.',
      'Gardez le nom « Cadrages » ou changez-le, puis cliquez sur <b>Ajouter</b>.'])+
      '<h3>Chrome</h3>'+pas(['Cliquez sur <b>Installer</b>, à droite de la barre d’adresse.','Sinon : menu <b>⋮</b> (Plus), <b>Caster, enregistrer et partager</b>, puis <b>Installer la page en tant qu’appli</b>.'])+
      '<h3>Edge</h3>'+pas(['Cliquez sur l’icône <b>Application disponible</b> dans la barre d’adresse, puis sur <b>Installer</b>.','Sinon : menu <b>…</b> (Paramètres et plus), <b>Autres outils</b>, <b>Applications</b>, puis <b>Installer ce site en tant qu’application</b>.'])],
    android:['Android','<h3>Chrome</h3>'+pas(['Touchez <b>⋮</b> (Plus), à droite de la barre d’adresse.','Touchez <b>Installer et créer un raccourci</b>, puis <b>Installer</b>.'])+
      '<p class="note">Avec Firefox, voir plus bas.</p>'],
    ordi:['Windows et Linux','<h3>Edge</h3>'+pas(['Cliquez sur l’icône <b>Application disponible</b> dans la barre d’adresse, puis sur <b>Installer</b>.','Sinon : menu <b>…</b> (Paramètres et plus), <b>Autres outils</b>, <b>Applications</b>, puis <b>Installer ce site en tant qu’application</b>.'])+
      '<h3>Chrome</h3>'+pas(['Cliquez sur <b>Installer</b>, à droite de la barre d’adresse.','Sinon : menu <b>⋮</b> (Plus), <b>Caster, enregistrer et partager</b>, puis <b>Installer la page en tant qu’appli</b>.'])],
    firefox:['Firefox','<p>Firefox ne fait pas partout la même chose. Les libellés exacts n’ont pas pu être vérifiés dans l’aide de Mozilla : cherchez le mot « installer » ou « écran d’accueil ».</p>'+
      '<h3>Windows</h3><p>Depuis Firefox 143, un bouton dans la barre d’adresse ajoute le site à la barre des tâches. L’aide de Mozilla s’appelle « Utilisez les applications web dans Firefox pour Windows ».</p>'+
      '<h3>Android</h3><p>Dans le menu <b>⋮</b>, cherchez <b>Installer</b> ou <b>Ajouter à l’écran d’accueil</b>, puis confirmez.</p>'+
      '<h3>Mac et Linux</h3><p>Sur Mac, Firefox n’installe pas les sites comme des applications. Sur Linux, la fonction est éteinte par défaut. Safari, Chrome ou Edge le font, voir plus haut.</p>']
  };
  var ordre=[ici].concat(['ios','mac','android','ordi','firefox'].filter(function(k){return k!==ici;}));
  var h='<h1 tabindex="-1" id="h1">Cadrages s’installe comme une application, sans passer par un magasin</h1>';
  h+='<div class="prose"><p>Une fois installé, Cadrages s’ouvre depuis l’écran d’accueil, le Dock ou la barre des tâches, dans sa propre fenêtre. Rien à télécharger, aucun compte. Hors connexion, les dernières pages lues restent lisibles.</p></div>';
  if(installe())h+='<p class="inst-ok">Cadrages tourne déjà en application sur cet appareil. Rien d’autre à faire.</p>';
  else if(INVITE)h+='<p class="inst-ok"><button class="btn hl" id="btnInstaller" type="button">Installer</button> Ce navigateur sait installer Cadrages en un clic.</p>';
  h+='<p class="note">La section de cet appareil passe en premier. Elle est devinée d’après le navigateur, sans rien envoyer nulle part.</p>';
  ordre.forEach(function(k,i){h+='<section class="inst'+(i===0?' ici':'')+'"><h2>'+S_[k][0]+(i===0?' <span class="mono mute">cet appareil</span>':'')+'</h2>'+S_[k][1]+'</section>';});
  h+='<p class="note">Pour retirer l’application : comme toute autre application de l’appareil. Chemins relevés dans l’aide d’Apple, de Google, de Microsoft et de Mozilla en novembre 2026. Les menus changent d’une version à l’autre.</p>';
  return h;
}
