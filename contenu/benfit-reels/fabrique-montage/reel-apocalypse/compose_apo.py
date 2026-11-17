"""Reel BEN&FIT x Apocalypse Training — compositing (reel d'entraînement, DA v2 naturelle).
Base étalonnée (build_base_apo.py) + punch-in par plan + intro co-branding + titre Anton + chips d'exercices
+ logos discrets en coin + carte de fin. Écrit video_apo_nosound.mp4 et events_apo.json (bruitages)."""
import sys, math, json, random, subprocess, os
import numpy as np, cairo
import PIL.Image as PImage

W, H, FPS = 1080, 1920, 30
D = json.load(open("/home/claude/work/apo/timeline.json"))
TL = D["timeline"]; BASE_DUR = D["total"]
HOLD = 1.3
DUR = BASE_DUR + HOLD
WHITE = (1, 1, 1); BLUE = (0.18, 0.42, 1.0); BLUE2 = (0.55, 0.72, 1.0); NAVY = (0.04, 0.125, 0.42)
STROKE = (0.08, 0.30, 0.92)
FONT = "Coda ExtraBold"; NUM = "Anton"; MARK = "Permanent Marker"; SERIF = "Liberation Serif"
EV = []; _seen = set()
def ev(key, t, kind):
    if key not in _seen: _seen.add(key); EV.append((t, kind))

clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 3 * x * x - 2 * x * x * x

def font(ctx, size, face=FONT, italic=False):
    ctx.select_font_face(face, cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if face == SERIF else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
_cap = {}
def cap_h(ctx, size, face, italic=False):
    k = (size, face, italic)
    if k not in _cap: font(ctx, size, face, italic); _cap[k] = ctx.text_extents("H")[3]
    return _cap[k]
def tw(ctx, s, size, face=FONT, italic=False):
    font(ctx, size, face, italic); return ctx.text_extents(s)[4]
def text(ctx, s, x, y, size, face=FONT, color=WHITE, alpha=1.0, anchor="c", stroke=None, sw=0, shadow=0.0, italic=False):
    font(ctx, size, face, italic)
    adv = ctx.text_extents(s)[4]; ch = cap_h(ctx, size, face, italic)
    x0 = x - adv / 2 if anchor == "c" else (x if anchor == "l" else x - adv)
    yb = y + ch / 2
    def path(): ctx.move_to(x0, yb); ctx.text_path(s)
    if shadow:
        ctx.save(); ctx.translate(0, 5); path(); ctx.set_source_rgba(0, 0, 0, shadow * alpha); ctx.fill(); ctx.restore()
    if stroke:
        path(); ctx.set_source_rgba(*stroke, alpha); ctx.set_line_width(sw); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke()
    path(); ctx.set_source_rgba(*color, alpha); ctx.fill()
    return adv
def rrect(ctx, x, y, w, h, r):
    r = min(r, h / 2, w / 2)
    ctx.new_sub_path(); ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); ctx.close_path()
def chip(ctx, s, x, y, size, fill=BLUE, color=WHITE, alpha=1.0, padx=18, pady=12, anchor="l", wipe=1.0):
    adv = tw(ctx, s, size); ch = cap_h(ctx, size, FONT)
    w, h = adv + 2 * padx, ch + 2 * pady
    x0 = x if anchor == "l" else (x - w / 2 if anchor == "c" else x - w)
    if wipe < 1: ctx.save(); ctx.rectangle(x0, y - h / 2 - 2, w * wipe, h + 4); ctx.clip()
    ctx.save(); rrect(ctx, x0, y - h / 2 + 5, w, h, 10); ctx.set_source_rgba(0, 0, 0, 0.25 * alpha); ctx.fill(); ctx.restore()
    rrect(ctx, x0, y - h / 2, w, h, 10); ctx.set_source_rgba(*fill, alpha); ctx.fill()
    text(ctx, s, x0 + w / 2, y, size, color=color, alpha=alpha)
    if wipe < 1: ctx.restore()
    return w, x0
rnd = random.Random(3); JIT = [rnd.uniform(-1, 1) for _ in range(400)]
def marker_path(ctx, pts, prog, width, color, alpha=1.0):
    if prog <= 0 or alpha <= 0: return
    n = max(2, int(len(pts) * clamp(prog)))
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for p, (w, a) in enumerate([(width, 0.9), (width * 0.55, 0.5)]):
        ctx.move_to(pts[0][0] + JIT[p], pts[0][1] + JIT[p + 1])
        for i, (x, y) in enumerate(pts[1:n]):
            ctx.line_to(x + JIT[(i + p * 7) % 400] * 1.2, y + JIT[(i * 3 + p) % 400] * 1.2)
        ctx.set_line_width(w); ctx.set_source_rgba(*color, a * alpha); ctx.stroke()
    ctx.restore()
