// Vérifie le rendu de toutes les vues du site, dans un navigateur : aucune erreur de console, aucun défilement
// horizontal, aucun « undefined » à l'écran, à 375 px et 1280 px, thèmes clair et sombre, sur chaque édition.
// Écrit aussi l'empreinte de chaque capture : deux passages donnent les mêmes empreintes si le rendu n'a pas bougé.
//
//   COMPARATEUR_DONNEES=/tmp/essai python3 essais/editions_essai.py
//   COMPARATEUR_DONNEES=/tmp/essai PORT=8765 python3 -m comparateur servir &
//   node essais/rendu.js http://127.0.0.1:8765 [fichier des empreintes] [dossier des captures]
//
// Demande Playwright et Chromium (outil de développement, pas une dépendance du site).
const { chromium } = require('playwright');
const crypto = require('crypto'), fs = require('fs');
const [B, EMPREINTES, CAPTURES] = process.argv.slice(2);
if (!B) { console.error('usage : node essais/rendu.js <adresse du site> [empreintes] [captures]'); process.exit(2); }
(async () => {
  const jours = await (await fetch(B + '/data/editions.json')).json();
  const br = await chromium.launch();
  const lignes = []; let pb = 0, n = 0;
  for (const [nom, vp] of [['375', { width: 375, height: 800 }], ['1280', { width: 1280, height: 900 }]]) {
    for (const theme of ['light', 'dark']) {
      const ctx = await br.newContext({ viewport: vp, colorScheme: theme, deviceScaleFactor: 1 });
      const page = await ctx.newPage();
      const errs = [];
      page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
      page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
      for (const j of jours) {
        const d = await (await fetch(`${B}/data/editions/${j}.json`)).json();
        const vues = ['#/', '#/pourquoi', '#/silences', '#/sujet/seuls', '#/semaine', '#/mois', '#/demarche', '#/origine', '#/mentions', '#/installer', '#/classement', '#/medias',
          '#/media/' + encodeURIComponent(d.medias[0].nom), '#/editions'].concat(d.sujets.map(s => '#/sujet/' + s.id));
        for (const v of vues) {
          await page.goto('about:blank'); await page.waitForTimeout(250);   // le guichet limite à 300 requêtes par minute
          await page.goto(`${B}/editions/${j}.html${v}`);
          const r = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
            texte: document.getElementById('app').innerText }));
          n++;
          const soucis = [];
          if (r.sw > r.cw) soucis.push(`défilement horizontal (${r.sw} > ${r.cw})`);
          if (/undefined|NaN/.test(r.texte)) soucis.push('« undefined » ou « NaN » à l’écran');
          if (r.texte.trim().length < 40) soucis.push('page vide');
          soucis.push(...errs.splice(0));
          if (soucis.length) { pb++; console.log('PROBLÈME', nom, theme, j, v, soucis); }
          const img = await page.screenshot({ fullPage: true });
          lignes.push(`${nom} ${theme} ${j} ${v} ${crypto.createHash('sha256').update(img).digest('hex').slice(0, 16)}`);
          if (CAPTURES) fs.writeFileSync(`${CAPTURES}/${j}${v.replace(/[#\/%]+/g, '_')}-${nom}-${theme}.png`, img);
        }
      }
      await ctx.close();
    }
  }
  await br.close();
  if (EMPREINTES) fs.writeFileSync(EMPREINTES, lignes.join('\n') + '\n');
  console.log(`${n} pages vues, ${pb} en défaut`);
  process.exit(pb ? 1 : 0);
})();
