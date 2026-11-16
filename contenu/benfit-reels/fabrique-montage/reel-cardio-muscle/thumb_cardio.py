"""Miniature 1080x1920 du Reel « Cardio et perte de muscle » (même style que « 4 qualités »)."""
import sys, math, cairo, numpy as np
import PIL.Image as PImage
sys.path.insert(0, "/home/claude/work")
from compose_cardio import text, chip, rrect, marker_path, underline_pts, tw, MARK, NUM, INK, BLUE, STROKE, NAVY, W, H
im = PImage.open("/home/claude/work/thumb_base.png").convert("RGBA")
a = np.asarray(im).astype(np.uint8)
bgra = np.ascontiguousarray(a[..., [2, 1, 0, 3]])
src = cairo.ImageSurface.create_for_data(bytearray(bgra.tobytes()), cairo.FORMAT_ARGB32, W, H, W * 4)
out = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(out)
ctx.save(); s = 1.04; ctx.translate(540, 900); ctx.scale(s, s); ctx.translate(-540, -900)
ctx.set_source_surface(src, 0, 0); ctx.paint(); ctx.restore()
# bandeau papier (titre manuscrit)
ctx.save(); ctx.translate(540, 385); ctx.rotate(math.radians(-2.5))
rrect(ctx, -455, -118 + 10, 910, 236, 6); ctx.set_source_rgba(0, 0, 0, 0.22); ctx.fill()
rrect(ctx, -455, -118, 910, 236, 6); ctx.set_source_rgba(0.98, 0.97, 0.94, 0.96); ctx.fill()
for x in (-400, 400):
    ctx.save(); ctx.translate(x, -118); ctx.rotate(math.radians(-8 if x < 0 else 8))
    ctx.rectangle(-60, -18, 120, 36); ctx.set_source_rgba(0.93, 0.89, 0.78, 0.8); ctx.fill(); ctx.restore()
text(ctx, "Le cardio fait-il", 0, -48, 74, face=MARK, color=INK)
adv = text(ctx, "fondre tes muscles ?", 0, 52, 74, face=MARK, color=INK)
marker_path(ctx, underline_pts(-adv / 2 + 10, adv / 2 - 60, 98), 1, 9, BLUE)
ctx.restore()
# dégradé de lisibilité en bas
g = cairo.LinearGradient(0, 1150, 0, 1750); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, *NAVY, 0.6)
ctx.rectangle(0, 1150, W, 600); ctx.set_source(g); ctx.fill()
text(ctx, "CARDIO", 540, 1410, 270, face=NUM, stroke=STROKE, sw=16, shadow=0.4)
chip(ctx, "= MOINS DE MUSCLE ?", 540, 1600, 76, anchor="c", padx=26, pady=18)
out.flush()
img = PImage.frombuffer("RGBA", (W, H), bytes(out.get_data()), "raw", "BGRA", 0, 1).convert("RGB")
img.save("/home/claude/work/miniature_cardio.jpg", quality=95)
# aperçu de la grille 3:4 (zone visible sur le profil)
prev = img.crop((0, 240, 1080, 1680)).resize((540, 720)); prev.save("/home/claude/work/miniature_grille.jpg")
print("ok")