def underline_pts(x0, x1, y):
    return [(x0 + (x1 - x0) * u, y + 5 * math.sin(u * 3.2) - 6 * u) for u in np.linspace(0, 1, 40)]
def win(T, t0, t1, fin=0.25, fout=0.25):
    if T < t0 or T > t1 + fout: return 0.0
    return eo((T - t0) / fin) * (1 - eio((T - t1) / fout))

# ---------------------------------------------------------------- logos
def load_logo(path):
    im = PImage.open(path).convert("RGBA"); a = np.asarray(im).astype(np.float32); al = a[..., 3:4] / 255
    bgra = np.concatenate([a[..., 2:3] * al, a[..., 1:2] * al, a[..., 0:1] * al, a[..., 3:4]], 2).astype(np.uint8)
    h, w = bgra.shape[:2]
    return cairo.ImageSurface.create_for_data(bytearray(np.ascontiguousarray(bgra).tobytes()), cairo.FORMAT_ARGB32, w, h, w * 4)
L_BEN = load_logo("/home/claude/work/apo/logo_benfit.png")
L_APO = load_logo("/home/claude/work/apo/logo_apo.png")
def logo(ctx, surf, cx, cy, size, a):
    if a <= 0: return
    w, h = surf.get_width(), surf.get_height(); s = size / max(w, h)
    ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s); ctx.set_source_surface(surf, -w / 2, -h / 2)
    ctx.get_source().set_filter(cairo.FILTER_BEST); ctx.paint_with_alpha(a); ctx.restore()
def cobrand(ctx, cx, cy, size, a, gap=0.62):
    logo(ctx, L_BEN, cx - size * gap, cy, size, a)
    logo(ctx, L_APO, cx + size * gap, cy, size * 0.98, a)
    text(ctx, "×", cx, cy, size * 0.32, alpha=a)

# ---------------------------------------------------------------- timings (temps de sortie)
def sec_range(*names):
    seg = [p for p in TL if p["sec"] in names]
    return seg[0]["start"], seg[-1]["start"] + seg[-1]["dur"]
HOOK = sec_range("hook"); HSPU = sec_range("hspu"); KB = sec_range("kb"); ROW = sec_range("row")
PULL = sec_range("pull"); PLATE = sec_range("plate"); END_T = sec_range("end")[0]
INTRO_END = 0.85
TITLE = (0.70, HOOK[1] - 0.1)

# ---------------------------------------------------------------- intro co-branding (< 1 s)
def legib_grad(ctx, a, y0, y1, k=0.6):
    g = cairo.LinearGradient(0, y0, 0, y1); g.add_color_stop_rgba(0, *NAVY, 0); g.add_color_stop_rgba(0.55, *NAVY, k); g.add_color_stop_rgba(1, *NAVY, 0)
    ctx.save(); ctx.rectangle(0, y0, W, y1 - y0); ctx.clip(); ctx.set_source(g); ctx.paint_with_alpha(a); ctx.restore()

def draw_intro(ctx, T):
    if T > INTRO_END + 0.15: return
    a = eo(T / 0.12) * (1 - eio((T - INTRO_END) / 0.15))
    legib_grad(ctx, a, 1000, 1700, 0.7)
    k = eo(T / 0.25)
    cobrand(ctx, 540, 1290 + (1 - k) * 25, 250, a)
    text(ctx, "BEN&FIT  ×  APOCALYPSE TRAINING", 540, 1475, 36, alpha=a * eo((T - 0.15) / 0.2))
    ev("intro", 0.0, "hit")

# ---------------------------------------------------------------- accroche (titre Anton)
def draw_title(ctx, T):
    t0, t1 = TITLE
    if not (t0 <= T <= t1 + 0.2): return
    out = 1 - eio((T - t1) / 0.2)
    legib_grad(ctx, out * eo((T - t0) / 0.2), 1000, 1700, 0.65)
    words = [("J'AI", t0), ("TESTÉ", t0 + 0.08), ("LE", t0 + 0.16), ("BLOC", t0 + 0.22)]
    size = 128; sp = 26
    widths = [tw(ctx, s, size, NUM) for s, _ in words]; x = 540 - (sum(widths) + sp * (len(words) - 1)) / 2
    for (s, t), wd in zip(words, widths):
        a = eo((T - t) / 0.14)
        if a > 0:
            text(ctx, s, x, 1255 + (1 - a) * 30, size, face=NUM, anchor="l", stroke=STROKE, sw=12, alpha=a * out, shadow=0.4)
        x += wd + sp
    tc = t0 + 0.38
    if T > tc:
        a = (T - tc) / 0.22
        chip(ctx, "D'APOCALYPSE TRAINING", 540, 1420, 64, anchor="c", alpha=out * eo(a), padx=26, pady=18, wipe=eo(a * 1.2))
        ev("title", tc, "hit")

