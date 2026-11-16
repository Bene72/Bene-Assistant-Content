"""Reel BEN&FIT « Cardio et perte de muscle » — compositing DA v2 naturelle.
Base étalonnée (build_base_naturel.py) + sous-titres Coda + motion design choisi passage par passage.
Écrit video_cardio_nosound.mp4 et events_cardio.json (bruitages)."""
import sys, math, json, random, subprocess
import numpy as np, cairo
import PIL.Image as PImage, PIL.ImageFilter as PFilter
sys.path.insert(0, "/home/claude/work")
from data_cardio import TL, TOTAL, WORDS, SUBS, tag_range, cut_at, norm

W, H, FPS = 1080, 1920, 30
BASE_DUR = TOTAL
HOLD = 1.3
DUR = BASE_DUR + HOLD
WHITE = (1, 1, 1); BLUE = (0.18, 0.42, 1.0); BLUE2 = (0.55, 0.72, 1.0); NAVY = (0.03, 0.07, 0.19)
STROKE = (0.08, 0.30, 0.92); INK = (0.04, 0.125, 0.42)
FONT = "Coda ExtraBold"; NUM = "Anton"; MARK = "Permanent Marker"; SERIF = "Liberation Serif"
BIB = "/home/claude/bene-assistant-content/contenu/bibliotheque/"
EV = []; _seen = set()
def ev(key, t, kind):
    if key not in _seen: _seen.add(key); EV.append((t, kind))

clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def eback(x):
    x = clamp(x); c = 1.4; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def wt(tag, word, nth=0):
    hits = [w for w in WORDS if w["tag"] == tag and norm(w["w"]) == norm(word)]
    return hits[nth]["t"] if len(hits) > nth else None
def wte(tag, word, nth=0):
    hits = [w for w in WORDS if w["tag"] == tag and norm(w["w"]) == norm(word)]
    return hits[nth]["te"] if len(hits) > nth else None
R = lambda *t: tag_range(*t)
def need(x, name):
    if x is None: raise SystemExit(f"mot introuvable : {name}")
    return x

# ---------------------------------------------------------------- texte
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
    adv = ctx.text_extents(s)[4]
    ch = cap_h(ctx, size, face, italic)
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
    rrect(ctx, x0, y - h / 2, w, h, 10); ctx.set_source_rgba(*fill, alpha); ctx.fill()
    text(ctx, s, x0 + w / 2, y, size, color=color, alpha=alpha)
    if wipe < 1: ctx.restore()
    return w

def pop(ctx, cx, cy, a, s0=0.85):
    s = s0 + (1 - s0) * eback(a)
    ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-cx, -cy)
    return clamp(a * 1.6)

def win(T, t0, t1, fin=0.3, fout=0.3):
    if T < t0 or T > t1 + fout: return 0.0
    return eo((T - t0) / fin) * (1 - eio((T - t1) / fout))

# ---------------------------------------------------------------- trait de feutre
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
def ellipse_pts(cx, cy, rx, ry):
    return [(cx + rx * (1 + 0.05 * math.sin(3 * a)) * math.cos(a), cy + ry * math.sin(a))
            for a in np.linspace(-2.6, -2.6 + 2 * math.pi * 1.08, 70)]

