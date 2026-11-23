"""Miniature du Reel « Acteur principal » : la photo résultat de Bene (vestiaire, déjà très sombre), sans retouche
de couleurs. Titre au feutre en haut, « C'EST TOI » (Anton) + bloc bleu « L'ACTEUR PRINCIPAL. » en bas,
dans la zone visible 3:4 (y 240 → 1680).   python thumb_semaine.py"""
import os, sys
import numpy as np
import cairo
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E
import build_semaine as B

im = Image.open(B.PHOTO).convert("RGB")
s = B.H / im.height
im = im.resize((int(im.width * s), B.H), Image.LANCZOS)
x0 = int(E.clamp(0.56 * im.width - B.W / 2, 0, im.width - B.W))
DESCENTE = 300  # photo descendue pour que le titre ne passe pas sur le visage (haut de la photo = déjà noir)
base = np.zeros((B.H, B.W, 3), np.uint8)
base[DESCENTE:] = np.asarray(im.crop((x0, 0, x0 + B.W, B.H - DESCENTE)))
fondu = np.linspace(0, 1, 60)[:, None, None]
base[DESCENTE:DESCENTE + 60] = (base[DESCENTE:DESCENTE + 60] * fondu).astype(np.uint8)
cv = E.Canvas(base)


def deco(c):
    titre = "7 jours d'entraînement"
    E.font(c, E.HAND, 74)
    tw = c.text_extents(titre).x_advance
    x, y = B.W / 2 - tw / 2, 330
    c.move_to(x, y)
    c.set_source_rgba(1, 1, 1, 0.96)
    c.show_text(titre)
    c.set_source_rgba(*E.BLUE, 1)
    c.set_line_width(10)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(x + 10, y + 28)
    c.curve_to(x + tw * 0.35, y + 40, x + tw * 0.7, y + 20, x + tw - 6, y + 34)
    c.stroke()
    B.draw_fin(c, 1.0)


cv.draw(deco)
out = os.path.join(B.WORK, "BENFIT_reel_acteur_principal_miniature.png")
Image.fromarray(cv.out()).save(out, optimize=True)
print("ok", out)
