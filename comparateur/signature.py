"""Signature aveugle RSA, RFC 9474, variante RSABSSA-SHA384-PSS-Randomized. Bibliothèque standard seulement.

Le guichet signe un bulletin qu'il ne voit pas ; l'appareil dévoile la signature, qui se vérifie comme une signature
RSA-PSS ordinaire (RFC 8017) et ne peut pas être rapprochée de la demande. Les quatre étapes de la RFC :

  preparer(message)                 l'appareil ajoute 32 octets au hasard en tête (PrepareRandomize, §4.1)
  aveugler(cle_publique, prepare)   l'appareil aveugle ; rend (bulletin aveuglé, inverse)          (§4.2)
  signer_aveugle(cle, aveugle)      le guichet signe sans voir, calcul masqué et revérifié          (§4.3, §7.1)
  finaliser(cle_publique, prepare, signature_aveugle, inverse)   l'appareil dévoile et vérifie     (§4.4)
  verifier(cle_publique, prepare, signature)                     l'urne vérifie                    (§4.5)

Une clé ne sert qu'à un questionnaire et à rien d'autre (RFC 9474, §6.2 et §7.2). La même règle est écrite en
JavaScript dans compte/aveugle-rsa.js ; les deux passent les vecteurs de l'annexe A.1 de la RFC.

Ce module ne connaît ni compte ni urne : il n'importe rien du paquet.
"""
import hashlib, hmac, secrets

HACHAGE = hashlib.sha384
LONGUEUR_HACHAGE = 48
LONGUEUR_SEL = 48          # sLen = longueur du hachage : la variante « PSS »
LONGUEUR_PREFIXE = 32      # PrepareRandomize
E = 65537


class ErreurSignature(Exception):
    pass


# ---- outils de la RFC 8017

def octets_en_entier(b):
    return int.from_bytes(b, "big")


def entier_en_octets(x, longueur):
    if x >= 256 ** longueur:
        raise ErreurSignature("entier trop grand")
    return x.to_bytes(longueur, "big")


def longueur_modulo(n):
    return (n.bit_length() + 7) // 8


def mgf1(graine, longueur):
    t = b""
    for i in range((longueur + LONGUEUR_HACHAGE - 1) // LONGUEUR_HACHAGE):
        t += HACHAGE(graine + i.to_bytes(4, "big")).digest()
    return t[:longueur]


def emsa_pss_encoder(message, bits, sel=None):
    """EMSA-PSS-ENCODE (RFC 8017, §9.1.1), SHA-384, MGF1-SHA-384, sel de 48 octets. `sel` n'est donné que par
    les vecteurs d'essai ; sinon il est tiré au hasard."""
    em_len = (bits + 7) // 8
    m_hash = HACHAGE(message).digest()
    if em_len < LONGUEUR_HACHAGE + LONGUEUR_SEL + 2:
        raise ErreurSignature("encodage impossible")
    sel = secrets.token_bytes(LONGUEUR_SEL) if sel is None else sel
    h = HACHAGE(b"\x00" * 8 + m_hash + sel).digest()
    db = b"\x00" * (em_len - LONGUEUR_SEL - LONGUEUR_HACHAGE - 2) + b"\x01" + sel
    masque = mgf1(h, em_len - LONGUEUR_HACHAGE - 1)
    masque_db = bytes(x ^ y for x, y in zip(db, masque))
    zeros = 8 * em_len - bits
    masque_db = bytes([masque_db[0] & (0xFF >> zeros)]) + masque_db[1:]
    return masque_db + h + b"\xbc"


def emsa_pss_verifier(message, em, bits):
    """EMSA-PSS-VERIFY (RFC 8017, §9.1.2). Rend True ou False."""
    em_len = (bits + 7) // 8
    m_hash = HACHAGE(message).digest()
    if len(em) != em_len or em_len < LONGUEUR_HACHAGE + LONGUEUR_SEL + 2 or em[-1] != 0xBC:
        return False
    masque_db, h = em[:em_len - LONGUEUR_HACHAGE - 1], em[em_len - LONGUEUR_HACHAGE - 1:-1]
    zeros = 8 * em_len - bits
    if masque_db[0] & (0xFF << (8 - zeros)) & 0xFF:
        return False
    db = bytes(x ^ y for x, y in zip(masque_db, mgf1(h, em_len - LONGUEUR_HACHAGE - 1)))
    db = bytes([db[0] & (0xFF >> zeros)]) + db[1:]
    bourrage = em_len - LONGUEUR_HACHAGE - LONGUEUR_SEL - 2
    if db[:bourrage] != b"\x00" * bourrage or db[bourrage] != 1:
        return False
    sel = db[-LONGUEUR_SEL:]
    return hmac.compare_digest(h, HACHAGE(b"\x00" * 8 + m_hash + sel).digest())


# ---- les clés

def _premier_probable(x, tours=40):
    if x < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if x % p == 0:
            return x == p
    d, s = x - 1, 0
    while d % 2 == 0:
        d, s = d // 2, s + 1
    for _ in range(tours):
        a = 2 + secrets.randbelow(x - 3)
        y = pow(a, d, x)
        if y in (1, x - 1):
            continue
        for _ in range(s - 1):
            y = pow(y, 2, x)
            if y == x - 1:
                break
        else:
            return False
    return True


def _premier(bits):
    while True:
        x = secrets.randbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2)) | 1   # deux bits forts : n a bien 2·bits
        if x % E != 1 and _premier_probable(x):
            return x


