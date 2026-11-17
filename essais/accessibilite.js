// Mesure d'accessibilité, écrite à la main, sans bibliothèque d'audit : chaque vue de chaque édition, à 375 px et
// 1280 px, en clair et en sombre. Elle contrôle ce qu'un lecteur d'écran, un clavier ou une vue faible rencontrent :
//
//   titres     un seul h1 par vue, aucun niveau sauté (h1 puis h3 sans h2)
//   contrastes chaque texte contre son fond réel, calculé comme le WCAG 2.2 (4,5:1 ; 3:1 pour un grand texte)
//   libellés   chaque lien, bouton, champ, image et figure (role="img") a un nom lisible par un lecteur d'écran
//   focus      chaque élément atteint au clavier montre un contour visible quand il a le focus
//   langue     la page déclare le français ; le titre de l'onglet suit la vue
//
// Les pages à part (aveugle.html, mail.html) sont contrôlées aussi. Le script échoue au premier défaut et les liste.
//
//   COMPARATEUR_DONNEES=/tmp/essai python3 essais/editions_essai.py
//   COMPARATEUR_DONNEES=/tmp/essai PORT=8765 python3 -m comparateur servir &
//   node essais/accessibilite.js http://127.0.0.1:8765        (avec COMPARATEUR_DERRIERE_PROXY=1 sur le serveur ;
//                                                           sans lui : PAUSE=250 node essais/accessibilite.js …)
//
// Demande Playwright et Chromium, comme essais/rendu.js (outil de développement, pas une dépendance du site).
const { chromium } = require('playwright');
const B = process.argv[2];
if (!B) { console.error('usage : node essais/accessibilite.js <adresse du site>'); process.exit(2); }

// Exécuté dans la page. Rend la liste des défauts de la vue affichée.
function controler() {
  const defauts = [];
  const dire = (quoi, el) => defauts.push(quoi + ' : ' + (el ? (el.outerHTML || '').replace(/\s+/g, ' ').slice(0, 140) : ''));
  const visible = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !el.closest('[aria-hidden="true"]')
      && !(el.closest('details:not([open])') && !el.closest('summary')); };
  const nom = el => (el.getAttribute('aria-label') || (el.getAttribute('aria-labelledby') || '').split(' ').map(i => (document.getElementById(i) || {}).textContent || '').join(' ')
    || el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('alt') || '').trim();

  // la langue et le titre
  if (document.documentElement.lang !== 'fr') dire('langue absente ou autre que fr', document.documentElement);
  if (!document.title.trim()) dire('titre de page vide', null);

  // les titres
  const titres = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(visible);
  const h1 = titres.filter(t => t.tagName === 'H1');
  if (h1.length !== 1) dire(h1.length + ' titres h1 au lieu d’un', h1[1] || null);
  let avant = 0;
  for (const t of titres) {
    const n = +t.tagName[1];
    if (avant && n > avant + 1) dire(`niveau de titre sauté (h${avant} puis h${n})`, t);
    if (!t.innerText.trim()) dire('titre vide', t);
    avant = n;
  }

  // les noms
  for (const el of document.querySelectorAll('a[href],button,[role="button"],[role="img"],img,svg[role]')) {
    if (!visible(el)) continue;
    if (!nom(el)) dire('élément sans nom accessible', el);
  }
  for (const el of document.querySelectorAll('input,select,textarea')) {
    if (el.type === 'hidden' || el.closest('[aria-hidden="true"]')) continue;
    const etiquette = (el.id && document.querySelector(`label[for="${el.id}"]`)) || el.closest('label') || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
    if (!etiquette) dire('champ sans étiquette', el);
  }
  for (const g of document.querySelectorAll('[role="group"],[role="radiogroup"],fieldset')) {
    if (!nom(g) && !(g.tagName === 'FIELDSET' && g.querySelector('legend'))) dire('groupe sans nom', g);
  }

  // les contrastes : couleur du texte contre le premier fond opaque en remontant (mélangé s'il est translucide)
  const rgb = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const melange = (haut, bas) => [0, 1, 2].map(i => haut[i] * haut[3] + bas[i] * (1 - haut[3])).concat(1);
  function fond(el) {
    const couches = [];
    for (let e = el; e; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.backgroundImage !== 'none' && !/gradient/.test(s.backgroundImage)) return null;   // image : on ne sait pas
      const c = rgb(s.backgroundColor);
      if (c && c[3] > 0) { couches.push(c); if (c[3] >= 1) break; }
    }
    let f = [255, 255, 255, 1];
    for (const c of couches.reverse()) f = melange(c, f);
    return f;
  }
  const vus = new Set();
  const marcheur = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = marcheur.nextNode(); n; n = marcheur.nextNode()) {
    const el = n.parentElement;
    if (!n.textContent.trim() || !el || vus.has(el) || !visible(el) || el.closest('script,style,.sr')) continue;
    vus.add(el);
    const s = getComputedStyle(el);
    let c = rgb(s.color), f = fond(el);
    if (!c || !f) continue;
    // une opacité réduite (bouton désactivé) éclaircit le texte
    for (let e = el; e; e = e.parentElement) { const x = parseFloat(getComputedStyle(e).opacity); if (x < 1) c = melange([c[0], c[1], c[2], x], f); }
    c = melange(c, f);
    const [a, b] = [lum(c), lum(f)].sort((x, y) => y - x), ratio = (a + 0.05) / (b + 0.05);
    const taille = parseFloat(s.fontSize), gras = +s.fontWeight >= 700;
    const seuil = taille >= 24 || (gras && taille >= 18.66) ? 3 : 4.5;
    if (ratio < seuil && !el.closest('[aria-disabled="true"],button:disabled')) dire(`contraste ${ratio.toFixed(2)}:1 sous ${seuil}:1 (« ${n.textContent.trim().slice(0, 30)} »)`, el);
  }
  return defauts;
}

