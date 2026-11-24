"""Miniature du Reel canapé : image du mur de vidéos (couleurs d'origine), titre Anton + bloc bleu Coda,
dans la zone visible 3:4 (y 240 → 1680).   python thumb_canape.py"""
import os, sys, subprocess
import numpy as np
import cairo
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E
WORK = os.environ.get("WORK", "/home/claude/run/canape")
W, H = 1080, 1920
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "9.4", "-i", os.path.join(WORK, "BENFIT_reel_canape.mp4"),
                      "-frames:v", "1", "-vf", "scale=in_color_matrix=bt709", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True, check=True).stdout
cv = E.Canvas(np.frombuffer(raw, np.uint8).reshape(H, W, 3).copy())


def deco(c):
    mot, size = "CHOISIS TA SÉANCE", 150
    E.font(c, E.NUM, size)
    while c.text_extents(mot).x_advance > 980:
        size -= 4
        E.font(c, E.NUM, size)
    mw = c.text_extents(mot).x_advance
    c.move_to(W / 2 - mw / 2, 1500)
    c.text_path(mot)
    c.set_source_rgba(0.04, 0.125, 0.42, 1)
    c.set_line_width(14)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke_preserve()
    c.set_source_rgba(1, 1, 1, 1)
    c.fill()
    tag = "depuis ton canapé."
    E.font(c, E.SANS_B, 62)
    tw = c.text_extents(tag).x_advance
    bx, by = W / 2 - tw / 2, 1615
    E.rrect(c, bx - 26, by - 56, tw + 52, 82, 12)
    c.set_source_rgba(*E.BLUE, 1)
    c.fill()
    c.move_to(bx, by)
    c.set_source_rgba(1, 1, 1, 1)
    c.show_text(tag)


cv.draw(deco)
out = os.path.join(WORK, "BENFIT_reel_canape_miniature.png")
Image.fromarray(cv.out()).save(out, optimize=True)
print("ok", out)
