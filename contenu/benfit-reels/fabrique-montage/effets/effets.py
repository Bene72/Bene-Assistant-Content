"""Effets « verre dépoli » BEN&FIT pour Reels 1080x1920.

Chaque effet est une fonction fx_xxx(cv, t, **params) qui dessine sur un Canvas
(la vraie image du Reel) au temps local t (secondes depuis le début de l'effet).
Inspiration : effets « Liquid Glass » (cartes en verre, toggles, graphe, liste focus,
compteur, match-cut), adaptés à la charte BEN&FIT : marine + bleu vif, sans halo ni lueur.
"""
import math
import cairo
import numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1920
NAVY = (0x0A / 255, 0x20 / 255, 0x6B / 255)
DEEP = (0x03 / 255, 0x0A / 255, 0x1A / 255)
BLUE = (0x2E / 255, 0x6B / 255, 1.0)
BLUE_L = (0x8C / 255, 0xB8 / 255, 1.0)
WHITE = (1, 1, 1)
SANS, SANS_B, NUM, SERIF, HAND = "Coda", "Coda ExtraBold", "Anton", "Instrument Serif", "Permanent Marker"


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(x):  # ease-out cubique, pas de rebond (règle DA)
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = clamp(x)
    return 3 * x * x - 2 * x ** 3


def env(t, dur, fin=0.35, fout=0.3):
    """Opacité d'entrée/sortie d'un élément visible entre 0 et dur."""
    return eo(t / fin) * (1 - eio((t - (dur - fout)) / fout))


