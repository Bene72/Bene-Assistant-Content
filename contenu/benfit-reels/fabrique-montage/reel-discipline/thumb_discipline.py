"""Miniature du Reel « Discipline » : image de la prise face caméra, couleurs d'origine (aucun étalonnage),
titre manuscrit en haut souligné au feutre bleu, mot-clé géant en bas (Anton) + bloc bleu Coda.
Tous les textes restent dans la zone visible de la grille Instagram 3:4 (y de 240 à 1680).
  python thumb_discipline.py   → $WORK/BENFIT_reel_discipline_miniature.png
"""
import os, sys, subprocess
import numpy as np
import cairo
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/work")
W, H = 1080, 1920
SRC, T = "VID_20261120_103837.mp4", 15.2

raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(T), "-i", os.path.join(RUSH, SRC), "-frames:v", "1",
                      "-vf", f"scale={W}:{H}:in_color_matrix=bt709:in_range=tv:flags=lanczos+accurate_rnd",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
# léger recadrage (zoom 1,08) pour remonter le visage, sans toucher aux couleurs
s = 1.08
cw, ch = W / s, H / s
x0, y0 = (W - cw) / 2, (H - ch) * 0.62
frame = np.asarray(Image.fromarray(frame).resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)))

cv = E.Canvas(np.array(frame))


def deco(c):
    # titre manuscrit en haut
    titre = "Pas de motivation ?"
    E.font(c, E.HAND, 92)
    tw = c.text_extents(titre).x_advance
    x, y = W / 2 - tw / 2, 360
    c.move_to(x, y)
    c.text_path(titre)
    c.set_source_rgba(*E.NAVY if hasattr(E, "NAVY") else (0.04, 0.125, 0.42), 1)
    c.set_line_width(14)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke_preserve()
    c.set_source_rgba(1, 1, 1, 1)
    c.fill()
    # souligné au feutre bleu (trait un peu irrégulier)
    c.set_source_rgba(*E.BLUE, 1)
    c.set_line_width(12)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(x + 10, y + 34)
    c.curve_to(x + tw * 0.35, y + 46, x + tw * 0.7, y + 26, x + tw - 6, y + 40)
    c.stroke()
    # mot-clé géant en bas
    mot = "DISCIPLINE"
    size = 230
    E.font(c, E.NUM, size)
    while c.text_extents(mot).x_advance > 980:
        size -= 4
        E.font(c, E.NUM, size)
    mw = c.text_extents(mot).x_advance
    yb = 1470
    c.move_to(W / 2 - mw / 2, yb)
    c.text_path(mot)
    c.set_source_rgba(0.04, 0.125, 0.42, 1)
    c.set_line_width(16)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke_preserve()
    c.set_source_rgba(1, 1, 1, 1)
    c.fill()
    # bloc bleu Coda avec ses mots
    tag = "le taf, il est là."
    E.font(c, E.SANS_B, 64)
    tw2 = c.text_extents(tag).x_advance
    bx, by = W / 2 - tw2 / 2, 1590
    E.rrect(c, bx - 26, by - 58, tw2 + 52, 84, 12)
    c.set_source_rgba(*E.BLUE, 1)
    c.fill()
    c.move_to(bx, by)
    c.set_source_rgba(1, 1, 1, 1)
    c.show_text(tag)


cv.draw(deco)
out = os.path.join(WORK, "BENFIT_reel_discipline_miniature.png")
Image.fromarray(cv.out()).save(out, optimize=True)
print("ok", out)
