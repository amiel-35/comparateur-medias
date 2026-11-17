// Mesure d'accessibilité, écrite à la main, sans bibliothèque d'audit : chaque vue de chaque édition, à 375 px et
// 1280 px, en clair et en sombre. Elle contrôle ce qu'un lecteur d'écran, un clavier ou une vue faible rencontrent :
//
//   titres     un seul h1 par vue, aucun niveau sauté (h1 puis h3 sans h2)
//   contrastes chaque texte contre son fond réel, calculé comme le WCAG 2.2 (4,5:1 ; 3:1 pour un grand texte) ;
//              la bordure des champs de saisie contre son fond (3:1)
//   libellés   chaque lien, bouton, champ, image et figure (role="img") a un nom lisible par un lecteur d'écran
//   focus      tout ce qu'atteint la touche Tab, jusqu'au bout de la page, montre un contour d'au moins 2 px dont
//              la couleur fait 3:1 avec le fond qui l'entoure ; dans les deux thèmes
//   langue     la page déclare le français ; le titre de l'onglet reprend le h1 de la vue
//
// Les pages à part (aveugle.html, mail.html) sont contrôlées aussi, avec leurs états qui n'apparaissent qu'après un
// geste : un lot à juger et la fin des lots (réponses du serveur simulées), le message d'erreur, le résultat d'un
// clic sur mail.html. Le script liste tous les défauts, puis échoue s'il y en a.
//
//   COMPARATEUR_DONNEES=/tmp/essai python3 essais/editions_essai.py
//   COMPARATEUR_DONNEES=/tmp/essai COMPARATEUR_SMTP_UTILISATEUR=essai COMPARATEUR_SMTP_MOT_DE_PASSE=essai \
//     python3 -m comparateur pages        (les réglages SMTP factices font paraître l'encart du mail ; rien ne part)
//   COMPARATEUR_DONNEES=/tmp/essai PORT=8765 python3 -m comparateur servir &
//   node essais/accessibilite.js http://127.0.0.1:8765
//
// Limites : ni le survol, ni les contenus ::before, ni les couleurs qu'un navigateur rendrait dans un format que
// le script ne lit pas (signalées comme défaut, pas sautées).
//
// Demande Playwright et Chromium, comme essais/rendu.js (outil de développement, pas une dépendance du site).
const { chromium } = require('playwright');
const B = process.argv[2];
// La page du compte vit sur son propre hôte (compte.<domaine>). En local : COMPTE=http://compte.localhost:8765, avec un
// serveur lancé avec COMPARATEUR_SITE_URL=http://localhost:8765 et des réglages SMTP factices. Ses trois écrans, et les
// dix de la page du panel, sont contrôlés, réponses du serveur simulées.
const COMPTE = process.env.COMPTE || '';
const SAIT = { sait: { compte: { adresse: 'essai@exemple.fr', cree_jour: '2026-11-17', vu_mois: '2026-11' },
  abonnements: [{ type: 'lettre', cible: '', etat: 'actif', cree_jour: '2026-11-17', fin_jour: null, dernier_envoi: null },
    { type: 'rubrique', cible: 'international', etat: 'actif', cree_jour: '2026-11-17', fin_jour: null, dernier_envoi: null }],
  sessions: [{ cree_jour: '2026-11-17', fin_jour: '2027-11-17' }] } };
// La page du panel (COMPTE/panel) : ses dix écrans, réponses du guichet et de l'urne simulées. Un membre, deux
// questionnaires (l'un commencé sur un autre appareil), un bulletin, un reçu et une carte déjà sur l'appareil, deux lots.
const URNE = COMPTE.replace('//compte.', '//urne.');
const CLE = { n: 'c0ffee', e: '010001' };
const PANEL = { membre: true, membre_depuis: '2026-10-01', urne: URNE, etiquette: 'Panel de volontaires. Ce n’est pas un sondage.',
  carte: { id: 'carte-2026t4', trimestre: '2026T4', cle: CLE, retiree: false },
  questionnaires: [
    { id: 'essai-confiance', titre: 'Trois questions sur la confiance dans les médias', intro: 'Deux minutes.', fermeture: '2026-11-30', cle: CLE, retire: false,
      questions: [{ id: 'q1', texte: 'Faites-vous confiance aux journaux télévisés ?', choix: ['Oui', 'Non', 'Je ne sais pas'] },
        { id: 'age', texte: 'Votre tranche d’âge ?', choix: ['Moins de 30 ans', '30 à 59 ans', '60 ans et plus'], profil: true }] },
    { id: 'essai-ailleurs', titre: 'Un questionnaire commencé ailleurs', intro: '', fermeture: '2026-12-15', cle: CLE, retire: true,
      questions: [{ id: 'q1', texte: 'Une question ?', choix: ['Oui', 'Non'] }] }] };
