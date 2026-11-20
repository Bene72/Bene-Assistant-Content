"""Optimise une photo SANS RIEN INVENTER (pas d'IA générative).

Retouche « photographe » uniquement : chaque pixel vient de la photo d'origine.
  1. débruitage léger (avant d'éclaircir, sinon le bruit des ombres ressort)
  2. tone mapping local : ombres débouchées, hautes lumières protégées (couche de base compressée)
  3. relief / clarté : micro-contraste renforcé (couche de détail amplifiée) — révèle ce qui existe, n'ajoute rien
  4. couleur : teinte conservée, légère chaleur et saturation douce
  5. agrandissement ×2 (Lanczos) + netteté sur la luminance seulement (pas de franges de couleur)
Interdit : changer le corps, la musculature, le visage, ajouter veines / définition / barbe, lisser la peau.

Usage : python optimise_photo.py entree.jpg sortie.jpg [--force 1.0] [--echelle 2]
  --force 0.5 = plus doux, 1.5 = plus marqué (éclaircissement + relief)
"""
import sys, argparse
import cv2
import numpy as np
from PIL import Image, ImageOps


def optimise(path, out, force=1.0, echelle=2):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    bgr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    # 1. débruitage léger
    bgr = cv2.fastNlMeansDenoisingColored(bgr, None, 3, 5, 7, 21)
    f = bgr.astype(np.float32) / 255.0
    lum = np.maximum(0.0722 * f[..., 0] + 0.7152 * f[..., 1] + 0.2126 * f[..., 2], 1e-4)
    logL = np.log(lum)
    # 2. couche de base (éclairage) lissée en préservant les bords
    base = cv2.bilateralFilter(logL, 0, 0.6, max(lum.shape) / 80)
    detail = logL - base
    # compression de la base : on débouche les tons moyens (le corps) mais on garde les noirs profonds
    b_lo = np.percentile(base, 8)
    b_hi = np.percentile(base, 99.5)
    t = np.clip((base - b_lo) / (b_hi - b_lo + 1e-6), 0, 1)
    lift = 0.55 * force * np.clip(np.sin(np.pi * t), 0, 1) ** 1.2   # max sur les tons moyens, ~0 sur les noirs et les blancs
    base2 = base + lift
    # 3. relief : détail amplifié (seulement là où il y a de la lumière, pour ne pas faire ressortir le bruit)
    logL2 = base2 + detail * (1 + 0.30 * force * t)
    L2 = np.exp(logL2)
    L2 = np.minimum(L2, 1.0)
    ratio = (L2 / lum)[..., None]
    f2 = np.clip(f * ratio, 0, 1)
    # 4. couleur : légère chaleur + saturation douce (teinte conservée)
    hsv = cv2.cvtColor((f2 * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 - 0.04 * force), 0, 255)
    f2 = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255.0
    
    # balance des blancs : on retire une partie de la dominante orange de l'éclairage (correction, pas invention)
    f2[..., 2] *= 1 - 0.05 * force   # rouge
    f2[..., 0] *= 1 + 0.04 * force   # bleu
    out8 = (np.clip(f2, 0, 1) * 255).astype(np.uint8)
    # 5. agrandissement + netteté luminance
    if echelle != 1:
        out8 = cv2.resize(out8, None, fx=echelle, fy=echelle, interpolation=cv2.INTER_LANCZOS4)
    lab = cv2.cvtColor(out8, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0]
    L = L + 0.8 * (L - cv2.GaussianBlur(L, (0, 0), 1.4 * echelle / 2))
    lab[..., 0] = np.clip(L, 0, 255)
    out8 = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)
    Image.fromarray(cv2.cvtColor(out8, cv2.COLOR_BGR2RGB)).save(out, quality=95, subsampling=0)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("entree")
    ap.add_argument("sortie")
    ap.add_argument("--force", type=float, default=1.0)
    ap.add_argument("--echelle", type=float, default=2)
    a = ap.parse_args()
    print("ok", optimise(a.entree, a.sortie, a.force, a.echelle))
