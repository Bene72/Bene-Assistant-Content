"""Miniature « studio » : Bene détouré sur fond marine sombre, contre-jour bleu, gros titre derrière lui.
Effets volontairement sobres (pas d'éclairs ni de statue) pour éviter le rendu « IA »."""
import numpy as np, cairo, math
from PIL import Image, ImageFilter
import sys
sys.path.insert(0, "/home/claude/work")
from compose_cardio import text, chip, marker_path, underline_pts, tw, MARK, NUM, BLUE, STROKE, NAVY, W, H

rng = np.random.default_rng(4)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# 1. fond : marine #0A206B -> presque noir, lumière douce derrière la tête
navy = np.array([10, 32, 107], np.float32); deep = np.array([3, 8, 26], np.float32)
d = np.sqrt(((xx - 470) / 700) ** 2 + ((yy - 620) / 900) ** 2)
t = np.clip(d, 0, 1)[..., None] ** 1.2
bg = navy * (1 - t) + deep * t
# brume légère (bruit basse fréquence)
n = Image.fromarray((rng.random((24, 14)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(60))
fog = (np.asarray(n, np.float32) / 255)[..., None]
bg += fog * np.array([30, 60, 140], np.float32) * 0.35
bg = np.clip(bg, 0, 255)

# 2. sujet
cut = Image.open("cutout_clean.png").convert("RGBA")
a = np.asarray(cut).astype(np.float32)
alpha = np.asarray(Image.fromarray(a[..., 3].astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
rgb = a[..., :3]
# léger étalonnage pour l'intégrer au fond sombre : un peu plus de contraste, ombres froides
lum = rgb.mean(-1, keepdims=True) / 255
rgb = rgb * 0.92 + (1 - lum) * np.array([-6, -2, 10], np.float32)
rgb = np.clip((rgb - 128) * 1.06 + 124, 0, 255)

# 3. contre-jour bleu (#2E6BFF) : halo extérieur + liseré intérieur sur les bords
A = Image.fromarray((alpha * 255).astype(np.uint8))
halo = np.asarray(A.filter(ImageFilter.GaussianBlur(28)), np.float32) / 255
rim_in = alpha - np.asarray(A.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
rim_in = np.clip(rim_in, 0, 1)
side = np.clip(np.abs(xx - 470) / 420, 0, 1) ** 0.8            # plus fort sur les côtés que sur le visage
top = np.clip((1300 - yy) / 900, 0, 1)                          # surtout tête et épaules
blue = np.array([46, 107, 255], np.float32)
glow = (halo * (1 - alpha))[..., None] * blue * 0.55

out = bg + glow

# 4. titre géant DERRIÈRE le sujet (effet profondeur)
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
text(ctx, "CARDIO", 540, 430, 360, face=NUM, color=(1, 1, 1), alpha=0.95)
surf.flush()
lay = np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data()).astype(np.float32)
la = lay[..., 3:4] / 255
out = out * (1 - la) + lay[..., [2, 1, 0]] * 1.0  # prémultiplié
# légère lueur bleue autour du titre
tg = np.asarray(Image.fromarray(lay[..., 3].astype(np.uint8)).filter(ImageFilter.GaussianBlur(30)), np.float32)[..., None] / 255
out = out + tg * (1 - la) * blue * 0.35

# sujet par-dessus
subj = rgb + (rim_in * side * top)[..., None] * (np.array([150, 190, 255], np.float32) - rgb) * 0.55
out = out * (1 - alpha[..., None]) + subj * alpha[..., None]

# 5. bas : dégradé + texte
gy = np.clip((yy - 1250) / 520, 0, 1)[..., None]
out = out * (1 - 0.6 * gy) + deep * 0.6 * gy
# vignette + grain
vig = 1 - 0.35 * np.clip(np.sqrt(((xx - 540) / 760) ** 2 + ((yy - 900) / 1150) ** 2) - 0.45, 0, 1)
out = out * vig[..., None]
out += rng.normal(0, 4.5, out.shape[:2])[..., None]
out = np.clip(out, 0, 255).astype(np.uint8)

img = Image.fromarray(out, "RGB").convert("RGBA")
arr = np.ascontiguousarray(np.asarray(img)[..., [2, 1, 0, 3]])
surf = cairo.ImageSurface.create_for_data(bytearray(arr.tobytes()), cairo.FORMAT_ARGB32, W, H, W * 4)
ctx = cairo.Context(surf)
adv = tw(ctx, "= moins de muscle ?", 92, MARK)
text(ctx, "= moins de muscle ?", 540, 1520, 92, face=MARK, color=(1, 1, 1), shadow=0.5)
marker_path(ctx, underline_pts(540 - adv / 2 + 20, 540 + adv / 2 - 20, 1595), 1, 12, BLUE)
text(ctx, "BEN&FIT", 540, 1650, 36, face=NUM, color=(0.62, 0.74, 1), alpha=0.85)
surf.flush()
res = Image.frombuffer("RGBA", (W, H), bytes(surf.get_data()), "raw", "BGRA", 0, 1).convert("RGB")
res.save("miniature_cardio_studio.jpg", quality=95)
res.crop((0, 240, 1080, 1680)).resize((540, 720)).save("miniature_studio_grille.jpg")
print("ok")
