"""Miniature 1080x1920 du Reel « Zone 2 / HYROX » : ZONE 2 géant derrière Bene + étiquette manuscrite + chip HYROX."""
import os, sys, math, subprocess
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

WORK = os.environ.get("WORK", "/home/claude/run/work")
T = float(sys.argv[1]) if len(sys.argv) > 1 else 5.3
W, H = 1080, 1920
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{T:.3f}", "-i", os.path.join(WORK, "base.mp4"), "-frames:v", "1",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
cv = E.Canvas(np.array(frame))
E.fx_derriere(cv, 2.0, lignes=("ZONE 2",), face=E.NUM, y=880, max_size=460, dur=10)


def deco(c):
    # étiquette papier manuscrite
    c.save()
    c.translate(540, 1390)
    c.rotate(math.radians(-2.5))
    E.rrect(c, -440, -100 + 10, 880, 200, 6)
    c.set_source_rgba(0, 0, 0, 0.22)
    c.fill()
    E.rrect(c, -440, -100, 880, 200, 6)
    c.set_source_rgba(*E.PAPER, 0.97)
    c.fill()
    E.text(c, "Cours lentement", 0, -18, E.HAND, 70, E.NAVY, 1, "c")
    adv = E.text(c, "pour courir vite", 0, 66, E.HAND, 70, E.NAVY, 1, "c")
    c.move_to(-adv / 2 + 10, 92)
    c.curve_to(-adv / 4, 84, adv / 4, 100, adv / 2 - 20, 88)
    c.set_source_rgba(*E.BLUE, 1)
    c.set_line_width(9)
    c.set_line_cap(1)
    c.stroke()
    c.restore()
    # chip HYROX
    E.font(c, E.SANS_B, 70)
    w = c.text_extents("HYROX").x_advance + 60
    E.rrect(c, 540 - w / 2, 1530, w, 104, 12)
    c.set_source_rgba(*E.BLUE, 1)
    c.fill()
    E.text(c, "HYROX", 540, 1606, E.SANS_B, 70, E.WHITE, 1, "c")


cv.draw(deco)
img = Image.fromarray(cv.out())
img.save(os.path.join(WORK, "miniature_zone2.jpg"), quality=95)
img.crop((0, 240, 1080, 1680)).resize((540, 720)).save(os.path.join(WORK, "miniature_grille.jpg"))
print("ok")
