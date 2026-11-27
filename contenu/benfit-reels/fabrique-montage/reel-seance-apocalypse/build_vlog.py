"""Version « vlog » de la séance × Apocalypse, à partir du MONTAGE DE BENE (27 nov. 2026).

Demande de Bene : garder son montage (côté vlog, propre, pas spectaculaire), AUCUN texte, et seulement :
  1. accroche = son selfie « sponsorisé par Apocalypse » en premier ;
  2. le long plan d'arraché (26 s) resserré sur 2 répétitions ;
  3. ~70 s au total ;
  + 3 transitions « néon orange » (filet de lumière orange qui balaie, léger flou de mouvement) avec bruitages
    (whoosh + petit impact grave). Orange = demande explicite de Bene pour ces transitions (hors palette habituelle).
Image d'origine plein cadre 1440×2560, aucun zoom / ralenti / étalonnage. Son d'origine de chaque plan, fondus de 15 ms.

  python build_vlog.py [stills T…]      ($SRC = montage de Bene, $WORK = sortie)
"""
import os, sys, subprocess, math, re, wave
import numpy as np
import cv2

SRC = os.environ.get("SRC", "/home/claude/run/ref/bene.mp4")
WORK = os.environ.get("WORK", "/home/claude/run/ref")
W, H, FPS = 1440, 2560, 30

# Morceaux du montage de Bene (temps source, s), dans l'ordre de la nouvelle version
SEG = [
    (84.10, 85.62),   # accroche : selfie « …sponsorisé par Apocalypse »
    (0.00, 4.40),     # échauffement au sol
    (6.77, 10.60),    # passages d'épaules
    (11.70, 24.60),   # Apocalypse : arraché (+ « je me suis arraché… »)
    (28.00, 33.60),   # Bene : arraché depuis le sol (1re rep gardée)
    (42.40, 46.60),   # Bene : 2e rep gardée
    (51.30, 57.10),   # autre plateau
    (59.30, 84.10),   # épaulés-jetés des deux + « tu viens à moi à la caméra »
    (86.47, 90.50),   # renfort : rowing
    (93.33, 95.70),   # rowing (autre angle)
]
TRANSITIONS = [1, 6, 8]   # transition néon AVANT le morceau d'indice i (hook→échauffement, changement de plateau, renfort)
TR = 0.42                 # durée d'une transition (s), centrée sur la coupe


def starts():
    t, out = 0.0, []
    for a, b in SEG:
        out.append(t)
        t += b - a
    return out, t


def decode(a, b):
    """Images une par une (un plan de 25 s en 1440×2560 ne tient pas en mémoire)."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-i", SRC, "-t", f"{b - a:.3f}", "-vf",
                          f"fps={FPS},scale={W}:{H}:in_color_matrix=bt709:in_range=tv:flags=lanczos+accurate_rnd+full_chroma_int",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n, sz, last = int(round((b - a) * FPS)), W * H * 3, None
    for _ in range(n):
        x = p.stdout.read(sz)
        if len(x) == sz:
            last = np.frombuffer(x, np.uint8).reshape(H, W, 3)
        yield last
    p.stdout.close()
    p.wait()


ORANGE = np.array([255, 110, 20], np.float32)
CORE = np.array([255, 225, 190], np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def neon(frame, u):
    """u de -1 à 1 (0 = la coupe). Filet néon orange en diagonale qui traverse l'écran + lueur + flou léger."""
    p = (u + 1) / 2                                   # 0 → 1
    pos = -0.3 * W + p * 1.6 * W                      # position du filet (gauche → droite)
    d = (xx - pos) + (yy - H / 2) * 0.35              # diagonale
    core = np.exp(-(d / 10) ** 2)                     # trait fin et vif
    glow = np.exp(-(d / 120) ** 2) * 0.55             # lueur autour
    wash = np.exp(-(d / 520) ** 2) * 0.18 * (1 - abs(u))   # léger voile orange près de la coupe
    k = int(26 * (1 - abs(u)))                        # flou de mouvement horizontal, max à la coupe
    f = frame.astype(np.float32)
    if k > 1:
        f = cv2.blur(f, (k, 1))
    f = f * (1 - wash[..., None]) + ORANGE * wash[..., None]
    f = f + ORANGE * glow[..., None]
    f = f * (1 - core[..., None]) + CORE * core[..., None]
    return np.clip(f, 0, 255).astype(np.uint8)


