/* Signature aveugle RSA côté appareil : RFC 9474, variante RSABSSA-SHA384-PSS-Randomized. Sans dépendance.
   L'aveuglement se fait en BigInt (crypto.subtle n'offre aucune opération RSA brute) ; la vérification finale passe
   par crypto.subtle.verify (RSA-PSS, SHA-384, sel de 48 octets). BigInt n'est pas à temps constant : sans gravité
   ici, l'appareil ne manipule aucun secret durable, seulement un aléa jetable.
   La même règle est écrite en Python dans comparateur/signature.py ; les deux passent les vecteurs de l'annexe A.1. */
var AveugleRSA = (function () {
  'use strict';
  var LH = 48, LSEL = 48, LPREFIXE = 32;
  var sub = (typeof crypto !== 'undefined' && crypto.subtle) ? crypto : (typeof require === 'function' ? require('crypto').webcrypto : null);

  function hex(b) { return Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join(''); }
  function deHex(h) { var o = new Uint8Array(h.length / 2); for (var i = 0; i < o.length; i++) o[i] = parseInt(h.substr(2 * i, 2), 16); return o; }
  function concat() { var n = 0, i, a; for (i = 0; i < arguments.length; i++) n += arguments[i].length; var o = new Uint8Array(n), p = 0; for (i = 0; i < arguments.length; i++) { a = arguments[i]; o.set(a, p); p += a.length; } return o; }
  function enEntier(b) { return b.length ? BigInt('0x' + hex(b)) : 0n; }
  function enOctets(x, n) { var h = x.toString(16); if (h.length > 2 * n) throw new Error('entier trop grand'); while (h.length < 2 * n) h = '0' + h; return deHex(h); }
  function bits(n) { return n.toString(2).length; }
  function lmod(n) { return Math.ceil(bits(n) / 8); }
  function modpow(b, e, m) { var r = 1n; b %= m; while (e > 0n) { if (e & 1n) r = r * b % m; e >>= 1n; b = b * b % m; } return r; }
  function modinv(a, m) {
    var r0 = m, r1 = ((a % m) + m) % m, t0 = 0n, t1 = 1n, q, x;
    while (r1 !== 0n) { q = r0 / r1; x = r0 - q * r1; r0 = r1; r1 = x; x = t0 - q * t1; t0 = t1; t1 = x; }
    if (r0 !== 1n) return null;
    return ((t0 % m) + m) % m;
  }
  function pgcd(a, b) { while (b) { var t = a % b; a = b; b = t; } return a; }
  function hasard(n) { var b = new Uint8Array(n); sub.getRandomValues(b); return b; }
  function sha384(b) { return sub.subtle.digest('SHA-384', b).then(function (x) { return new Uint8Array(x); }); }
  /* un entier uniforme dans [1, n) : tirage avec rejet */
  function aleaMod(n) {
    var k = lmod(n), x;
    do { x = enEntier(hasard(k)) & ((1n << BigInt(bits(n))) - 1n); } while (x === 0n || x >= n);
    return x;
  }
  async function mgf1(graine, longueur) {
    var t = new Uint8Array(0), i = 0;
    while (t.length < longueur) { t = concat(t, await sha384(concat(graine, new Uint8Array([i >>> 24, (i >>> 16) & 255, (i >>> 8) & 255, i & 255])))); i++; }
    return t.slice(0, longueur);
  }
  /* EMSA-PSS-ENCODE, RFC 8017, §9.1.1 */
  async function encoder(message, emBits, sel) {
    var emLen = Math.ceil(emBits / 8), mHash = await sha384(message);
    if (emLen < LH + LSEL + 2) throw new Error('encodage impossible');
    sel = sel || hasard(LSEL);
    var h = await sha384(concat(new Uint8Array(8), mHash, sel));
    var db = concat(new Uint8Array(emLen - LSEL - LH - 2), new Uint8Array([1]), sel);
    var masque = await mgf1(h, emLen - LH - 1), mdb = new Uint8Array(db.length);
    for (var i = 0; i < db.length; i++) mdb[i] = db[i] ^ masque[i];
    mdb[0] &= 0xff >> (8 * emLen - emBits);
    return concat(mdb, h, new Uint8Array([0xbc]));
  }
  function b64url(b) {
    var s = ''; for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return (typeof btoa === 'function' ? btoa(s) : Buffer.from(b).toString('base64')).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function cle(pk) { return { n: BigInt('0x' + pk.n), e: BigInt('0x' + pk.e) }; }

  /* PrepareRandomize : 32 octets au hasard en tête du message */
  function preparer(message, prefixe) { prefixe = prefixe || hasard(LPREFIXE); if (prefixe.length !== LPREFIXE) throw new Error('préfixe'); return concat(prefixe, message); }

  /* Blind : pk = {n, e} en hexadécimal. Rend {aveugle (octets), inv (BigInt)}. sel et r : vecteurs d'essai seulement. */
  async function aveugler(pk, prepare, sel, r) {
    var k = cle(pk), m = enEntier(await encoder(prepare, bits(k.n) - 1, sel));
    if (pgcd(m, k.n) !== 1n) throw new Error('entrée invalide');
    var inv = null;
    while (inv === null) { var rr = r || aleaMod(k.n); inv = modinv(rr, k.n); if (inv === null && r) throw new Error('aveuglement impossible'); }
    return { aveugle: enOctets(m * modpow(rr, k.e, k.n) % k.n, lmod(k.n)), inv: inv };
  }

  /* Vérifie une signature RSA-PSS par crypto.subtle : rend true ou false */
  async function verifier(pk, prepare, sig) {
    var k = cle(pk), n = enOctets(k.n, lmod(k.n)), e = enOctets(k.e, Math.ceil(bits(k.e) / 8));
    try {
      var c = await sub.subtle.importKey('jwk', { kty: 'RSA', n: b64url(n), e: b64url(e), alg: 'PS384', ext: true },
        { name: 'RSA-PSS', hash: 'SHA-384' }, false, ['verify']);
      return await sub.subtle.verify({ name: 'RSA-PSS', saltLength: LSEL }, c, sig, prepare);
    } catch (_) { return false; }
  }

  /* Finalize : dévoile la signature et la vérifie. Rend la signature (octets) ou lève une erreur. */
  async function finaliser(pk, prepare, sigAveugle, inv) {
    var k = cle(pk), l = lmod(k.n);
    if (sigAveugle.length !== l) throw new Error('taille inattendue');
    var sig = enOctets(enEntier(sigAveugle) * inv % k.n, l);
    if (!(await verifier(pk, prepare, sig))) throw new Error('signature invalide');
    return sig;
  }

  return { preparer: preparer, aveugler: aveugler, finaliser: finaliser, verifier: verifier, encoder: encoder,
           hex: hex, deHex: deHex, hasard: hasard };
})();
if (typeof module !== 'undefined') module.exports = AveugleRSA;
