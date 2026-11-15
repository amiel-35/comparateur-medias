/* Le service worker de Cadrages : réseau d'abord, toujours.
   Quand le réseau répond, c'est sa réponse qui est servie, quelle qu'elle soit : jamais une édition périmée.
   La copie gardée ne sert que si le réseau ne répond pas du tout (appareil hors ligne).
   Seules les pages et fichiers du site, en GET, sont gardés. L'API (/api/) n'est jamais gardée. */
var CACHE = 'cadrages-v1';

self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (cles) {
    return Promise.all(cles.filter(function (c) { return c !== CACHE; }).map(function (c) { return caches.delete(c); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  var r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== self.location.origin || u.pathname.indexOf('/api/') === 0 || u.pathname === '/sante') return;
  e.respondWith(fetch(r).then(function (rep) {
    if (rep.ok && rep.type === 'basic') {
      var copie = rep.clone();
      caches.open(CACHE).then(function (c) { return c.put(r, copie); }).catch(function () {});
    }
    return rep;
  }, function (panne) {
    return caches.match(r, { ignoreSearch: true }).then(function (vieux) {
      if (vieux) return vieux;
      if (r.mode === 'navigate') return caches.match('/');
      throw panne;
    }).then(function (x) { if (x) return x; throw panne; });
  }));
});