const APPAREIL = { 'cadrages.bord': '0',
  'cadrages.bulletins': JSON.stringify({ 'essai-confiance': { bulletin: 'ab', signature: 'cd', titre: 'Trois questions', fermeture: '2026-11-30' } }),
  'cadrages.recus': JSON.stringify([{ questionnaire: 'essai-ancien', titre: 'Un questionnaire déjà rendu', fermeture: '2026-11-01', bulletin: 'ef' }]),
  'cadrages.carte': JSON.stringify({ id: 'carte-2026t4', trimestre: '2026T4', carte: 'ab', signature: 'cd' }) };
const LOTS = { lots: [1, 2].map(id => ({ id, titres: Array.from({ length: 10 }, (_, i) => `Un titre d’essai numéro ${i + 1}, assez long pour une ligne`) })) };
const ECRANS_PANEL = ['hors', 'accueil', 'membre', 'quitter', 'bord', 'question', 'envoi', 'envoye', 'lot', 'lots-fini'];
// Les gestes qui mènent à chaque écran du panel, depuis l'écran du membre.
async function gestesPanel(page, e) {
  await page.waitForSelector('section:not([hidden]) h1');
  if (e === 'quitter') await page.click('#vers-quitter');
  if (['bord', 'question', 'envoi', 'envoye'].includes(e)) await page.click('#questionnaires button');   // « Reprendre » : le bulletin est sur l'appareil
  if (['question', 'envoi', 'envoye'].includes(e)) await page.click('#bord-suivant');
  if (e === 'envoi' || e === 'envoye') for (const i of [0, 1]) { await page.check('#q-choix input[value="0"]'); await page.click('#q-suivant'); }
  if (e === 'envoye') await page.click('#envoyer');
  if (e === 'lot' || e === 'lots-fini') { await page.click('#voter'); await page.click('#bord-suivant'); }
  await page.waitForFunction(id => !document.getElementById(id).hidden, e);
}
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
  const h1v = [...document.querySelectorAll('h1')].find(visible);
  if (h1v && location.pathname.indexOf('/editions/') === 0) {   // le routage met le h1 en tête du titre de l'onglet
    const attendu = h1v.textContent.replace(/écrit par un modèle/, '').trim();
    if (!document.title.startsWith(attendu)) dire(`titre de l’onglet (« ${document.title} ») sans le h1`, null);
  }

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
  const rgb = c => {
    let m = c.match(/^rgba?\(([^)]+)\)$/);
    if (m) { const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = c.match(/^color\(srgb ([^)]+)\)$/);
    if (m) { const p = m[1].split(/[ /]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; }
    illisibles.add(c); return null;
  };
  const illisibles = new Set();
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
  // la bordure des champs de saisie : 3:1 contre le fond (WCAG 1.4.11)
  for (const el of document.querySelectorAll('input:not([type=hidden]),select,textarea')) {
    if (!visible(el)) continue;
    const s = getComputedStyle(el), b = rgb(s.borderTopColor), f = fond(el.parentElement);
    if (!b || !f || parseFloat(s.borderTopWidth) === 0) continue;
    const [x, y] = [lum(melange(b, f)), lum(f)].sort((p, q) => q - p), r = (x + 0.05) / (y + 0.05);
    if (r < 3) dire(`bordure de champ à ${r.toFixed(2)}:1 sous 3:1`, el);
  }
  for (const c of illisibles) dire('couleur que la mesure ne sait pas lire : ' + c, null);
  window.__fond = fond; window.__rgb = rgb; window.__lum = lum; window.__melange = melange;
  return defauts;
}

// Le focus : chaque élément atteint par la touche Tab, jusqu'à ce que le focus revienne au début, doit montrer un
// contour (outline) d'au moins 2 px, d'une couleur qui fait 3:1 avec le fond autour de l'élément.
async function focus(page) {
  const defauts = [], vus = new Set();
  await page.evaluate(() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); });
  for (let i = 0; i < 600; i++) {
    await page.keyboard.press('Tab');
    const r = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const s = getComputedStyle(el), html = el.outerHTML.replace(/\s+/g, ' ').slice(0, 120);
      if (s.outlineStyle === 'none' || parseFloat(s.outlineWidth) < 2) return { html, ratio: 0 };
      const c = window.__rgb(s.outlineColor), f = window.__fond(el.parentElement || el);
      if (!c || !f) return { html, ratio: null };
      const [a, b] = [window.__lum(window.__melange(c, f)), window.__lum(f)].sort((x, y) => y - x);
      return { html, ratio: (a + 0.05) / (b + 0.05) };
    });
    if (!r || vus.has(r.html)) break;   // revenu au début : la page est parcourue
    vus.add(r.html);
    if (r.ratio === 0) defauts.push('focus sans contour visible : ' + r.html);
    else if (r.ratio === null) defauts.push('focus : couleur du contour illisible : ' + r.html);
    else if (r.ratio < 3) defauts.push(`focus à ${r.ratio.toFixed(2)}:1 sous 3:1 : ${r.html}`);
  }
  return defauts;
}

