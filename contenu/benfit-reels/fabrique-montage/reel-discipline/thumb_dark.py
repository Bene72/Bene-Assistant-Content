"""Miniature « dark » du Reel « Discipline » (demande de Bene, 21 nov. : « très dark »).

Photo réelle (snatch bras tendu, rush 112349), ambiance low-key : décor presque noir, Bene détouré
(rembg u2net_human_seg) et gardé lisible, contraste plus dur, vignette. Rien d'inventé sur le corps,
pas de halo ni d'éclairs. Textes dans la zone visible 3:4 (y 240 → 1680).
  python thumb_dark.py   → $WORK/BENFIT_reel_discipline_miniature_dark.png
"""
import os, sys, subprocess
import numpy as np
import cairo
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/work")
W, H = 1080, 1920
SRC, T = "VID_20261120_112349.mp4", 8.1
DESCENTE = 230        # on descend la photo pour libérer le haut (titre) sans couvrir l'haltère

raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(T), "-i", os.path.join(RUSH, SRC), "-frames:v", "1",
                      "-vf", f"scale={W}:{H}:in_color_matrix=bt709:in_range=tv:flags=lanczos+accurate_rnd",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
photo = Image.fromarray(np.frombuffer(raw, np.uint8).reshape(H, W, 3))

from rembg import remove, new_session
mask = remove(photo, session=new_session("u2net_human_seg"), only_mask=True)
mask = np.asarray(mask.filter(ImageFilter.GaussianBlur(2)), np.float32) / 255

img = np.asarray(photo, np.float32)
canvas = np.zeros((H, W, 3), np.float32)
alpha = np.zeros((H, W), np.float32)
canvas[DESCENTE:] = img[:H - DESCENTE]
alpha[DESCENTE:] = mask[:H - DESCENTE]

lum = canvas.mean(-1, keepdims=True)
# décor : presque noir, couleurs éteintes
bg = (canvas * 0.45 + lum * 0.55) * 0.16
# sujet : un peu plus sombre et plus contrasté, légèrement désaturé, rien d'ajouté
subj = canvas * 0.85 + lum * 0.15
subj = np.clip((subj / 255) ** 1.25 * 255 * 0.95, 0, 255)
subj = np.clip((subj - 110) * 1.18 + 100, 0, 255)
out = bg * (1 - alpha[..., None]) + subj * alpha[..., None]

# vignette forte + ombres très légèrement froides (marine)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
d = np.sqrt(((xx - W * 0.52) / (W * 0.62)) ** 2 + ((yy - H * 0.42) / (H * 0.55)) ** 2)
vig = np.clip(1.15 - d ** 1.6 * 0.75, 0.12, 1)[..., None]
out = out * vig
shadow = np.clip(1 - out.mean(-1, keepdims=True) / 90, 0, 1)
out = out + shadow * np.array([0, 2, 9], np.float32)
out = np.clip(out, 0, 255).astype(np.uint8)

cv = E.Canvas(out.copy())
NAVY = (0.04, 0.125, 0.42)


def deco(c):
    titre = "Pas de motivation ?"
    E.font(c, E.HAND, 86)
    tw = c.text_extents(titre).x_advance
    x, y = W / 2 - tw / 2, 330
    c.move_to(x, y)
    c.set_source_rgba(1, 1, 1, 0.96)
    c.show_text(titre)
    c.set_source_rgba(*E.BLUE, 1)
    c.set_line_width(11)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(x + 10, y + 32)
    c.curve_to(x + tw * 0.35, y + 44, x + tw * 0.7, y + 24, x + tw - 6, y + 38)
    c.stroke()
    mot, size = "DISCIPLINE", 230
    E.font(c, E.NUM, size)
    while c.text_extents(mot).x_advance > 980:
        size -= 4
        E.font(c, E.NUM, size)
    mw = c.text_extents(mot).x_advance
    c.move_to(W / 2 - mw / 2, 1480)
    c.text_path(mot)
    c.set_source_rgba(*NAVY, 1)
    c.set_line_width(14)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke_preserve()
    c.set_source_rgba(1, 1, 1, 1)
    c.fill()
    tag = "le taf, il est là."
    E.font(c, E.SANS_B, 62)
    tw2 = c.text_extents(tag).x_advance
    bx, by = W / 2 - tw2 / 2, 1600
    E.rrect(c, bx - 26, by - 56, tw2 + 52, 82, 12)
    c.set_source_rgba(*E.BLUE, 1)
    c.fill()
    c.move_to(bx, by)
    c.set_source_rgba(1, 1, 1, 1)
    c.show_text(tag)


cv.draw(deco)
dst = os.path.join(WORK, "BENFIT_reel_discipline_miniature_dark.png")
Image.fromarray(cv.out()).save(dst, optimize=True)
print("ok", dst)