# ---------------------------------------------------------------- GIFs de la bibliothèque
class Gif:
    def __init__(self, name, crop=None, max_s=None):
        im = PImage.open(BIB + name); self.frames = []; self.durs = []
        n = getattr(im, "n_frames", 1); i = 0
        while i < n and (max_s is None or sum(self.durs) < max_s):
            im.seek(i); fr = im.convert("RGBA")
            if crop: fr = fr.crop(crop)
            a = np.asarray(fr).astype(np.float32); al = a[..., 3:4] / 255.0
            bgra = np.concatenate([a[..., 2:3] * al, a[..., 1:2] * al, a[..., 0:1] * al, a[..., 3:4]], 2).astype(np.uint8)
            h, w = bgra.shape[:2]; stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
            buf = np.zeros((h, stride // 4, 4), np.uint8); buf[:, :w] = bgra
            self.frames.append(cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride))
            self.durs.append(max(im.info.get("duration", 80), 40) / 1000); i += 1
        self.w, self.h = self.frames[0].get_width(), self.frames[0].get_height(); self.total = sum(self.durs)
    def at(self, t, loop=True):
        t = t % self.total if loop else min(max(t, 0), self.total - 1e-3)
        for f, d in zip(self.frames, self.durs):
            if t < d: return f
            t -= d
        return self.frames[-1]

def draw_media(ctx, g, t, cx, cy, bw, bh, a=1.0, tilt=0.0, border=10, radius=26, loop=True):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(math.radians(tilt))
    rrect(ctx, -bw / 2 - border, -bh / 2 - border + 10, bw + 2 * border, bh + 2 * border, radius + border)
    ctx.set_source_rgba(0, 0, 0, 0.30 * a); ctx.fill()
    rrect(ctx, -bw / 2 - border, -bh / 2 - border, bw + 2 * border, bh + 2 * border, radius + border)
    ctx.set_source_rgba(1, 1, 1, a); ctx.fill()
    rrect(ctx, -bw / 2, -bh / 2, bw, bh, radius); ctx.clip()
    sc = max(bw / g.w, bh / g.h); ctx.scale(sc, sc); ctx.set_source_surface(g.at(t, loop), -g.w / 2, -g.h / 2)
    ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.paint_with_alpha(a)
    ctx.restore()

def polaroid(ctx, g, t, cx, cy, pw, ph, a, tilt, caption):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(math.radians(tilt))
    bw, top, bot = 14, 14, 70
    w, h = pw + 2 * bw, ph + top + bot
    ctx.rectangle(-w / 2 + 6, -h / 2 + 12, w, h); ctx.set_source_rgba(0, 0, 0, 0.28 * a); ctx.fill()
    ctx.rectangle(-w / 2, -h / 2, w, h); ctx.set_source_rgba(0.97, 0.96, 0.93, a); ctx.fill()
    ctx.save(); ctx.rectangle(-pw / 2, -h / 2 + top, pw, ph); ctx.clip()
    sc = max(pw / g.w, ph / g.h); ctx.translate(0, -h / 2 + top + ph / 2); ctx.scale(sc, sc)
    ctx.set_source_surface(g.at(t), -g.w / 2, -g.h / 2); ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(a); ctx.restore()
    text(ctx, caption, 0, h / 2 - bot / 2 + 4, 36, face=MARK, color=(0.12, 0.14, 0.22), alpha=a)
    ctx.save(); ctx.translate(0, -h / 2 + 2); ctx.rotate(math.radians(-6))
    ctx.rectangle(-70, -20, 140, 40); ctx.set_source_rgba(0.93, 0.89, 0.78, 0.75 * a); ctx.fill(); ctx.restore()
    ctx.restore()

G = {"tread": Gif("sport/cardio.2.gif", crop=(0, 0, 498, 250)),
     "lift": Gif("sport/happyb.lift.gif", crop=(0, 0, 220, 290), max_s=3.2),
     "fail": Gif("sport/fail.lifting.gif"),
     "corgi": Gif("reactions/confused.gif")}

def put_polaroid(ctx, T, key, t0, t1, caption, cx=850, cy=660, pw=350, ph=235, tilt=5):
    a = win(T, t0, t1, 0.35, 0.3)
    if a <= 0: return
    k = eo((T - t0) / 0.35)
    polaroid(ctx, G[key], T - t0, cx, cy + (1 - k) * 50 + 3 * math.sin(T * 2.1), pw, ph, a,
             tilt + 0.6 * math.sin(T * 1.3), caption)
    ev(("pol", key), t0, "swoosh")

def sticker(ctx, T, key, t0, t1, cx, cy, bw, bh, tilt):
    if not (t0 <= T <= t1 + 0.2): return
    k = eo((T - t0) / 0.25) * (1 - eio((T - t1) / 0.2))
    ctx.save(); s = 0.8 + 0.2 * k; ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-cx, -cy)
    draw_media(ctx, G[key], T - t0, cx, cy + 2 * math.sin(T * 2.3), bw, bh, a=k, tilt=tilt + 0.5 * math.sin(T * 1.5))
    ctx.restore()
    ev(("st", key), t0, "swoosh")