// Le focus : chaque élément atteint par la touche Tab doit montrer un contour (outline) ou un changement de bordure.
async function focus(page) {
  const defauts = [];
  await page.evaluate(() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); });
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press('Tab');
    const r = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const s = getComputedStyle(el);
      const contour = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2;
      return { contour, html: el.outerHTML.replace(/\s+/g, ' ').slice(0, 120) };
    });
    if (!r) break;
    if (!r.contour) defauts.push('focus sans contour visible : ' + r.html);
  }
  return defauts;
}

(async () => {
  const jours = await (await fetch(B + '/data/editions.json')).json();
  const br = await chromium.launch();
  let n = 0; const tous = new Map();
  for (const [nomVp, vp] of [['375', { width: 375, height: 800 }], ['1280', { width: 1280, height: 900 }]]) {
    for (const theme of ['light', 'dark']) {
      const ctx = await br.newContext({ viewport: vp, colorScheme: theme, deviceScaleFactor: 1 });
      const page = await ctx.newPage();
      const pages = [];
      for (const j of jours) {
        const d = await (await fetch(`${B}/data/editions/${j}.json`)).json();
        const vues = ['#/', '#/pourquoi', '#/silences', '#/sujet/seuls', '#/semaine', '#/mois', '#/demarche', '#/origine', '#/mentions', '#/installer',
          '#/classement', '#/medias', '#/situer', '#/media/' + encodeURIComponent(d.medias[0].nom), '#/editions'].concat(d.sujets.map(s => '#/sujet/' + s.id));
        for (const v of vues) pages.push(`/editions/${j}.html${v}`);
      }
      pages.push('/aveugle.html', '/mail.html#confirmer=essai-essai-essai', '/mail.html#desinscrire=essai-essai-essai', '/mail.html');
      for (const p of pages) {
        // Le guichet limite à 300 requêtes par minute et par adresse. Avec COMPARATEUR_DERRIERE_PROXY=1 sur le serveur
        // d'essai, chaque page porte une adresse différente ; sans lui, une pause suffit, en plus long.
        await page.setExtraHTTPHeaders({ 'X-Forwarded-For': `10.9.${n % 250}.${(n / 250 | 0) % 250}` });
        await page.goto('about:blank'); await page.waitForTimeout(process.env.PAUSE ? +process.env.PAUSE : 30);
        await page.goto(B + p);
        await page.waitForTimeout(50);
        // Les messages d'erreur des pages à part n'apparaissent qu'après un geste : on en écrit un, pour en voir le contraste.
        await page.evaluate(() => { const m = document.getElementById('message'); if (m && !m.textContent.trim()) { m.textContent = 'Message d’erreur d’essai'; m.className = 'ko'; } });
        const defauts = (await page.evaluate(controler)).concat(theme === 'light' ? await focus(page) : []);
        n++;
        for (const x of defauts) {   // un même défaut, sur plusieurs pages, n'est listé qu'une fois
          const cle = x.replace(/\d+(\.\d+)?:1/, 'n:1');
          if (!tous.has(cle)) tous.set(cle, { x, ou: [] });
          tous.get(cle).ou.push(`${nomVp} ${theme} ${p}`);
        }
      }
      await ctx.close();
    }
  }
  await br.close();
  for (const { x, ou } of tous.values()) console.log('DÉFAUT', x, '\n   ', ou.length, 'fois, dont', ou.slice(0, 3).join(' ; '));
  console.log(`${n} pages contrôlées, ${tous.size} défauts distincts`);
  process.exit(tous.size ? 1 : 0);
})();