# ---------------------------------------------------------------- chips d'exercice
# Chaque chip : (début, fin, numéro, étiquette, lignes, x, y de la 1re ligne, ancre)
# lignes : (texte, apparition, (début actif, fin actif)) — la ligne active est en bleu, l'autre en marine.
# Positions vérifiées plan par plan : jamais sur Bene ni sur la charge.
def seg_t(sec, k):  # début du k-ième plan d'une section
    return [p for p in TL if p["sec"] == sec][k]["start"]
CHIPS = [
    (PULL[0], PULL[1], "01", "", [("STRICT PULL-UPS", PULL[0], (PULL[0], seg_t("pull", 1))),
                                  ("+ BUTTERFLY CHEST TO BAR", seg_t("pull", 1), (seg_t("pull", 1), PULL[1]))], 60, 1420, "l"),
    (HSPU[0], HSPU[1], "02", "", [("WALL WALKS", HSPU[0], (0, 99)),
                                  ("+ WALL FACING HSPU", HSPU[0] + 0.25, (0, 99))], 60, 430, "l"),
    (KB[0], KB[1], "03", "SUPERSET", [("KB PUSH PRESS", KB[0], (KB[0], KB[1])),
                                      ("+ GORILLA ROW", KB[0] + 0.25, (ROW[0], ROW[1]))], 1030, 1250, "r"),
    (ROW[0], ROW[1], "03", "SUPERSET", [("KB PUSH PRESS", ROW[0], (KB[0], KB[1])),
                                        ("+ GORILLA ROW", ROW[0] + 0.1, (ROW[0], ROW[1]))], 60, 430, "l"),
    (PLATE[0], PLATE[1], "04", "", [("COMPLEXE", PLATE[0], (0, 99)), ("ÉPAULES", PLATE[0] + 0.15, (0, 99))], 60, 1420, "l"),
]
def draw_chips(ctx, T):
    for t0, t1, num, tag, lines, x, y, anc in CHIPS:
        t0b = t0 + 0.08; t1b = min(t1, END_T) - 0.2
        a = win(T, t0b, t1b, 0.25, 0.2)
        if a <= 0: continue
        dx = (1 - eo((T - t0b) / 0.3)) * (-30 if anc == "l" else 30)
        x0s = []
        for i, (txt, ta, (aa, ab)) in enumerate(lines):
            if T < ta: continue
            k = eo((T - ta) / 0.3)
            active = aa <= T < ab
            w, x0 = chip(ctx, txt, x + dx, y + i * 74, 42, fill=BLUE if active else NAVY, anchor=anc,
                         alpha=a * (1 if active else 0.92), wipe=k)
            x0s.append((x0, w))
            ev(("chip", num, txt, t0), ta, "swoosh")
        x0, w = x0s[0]
        nx = x0 if anc == "l" else x0 + w
        ka = a * eo((T - t0b - 0.1) / 0.25)
        adv = text(ctx, num, nx + dx, y - 64, 56, face=NUM, anchor=anc, alpha=ka, stroke=STROKE, sw=8, shadow=0.35)
        if tag:
            tx = nx + dx + adv + 16 if anc == "l" else nx + dx - adv - 16
            text(ctx, tag, tx, y - 60, 34, face=NUM, anchor=anc, alpha=ka, stroke=STROKE, sw=6, shadow=0.35)

# ---------------------------------------------------------------- logos discrets en coin
def draw_corner(ctx, T):
    t0 = TITLE[1] + 0.1
    a = win(T, t0, END_T - 0.1, 0.4, 0.2) * 0.6
    if a <= 0: return
    logo(ctx, L_BEN, 890, 300, 84, a)
    logo(ctx, L_APO, 990, 300, 84, a)

