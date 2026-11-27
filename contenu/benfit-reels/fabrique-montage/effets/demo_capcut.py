"""Démo du lot « modèles CapCut » (27 nov. 2026) sur les rushs de la séance avec Apocalypse (26 nov.).

Usage : python demo_capcut.py [--stills]   (RUSH = dossier des rushs VID_20261126_*, WORK = sortie)
Rend une vidéo ~25 s : chaque effet ~2 s avec son nom en haut ; --stills : une image par effet dans apercus/.
"""
import os, sys, subprocess, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import effets as E
import segmentation

W, H, FPS = E.W, E.H, 30
RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/fx")
HERE = os.path.dirname(os.path.abspath(__file__))
R = lambda n: os.path.join(RUSH, f"VID_20261126_{n}.mp4")


def dec(clip, a, dur, size=(W, H)):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(a), "-i", R(clip), "-t", str(dur), "-vf",
                          f"fps={FPS},scale={size[0]}:{size[1]}:in_color_matrix=bt709:flags=lanczos", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    fs, sz = [], size[0] * size[1] * 3
    while True:
        b = p.stdout.read(sz)
        if len(b) < sz:
            break
        fs.append(np.frombuffer(b, np.uint8).reshape(size[1], size[0], 3))
    return fs


def label(f, txt):
    cv = E.Canvas(f)

    def d(c):
        E.font(c, E.SANS_B, 40)
        tw = c.text_extents(txt).x_advance
        E.rrect(c, W / 2 - tw / 2 - 20, 150, tw + 40, 64, 10)
        c.set_source_rgba(*E.NAVY, 0.92)
        c.fill()
        c.move_to(W / 2 - tw / 2, 196)
        c.set_source_rgba(1, 1, 1, 1)
        c.show_text(txt)
    cv.draw(d)
    return cv.out()


def scenes():
    """(nom, liste d'images) pour chaque effet."""
    out = []
    # 1. zoom flou : arraché Bene → arraché Apocalypse
    a, b = dec("144615", 31.6, 1.0), dec("144752", 25.2, 1.0)
    fr = [E.tr_zoom_flou(a[min(i, len(a) - 1)], b[min(i, len(b) - 1)], i / 9) for i in range(10)]
    out.append(("01 · Zoom flou (transition)", a[:20] + fr + b[10:30]))
    # 2. décalage RVB sur la réception
    a = dec("151817", 59.0, 1.6)
    fr = [E.fx_rgb(f, max(0, 1 - abs(i - 10) / 4)) for i, f in enumerate(a)]
    out.append(("02 · Décalage RVB (temps fort)", fr))
    # 3. éclats de miroir
    a = dec("145519", 14.6, 1.8)
    fr = [E.fx_eclats(f, i / FPS, E.eo(min(1, i / 6)) * (1 - E.clamp((i - 40) / 8))) for i, f in enumerate(a)]
    out.append(("03 · Éclats de miroir", fr))
    # 4. zoom à travers les cadres
    a, b = dec("151407", 39.0, 1.0), dec("151631", 62.6, 1.2)
    n = 26
    fr = [E.tr_cadres(a[min(i, len(a) - 1)], b[min(i, len(b) - 1)], i / (n - 1)) for i in range(n)]
    out.append(("04 · Zoom à travers les cadres", a[:12] + fr + b[12:30]))
    # 5, 6, 7, 8 : effets avec détourage (prise où Bene est seul, plan large)
    a = dec("151817", 58.3, 2.2)
    masks = [segmentation.mask(f) for f in a]
    fr = [E.fx_fond_noir(f, m, E.eio(min(1, i / 8)) * (1 - E.clamp((i - 52) / 10))) for i, (f, m) in
          enumerate(zip(a, masks))]
    out.append(("05 · Fond noir", fr))
    fr = [E.fx_echo(a[:i + 1], masks[:i + 1]) for i in range(len(a))]
    out.append(("06 · Écho fantôme", fr))
    fr = [E.fx_clones(f, m, dx=int(330 * E.eo(min(1, i / 10)))) for i, (f, m) in enumerate(zip(a, masks))]
    out.append(("07 · Clones", fr))
    fr = []
    for i, (f, m) in enumerate(zip(a, masks)):
        cv = E.Canvas(f.copy())
        E.fx_texte_echo(cv, m, i / FPS, mot="BEN&FIT", y=760, size=210)
        fr.append(cv.out())
    out.append(("08 · Texte écho derrière", fr))
    fr = [E.fx_titre_sol(f, m, i / FPS, mot="ÉPAULÉ-JETÉ", y_sol=1560, hauteur=220) for i, (f, m) in
          enumerate(zip(a, masks))]
    out.append(("09 · Titre géant dans le décor", fr))
    # 10. mosaïque inclinée
    med = [dec(c, s, 2.0, size=(300, 533)) for c, s in (("144615", 31.5), ("144752", 25.0), ("151817", 53.0),
                                                        ("151631", 51.0), ("145519", 14.5), ("155452", 5.0),
                                                        ("151407", 39.0))]
    fr = [E.fx_mosaique(med, i / FPS) for i in range(60)]
    out.append(("10 · Mosaïque inclinée", fr))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", action="store_true")
    args = ap.parse_args()
    sc = scenes()
    if args.stills:
        from PIL import Image
        os.makedirs(os.path.join(HERE, "apercus"), exist_ok=True)
        for nom, fr in sc:
            f = label(fr[len(fr) // 2], nom)
            slug = nom.split("·")[1].strip().lower().replace(" ", "-").replace("é", "e").replace("è", "e") \
                .replace("à", "a").replace("ô", "o").replace("ï", "i").replace("(", "").replace(")", "")
            Image.fromarray(f).resize((540, 960)).save(os.path.join(HERE, "apercus", f"capcut-{slug}.jpg"), quality=85)
    else:
        out = os.path.join(WORK, "demo_capcut.mp4")
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709,format=yuv420p",
                               "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                               "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", out],
                              stdin=subprocess.PIPE)
        for nom, fr in sc:
            for f in fr:
                wr.stdin.write(label(f, nom).tobytes())
        wr.stdin.close()
        wr.wait()
        print("ok", out)
