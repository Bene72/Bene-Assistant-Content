"""Couverture « SNATCH SESSION » (séance × Apocalypse, 27 nov. 2026).
Photo réelle de Bene en réception d'arraché (rush 144615 à 43,0 s), couleurs d'origine ; titre Anton en haut ;
logos BEN&FIT × APOCALYPSE en bas ; tout dans la zone visible 3:4 (y 240 → 1680).   python thumb_snatch.py"""
import os, sys, subprocess
import numpy as np
import cv2
import cairo
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E
RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/logo")
LOGOS = os.path.join(HERE, "..", "..", "..", "logos")
W, H, DESC = 1080, 1920, 190

raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "43.0", "-i", os.path.join(RUSH, "VID_20261126_144615.mp4"),
                      "-frames:v", "1", "-vf", f"scale={W}:{H}:in_color_matrix=bt709:flags=lanczos", "-f", "rawvideo",
                      "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
ph = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
# on descend la photo pour libérer le haut (plafond sombre prolongé)
img = np.empty_like(ph)
img[DESC:] = ph[:H - DESC]
top = cv2.GaussianBlur(cv2.resize(ph[:DESC * 2], (W, DESC)), (0, 0), 12)
img[:DESC] = (top * 0.8).astype(np.uint8)
fade = np.linspace(0, 1, 60)[:, None, None]
img[DESC:DESC + 60] = (img[DESC:DESC + 60] * fade + img[DESC - 1:DESC] * (1 - fade)).astype(np.uint8)
# léger assombrissement du haut pour la lisibilité du titre (dégradé vers le bas)
g = np.clip(1 - np.linspace(0.45, 0, 700), 0, 1)[:, None, None]
img[:700] = (img[:700] * g).astype(np.uint8)
cv = E.Canvas(img.copy())


def logo(c, name, cx, cy, h):
    im = Image.open(os.path.join(LOGOS, name)).convert("RGBA")
    w = int(im.width * h / im.height)
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im).copy()
    a[..., :3] = a[..., [2, 1, 0]]               # RGBA → BGRA (cairo)
    a = (a.astype(np.float32) * np.concatenate([a[..., 3:4] / 255] * 3 + [np.ones_like(a[..., 3:4])], -1)).astype(np.uint8)
    surf = cairo.ImageSurface.create_for_data(bytearray(a.tobytes()), cairo.FORMAT_ARGB32, w, h, w * 4)
    c.set_source_surface(surf, cx - w / 2, cy - h / 2)
    c.paint()


def deco(c):
    for txt, y in (("SNATCH", 470), ("SESSION", 670)):
        E.font(c, E.NUM, 230)
        tw = c.text_extents(txt).x_advance
        s = min(1.0, 1000 / tw)
        c.save()
        c.translate(W / 2, y)
        c.scale(s, s)
        c.move_to(-tw / 2, 0)
        c.text_path(txt)
        c.set_source_rgba(0.04, 0.125, 0.42, 1)
        c.set_line_width(18)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke_preserve()
        c.set_source_rgba(1, 1, 1, 1)
        c.fill()
        c.restore()
    logo(c, "benfit.png", W / 2 - 200, 1530, 220)
    logo(c, "apocalypse-training.png", W / 2 + 200, 1530, 250)
    L = 26
    c.set_source_rgba(1, 1, 1, 1)
    c.set_line_width(9)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for d in (1, -1):
        c.move_to(W / 2 - L, 1530 - d * L)
        c.line_to(W / 2 + L, 1530 + d * L)
    c.stroke()


cv.draw(deco)
out = os.path.join(WORK, "BENFIT_x_APOCALYPSE_snatch_session.png")
Image.fromarray(cv.out()).save(out, optimize=True)
print("ok", out)