# ------------------------------------------------------------------ canvas
class Canvas:
    """Image du Reel (float32 0..1) + calques cairo composés par-dessus."""

    def __init__(self, frame_uint8):
        self.f = frame_uint8.astype(np.float32) / 255.0
        self._blur = None

    def blurred(self, radius=26):
        if self._blur is None:
            im = Image.fromarray((self.f * 255).astype(np.uint8))
            small = im.resize((W // 3, H // 3), Image.BILINEAR).filter(ImageFilter.GaussianBlur(radius / 3))
            self._blur = np.asarray(small.resize((W, H), Image.BILINEAR)).astype(np.float32) / 255.0
        return self._blur

    def _mask(self, path_fn, blur=0):
        s = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
        c = cairo.Context(s)
        path_fn(c)
        c.fill()
        s.flush()
        stride = s.get_stride()
        m = np.ndarray((H, stride), np.uint8, s.get_data())[:, :W].astype(np.float32) / 255.0
        if blur:
            im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
            m = np.asarray(im).astype(np.float32) / 255.0
        return m[..., None]

    def shadow(self, path_fn, alpha=0.35, blur=28, dy=18):
        def p(c):
            c.translate(0, dy)
            path_fn(c)
        m = self._mask(p, blur) * alpha
        self.f = self.f * (1 - m)

    def glass(self, path_fn, alpha=1.0, tint=0.32, light=0.05):
        m = self._mask(path_fn) * alpha
        b = self.blurred()
        g = b * (1 - tint - light) + np.array(NAVY, np.float32) * tint + light
        self.f = self.f * (1 - m) + g * m

    def paper(self, path_fn, alpha=1.0, color=(0.97, 0.97, 0.96)):
        m = self._mask(path_fn) * alpha
        self.f = self.f * (1 - m) + np.array(color, np.float32) * m

    def draw(self, fn):
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        c = cairo.Context(s)
        fn(c)
        s.flush()
        a = np.ndarray((H, W, 4), np.uint8, s.get_data()).astype(np.float32) / 255.0
        rgb = a[..., [2, 1, 0]]
        al = a[..., 3:4]
        self.f = self.f * (1 - al) + rgb

    def frost(self, alpha, box=None):
        """Floute légèrement tout le fond (pour faire ressortir un élément)."""
        b = self.blurred()
        self.f = self.f * (1 - alpha) + (b * 0.8 + np.array(DEEP, np.float32) * 0.2) * alpha

    def out(self):
        return (np.clip(self.f, 0, 1) * 255).astype(np.uint8)


# ------------------------------------------------------------------ dessin
def rrect(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def place(c, cx, cy, rot=0.0, sc=1.0):
    c.translate(cx, cy)
    c.rotate(math.radians(rot))
    c.scale(sc, sc)


def font(c, face, size, italic=False):
    c.select_font_face(face, cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,
                       cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)


def text(c, s, x, y, face, size, color=WHITE, alpha=1.0, anchor="l", italic=False):
    font(c, face, size, italic)
    e = c.text_extents(s)
    if anchor == "c":
        x -= e.x_advance / 2
    elif anchor == "r":
        x -= e.x_advance
    c.move_to(x, y)
    c.set_source_rgba(*color, alpha)
    c.show_text(s)
    return e.x_advance


def tw(c, s, face, size, italic=False):
    font(c, face, size, italic)
    return c.text_extents(s).x_advance


def mixed_title(c, bold, ital, x, y, size, alpha, color_b=WHITE, color_i=BLUE_L, anchor="l"):
    """Titre mixte de la charte : « Mot *italique* » (Coda ExtraBold + serif italique)."""
    wb = tw(c, bold + " ", SANS_B, size)
    wi = tw(c, ital, SERIF, size * 1.18, True)
    if anchor == "c":
        x -= (wb + wi) / 2
    text(c, bold + " ", x, y, SANS_B, size, color_b, alpha)
    text(c, ital, x + wb, y, SERIF, size * 1.18, color_i, alpha, italic=True)


def card_edges(c, w, h, r, alpha):
    """Bord de verre : filet blanc + reflet fin en haut (pas de lueur)."""
    rrect(c, -w / 2, -h / 2, w, h, r)
    c.set_source_rgba(1, 1, 1, 0.30 * alpha)
    c.set_line_width(2)
    c.stroke()
    c.move_to(-w / 2 + r, -h / 2 + 1.5)
    c.line_to(w / 2 - r, -h / 2 + 1.5)
    c.set_source_rgba(1, 1, 1, 0.35 * alpha)
    c.set_line_width(1.5)
    c.stroke()


def glass_card(cv, cx, cy, w, h, r=36, rot=0.0, sc=1.0, alpha=1.0, content=None, tint=0.32):
    """Carte en verre complète : ombre, verre flouté, bord, puis contenu (repère centré)."""
    if alpha <= 0.002:
        return

    def path(c):
        place(c, cx, cy, rot, sc)
        rrect(c, -w / 2, -h / 2, w, h, r)

    cv.shadow(path, 0.32 * alpha)
    cv.glass(path, alpha, tint)

    def deco(c):
        place(c, cx, cy, rot, sc)
        card_edges(c, w, h, r, alpha)
        if content:
            content(c, alpha)
    cv.draw(deco)


def toggle(c, x, y, on, alpha, w=84, h=48):
    """Interrupteur façon iOS, accent bleu BEN&FIT. on: 0..1 (animé)."""
    rrect(c, x, y, w, h, h / 2)
    off = (1, 1, 1)
    col = tuple(off[i] * (1 - on) + BLUE[i] * on for i in range(3))
    c.set_source_rgba(*col, (0.22 * (1 - on) + 1.0 * on) * alpha)
    c.fill()
    kx = x + h / 2 + (w - h) * eio(on)
    c.arc(kx, y + h / 2, h / 2 - 5, 0, 2 * math.pi)
    c.set_source_rgba(1, 1, 1, alpha)
    c.fill()


def marker_arrow(c, x0, y0, x1, y1, prog, alpha, color=WHITE, width=5):
    """Flèche au feutre qui se dessine (légère courbe)."""
    prog = clamp(prog)
    if prog <= 0:
        return
    mx, my = (x0 + x1) / 2 + (y1 - y0) * 0.25, (y0 + y1) / 2 - (x1 - x0) * 0.25
    pts = []
    n = 30
    for i in range(int(n * prog) + 1):
        u = i / n
        px = (1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1
        py = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1
        pts.append((px, py))
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_source_rgba(*color, alpha)
    c.set_line_width(width)
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.stroke()
    if prog > 0.85 and len(pts) > 2:
        (ax, ay), (bx, by) = pts[-3], pts[-1]
        ang = math.atan2(by - ay, bx - ax)
        k = (prog - 0.85) / 0.15
        for d in (2.5, -2.5):
            c.move_to(bx, by)
            c.line_to(bx - 26 * k * math.cos(ang + d / 6), by - 26 * k * math.sin(ang + d / 6))
        c.stroke()


# ================================================================== EFFETS
def fx_toggles(cv, t, rows=("Échauffement", "Allure à 80 %", "WOD fini debout"), dur=4.6,
               cy=1240, step=0.65, t_first=0.7):
    """Carte d'interrupteurs qui s'allument un par un (checklist « une étape = un toggle »)."""
    a = env(t, dur)
    if a <= 0:
        return
    w, rh = 640, 92
    h = rh * len(rows) + 48
    cx = W / 2
    y = cy + 40 * (1 - eo(t / 0.45))

    def content(c, al):
        for i, r in enumerate(rows):
            yy = -h / 2 + 24 + i * rh
            on = eo((t - t_first - i * step) / 0.25)
            text(c, r, -w / 2 + 44, yy + rh / 2 + 14, SANS_B, 40, WHITE, al * (0.65 + 0.35 * on))
            toggle(c, w / 2 - 44 - 84, yy + rh / 2 - 24, on, al)
            if i < len(rows) - 1:
                c.move_to(-w / 2 + 44, yy + rh)
                c.line_to(w / 2 - 44, yy + rh)
                c.set_source_rgba(1, 1, 1, 0.12 * al)
                c.set_line_width(1.5)
                c.stroke()
    glass_card(cv, cx, y, w, h, 40, rot=-2.0, alpha=a, content=content)


def fx_graphe(cv, t, label="ALLURE TENUE", start=21, end=82, dur=5.0, cy=1230,
              pts=(0.0, 0.10, 0.18, 0.15, 0.32, 0.44, 0.40, 0.62, 0.78, 1.0)):
    """Carte graphe : la courbe se trace pendant que le chiffre compte."""
    a = env(t, dur)
    if a <= 0:
        return
    w, h = 720, 470
    p = eio((t - 0.5) / 2.6)
    val = round(start + (end - start) * p)

    def content(c, al):
        text(c, label, -w / 2 + 44, -h / 2 + 70, SANS_B, 30, BLUE_L, al)
        n = text(c, str(val), w / 2 - 44 - 46, -h / 2 + 118, NUM, 112, WHITE, al, "r")
        text(c, "%", w / 2 - 44, -h / 2 + 118, NUM, 56, WHITE, al, "r")
        gx0, gx1, gy0, gy1 = -w / 2 + 44, w / 2 - 44, h / 2 - 50, -h / 2 + 170
        c.set_line_width(1.2)
        for k in range(4):  # 3 repères discrets, pas de grille chargée
            yy = gy0 + (gy1 - gy0) * k / 3
            c.move_to(gx0, yy)
            c.line_to(gx1, yy)
            c.set_source_rgba(1, 1, 1, 0.08 * al)
            c.stroke()
        P = [(gx0 + (gx1 - gx0) * i / (len(pts) - 1), gy0 + (gy1 - gy0) * v) for i, v in enumerate(pts)]
        # trace jusqu'à p
        tot = (len(P) - 1) * p
        k = int(tot)
        fr = tot - k
        path = P[:k + 1]
        if k < len(P) - 1:
            path.append((P[k][0] + (P[k + 1][0] - P[k][0]) * fr, P[k][1] + (P[k + 1][1] - P[k][1]) * fr))
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(*path[0])
        for q in path[1:]:
            c.line_to(*q)
        c.set_source_rgba(*BLUE, al)
        c.set_line_width(7)
        c.stroke()
        hx, hy = path[-1]
        c.arc(hx, hy, 13, 0, 2 * math.pi)
        c.set_source_rgba(1, 1, 1, al)
        c.fill()
        c.arc(hx, hy, 13, 0, 2 * math.pi)
        c.set_source_rgba(*BLUE, al)
        c.set_line_width(5)
        c.stroke()
    glass_card(cv, W / 2, cy + 40 * (1 - eo(t / 0.45)), w, h, 40, rot=1.5, alpha=a, content=content)


def fx_focus(cv, t, items=(("01", "BUILD", "force"), ("02", "RUN", "moteur"), ("03", "PERFORM", "intensité"),
                          ("04", "MOVE", "mobilité")), dur=5.6, step=1.05, cy=1180, note="tu es ici"):
    """Liste « focus » : l'étape en cours est nette et agrandie, les autres floues ; les étapes
    passées s'allument. Idéal pour un Reel en chapitres (les 4 piliers)."""
    a = env(t, dur)
    if a <= 0:
        return
    n = len(items)
    raw = max(0.0, (t - 0.5) / step)
    cur = min(int(raw), n - 1)
    mv = eio((raw - cur) / 0.3) if cur > 0 else 1.0
    pos = (cur - 1) + mv if cur > 0 else 0.0
    rh = 104
    y0 = cy - rh * (n - 1) / 2 + 40 * (1 - eo(t / 0.45))
    for i, (num, word, ital) in enumerate(items):
        d = abs(i - pos) if i != cur else 0
        focus = 1.0 if i == cur else 0.0
        if i == cur and cur > 0:
            focus = mv
        if i == cur - 1:
            focus = 1 - mv
        sc = 0.88 + 0.14 * focus
        w = 660
        yy = y0 + i * rh
        al = a * (0.45 + 0.55 * focus)
        done = 1.0 if i < cur else (eo((t - 0.5 - (i + 0.8) * step) / 0.25) if i == cur else 0.0)

        def content(c, al2, num=num, word=word, ital=ital, done=done, focus=focus):
            text(c, num, -w / 2 + 34, 15, NUM, 34, BLUE_L, al2)
            x = -w / 2 + 96
            x += text(c, word + " ", x, 16, SANS_B, 40, WHITE, al2)
            text(c, ital, x, 16, SERIF, 46, BLUE_L, al2, italic=True)
            toggle(c, w / 2 - 34 - 84, -24, done, al2)
        glass_card(cv, W / 2, yy, w, 84, 42, rot=0, sc=sc, alpha=al, content=content,
                   tint=0.26 + 0.16 * focus)
    # annotation manuscrite qui suit l'étape active
    ya = y0 + pos * rh

    def note_fn(c):
        ap = a * eo((t - 0.9) / 0.4)
        marker_arrow(c, 250, ya + 150, 175, ya + 52, eo((t - 0.9) / 0.5), ap)
        c.save()
        c.translate(262, ya + 168)
        c.rotate(math.radians(-4))
        text(c, note, 0, 0, HAND, 40, WHITE, ap)
        c.restore()
    cv.draw(note_fn)


def fx_preuve(cv, t, label="SQUAT · EN 12 SEMAINES", prefix="+", value=20, unit=" kg",
              sub="de 80 à 100 kg", note="sans forcer", dur=4.8, cy=1240):
    """Carte « preuve » : gros chiffre qui compte + sous-titre italique + annotation au feutre."""
    a = env(t, dur)
    if a <= 0:
        return
    w, h = 660, 330
    p = eo((t - 0.4) / 1.4)
    v = round(value * p)

    def content(c, al):
        text(c, label, -w / 2 + 44, -h / 2 + 66, SANS_B, 28, BLUE_L, al)
        x = -w / 2 + 40
        x += text(c, f"{prefix}{v}", x, 52, NUM, 150, WHITE, al)
        text(c, unit, x, 52, NUM, 80, WHITE, al)
        # trait de feutre sous le chiffre
        ul = eo((t - 1.7) / 0.4)
        if ul > 0:
            c.move_to(-w / 2 + 44, 80)
            c.curve_to(-w / 2 + 160, 72, -w / 2 + 300, 88, -w / 2 + 44 + 360 * ul, 76)
            c.set_source_rgba(*BLUE, al)
            c.set_line_width(9)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.stroke()
        text(c, sub, -w / 2 + 44, h / 2 - 44, SERIF, 46, WHITE, al * 0.9, italic=True)
    y = cy + 40 * (1 - eo(t / 0.45))
    glass_card(cv, W / 2, y, w, h, 40, rot=-1.5, alpha=a, content=content)

    def note_fn(c):
        ap = a * eo((t - 2.0) / 0.4)
        marker_arrow(c, 830, y + 330, 760, y + 175, eo((t - 2.0) / 0.5), ap)
        c.save()
        c.translate(650, y + 380)
        c.rotate(math.radians(-5))
        text(c, note, 0, 0, HAND, 44, WHITE, ap)
        c.restore()
    cv.draw(note_fn)


_PAGES = [
    "Tu pars trop vite. Le premier round te semble facile, alors tu accélères. Trois minutes plus tard, "
    "tout brûle et le reste du WOD devient une survie. Le problème n'est pas ton cardio, c'est ton",
    "La plupart des athlètes ratent leur WOD dans les deux premières minutes. Ils confondent intensité "
    "et précipitation. Ce qui sépare un bon temps d'un mauvais, c'est presque toujours le",
    "Respire par le nez au premier tour. Coupe tes séries avant l'échec. Vise des rounds réguliers. "
    "Trois règles simples qui changent tout, parce qu'elles parlent toutes du même sujet : le",
    "Les meilleurs ne vont pas plus vite au début. Ils perdent moins de temps à la fin. Regarde leurs "
    "splits : ils sont plats. Leur secret n'a rien de génétique, il s'appelle le",
]


def fx_matchcut(cv, t, word="PACING", dur=2.8, swap=0.2):
    """Match-cut : des pages de texte défilent en coupe sèche, le mot-clé reste verrouillé au centre."""
    if t < 0 or t > dur:
        return
    a = eo(t / 0.12) * (1 - eio((t - (dur - 0.18)) / 0.18))
    idx = int(t / swap) % len(_PAGES)
    rnd = np.random.default_rng(idx + 3)
    sc = 1.0 + 0.03 * ((t % swap) / swap)
    cv.paper(lambda c: c.rectangle(0, 0, W, H), a, (0.96, 0.96, 0.95))

    def page(c):
        c.translate(W / 2, H / 2)
        c.scale(sc, sc)
        c.rotate(math.radians(rnd.uniform(-1.5, 1.5)))
        c.translate(-W / 2, -H / 2)
        words = _PAGES[idx].split()
        size = 74
        font(c, SERIF, size)
        lines, line = [], ""
        for wd in words:
            if tw(c, line + " " + wd, SERIF, size) > W * 1.15 and line:
                lines.append(line)
                line = wd
            else:
                line = (line + " " + wd).strip()
        lines.append(line)
        # place la dernière ligne pour que le mot-clé tombe au centre
        lh = 96
        y_last = H / 2 + 26
        font(c, SANS_B, 90)
        pw = c.text_extents(word).x_advance + 56
        x_last = W / 2 - pw / 2 - 16 - tw(c, lines[-1], SERIF, size)
        for k, ln in enumerate(lines):
            yy = y_last - (len(lines) - 1 - k) * lh
            xx = x_last if k == len(lines) - 1 else x_last - rnd.uniform(0, 240) - 200
            text(c, ln, xx, yy, SERIF, size, (0.10, 0.11, 0.14), a * 0.92)
    cv.draw(page)
    # profondeur : bords flous
    blur_m = cv._mask(lambda c: (c.rectangle(0, 0, W, 560), c.rectangle(0, H - 560, W, 560)), 160)
    b = Canvas((np.clip(cv.f, 0, 1) * 255).astype(np.uint8)).blurred()
    cv.f = cv.f * (1 - blur_m * a) + b * blur_m * a

    def lock(c):
        font(c, SANS_B, 90)
        e = c.text_extents(word)
        pw, ph = e.x_advance + 56, 130
        rrect(c, W / 2 - pw / 2, H / 2 - ph / 2, pw, ph, 18)
        c.set_source_rgba(*BLUE, a)
        c.fill()
        text(c, word, W / 2, H / 2 + 36, SANS_B, 90, WHITE, a, "c")
    cv.draw(lock)


def fx_eventail(cv, t, cards=(("01", "Genoux", "qui rentrent"), ("02", "Talons", "qui décollent"),
                              ("03", "Dos", "qui s'arrondit")), dur=5.2, cy=1200, hero_at=3.0, hero=0):
    """Cartes-titres en éventail : elles sortent d'une pile, puis l'une passe devant."""
    a = env(t, dur)
    if a <= 0:
        return
    fan = eio((t - 0.35) / 0.7)
    hp = eio((t - hero_at) / 0.5)
    order = [i for i in range(len(cards)) if i != hero] + [hero]
    order = list(range(len(cards))) if hp < 0.5 else order
    for i in order:
        num, bold, ital = cards[i]
        off = i - (len(cards) - 1) / 2
        is_h = i == hero
        rot = off * 11 * fan * (1 - (hp if is_h else 0))
        x = W / 2 + off * 250 * fan * (1 - (hp if is_h else 0)) + (0 if not is_h else 0)
        yy = cy + abs(off) * 30 * fan - (60 * hp if is_h else -20 * hp)
        sc = 1.0 + (0.12 * hp if is_h else -0.06 * hp)
        al = a * (1 if is_h or hp == 0 else 1 - 0.45 * hp)

        def content(c, al2, num=num, bold=bold, ital=ital):
            text(c, num, -130, -150, NUM, 44, BLUE_L, al2)
            text(c, bold, -130, -20, SANS_B, 64, WHITE, al2)
            text(c, ital, -130, 50, SERIF, 52, BLUE_L, al2, italic=True)
            c.move_to(-130, 150)
            c.line_to(130, 150)
            c.set_source_rgba(*BLUE, al2)
            c.set_line_width(6)
            c.stroke()
        glass_card(cv, x, yy, 320, 420, 34, rot=rot, sc=sc, alpha=al, content=content)


def fx_epaule(cv, t, chips=(("AVANT", "5 km"), ("APRÈS", "10 km")), dur=4.4,
              spots=((860, 500, 6), (850, 800, -5)), gap=1.3):
    """Pastilles « par-dessus l'épaule » qui apparaissent à côté de la tête, un chiffre chacune."""
    for k, ((lab, val), (x, y, rot)) in enumerate(zip(chips, spots)):
        tt = t - k * gap
        a = env(tt, dur - k * gap)
        if a <= 0:
            continue
        sc = 0.85 + 0.15 * eo(tt / 0.3)

        def content(c, al, lab=lab, val=val):
            text(c, lab, 0, -38, SANS_B, 26, NAVY, al, "c")
            text(c, val, 0, 52, NUM, 92, NAVY, al, "c")

        def path(c, x=x, y=y, rot=rot, sc=sc):
            place(c, x, y, rot, sc)
            rrect(c, -140, -95, 280, 190, 30)
        cv.shadow(path, 0.30 * a, 24, 14)
        cv.paper(path, a, (1, 1, 1))

        def deco(c, x=x, y=y, rot=rot, sc=sc, a=a, content=content):
            place(c, x, y, rot, sc)
            content(c, a)
        cv.draw(deco)


EFFETS = {
    "toggles": (fx_toggles, 4.6),
    "graphe": (fx_graphe, 5.0),
    "focus": (fx_focus, 5.6),
    "preuve": (fx_preuve, 4.8),
    "matchcut": (fx_matchcut, 2.8),
    "eventail": (fx_eventail, 5.2),
    "epaule": (fx_epaule, 4.4),
}