// Les états des pages à part qui n'apparaissent qu'après un geste. Les réponses du serveur sont simulées.
async function etats(page, chemin) {
  if (chemin === '/aveugle.html#lot') {
    await page.route('**/api/lot', r => r.fulfill({ json: { lot: { id: 1, titres: Array.from({ length: 10 }, (_, i) => `Un titre d’essai numéro ${i + 1}, assez long pour une ligne`) }, restants: 3 } }));
    await page.addInitScript(() => { try { localStorage.setItem('comparateur.jeton', 'essai'); } catch (e) {} });
  } else if (chemin === '/aveugle.html#fini') {
    await page.route('**/api/lot', r => r.fulfill({ json: { lot: null, restants: 0 } }));
    await page.addInitScript(() => { try { localStorage.setItem('comparateur.jeton', 'essai'); } catch (e) {} });
  } else if (chemin.startsWith('COMPTE')) {
    // le registre, demandé au vrai serveur sous le nom d'hôte du compte (fetch de Node ne laisse pas changer Host)
    const reg = await new Promise((ok, ko) => require('http').get({ host: new URL(B).hostname, port: new URL(B).port, path: '/api/compte/registre',
      headers: { Host: new URL(COMPTE).host } }, r => { let t = ''; r.on('data', x => t += x); r.on('end', () => ok(JSON.parse(t))); }).on('error', ko));
    await page.route('**/api/compte', r => chemin === 'COMPTE#compte' ? r.fulfill({ json: Object.assign({}, SAIT, reg) }) : r.fulfill({ status: 401, json: {} }));
    await page.route('**/api/compte/code', r => r.fulfill({ status: 202, json: { ok: true } }));
  } else if (chemin.startsWith('PANEL#')) {
    const e = chemin.slice(6), cors = { 'Access-Control-Allow-Origin': new URL(COMPTE).origin };
    await page.route('**/api/compte/panel', r => e === 'hors' ? r.fulfill({ status: 401, json: {} })
      : r.fulfill({ json: e === 'accueil' ? Object.assign({}, PANEL, { membre: false, membre_depuis: null, questionnaires: [], carte: null }) : PANEL }));
    await page.route('**/api/compte/lots', r => r.fulfill({ json: LOTS }));
    await page.route(URNE + '/api/urne/**', r => r.request().method() === 'OPTIONS'
      ? r.fulfill({ status: 204, headers: Object.assign({ 'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type' }, cors) })
      : r.fulfill({ status: r.request().url().endsWith('/depot') ? 201 : 200, headers: cors, json: { ok: true, lots: e === 'lots-fini' ? [1, 2] : [] } }));
    if (e !== 'hors' && e !== 'accueil') await page.addInitScript(a => { try { for (const k in a) localStorage.setItem(k, a[k]); } catch (x) {} }, APPAREIL);
  } else if (chemin.startsWith('/mail.html#confirmer') || chemin.startsWith('/mail.html#desinscrire')) {
    await page.route('**/api/mail/**', r => r.fulfill({ status: chemin.endsWith('404') ? 404 : 200, json: {} }));
  }
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
      pages.push('/aveugle.html', '/aveugle.html#lot', '/aveugle.html#fini', '/mail.html#confirmer=essai-essai-essai',
        '/mail.html#desinscrire=essai-essai-essai', '/mail.html#desinscrire=essai-essai-clic', '/mail.html#confirmer=essai-essai-404', '/mail.html');
      if (COMPTE) pages.push('COMPTE#adresse', 'COMPTE#code', 'COMPTE#compte', ...ECRANS_PANEL.map(e => 'PANEL#' + e));
      // « Mes sujets » n'apparaît à l'accueil que si l'appareil en suit : une visite avec deux sujets suivis
      pages.push('/editions/' + jours[jours.length - 1] + '.html#/?mes');
      for (const p of pages) {
        await page.unrouteAll();
        await etats(page, p);
        await page.goto('about:blank'); await page.waitForTimeout(30);
        if (p.endsWith('#/?mes')) await page.addInitScript(() => { try { localStorage.setItem('cadrages.sujets', JSON.stringify([{ id: 's45', titre: 'Un sujet suivi' }, { id: 'zz9', titre: 'Un sujet absent' }])); } catch (e) {} });
        await page.goto(p.startsWith('COMPTE') ? COMPTE + '/' : p.startsWith('PANEL') ? COMPTE + '/panel' : B + p.replace(/#(lot|fini)$/, '').replace(/\?mes$/, ''));
        if (p === 'COMPTE#code') { await page.waitForTimeout(80); await page.fill('#adr', 'essai@exemple.fr'); await page.click('#f-adresse button'); }
        if (p.startsWith('PANEL#')) await gestesPanel(page, p.slice(6));
        await page.waitForTimeout(80);
        if (p.startsWith('/mail.html#') && !p.endsWith('essai')) {   // le résultat d'un clic sur le bouton
          await page.click('section:not([hidden]) button').catch(() => {});
          await page.waitForTimeout(80);
        }
        // Les messages d'erreur des pages à part n'apparaissent qu'après un geste : on en écrit un, pour en voir le contraste.
        await page.evaluate(() => { const m = document.getElementById('message'); if (m && !m.textContent.trim()) { m.textContent = 'Message d’erreur d’essai'; m.className = 'ko'; } });
        const defauts = (await page.evaluate(controler)).concat(await focus(page));
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
