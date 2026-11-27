"""Animation de logos BEN&FIT × Apocalypse Training, style clip de rap, 5 s, fond transparent (27 nov. 2026).

  0,0–0,4  BEN&FIT tombe (gros zoom qui rétrécit, flou de vitesse) → impact : tremblement + décalage RVB
  0,4–1,6  deux « bumps » de zoom sur le temps + petits glitchs (tranches décalées)
  1,6–2,1  BEN&FIT part en tourbillon (rotation + spirale) et disparaît
  2,1–2,6  APOCALYPSE sort du tourbillon
  2,6–3,6  bumps + glitchs
  3,6–4,4  fusion : les deux logos côte à côte qui claquent ensemble, « × » au milieu
  4,4–5,0  tout repart en tourbillon et disparaît
Logos : contenu/logos/benfit.png et apocalypse-training.png (fonds transparents).

Sorties ($WORK) : logo_anim.mov (ProRes 4444 avec transparence), logo_anim.webm (VP9 avec transparence),
logo_anim_fond_vert.mp4 (fond vert pour l'incrustation « chroma key » de CapCut).
  python logo_anim.py [stills T…]
"""
import os, sys, math, subprocess
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LOGOS = os.path.join(HERE, "..", "..", "..", "logos")
WORK = os.environ.get("WORK", "/home/claude/run/logo")
W, H, FPS, DUR = 1080, 1920, 30, 5.0


def load(name, w):
    im = Image.open(os.path.join(LOGOS, name)).convert("RGBA")
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]                      # prémultiplié
    return a


BEN = load("benfit.png", 760)
APO = load("apocalypse-training.png", 700)
BEN_S = load("benfit.png", 430)
APO_S = load("apocalypse-training.png", 400)