def render(only=None):
    st, total = starts()
    cuts = [st[i] for i in TRANSITIONS]
    for i, (a, b) in enumerate(SEG):
        n = int(round((b - a) * FPS))
        idx = [k for k in range(n) if only is None or any(abs(st[i] + k / FPS - T) < 0.5 / FPS for T in only)]
        if not idx:
            continue
        want = set(idx)
        for k, f in enumerate(decode(a, b)):
            if k not in want:
                continue
            T = st[i] + k / FPS
            for c in cuts:
                if abs(T - c) < TR / 2:
                    f = neon(f, (T - c) / (TR / 2))
            yield T, f


def whoosh(sr, dur=0.5, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    x = rng.standard_normal(n).astype(np.float32)
    # bruit filtré dont la brillance monte puis redescend (passe-bas glissant)
    y, s = np.zeros(n, np.float32), 0.0
    for i in range(n):
        u = i / n
        a = 0.015 + 0.35 * math.sin(math.pi * u) ** 2
        s += a * (x[i] - s)
        y[i] = s
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    y = y * env
    return y / (np.abs(y).max() + 1e-9)


def impact(sr, dur=0.35):
    t = np.arange(int(dur * sr)) / sr
    f = 70 * np.exp(-t * 6) + 42
    y = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 11)
    return (y / np.abs(y).max()).astype(np.float32)


def audio():
    st, total = starts()
    SR = 48000
    buf = np.zeros(int((total + 0.5) * SR), np.float32)
    for i, (a, b) in enumerate(SEG):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", SRC, "-af",
                              f"pan=mono|c0=0.5*c0+0.5*c1,aresample={SR}", "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).copy()
        f = int(0.015 * SR)
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
        j = int(st[i] * SR)
        buf[j:j + len(x)] += x[:len(buf) - j]
    # niveau de l'ambiance d'origine mesuré, bruitages posés un peu en dessous
    ref = float(np.sqrt(np.mean(buf ** 2)) + 1e-9)
    fx = np.zeros_like(buf)
    for k, i in enumerate(TRANSITIONS):
        c = st[i]
        w = whoosh(SR, 0.5, seed=k) * ref * 4.0
        j = int((c - 0.30) * SR)
        fx[j:j + len(w)] += w
        im = impact(SR) * ref * 3.2
        j = int(c * SR)
        fx[j:j + len(im)] += im
    mix = buf + fx
    tmp = os.path.join(WORK, "vlog_mix_raw.wav")
    with wave.open(tmp, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix / max(1.0, np.abs(mix).max()), -1, 1) * 32767).astype(np.int16).tobytes())
    m = subprocess.run(["ffmpeg", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", m)[-1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    f"pan=stereo|c0=0.708*c0|c1=0.708*c0,volume={-14 - I + 3:.2f}dB,alimiter=limit=0.89:level=false",
                    "-ar", str(SR), os.path.join(WORK, "vlog_mix.wav")], check=True)


def video():
    out = os.path.join(WORK, "vlog_v.mp4")
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-vf",
                           "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high", "-tune", "film",
                           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                           "-color_range", "tv", out], stdin=subprocess.PIPE)
    for _, f in render():
        wr.stdin.write(np.ascontiguousarray(f).tobytes())
    wr.stdin.close()
    wr.wait()
    audio()
    final = os.path.join(WORK, "BENFIT_x_APOCALYPSE_vlog.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "vlog_mix.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("ok", final, round(starts()[1], 2), "s")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        from PIL import Image
        for T, f in render(only=[float(x) for x in sys.argv[2:]]):
            Image.fromarray(f).resize((360, 640)).save(os.path.join(WORK, f"vl_{T:05.2f}.png"))
    else:
        video()
