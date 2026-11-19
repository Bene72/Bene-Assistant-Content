"""Démo de tous les effets verre sur un rush de Bene (pour vérifier le rendu après une modification).

Usage : python demo.py RUSH.mp4 [sortie.mp4] [--debut 2.6] [--stills]
  --debut : seconde du rush où Bene est en place (on saute l'installation de la caméra)
  --stills : rend seulement 2 images par effet (apercus/), sans vidéo
Prérequis : pip install pycairo numpy pillow ; polices de contenu/polices/ installées ; ffmpeg.
"""
import sys, os, subprocess, tempfile, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import effets as E

W, H, FPS = E.W, E.H, 30
ORDER = ["toggles", "graphe", "focus", "preuve", "matchcut", "eventail", "epaule"]
NAMES = {"toggles": "Interrupteurs", "graphe": "Graphe en verre", "focus": "Liste focus",
         "preuve": "Carte preuve", "matchcut": "Match-cut", "eventail": "Cartes en éventail",
         "epaule": "Pastilles épaule"}
GAP = 0.6


def build_timeline():
    tl, t0 = [], 0.4
    for k in ORDER:
        fn, d = E.EFFETS[k]
        tl.append((k, fn, t0, d))
        t0 += d + GAP
    return tl, t0


def label(cv, name, idx, a):
    def f(c):
        s = f"{idx:02d} · {name}"
        E.font(c, E.SANS_B, 34)
        w = c.text_extents(s).x_advance + 48
        E.rrect(c, 60, 150, w, 66, 33)
        c.set_source_rgba(*E.DEEP, 0.55 * a)
        c.fill()
        E.text(c, s, 84, 195, E.SANS_B, 34, E.WHITE, a)
    cv.draw(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rush")
    ap.add_argument("sortie", nargs="?", default="demo_effets.mp4")
    ap.add_argument("--debut", type=float, default=2.6)
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()

    raw = os.path.join(tempfile.gettempdir(), "plate_effets.raw")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.debut), "-i", a.rush, "-t", "14",
                    "-vf", f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", raw], check=True)
    plate = np.memmap(raw, np.uint8, "r").reshape(-1, H, W, 3)
    tl, dur = build_timeline()

    def frame(T):
        k, s0 = 0, 0.0
        for i, (_, _, s, d) in enumerate(tl):
            if T >= s - GAP / 2:
                k, s0 = i, s - GAP / 2
        local = (k * 4.1) % 7.5 + (T - s0)
        cv = E.Canvas(np.array(plate[min(int(local * FPS), plate.shape[0] - 1)]))
        for i, (key, fn, s, d) in enumerate(tl):
            if s - 0.1 <= T <= s + d + 0.1:
                fn(cv, T - s)
                label(cv, NAMES[key], i + 1, E.env(T - s, d, 0.2, 0.2))
        return cv.out()

    if a.stills:
        from PIL import Image
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apercus")
        os.makedirs(out, exist_ok=True)
        for key, fn, s, d in tl:
            Image.fromarray(frame(s + d * 0.9)).resize((540, 960)).save(f"{out}/{key}.jpg", quality=82)
        return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                          "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.sortie], stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print("ok", a.sortie, round(dur, 1), "s")


if __name__ == "__main__":
    main()
