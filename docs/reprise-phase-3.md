# Reprise de la phase 3 (note du 17/11/2026)

État au moment de l'arrêt. À lire avant de continuer, puis à supprimer.

## Ce qui est fait, sur `phase-3`

- `signature.py` et `compte/aveugle-rsa.js` : RFC 9474 (RSABSSA-SHA384-PSS-Randomized), vecteurs de l'annexe A.1
  passés des deux côtés (`tests/vecteurs-rfc9474.json`), bulletin d'un langage à l'autre.
- `urne.py` (une urne par questionnaire, sans date ni rang, effacement par le reçu, résultats après clôture,
  carte de votant par trimestre), côté guichet dans `comptes.py` (invitations au panel, adhésion, retrait,
  destruction de la clé), `ceremonie.py` (ouvrir, fermer, cartes, échéances), routes de `urne.` et du panel.
- `tests/test_panel.py` : parcours entier, refus (409, 403, 400 sur cookie), clôture, séparation des modules.
- Compose (volume des urnes), `docs/deploiement-phase-3.md`. Les corrections de la relecture de la phase 2 sont
  fusionnées. Tous les tests passent.

## Ce qui reste

1. **La page du panel** : branche `p3-panel-en-cours` (tests verts, non relue). `compte/panel.html`, lien depuis
   `compte.html`, écrans ajoutés à `essais/accessibilite.js`, test de la page. À relire, à essayer dans un
   navigateur (parcours complet à 375 et 1280 px, aucune requête vers `urne.` avec cookie), puis à fusionner.
2. **Le vote à l'aveugle migré** : branche `p3-aveugle-en-cours`, **inachevée** (7 échecs, 2 erreurs). Le cahier
   des charges : migration `verser-votes` / `oublier-votes` (avis vers `urnes/aveugle-historique.db`, accords
   agrégés), retrait des routes `/api/inscription`, `/api/lot`, `/api/avis-aveugle`, `/api/avis-note`,
   `/api/resultats`, nouvelle `aveugle.html` qui renvoie vers `compte./panel`, commande `panel-inviter`, lots
   publiés dans `public/aveugle/lots.json`, `aveugle.resultats` calculé sur les agrégats publiés par l'urne
   (`compter_agreges`), affichage « Perçu à l'aveugle par le panel » à côté du classement FrIdéo (Classement,
   fiche d'un média), vue `#/panel` des résultats de questionnaires, Mentions et README.
3. **La commande `questionnaire ouvrir|fermer|resultats <…>`** dans `__main__.py` (citée par
   `docs/deploiement-phase-3.md`, pas encore écrite ; `ceremonie.ouvrir`, `fermer`, `republier` existent).
4. **La relecture adverse Fable** du diff `phase-2..phase-3`, en un appel seul, puis ses corrections.
5. **La PR en brouillon** `phase-3` vers `phase-2`, sur le modèle des PR #6, #7, #8 (ce qui est fait, relecture,
   reste à Amiel, essais avant déploiement, conflits avec `claude/stoic-noether-6kt47x`).