# ---------------------------------------------------------------- cartes en verre dépoli
_frost = {}
def frost(ctx, src_surf, x, y, w, h, a, radius=30):
    """carte translucide : fond flouté + voile blanc + liseré + ombre douce"""
    if a <= 0: return
    key = (int(x), int(y), int(w), int(h))
    src_surf.flush()
    arr = np.ndarray((H, W, 4), np.uint8, buffer=src_surf.get_data())
    x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h))
    crop = PImage.fromarray(arr[y0:y1, x0:x1].copy(), "RGBA").filter(PFilter.GaussianBlur(22))
    b = np.ascontiguousarray(np.asarray(crop))
    surf = cairo.ImageSurface.create_for_data(bytearray(b.tobytes()), cairo.FORMAT_ARGB32, x1 - x0, y1 - y0, (x1 - x0) * 4)
    ctx.save()
    rrect(ctx, x, y + 14, w, h, radius); ctx.set_source_rgba(0, 0, 0, 0.18 * a); ctx.fill()
    rrect(ctx, x, y, w, h, radius); ctx.clip()
    ctx.set_source_surface(surf, x0, y0); ctx.paint_with_alpha(a)
    ctx.set_source_rgba(0.06, 0.09, 0.2, 0.42 * a); ctx.paint()
    ctx.restore()
    rrect(ctx, x + 1, y + 1, w - 2, h - 2, radius); ctx.set_line_width(2); ctx.set_source_rgba(1, 1, 1, 0.35 * a); ctx.stroke()

def card_title(ctx, bold, ital, x, y, a, size=50):
    adv = text(ctx, bold, x, y, size, alpha=a, anchor="l")
    text(ctx, ital, x + adv + 14, y + 2, size * 1.12, face=SERIF, italic=True, color=BLUE2, alpha=a, anchor="l")

def check(ctx, x, y, k, a, r=24):
    ctx.arc(x, y, r, 0, 2 * math.pi); ctx.set_line_width(3); ctx.set_source_rgba(1, 1, 1, 0.6 * a); ctx.stroke()
    if k <= 0: return
    ctx.arc(x, y, r * (0.7 + 0.3 * eo(k)), 0, 2 * math.pi); ctx.set_source_rgba(*BLUE, a * eo(k)); ctx.fill()
    pts = [(x - 10, y + 1), (x - 3, y + 9), (x + 11, y - 9)]
    n = clamp(k * 1.6)
    ctx.set_line_width(5); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(*pts[0])
    if n < 0.5: ctx.line_to(pts[0][0] + (pts[1][0] - pts[0][0]) * n * 2, pts[0][1] + (pts[1][1] - pts[0][1]) * n * 2)
    else:
        ctx.line_to(*pts[1]); u = (n - 0.5) * 2
        ctx.line_to(pts[1][0] + (pts[2][0] - pts[1][0]) * u, pts[1][1] + (pts[2][1] - pts[1][1]) * u)
    ctx.set_source_rgba(1, 1, 1, a); ctx.stroke()

# ================================================================ timings (temps de sortie)
HOOK_W = [w for w in WORDS if w["tag"] == "hook"]
HOOK_END = HOOK_W[-1]["te"] + 0.15
T_CARDIO_H = need(wt("hook", "cardio"), "cardio"); T_PERDRE_H = need(wt("hook", "perdre"), "perdre")
T_MASSE_H = need(wt("hook", "masse"), "masse")
A1 = R("A1"); A3 = R("A3")
CHAPTERS = [(1, A1[0], "LE MYTHE"), (2, R("A2")[0], "LA GESTION"), (3, R("B0")[0], "LES MODALITÉS"),
            (4, R("E1a")[0], "BIEN PROGRAMMÉ")]
END_T = R("F1")[1] + 0.12
COMP = (R("C1")[0] - 0.05, R("C4")[1])            # carte comparaison haute / basse intensité
WEEK = (R("D1")[0] + 0.05, R("D2")[1] - 0.1)     # agenda « du lundi au lundi »
LIST = (R("E2")[0] - 0.05, R("E3")[1] + 0.15)     # checklist
CARD_Y = 960

def no_subs(T):
    return T < HOOK_END or (A1[0] - 0.06 <= T <= A1[1] + 0.2) or T >= END_T - 0.01

# ---------------------------------------------------------------- accroche (typo animée)
def legib_grad(ctx, a, y0=880, y1=1640):
    g = cairo.LinearGradient(0, y0, 0, y1); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, *NAVY, 0.6)
    ctx.save(); ctx.rectangle(0, y0, W, y1 - y0); ctx.clip(); ctx.set_source(g); ctx.paint_with_alpha(a); ctx.restore()