# ---------------------------------------------------------------- carte de fin
BONE = (0.90, 0.87, 0.80)
_v = PImage.open("/home/claude/work/apo/volcan.png").convert("RGBA")
VOLCAN = load_logo("/home/claude/work/apo/volcan.png")
def draw_end(ctx, T):
    """Carte de fin dans l'univers Apocalypse : noir, texte blanc / os, signature volcan."""
    if T < END_T: return
    u = T - END_T; a = eo(u / 0.3)
    ctx.rectangle(0, 0, W, H); ctx.set_source_rgba(0.02, 0.02, 0.02, 0.86 * a); ctx.fill()
    g = cairo.RadialGradient(540, 900, 300, 540, 900, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.6)
    ctx.set_source(g); ctx.paint_with_alpha(a)
    k = eo((u - 0.05) / 0.3)
    cobrand(ctx, 540, 480 + (1 - k) * 20, 210, k)
    k = (u - 0.35) / 0.3
    if k > 0: text(ctx, "TU VEUX TESTER", 540, 790 + (1 - eo(k)) * 30, 104, face=NUM, alpha=eo(k), shadow=0.5)
    k = (u - 0.55) / 0.3
    if k > 0:
        text(ctx, "ce bloc ?", 540, 925 + (1 - eo(k)) * 30, 112, face=SERIF, italic=True, color=BONE, alpha=eo(k))
        marker_path(ctx, underline_pts(345, 735, 995), (u - 0.8) / 0.45, 8, WHITE, 0.85)
    k = (u - 1.0) / 0.25
    if k > 0:
        ka = eo(k); size = 48; vs = 64; gap = 14
        w1 = tw(ctx, "ÉCRIS", size); w2 = tw(ctx, "EN COMMENTAIRE", size)
        wt = w1 + gap + vs + gap + w2; padx = 26; h = 92
        x0 = 540 - wt / 2 - padx; y = 1135
        ctx.save(); ctx.rectangle(x0, y - h / 2 - 2, (wt + 2 * padx) * eo(k * 1.2), h + 4); ctx.clip()
        rrect(ctx, x0, y - h / 2, wt + 2 * padx, h, 10); ctx.set_source_rgba(*BONE, ka); ctx.fill()
        text(ctx, "ÉCRIS", x0 + padx, y, size, color=(0.05, 0.05, 0.05), anchor="l", alpha=ka)
        logo(ctx, VOLCAN, x0 + padx + w1 + gap + vs / 2, y - 2, vs, ka)
        text(ctx, "EN COMMENTAIRE", x0 + padx + w1 + gap + vs + gap, y, size, color=(0.05, 0.05, 0.05), anchor="l", alpha=ka)
        ctx.restore()
        ev("cta", END_T + 1.0, "tick")
    k = (u - 1.3) / 0.3
    if k > 0: text(ctx, "+ abonne-toi pour la suite du bloc", 540, 1255, 44, alpha=eo(k))
    k = (u - 1.6) / 0.3
    if k > 0: text(ctx, "Programmation : Apocalypse Training", 540, 1360, 40, face=MARK, color=BONE, alpha=eo(k))
    ev("end", END_T, "end")

# ---------------------------------------------------------------- cadrage (punch-in)
def seg_at(T):
    for i, p in enumerate(TL):
        if T < p["start"] + p["dur"]: return i, p
    return len(TL) - 1, TL[-1]
def base_scale(T):
    i, p = seg_at(min(T, BASE_DUR - 0.01))
    u = T - p["start"]
    s = p["zoom"] + 0.025 * clamp(u / max(p["dur"], 0.5))           # léger glissé
    if i % 2 == 1 and p["sec"] not in ("hook", "end"): s += 0.07 * (1 - eo(u / 0.22))   # punch-in rapide à la coupe
    return s

def overlays(ctx, T):
    draw_intro(ctx, T); draw_title(ctx, T); draw_chips(ctx, T); draw_corner(ctx, T)

def render_frame(T, fb, surf):
    ctx = cairo.Context(surf)
    src = cairo.ImageSurface.create_for_data(fb, cairo.FORMAT_ARGB32, W, H, W * 4)
    s = base_scale(T)
    ctx.save(); ctx.translate(540, 900); ctx.scale(s, s); ctx.translate(-540, -900)
    ctx.set_source_surface(src, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.paint(); ctx.restore()
    overlays(ctx, T)
    draw_end(ctx, T)

def main(t_from=0.0, t_to=None, stills=None):
    t_to = DUR if t_to is None else t_to
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{min(t_from, BASE_DUR - 0.1):.3f}", "-i", "/home/claude/work/apo/base_apo.mp4",
                           "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    wr = None
    if stills is None:
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                               "/home/claude/work/apo/video_apo_nosound.mp4"], stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    n = int(round((t_to - t_from) * FPS)); last = None
    for i in range(n):
        T = t_from + i / FPS
        buf = rd.stdout.read(W * H * 4) if (T < BASE_DUR - 0.5 / FPS or last is None) else b""
        if len(buf) == W * H * 4: last = bytearray(buf)
        render_frame(T, last, surf); surf.flush()
        if wr: wr.stdin.write(bytes(surf.get_data()))
        elif i == 0:
            PImage.frombuffer("RGBA", (W, H), bytes(surf.get_data()), "raw", "BGRA", 0, 1).convert("RGB").save(
                f"/home/claude/work/apo/frames/t_{T:06.2f}.jpg", quality=85)
    rd.kill()
    if wr: wr.stdin.close(); wr.wait()
    if stills is None: json.dump(sorted(EV), open("/home/claude/work/apo/events_apo.json", "w"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        os.makedirs("/home/claude/work/apo/frames", exist_ok=True)
        for t in map(float, sys.argv[2:]): main(t, t + 0.04, stills=True)
    else:
        main()
