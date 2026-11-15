"""Fabrique les icônes PNG de l'application (manifest, écran d'accueil d'iPhone) à partir du dessin de
favicon.svg : fond clair, barre noire. Bibliothèque standard seulement (zlib, struct).

    python3 essais/icones.py

Écrit dans comparateur/site/ : icone-192.png, icone-512.png, icone-masquable-512.png, apple-touch-icon.png.
Les PNG sont versionnés : ce script ne sert qu'à les refaire si le dessin change.
"""
import os, struct, zlib

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comparateur", "site")
FOND = (0xF1, 0xED, 0xE4)    # --bg de base.css, fond de favicon.svg
ENCRE = (0x16, 0x14, 0x0F)   # --ink de base.css, barre de favicon.svg


def png(cote, barre):
    """Une image carrée de `cote` pixels. barre = (x, y, largeur, hauteur) en fractions du côté."""
    x0, y0 = round(barre[0] * cote), round(barre[1] * cote)
    x1, y1 = x0 + round(barre[2] * cote), y0 + round(barre[3] * cote)
    lignes = []
    for y in range(cote):
        if y0 <= y < y1:
            ligne = bytes(FOND) * x0 + bytes(ENCRE) * (x1 - x0) + bytes(FOND) * (cote - x1)
        else:
            ligne = bytes(FOND) * cote
        lignes.append(b"\x00" + ligne)   # filtre 0 : aucun

    def bloc(nom, data):
        return struct.pack(">I", len(data)) + nom + data + struct.pack(">I", zlib.crc32(nom + data) & 0xFFFFFFFF)

    entete = struct.pack(">IIBBBBB", cote, cote, 8, 2, 0, 0, 0)   # 8 bits, RVB, sans entrelacement
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", entete) + bloc(b"IDAT", zlib.compress(b"".join(lignes), 9))
            + bloc(b"IEND", b""))


# Le dessin de favicon.svg : viewBox 32, barre x=3 y=10, 26 sur 12.
NORMALE = (3 / 32, 10 / 32, 26 / 32, 12 / 32)
# Icône « maskable » : le système peut la découper en cercle. Tout le dessin doit tenir dans le cercle central
# de 80 % du côté (rayon 0,4). La barre est réduite de moitié : sa demi-diagonale vaut alors 0,22 du côté.
MASQUABLE = (0.5 - 13 / 32 / 2, 0.5 - 6 / 32 / 2, 13 / 32, 6 / 32)

ICONES = {"icone-192.png": (192, NORMALE), "icone-512.png": (512, NORMALE),
          "icone-masquable-512.png": (512, MASQUABLE), "apple-touch-icon.png": (180, NORMALE)}

if __name__ == "__main__":
    for nom, (cote, barre) in ICONES.items():
        with open(os.path.join(SITE, nom), "wb") as f:
            f.write(png(cote, barre))
        print(nom, cote, "px")