def words_line(ctx, T, items, y, size, out, sp=24):
    """items: (mot, t_apparition) — mots qui arrivent un par un"""
    widths = [tw(ctx, s, size) for s, _ in items]; x = 540 - (sum(widths) + sp * (len(items) - 1)) / 2
    for (s, t), wd in zip(items, widths):
        a = (T - t) / 0.16
        if a > 0:
            ctx.save(); al = pop(ctx, x + wd / 2, y, a, 0.75)
            text(ctx, s, x, y, size, anchor="l", stroke=STROKE, sw=10, alpha=al * out, shadow=0.35); ctx.restore()
        x += wd + sp

def draw_hook(ctx, T):
    if T > HOOK_END + 0.2: return
    legib_grad(ctx, 1 - eio((T - HOOK_END) / 0.2))
    p2, p3 = T_CARDIO_H + 0.05, T_MASSE_H - 0.1
    if T < p2 + 0.1:
        out = 1 - eio((T - p2) / 0.1)
        words_line(ctx, T, [("TU", 0.0), ("FAIS", 0.12), ("DE", 0.28), ("LA", 0.36)], 1130, 96, out)
        a = (T - 0.55) / 0.22
        if a > 0:
            ctx.save(); al = pop(ctx, 540, 1290, a, 0.6)
            chip(ctx, "MUSCU", 540, 1290, 140, anchor="c", alpha=al * out, padx=30, pady=22); ctx.restore()
        ev("hook1", 0.0, "hit")
    elif T < p3 + 0.1:
        out = 1 - eio((T - p3) / 0.1)
        words_line(ctx, T, [("ET", p2), ("TU", p2 + 0.08), ("AS", p2 + 0.16), ("PEUR", p2 + 0.26), ("DE", p2 + 0.36)], 1110, 84, out)
        a = (T - T_PERDRE_H + 0.05) / 0.22
        if a > 0:
            ctx.save(); al = pop(ctx, 540, 1250, a, 0.7)
            chip(ctx, "PERDRE DU MUSCLE", 540, 1250, 92, anchor="c", alpha=al * out, padx=24, pady=18, wipe=eo(a * 1.2)); ctx.restore()
    else:
        out = 1 - eio((T - HOOK_END + 0.12) / 0.15)
        words_line(ctx, T, [("EN", p3), ("FAISANT", p3 + 0.1), ("DU", p3 + 0.22)], 1060, 86, out)
        a = (T - p3 - 0.3) / 0.25
        if a > 0:
            ctx.save(); al = pop(ctx, 540, 1255, a, 0.55)
            text(ctx, "CARDIO ?", 540, 1255, 250, face=NUM, stroke=STROKE, sw=14, alpha=al * out, shadow=0.4); ctx.restore()
            ev("hook3", p3 + 0.3, "hit")

# ---------------------------------------------------------------- 01 : mot géant
def draw_mot_geant(ctx, T):
    t0, t1 = A1[0], A1[1]
    if not (t0 - 0.05 <= T <= t1 + 0.35): return
    out = 1 - eio((T - t1) / 0.18)
    legib_grad(ctx, out * eo((T - t0) / 0.25), 900, 1700)
    k1 = eo((T - t0) / 0.3)
    text(ctx, "Le cardio", 540, 1135 + (1 - k1) * 30, 118, alpha=k1 * out, stroke=STROKE, sw=10, shadow=0.35)
    tp = need(wt("A1", "pas"), "pas") - 0.15
    k2 = eo((T - tp) / 0.3)
    if T > tp:
        text(ctx, "n'est pas", 540, 1272 + (1 - k2) * 30, 108, face=SERIF, italic=True, alpha=k2 * out, shadow=0.45)
    te = need(wt("A1", "muscle,"), "muscle") - 0.35
    if T > te:
        a = (T - te) / 0.25
        ctx.save(); al = pop(ctx, 540, 1425, a, 0.7)
        chip(ctx, "TON ENNEMI.", 540, 1425, 112, anchor="c", alpha=al * out, padx=28, pady=20, wipe=eo(a * 1.3)); ctx.restore()
        ev("geant", te, "hit")