def nouvelle_cle(bits=2048):
    """Une paire de clés RSA neuve, propre à un questionnaire. Rend {n, e, d, p, q} (entiers)."""
    while True:
        p, q = _premier(bits // 2), _premier(bits // 2)
        if p == q:
            continue
        n, phi = p * q, (p - 1) * (q - 1)
        if n.bit_length() != bits:
            continue
        try:
            d = pow(E, -1, phi)
        except ValueError:
            continue
        return {"n": n, "e": E, "d": d, "p": p, "q": q}


def publique(cle):
    return {"n": cle["n"], "e": cle["e"]}


def en_hex(pk):
    """La clé publique en hexadécimal, comme la lit compte/aveugle-rsa.js."""
    return {"n": format(pk["n"], "x"), "e": format(pk["e"], "x")}


def de_hex(pk):
    return {"n": int(pk["n"], 16), "e": int(pk["e"], 16)}


# ---- le protocole

def preparer(message, prefixe=None):
    """PrepareRandomize : 32 octets au hasard en tête du message."""
    prefixe = secrets.token_bytes(LONGUEUR_PREFIXE) if prefixe is None else prefixe
    if len(prefixe) != LONGUEUR_PREFIXE:
        raise ErreurSignature("préfixe de longueur fausse")
    return prefixe + message


def aveugler(pk, prepare, sel=None, r=None):
    """Blind : rend (bulletin aveuglé, inverse). `sel` et `r` ne sont donnés que par les vecteurs d'essai."""
    n, e = pk["n"], pk["e"]
    k = longueur_modulo(n)
    m = octets_en_entier(emsa_pss_encoder(prepare, n.bit_length() - 1, sel))
    if _pgcd(m, n) != 1:
        raise ErreurSignature("entrée invalide")
    while True:
        r_ = r if r is not None else 1 + secrets.randbelow(n - 1)
        try:
            inv = pow(r_, -1, n)
            break
        except ValueError:
            if r is not None:
                raise ErreurSignature("aveuglement impossible")
    return entier_en_octets(m * pow(r_, e, n) % n, k), inv


def signer_aveugle(cle, aveugle):
    """BlindSign. Le calcul privé est masqué par un aléa (RFC 9474, §7.1 : contre la mesure du temps), et le
    résultat est revérifié avant d'être rendu (§4.3, étapes 3 et 4)."""
    n, e, d = cle["n"], cle["e"], cle["d"]
    k = longueur_modulo(n)
    if len(aveugle) != k:
        raise ErreurSignature("taille inattendue")
    m = octets_en_entier(aveugle)
    if m >= n:
        raise ErreurSignature("représentant hors de l'intervalle")
    while True:
        masque = 1 + secrets.randbelow(n - 1)
        try:
            inverse_masque = pow(masque, -1, n)
            break
        except ValueError:
            continue
    s = pow(m * pow(masque, e, n) % n, d, n) * inverse_masque % n
    if pow(s, e, n) != m:
        raise ErreurSignature("échec de signature")
    return entier_en_octets(s, k)


def finaliser(pk, prepare, signature_aveugle, inv):
    """Finalize : dévoile la signature et la vérifie. Rend la signature, ou lève ErreurSignature."""
    n = pk["n"]
    k = longueur_modulo(n)
    if len(signature_aveugle) != k:
        raise ErreurSignature("taille inattendue")
    sig = entier_en_octets(octets_en_entier(signature_aveugle) * inv % n, k)
    if not verifier(pk, prepare, sig):
        raise ErreurSignature("signature invalide")
    return sig


def verifier(pk, prepare, sig):
    """RSASSA-PSS-VERIFY (RFC 8017, §8.1.2). Rend True ou False, jamais d'exception."""
    n, e = pk["n"], pk["e"]
    k = longueur_modulo(n)
    if not isinstance(sig, (bytes, bytearray)) or len(sig) != k:
        return False
    s = octets_en_entier(sig)
    if s >= n:
        return False
    em_bits = n.bit_length() - 1
    em_len = (em_bits + 7) // 8
    try:
        em = entier_en_octets(pow(s, e, n), em_len)
    except ErreurSignature:
        return False
    return emsa_pss_verifier(prepare, em, em_bits)


def _pgcd(a, b):
    while b:
        a, b = b, a % b
    return a
