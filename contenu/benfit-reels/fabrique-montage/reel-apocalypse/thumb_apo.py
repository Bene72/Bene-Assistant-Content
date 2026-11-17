"""Miniature 1080x1920 du Reel BEN&FIT x Apocalypse Training (handstand tenu + titre Anton + chip bleu)."""
import sys, cairo, numpy as np
import PIL.Image as PImage
sys.path.insert(0, "/home/claude/work/apo")
from compose_apo import text, chip, cobrand, legib_grad, marker_path, underline_pts, NUM, MARK, BLUE, STROKE, W, H
im = PImage.open("/home/claude/work/apo/thumb_base.png").convert("RGBA")
a = np.ascontiguousarray(np.asarray(im)[..., [2, 1, 0, 3]])
src = cairo.ImageSurface.create_for_data(bytearray(a.tobytes()), cairo.FORMAT_ARGB32, W, H, W * 4)
out = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(out)
ctx.save(); s = 1.0; ctx.translate(540, 700); ctx.scale(s, s); ctx.translate(-540, -700)
ctx.set_source_surface(src, 0, -150); ctx.paint(); ctx.restore()
legib_grad(ctx, 1, 980, 1800, 0.75)
text(ctx, "J'AI TESTÉ", 540, 1270, 165, face=NUM, stroke=STROKE, sw=14, shadow=0.45)
text(ctx, "SON BLOC", 540, 1440, 165, face=NUM, stroke=STROKE, sw=14, shadow=0.45)
chip(ctx, "APOCALYPSE TRAINING", 540, 1600, 64, anchor="c", padx=26, pady=18)
cobrand(ctx, 850, 760, 120, 0.95)
out.flush()
img = PImage.frombuffer("RGBA", (W, H), bytes(out.get_data()), "raw", "BGRA", 0, 1).convert("RGB")
img.save("/home/claude/work/apo/miniature_apocalypse.jpg", quality=95)
img.crop((0, 240, 1080, 1680)).resize((540, 720)).save("/home/claude/work/apo/chk/miniature_grille.jpg")
print("ok")