# ---------------------------------------------------------------- tags de chapitre
def chapter_tags(ctx, T):
    for i, (ch, tc, name) in enumerate(CHAPTERS):
        nxt = CHAPTERS[i + 1][1] if i + 1 < len(CHAPTERS) else 1e9
        dur = min(3.0, nxt - tc - 0.45)
        u = T - tc
        if -0.05 <= u <= dur + 0.4:
            a = eo(u / 0.35) * (1 - eio((u - dur) / 0.4))
            ctx.save(); ctx.translate(-(1 - eo(u / 0.35)) * 30, 0)
            text(ctx, f"0{ch}", 80, 375, 62, face=NUM, color=INK, alpha=a, anchor="l")
            adv = text(ctx, name, 156, 375, 50, color=INK, alpha=a, anchor="l")
            ctx.restore()
            marker_path(ctx, underline_pts(76, 170 + adv, 424), (u - 0.3) / 0.45, 8, BLUE, a)
            ev(("ch", ch), tc, "tick")

# ---------------------------------------------------------------- 02 : phrase manuscrite
def draw_probleme(ctx, T):
    t0 = need(wt("A3", "conduire"), "conduire") - 0.1; t1 = R("B0")[0] - 0.45
    a = win(T, t0, t1, 0.3, 0.35)
    if a <= 0: return
    k = eo((T - t0) / 0.3)
    text(ctx, "Le problème,", 80 - (1 - k) * 25, 330, 56, face=MARK, color=INK, alpha=a, anchor="l")
    t2 = t0 + 0.45
    if T > t2:
        k2 = eo((T - t2) / 0.3)
        adv = tw(ctx, "c'est la ", 56, MARK)
        text(ctx, "c'est la ", 80 - (1 - k2) * 25, 412, 56, face=MARK, color=INK, alpha=a * k2, anchor="l")
        adv2 = text(ctx, "programmation.", 80 + adv - (1 - k2) * 25, 412, 56, face=MARK, color=BLUE, alpha=a * k2, anchor="l")
        marker_path(ctx, underline_pts(80 + adv - 4, 80 + adv + adv2, 452), (T - t2 - 0.25) / 0.45, 8, BLUE, a)
        ev("prob", t2, "swoosh")

# ---------------------------------------------------------------- 03 : chiffres empilés à droite
def draw_glucides(ctx, T):
    tp = need(wt("B3", "protéines"), "protéines"); t50 = need(wt("B5", "50"), "50"); teq = need(wt("B6", "d'équilibre."), "équilibre")
    t_end = R("B6")[1] + 0.15
    x = 1010
    a = win(T, tp - 0.05, t_end, 0.3, 0.35)
    if a > 0:
        dx = (1 - eo((T - tp + 0.05) / 0.3)) * 25
        adv = text(ctx, "PROTÉINES", x + dx, 500, 58, color=INK, alpha=a, anchor="r")
        check(ctx, x - adv - 40 + dx, 500, (T - tp - 0.1) / 0.35, a, r=22)
        ev("prot", tp, "tick")
    a = win(T, t50 - 0.05, t_end, 0.3, 0.35)
    if a > 0:
        dx = (1 - eo((T - t50 + 0.05) / 0.3)) * 25
        text(ctx, "+50 g", x + dx, 640, 140, face=NUM, color=INK, alpha=a, anchor="r")
        k = eo((T - t50 - 0.35) / 0.3)
        text(ctx, "de glucides / jour", x + dx, 745, 42, face=MARK, color=INK, alpha=a * k, anchor="r")
        ev("50", t50, "hit")
    if T > teq - 0.1:
        a2 = win(T, teq - 0.1, t_end, 0.2, 0.35)
        marker_path(ctx, ellipse_pts(880, 650, 170, 92), (T - teq + 0.1) / 0.5, 8, BLUE, a2)
        k = eo((T - teq) / 0.3)
        text(ctx, "= équilibre", 1010, 830, 46, face=MARK, color=BLUE, alpha=a2 * k, anchor="r")