def eo(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def place(canvas, layer, cx, cy, scale=1.0, rot=0.0, alpha=1.0, swirl=0.0, blur=0):
    """Pose un logo (RGBA prémultiplié) sur le canevas, avec échelle, rotation, tourbillon et flou radial."""
    if alpha <= 0.002 or scale <= 0.01:
        return
    h, w = layer.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
    M[:, 2] += (cx - w / 2, cy - h / 2)
    img = cv2.warpAffine(layer, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    if abs(swirl) > 0.01:                         # spirale : angle qui augmente vers le centre
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dx, dy = xx - cx, yy - cy
        r = np.sqrt(dx * dx + dy * dy)
        R = max(w, h) * scale * 0.75 + 1
        th = swirl * np.clip(1 - r / R, 0, 1) ** 2
        c, s = np.cos(th), np.sin(th)
        img = cv2.remap(img, cx + c * dx - s * dy, cy + s * dx + c * dy, cv2.INTER_LINEAR,
                        borderValue=(0, 0, 0, 0))
    if blur > 1:                                  # flou de vitesse radial (zoom)
        acc = np.zeros_like(img)
        for k in range(6):
            s = 1 + blur * 0.004 * k
            Mz = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
            acc += cv2.warpAffine(img, Mz, (W, H), borderValue=(0, 0, 0, 0))
        img = acc / 6
    canvas[:] = canvas * (1 - img[..., 3:4] * alpha) + img * alpha


def rgb_split(c, d):
    d = int(round(d))
    if d <= 0:
        return c
    out = c.copy()
    out[..., 0] = np.roll(c[..., 0], d, axis=1)
    out[..., 2] = np.roll(c[..., 2], -d, axis=1)
    out[..., 3] = np.maximum(np.maximum(np.roll(c[..., 3], d, axis=1), np.roll(c[..., 3], -d, axis=1)), c[..., 3])
    return out


def glitch(c, t, seed):
    """Quelques tranches horizontales décalées (1–2 images)."""
    rng = np.random.default_rng(seed)
    out = c.copy()
    for _ in range(rng.integers(3, 7)):
        y = int(rng.integers(500, 1400))
        h = int(rng.integers(12, 70))
        out[y:y + h] = np.roll(c[y:y + h], int(rng.integers(-60, 60)), axis=1)
    return out


def bump(t, t0):
    """Petit coup de zoom sur un temps (1 → 1,09 → 1 en 0,25 s)."""
    u = (t - t0) / 0.25
    return 0.09 * math.sin(math.pi * u) if 0 <= u <= 1 else 0.0


def frame(t):
    c = np.zeros((H, W, 4), np.float32)
    cx, cy = W / 2, H / 2
    shake = (0, 0)
    split = 0
    gl = None
    # --- BEN&FIT
    if t < 2.1:
        if t < 0.4:
            u = eo(t / 0.4)
            s, blur, a = 2.6 - 1.6 * u, 40 * (1 - u), min(1, t / 0.12)
        elif t < 1.6:
            s = 1.0 + bump(t, 0.75) + bump(t, 1.15)
            blur, a = 0, 1
        else:
            u = (t - 1.6) / 0.5
            s, blur, a = 1.0 - 0.9 * eo(u), 0, 1 - u ** 3
        sw = 0 if t < 1.6 else 9 * eo((t - 1.6) / 0.5)
        rot = 0 if t < 1.6 else -220 * eo((t - 1.6) / 0.5)
        place(c, BEN, cx, cy, s, rot, a, sw, blur)
        if 0.4 <= t < 0.62:
            k = 1 - (t - 0.4) / 0.22
            shake = (int(24 * k * math.sin(t * 160)), int(18 * k * math.cos(t * 130)))
            split = 22 * k
        if 1.0 <= t < 1.08 or 1.38 <= t < 1.44:
            gl = int(t * 100)
    # --- APOCALYPSE
    if 2.0 <= t < 3.6:
        if t < 2.6:
            u = eo((t - 2.0) / 0.6)
            s, a, sw, rot = 0.15 + 0.85 * u, min(1, (t - 2.0) / 0.2), -9 * (1 - u), 220 * (1 - u)
        else:
            s, a, sw, rot = 1.0 + bump(t, 2.85) + bump(t, 3.25), 1, 0, 0
        place(c, APO, cx, cy, s, rot, a, sw)
        if 2.6 <= t < 2.8:
            k = 1 - (t - 2.6) / 0.2
            shake = (int(20 * k * math.sin(t * 150)), int(14 * k * math.cos(t * 120)))
            split = 18 * k
        if 3.0 <= t < 3.07 or 3.45 <= t < 3.5:
            gl = int(t * 100)
    # --- fusion : les deux ensemble
    if t >= 3.6:
        if t < 3.9:
            u = eo((t - 3.6) / 0.3)
            off, s, a = 700 * (1 - u), 1.0, min(1, (t - 3.6) / 0.1)
        elif t < 4.4:
            off, s, a = 0, 1.0 + bump(t, 4.05) * 0.8, 1
        else:
            u = (t - 4.4) / 0.6
            off, s, a = 0, 1.0 - 0.95 * eo(u), 1 - u ** 2
        sw = 0 if t < 4.4 else 10 * eo((t - 4.4) / 0.6)
        rot = 0 if t < 4.4 else -260 * eo((t - 4.4) / 0.6)
        gap = 285 * s
        place(c, BEN_S, cx - gap - off, cy, s, rot, a, sw)
        place(c, APO_S, cx + gap + off, cy, s, rot, a, sw)
        if t < 4.4:                                # « × » au centre
            ax = np.zeros((H, W, 4), np.float32)
            L = int(46 * s)
            for d in (1, -1):
                cv2.line(ax, (int(cx - L), int(cy - d * L)), (int(cx + L), int(cy + d * L)), (1, 1, 1, 1), 12,
                         cv2.LINE_AA)
            ka = a * min(1, max(0, (t - 3.85) / 0.1))
            c[:] = c * (1 - ax[..., 3:4] * ka) + ax * ka
        if 3.9 <= t < 4.1:
            k = 1 - (t - 3.9) / 0.2
            shake = (int(26 * k * math.sin(t * 170)), int(20 * k * math.cos(t * 140)))
            split = 24 * k
    if shake != (0, 0):
        c = np.roll(c, shake, axis=(1, 0))
    c = rgb_split(c, split)
    if gl is not None:
        c = glitch(c, t, gl)
    return np.clip(c, 0, 1)


def render():
    n = int(DUR * FPS)
    rgba = os.path.join(WORK, "anim_rgba.raw")
    with open(rgba, "wb") as f:
        for i in range(n):
            c = frame(i / FPS)
            a = c[..., 3:4]
            straight = np.where(a > 1e-4, c[..., :3] / np.maximum(a, 1e-4), 0)   # dé-prémultiplier
            f.write((np.dstack([straight, a]) * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
    inp = ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", rgba]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-c:v", "prores_ks", "-profile:v", "4444",
                    "-pix_fmt", "yuva444p10le", "-vendor", "apl0", os.path.join(WORK, "logo_anim.mov")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0",
                    "-crf", "18", "-row-mt", "1", "-auto-alt-ref", "0", os.path.join(WORK, "logo_anim.webm")],
                   check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x00FF00:s={W}x{H}:r={FPS}:d={DUR}",
                    *inp, "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p", "-c:v", "libx264",
                    "-crf", "12", "-preset", "slow", os.path.join(WORK, "logo_anim_fond_vert.mp4")], check=True)
    os.remove(rgba)
    print("ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        ts = [float(x) for x in sys.argv[2:]]
        tiles = []
        for t in ts:
            c = frame(t)
            bg = np.zeros((H, W, 3), np.float32)
            bg[(np.indices((H, W)).sum(0) // 60) % 2 == 0] = 0.25
            bg += 0.12
            out = bg * (1 - c[..., 3:4]) + c[..., :3]
            tiles.append(Image.fromarray((out * 255).astype(np.uint8)).resize((270, 480)))
        o = Image.new("RGB", (270 * len(tiles), 480))
        for i, t_ in enumerate(tiles):
            o.paste(t_, (i * 270, 0))
        o.save(os.path.join(WORK, "anim_stills.jpg"))
    else:
        render()
