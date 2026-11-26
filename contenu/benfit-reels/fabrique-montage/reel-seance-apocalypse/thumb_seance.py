"""Miniature du Reel séance à deux : réception de l'arraché de Bene (image du Reel, couleurs d'origine),
titre Anton en haut (au-dessus de lui), bloc bleu co-branding ; zone visible 3:4 (y 240 → 1680).
python thumb_seance.py"""
import os, sys, subprocess
import numpy as np
import cairo
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E
WORK = os.environ.get("WORK", "/home/claude/run/seance")
W, H = 1080, 1920
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "2.0", "-i", os.path.join(WORK, "v.mp4"), "-frames:v", "1", "-vf",
                      "scale=in_color_matrix=bt709", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True, check=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(H, W, 3).copy()
f[150:215] = f[215:216]            # efface la barre de progression du Reel (bande du haut)
cv = E.Canvas(f)


def deco(c):
    for txt, y in (("SÉANCE", 470), ("À DEUX", 650)):
        E.font(c, E.NUM, 200)
        tw = c.text_extents(txt).x_advance
        c.move_to(W / 2 - tw / 2, y)
        c.text_path(txt)
        c.set_source_rgba(0.04, 0.125, 0.42, 1)
        c.set_line_width(16)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke_preserve()
        c.set_source_rgba(1, 1, 1, 1)
        c.fill()
    tag = "BEN&FIT × APOCALYPSE TRAINING"
    E.font(c, E.SANS_B, 48)
    tw = c.text_extents(tag).x_advance
    E.rrect(c, W / 2 - tw / 2 - 24, 1560, tw + 48, 74, 10)
    c.set_source_rgba(*E.BLUE, 1)
    c.fill()
    c.move_to(W / 2 - tw / 2, 1612)
    c.set_source_rgba(1, 1, 1, 1)
    c.show_text(tag)


cv.draw(deco)
out = os.path.join(WORK, "BENFIT_x_APOCALYPSE_miniature.png")
Image.fromarray(cv.out()).save(out, optimize=True)
print("ok", out)