# ---------------------------------------------------------------- 03 : carte comparaison
def draw_comp(ctx, T, src):
    t0, t1 = COMP
    a = win(T, t0, t1, 0.3, 0.3)
    if a <= 0: return
    dy = (1 - eo((T - t0) / 0.35)) * 50
    y = CARD_Y + dy; h = 320
    frost(ctx, src, 70, y, 940, h, a)
    card_title(ctx, "Le", "carburant", 110, y + 52, a, 46)
    tb = need(wt("C1", "basse"), "basse"); tl_ = need(wt("C2", "lipolyse."), "lipolyse"); tm = need(wt("C4", "muscles."), "muscles")
    cy1, cy2 = y + 145, y + 222
    # colonne gauche : haute intensité -> glucides (rappel du passage précédent)
    ka = eo((T - t0 - 0.25) / 0.3)
    text(ctx, "HAUTE INTENSITÉ", 290, cy1, 40, alpha=a * ka)
    text(ctx, "→ glucides", 290, cy2, 46, face=MARK, color=BLUE2, alpha=a * ka)
    # séparateur
    ctx.rectangle(539, y + 110, 2, 190); ctx.set_source_rgba(1, 1, 1, 0.3 * a * ka); ctx.fill()
    if T > tb - 0.05:
        kb = (T - tb + 0.05) / 0.25
        ctx.save(); al = pop(ctx, 790, cy1, kb, 0.8)
        chip(ctx, "BASSE INTENSITÉ", 790, cy1, 38, anchor="c", alpha=a * al, padx=14, pady=10); ctx.restore()
        ev("basse", tb, "tick")
    if T > tl_ - 0.05:
        kl = eo((T - tl_ + 0.05) / 0.3)
        text(ctx, "→ graisses", 790, cy2, 46, face=MARK, color=WHITE, alpha=a * kl)
    if T > tm - 0.2:
        km = eo((T - tm + 0.2) / 0.3)
        text(ctx, "(pas les muscles)", 790, y + 282, 38, face=MARK, color=BLUE2, alpha=a * km)
        marker_path(ctx, underline_pts(655, 925, y + 306), (T - tm) / 0.4, 6, BLUE, a * km)
    ev("comp", t0, "swoosh")

# ---------------------------------------------------------------- 03 : agenda « du lundi au lundi »
def draw_week(ctx, T, src):
    t0, t1 = WEEK
    a = win(T, t0, t1, 0.3, 0.3)
    if a <= 0: return
    dy = (1 - eo((T - t0) / 0.35)) * 50
    y = CARD_Y + dy; h = 280
    frost(ctx, src, 70, y, 940, h, a)
    card_title(ctx, "Ta", "semaine", 110, y + 52, a, 46)
    tl1 = need(wt("D2", "lundi"), "lundi"); tl2 = need(wt("D2", "lundi,"), "lundi2")
    days = ["L", "M", "M", "J", "V", "S", "D"]
    span = max(0.6, tl2 - tl1)
    for i, d in enumerate(days):
        x = 165 + i * 125; cy = y + 155
        ti = tl1 + span * i / 6
        k = eo((T - ti) / 0.2) if T > ti else 0
        ctx.arc(x, cy, 46, 0, 2 * math.pi)
        if k > 0: ctx.set_source_rgba(*BLUE, a * k); ctx.fill_preserve()
        ctx.set_line_width(3); ctx.set_source_rgba(1, 1, 1, a * (0.45 + 0.55 * k)); ctx.stroke()
        text(ctx, d, x, cy, 38, alpha=a)
        if k > 0: text(ctx, "HIIT", x, cy + 80, 24, color=BLUE2, alpha=a * k)
        if T > ti: ev(("day", i), ti, "tick")

