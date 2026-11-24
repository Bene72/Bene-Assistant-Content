"""Habillage texte du Reel canapé (hook + textes calés sur les actions), posé sur la vidéo déjà rendue.
Style sous-titres BEN&FIT : Coda blanc bord bleu, mots-clés dans un bloc bleu, tiers haut de l'écran
(le bas est pris par le carrousel et l'interface Instagram).   python textes_canape.py"""
import os, sys, subprocess
import numpy as np
import cairo
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

WORK = os.environ.get("WORK", "/home/claude/run/canape")
W, H, FPS = 1080, 1920, 30
STROKE = (0.08, 0.30, 0.92)
# (début, fin, lignes) en secondes de la vidéo finale ; *mot* = mot-clé dans le bloc bleu
TEXTES = [
    (0.00, 1.20, ["POV : t'as *pas envie*", "d'aller à la salle"]),        # hook
    (1.25, 6.25, ["Bon… juste un", "petit truc *léger*"]),               # carrousel
    (6.30, 6.95, ["…*ah.*"]),                                            # le carrousel s'arrête sur l'arraché
    (6.97, 7.80, ["Le corps a *décidé*", "tout seul"]),                  # claquement
    (8.58, 11.85, ["*Trop tard.*"]),                                     # clap → mur
    (11.90, 15.00, ["Une fois dans", "la *spirale*…"]),                  # tornade
    (15.00, 17.46, ["…t'en sors *plus.*"]),                              # il avance vers la caméra
]
Y0, SIZE, INTERLIGNE = 330, 76, 96


def draw(c, T):
    for a, b, lignes in TEXTES:
        if a <= T < b:
            break
    else:
        return
    sc = 0.92 + 0.08 * E.eo((T - a) / 0.1)
    c.save()
    c.translate(W / 2, Y0)
    c.scale(sc, sc)
    c.translate(-W / 2, -Y0)
    E.font(c, E.SANS_B, SIZE)
    for k, ligne in enumerate(lignes):
        y = Y0 + k * INTERLIGNE
        # morceaux alternés normal / mot-clé : « POV : t'as *pas envie* » → [« POV : t'as  », « pas envie »]
        morceaux = [(m, j % 2 == 1) for j, m in enumerate(ligne.split("*")) if m]
        pad = SIZE * 0.18
        larg = [c.text_extents(m).x_advance + (2 * pad if key else 0) for m, key in morceaux]
        x = W / 2 - sum(larg) / 2
        for (m, key), w in zip(morceaux, larg):
            if key:
                E.rrect(c, x, y - SIZE * 0.80, w, SIZE * 1.05, 10)
                c.set_source_rgba(*E.BLUE, 1)
                c.fill()
            c.move_to(x + (pad if key else 0), y)
            c.text_path(m)
            if not key:
                c.set_source_rgba(*STROKE, 1)
                c.set_line_width(10)
                c.set_line_join(cairo.LINE_JOIN_ROUND)
                c.stroke_preserve()
            c.set_source_rgba(1, 1, 1, 1)
            c.fill()
            x += w
    c.restore()


def main(only=None):
    src = os.path.join(WORK, "v.mp4")
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", "scale=in_color_matrix=bt709:in_range=tv",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    if only is None:
        out = os.path.join(WORK, "v_textes.mp4")
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-vf",
                               "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
                               "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high",
                               "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                               "-color_range", "tv", out], stdin=subprocess.PIPE)
    i = 0
    while True:
        b = rd.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        T = i / FPS
        if only is None or any(abs(T - t) < 0.5 / FPS for t in only):
            cv = E.Canvas(np.frombuffer(b, np.uint8).reshape(H, W, 3).copy())
            cv.draw(lambda c: draw(c, T))
            f = cv.out()
            if only is None:
                wr.stdin.write(f.tobytes())
            else:
                from PIL import Image
                Image.fromarray(f).resize((360, 640)).save(os.path.join(WORK, f"tx_{T:05.2f}.png"))
        i += 1
    if only is None:
        wr.stdin.close()
        wr.wait()
        final = os.path.join(WORK, "BENFIT_reel_canape_textes.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "son.wav"), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", final], check=True)
        print("ok", final)


if __name__ == "__main__":
    main([float(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None)