# ---------------------------------------------------------------- 04 : checklist
def draw_list(ctx, T, src):
    t0, t1 = LIST
    a = win(T, t0, t1, 0.3, 0.3)
    if a <= 0: return
    dy = (1 - eo((T - t0) / 0.35)) * 50
    y = CARD_Y - 20 + dy; h = 330
    frost(ctx, src, 70, y, 940, h, a)
    card_title(ctx, "Ta", "checklist", 110, y + 52, a, 46)
    items = [("Dormir", wt("E2", "dormir,")), ("Manger", wt("E2", "manger,")),
             ("S'hydrater", wt("E2", "s'hydrater")), ("S'entraîner", wt("E2", "s'entraîner"))]
    for i, (lab, t) in enumerate(items):
        t = need(t, lab)
        x = 140 + (i % 2) * 450; cy = y + 135 + (i // 2) * 82
        k = (T - t + 0.05) / 0.35
        check(ctx, x, cy, k, a)
        text(ctx, lab, x + 44, cy, 46, alpha=a * (0.55 + 0.45 * eo(k)), anchor="l")
        if T > t: ev(("chk", i), t, "tick")
    tp = need(wt("E3", "programme"), "programme")
    if T > tp - 0.05:
        k = (T - tp + 0.05) / 0.25
        ctx.save(); al = pop(ctx, 540, y + h - 50, k, 0.8)
        chip(ctx, "+ UN PROGRAMME ADAPTÉ", 540, y + h - 50, 40, anchor="c", alpha=a * al, padx=18, pady=12); ctx.restore()
        ev("prog", tp, "hit")

# ---------------------------------------------------------------- carte de fin
def draw_end(ctx, T):
    if T < END_T: return
    u = T - END_T; a = eo(u / 0.35)
    ctx.rectangle(0, 0, W, H); ctx.set_source_rgba(*NAVY, 0.84 * a); ctx.fill()
    k = (u - 0.1) / 0.3
    if k > 0:
        text(ctx, "Force et endurance", 540, 500 + (1 - eo(k)) * 30, 86, alpha=eo(k))
    k = (u - 0.4) / 0.3
    if k > 0:
        text(ctx, "peuvent coexister.", 540, 620 + (1 - eo(k)) * 30, 100, face=SERIF, italic=True, color=BLUE2, alpha=eo(k))
        marker_path(ctx, underline_pts(250, 830, 690), (u - 0.7) / 0.5, 8, BLUE, 1)
    k = (u - 1.2) / 0.25
    if k > 0:
        ctx.save(); al = pop(ctx, 540, 900, k, 0.75)
        chip(ctx, "ET TOI ?", 540, 900, 96, anchor="c", alpha=al, padx=28, pady=20); ctx.restore()
    for i, (s, d) in enumerate([("Tu fais du cardio", 1.45), ("à côté de ta muscu ?", 1.6)]):
        k = (u - d) / 0.3
        if k > 0: text(ctx, s, 540, 1050 + i * 88 + (1 - eo(k)) * 25, 66, alpha=eo(k), stroke=STROKE, sw=8)
    k = (u - 2.1) / 0.3
    if k > 0:
        text(ctx, "DIS-LE MOI EN COMMENTAIRE", 540, 1300, 38, alpha=eo(k))
        text(ctx, "BEN&FIT", 540, 1395, 46, face=NUM, color=BLUE2, alpha=eo(k) * 0.9)
    ev("end", END_T, "end")

# ---------------------------------------------------------------- sous-titres
def draw_subs(ctx, T, y, size):
    if no_subs(T): return
    for s in SUBS:
        if s["t0"] <= T < s["t1"]: break
    else: return
    a = eo((T - s["t0"]) / 0.13)
    space = tw(ctx, " ", size) * 1.1
    lines, cur, cw = [], [], 0
    for w in s["words"]:
        ww = tw(ctx, w["w"], size)
        if cur and cw + space + ww > 880: lines.append((cur, cw)); cur, cw = [], 0
        cur.append((w, ww)); cw += (space if len(cur) > 1 else 0) + ww
    lines.append((cur, cw))
    lh = size * 1.32
    y0 = y - (len(lines) - 1) * lh / 2 + (1 - a) * 14
    ctx.save(); sc = 0.94 + 0.06 * a
    ctx.translate(W / 2, y); ctx.scale(sc, sc); ctx.translate(-W / 2, -y)
    for li, (ws, lw) in enumerate(lines):
        x = W / 2 - lw / 2; yy = y0 + li * lh
        for w, ww in ws:
            if w["key"]:
                k = eo((T - w["t"] + 0.04) / 0.16); pad = size * 0.2
                if k > 0:
                    rrect(ctx, x - pad, yy - size * 0.52, (ww + 2 * pad) * k, size * 1.04, 12); ctx.set_source_rgba(*BLUE, a); ctx.fill()
                text(ctx, w["w"], x, yy, size, anchor="l", stroke=STROKE if k < 0.5 else None, sw=9, alpha=a, shadow=0.0 if k > 0.5 else 0.35)
            else:
                text(ctx, w["w"], x, yy, size, anchor="l", stroke=STROKE, sw=9, alpha=a, shadow=0.35)
            x += ww + space
    ctx.restore()

# ---------------------------------------------------------------- cadrage (punch-in)
TAGS = []
for c in TL:
    if c["tag"] not in TAGS: TAGS.append(c["tag"])
PUNCH = {"non": 0.12, "A1": 0.05, "D2": 0.08, "D3": 0.04, "F1": 0.04, "B6": 0.06}
def base_scale(T):
    c = cut_at(min(T, BASE_DUR - 0.01))
    ti = TAGS.index(c["tag"]); a, b = tag_range(c["tag"])
    s = (1.0 if ti % 2 == 0 else 1.05) + 0.05 * (c["sub"] % 2) + PUNCH.get(c["tag"], 0)
    s += 0.03 * clamp((T - a) / max(b - a, 0.5))
    if c["tag"] == "hook": s = 1.04 + 0.03 * clamp(T / 4) + 0.18 * (1 - eo(T / 0.55))
    return s

# ---------------------------------------------------------------- rendu
def overlays(ctx, T, surf):
    draw_hook(ctx, T)
    chapter_tags(ctx, T)
    draw_mot_geant(ctx, T)
    draw_probleme(ctx, T)
    # 03
    put_polaroid(ctx, T, "tread", need(wt("B1b", "haute"), "haute") - 0.05, need(wt("B2", "glucides,"), "glucides") + 0.5, "haute intensité")
    draw_glucides(ctx, T)
    draw_comp(ctx, T, surf)
    draw_week(ctx, T, surf)
    sticker(ctx, T, "fail", need(wt("D3", "blessure,"), "blessure") - 0.1, R("D3")[1] + 0.1, 830, 620, 380, 216, -4)
    # 04
    put_polaroid(ctx, T, "lift", need(wt("E1b", "séances"), "séances") - 0.05, R("E1b")[1] + 0.25, "la muscu", pw=260, ph=340, cy=660, tilt=-4)
    draw_list(ctx, T, surf)
    # conclusion
    sticker(ctx, T, "corgi", need(wt("F1", "oui"), "oui") - 0.1, R("F1")[1] - 0.2, 925, 330, 230, 196, 5)

def render_frame(T, fb, surf):
    ctx = cairo.Context(surf)
    src = cairo.ImageSurface.create_for_data(fb, cairo.FORMAT_ARGB32, W, H, W * 4)
    s = base_scale(T)
    ctx.save(); ctx.translate(540, 760); ctx.scale(s, s); ctx.translate(-540, -760)
    ctx.set_source_surface(src, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.paint(); ctx.restore()
    overlays(ctx, T, surf)
    if T >= END_T - 0.01: draw_end(ctx, T)
    else:
        card = any(a0 <= T <= a1 + 0.3 for a0, a1 in (COMP, WEEK, LIST))
        draw_subs(ctx, T, 1395 if card else 1300, 74)

def main(t_from=0.0, t_to=None, stills=None):
    t_to = DUR if t_to is None else t_to
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t_from:.3f}", "-i", "/home/claude/work/base_v2.mp4",
                           "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    wr = None
    if stills is None:
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-pix_fmt", "yuv420p",
                               "/home/claude/work/video_cardio_nosound.mp4"], stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    n = int(round((t_to - t_from) * FPS)); last = None
    for i in range(n):
        T = t_from + i / FPS
        buf = rd.stdout.read(W * H * 4) if T < BASE_DUR - 0.5 / FPS else b""
        if len(buf) == W * H * 4: last = bytearray(buf)
        render_frame(T, last, surf); surf.flush()
        if wr: wr.stdin.write(bytes(surf.get_data()))
        elif i == 0:
            PImage.frombuffer("RGBA", (W, H), bytes(surf.get_data()), "raw", "BGRA", 0, 1).convert("RGB").save(
                f"/home/claude/work/frames/t_{T:06.2f}.jpg", quality=85)
        if wr and i % 300 == 0: print(f"{T:.1f}s", flush=True)
    rd.kill()
    if wr: wr.stdin.close(); wr.wait()
    if stills is None: json.dump(sorted(EV), open("/home/claude/work/events_cardio.json", "w"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        import os; os.makedirs("/home/claude/work/frames", exist_ok=True)
        for t in map(float, sys.argv[2:]): main(t, t + 0.04, stills=True)
    else:
        main()
