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

    def __init__(self, frame_uint8, person_mask=None):
        self.src = frame_uint8
        self.f = frame_uint8.astype(np.float32) / 255.0
        self._blur = None
        self._person = person_mask

    def person(self):
        """Masque de Bene (H, W) 0..1, calculé à la demande (segmentation.py) ou fourni à l'avance."""
        if self._person is None:
            import segmentation
            self._person = segmentation.mask(self.src)
        return self._person

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


# ================================================================== EFFETS — LOT 2 (19 nov. 2026)
# Inspirés de corbinsylk (split démo, anatomie) et justyn.ai (texte derrière, cadran, calendrier,
# carte barrée, téléphone) + liste « 17 video effects » (paper cut, doodle boil, phone mockup…).
PAPER = (0xFA / 255, 0xF7 / 255, 0xF0 / 255)


def charger_media(path, fps=30, max_s=6):
    """Charge un GIF ou une vidéo en liste d'images uint8 (pour fx_split / fx_telephone)."""
    import subprocess, json
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "json", path], capture_output=True, text=True)
    st = json.loads(pr.stdout)["streams"][0]
    w, h = st["width"], st["height"]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", str(max_s), "-vf", f"fps={fps}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    return [np.frombuffer(raw, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3) for i in range(n)]


def _cover(img, w, h):
    """Recadre une image pour remplir w x h (comme object-fit: cover)."""
    im = Image.fromarray(img)
    sc = max(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * sc + 0.5)), max(1, int(im.height * sc + 0.5))), Image.BILINEAR)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return np.asarray(im.crop((x0, y0, x0 + w, y0 + h))).astype(np.float32) / 255.0


def _paste_media(cv, img, x, y, w, h, r, alpha, rot=0.0):
    """Colle une image arrondie (et éventuellement tournée) dans le Reel."""
    tile = _cover(img, int(w), int(h))
    big = np.zeros((H, W, 3), np.float32)
    # placement par transformée affine (PIL) pour gérer la rotation
    t_im = Image.fromarray((tile * 255).astype(np.uint8))
    canvas = Image.new("RGB", (W, H))
    if rot:
        t_im = t_im.rotate(-rot, resample=Image.BICUBIC, expand=True)
    cx, cy = x + w / 2, y + h / 2
    canvas.paste(t_im, (int(cx - t_im.width / 2), int(cy - t_im.height / 2)))
    big = np.asarray(canvas).astype(np.float32) / 255.0
    m = cv._mask(lambda c: (place(c, cx, cy, rot), rrect(c, -w / 2, -h / 2, w, h, r))) * alpha
    cv.f = cv.f * (1 - m) + big * m


def _behind(cv, draw_fn, alpha=1.0):
    """Dessine un calque cairo DERRIÈRE Bene (le masque de la personne passe devant)."""
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    draw_fn(c)
    s.flush()
    a = np.ndarray((H, W, 4), np.uint8, s.get_data()).astype(np.float32) / 255.0
    keep = (1 - cv.person())[..., None] * alpha
    cv.f = cv.f * (1 - a[..., 3:4] * keep) + a[..., [2, 1, 0]] * keep


def fx_derriere(cv, t, lignes=("1 2 3",), face=NUM, y=960, interligne=0.92, dur=3.8, step=0.35,
                color=WHITE, italic=False, max_size=560):
    """Texte géant DERRIÈRE Bene (il passe devant les lettres). Les mots arrivent un par un."""
    a = env(t, dur, 0.15, 0.3)
    if a <= 0:
        return
    words_all = [(li, wd) for li, ln in enumerate(lignes) for wd in ln.split()]

    def draw(c):
        k = 0
        yy = y
        sizes = []
        for ln in lignes:
            size = max_size
            while tw(c, ln, face, size, italic) > 1000 and size > 60:
                size -= 10
            sizes.append(size)
        tot = sum(s * interligne for s in sizes)
        yy = y - tot + sizes[0] * interligne
        for li, ln in enumerate(lignes):
            size = sizes[li]
            x = W / 2 - tw(c, ln, face, size, italic) / 2
            for wd in ln.split():
                p = eo((t - k * step) / 0.25)
                if p > 0:
                    c.save()
                    wdw = tw(c, wd, face, size, italic)
                    c.translate(x + wdw / 2, yy - size * 0.35)
                    sc = 1.08 - 0.08 * p
                    c.scale(sc, sc)
                    text(c, wd, -wdw / 2, size * 0.35, face, size, color, a * p, italic=italic)
                    c.restore()
                x += tw(c, wd + " ", face, size, italic)
                k += 1
            yy += size * interligne
    _behind(cv, draw)


def fx_decoupe(cv, t, dur=4.2, note="ça, c'est toi", doodles=True, dim=0.35):
    """Contour « découpé » blanc autour de Bene (effet sticker / paper cut) + gribouillis qui
    tremblent (doodle boil). Le fond s'assombrit légèrement."""
    a = env(t, dur, 0.25, 0.3)
    if a <= 0:
        return
    pm = cv.person()
    small = Image.fromarray((pm[::2, ::2] * 255).astype(np.uint8))
    dil = np.asarray(small.filter(ImageFilter.MaxFilter(9)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    ring = np.clip(dil - pm, 0, 1)[..., None]
    keep = 1 - pm[..., None]
    cv.f = cv.f * (1 - dim * a * keep) + cv.f * 0  # fond assombri, Bene intact
    cv.f = cv.f * (1 - ring * a) + ring * a
    if not doodles:
        return
    boil = int(t * 8)
    rnd = np.random.default_rng(boil)

    def jit(v):
        return v + rnd.uniform(-3, 3)

    def dfn(c):
        al = a * eo((t - 0.3) / 0.3)
        c.set_source_rgba(1, 1, 1, al)
        c.set_line_width(6)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        # étoile à droite de la tête
        cx, cy, R = 860, 520, 46
        for i in range(4):
            ang = i * math.pi / 4
            c.move_to(jit(cx - R * math.cos(ang)), jit(cy - R * math.sin(ang)))
            c.line_to(jit(cx + R * math.cos(ang)), jit(cy + R * math.sin(ang)))
        c.stroke()
        # traits de mouvement à gauche
        for i in range(3):
            c.move_to(jit(150), jit(640 + i * 50))
            c.line_to(jit(230 - i * 15), jit(625 + i * 50))
        c.stroke()
        # gribouillis en spirale en haut à gauche
        c.move_to(jit(170), jit(420))
        for i in range(1, 22):
            ang = i * 0.6
            rr = 6 + i * 2.2
            c.line_to(jit(200 + rr * math.cos(ang)), jit(430 + rr * math.sin(ang)))
        c.stroke()
        if note:
            c.save()
            c.translate(jit(600), jit(420))
            c.rotate(math.radians(-6))
            text(c, note, 0, 0, HAND, 52, WHITE, al)
            c.restore()
            marker_arrow(c, 640, 445, 560, 540, 1.0, al)
    cv.draw(dfn)


def fx_split(cv, t, media, mots=(), dur=5.0, fps=30):
    """Écran séparé « démo en haut / Bene en bas » : une vidéo ou un GIF arrive en haut,
    Bene glisse en bas, un mot-clé bleu s'affiche sous la démo. mots = [(t_debut, "mot"), …]"""
    if t < 0 or t > dur:
        return
    p = eio(t / 0.45) * (1 - eio((t - (dur - 0.4)) / 0.4))
    off = int(560 * p)
    src = cv.f.copy()
    deep = np.array(DEEP, np.float32)
    cv.f[:] = deep
    if off < H:
        cv.f[off:] = src[:H - off]
    # zone haute sombre derrière la démo
    if off > 0:
        cv.f[:off] = deep
    img = media[int(t * fps) % len(media)]
    pw, ph = 960, 720
    py = 110 - (1 - p) * 900
    _paste_media(cv, img, (W - pw) / 2, py, pw, ph, 34, 1.0)

    def deco(c):
        rrect(c, (W - pw) / 2, py, pw, ph, 34)
        c.set_source_rgba(1, 1, 1, 0.25 * p)
        c.set_line_width(2)
        c.stroke()
        cur = None
        for t0, m in mots:
            if t >= t0:
                cur = (t0, m)
        if cur and p > 0.6:
            q = eo((t - cur[0]) / 0.15)
            font(c, SANS_B, 58)
            e = c.text_extents(cur[1])
            bw = e.x_advance + 44
            rrect(c, W / 2 - bw / 2, py + ph + 26, bw, 84, 12)
            c.set_source_rgba(*BLUE, q * p)
            c.fill()
            text(c, cur[1], W / 2, py + ph + 88, SANS_B, 58, WHITE, q * p, "c")
    cv.draw(deco)


def fx_macros(cv, t, kcal=2450, macros=(("Protéines", 160), ("Glucides", 280), ("Lipides", 75)),
              titre=("Ta", "journée"), dur=5.0, cy=1260):
    """Carte nutrition : anneau qui se remplit + kcal qui comptent + grammes par macro."""
    a = env(t, dur)
    if a <= 0:
        return
    w, h = 820, 470
    p = eio((t - 0.4) / 1.8)

    def content(c, al):
        mixed_title(c, titre[0], titre[1], -w / 2 + 44, -h / 2 + 78, 44, al)
        cx, cy2, R = -w / 2 + 200, 40, 125
        c.new_path()
        c.set_line_width(26)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.arc(cx, cy2, R, 0, 2 * math.pi)
        c.set_source_rgba(1, 1, 1, 0.14 * al)
        c.stroke()
        if p > 0.01:
            c.arc(cx, cy2, R, -math.pi / 2, -math.pi / 2 + 2 * math.pi * 0.92 * p)
            c.set_source_rgba(*BLUE, al)
            c.stroke()
        text(c, f"{round(kcal * p):,}".replace(",", " "), cx, cy2 + 22, NUM, 64, WHITE, al, "c")
        text(c, "kcal", cx, cy2 + 62, SANS, 28, BLUE_L, al, "c")
        x0 = -w / 2 + 390
        for i, (lab, g) in enumerate(macros):
            yy = -40 + i * 100
            q = eo((t - 0.8 - i * 0.3) / 0.6)
            text(c, lab, x0, yy, SANS_B, 32, BLUE_L, al)
            text(c, f"{round(g * q)} g", w / 2 - 44, yy + 4, NUM, 52, WHITE, al, "r")
            c.move_to(x0, yy + 26)
            c.line_to(x0 + (w / 2 - 44 - x0) * q, yy + 26)
            c.set_source_rgba(*BLUE, al)
            c.set_line_width(5)
            c.stroke()
    glass_card(cv, W / 2, cy + 40 * (1 - eo(t / 0.45)), w, h, 40, rot=-1.0, alpha=a, content=content)


def fx_cadran(cv, t, label="RPE", valeur=8, maxi=10, gauche="FACILE", droite="MAX", dur=4.6, cy=1250):
    """Cadran d'effort (molette) : l'aiguille tourne jusqu'à la valeur (ex. RPE 8/10)."""
    a = env(t, dur)
    if a <= 0:
        return
    w = h = 560
    p = eio((t - 0.5) / 1.3)
    v = valeur * p
    A0, A1 = math.radians(135), math.radians(405)

    def content(c, al):
        R = 190
        cy2 = 10
        text(c, label, 0, -h / 2 + 66, SANS_B, 34, BLUE_L, al, "c")
        c.new_path()
        c.set_line_width(14)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.arc(0, cy2, R, A0, A1)
        c.set_source_rgba(1, 1, 1, 0.14 * al)
        c.stroke()
        if v > 0.01:
            c.arc(0, cy2, R, A0, A0 + (A1 - A0) * v / maxi)
            c.set_source_rgba(*BLUE, al)
            c.stroke()
        for i in range(maxi + 1):
            ang = A0 + (A1 - A0) * i / maxi
            r1, r2 = R - 34, R - (52 if i % 5 == 0 else 44)
            c.move_to(r1 * math.cos(ang), cy2 + r1 * math.sin(ang))
            c.line_to(r2 * math.cos(ang), cy2 + r2 * math.sin(ang))
            c.set_source_rgba(1, 1, 1, 0.55 * al)
            c.set_line_width(3)
            c.stroke()
        ang = A0 + (A1 - A0) * v / maxi
        c.move_to(0, cy2)
        c.line_to((R - 70) * math.cos(ang), cy2 + (R - 70) * math.sin(ang))
        c.set_source_rgba(1, 1, 1, al)
        c.set_line_width(8)
        c.stroke()
        c.arc(0, cy2, 22, 0, 2 * math.pi)
        c.set_source_rgba(*NAVY, al)
        c.fill_preserve()
        c.set_source_rgba(1, 1, 1, al)
        c.set_line_width(4)
        c.stroke()
        text(c, gauche, -R * 0.72, cy2 + R * 0.95, SANS_B, 24, BLUE_L, al, "c")
        text(c, droite, R * 0.72, cy2 + R * 0.95, SANS_B, 24, BLUE_L, al, "c")
        text(c, f"{round(v)}/{maxi}", 0, cy2 + 150, NUM, 70, WHITE, al, "c")
    glass_card(cv, W / 2, cy + 40 * (1 - eo(t / 0.45)), w, h, 48, rot=2.0, alpha=a, content=content)


def fx_barre(cv, t, titre="Pour progresser", barres=("Plus de séances", "S'entraîner tous les jours"),
             juste="Mieux récupérer", dur=5.2, cy=1250):
    """Carte papier : des idées reçues se font barrer au feutre, la bonne réponse s'écrit à la main."""
    a = env(t, dur)
    if a <= 0:
        return
    w, h = 720, 120 + 86 * (len(barres) + 1) + 40
    cx, y = W / 2, cy + 40 * (1 - eo(t / 0.45))

    def path(c):
        place(c, cx, y, -2.0)
        rrect(c, -w / 2, -h / 2, w, h, 24)
    cv.shadow(path, 0.3 * a)
    cv.paper(path, a, PAPER)

    def deco(c):
        place(c, cx, y, -2.0)
        text(c, titre, 0, -h / 2 + 86, SERIF, 64, NAVY, a, "c", italic=True)
        for i, b in enumerate(barres):
            yy = -h / 2 + 180 + i * 86
            bw = text(c, b, -tw(c, b, SANS_B, 40) / 2, yy, SANS_B, 40, NAVY, a * 0.85)
            q = eo((t - 0.9 - i * 0.6) / 0.35)
            if q > 0:
                x0 = -bw / 2 - 12
                c.move_to(x0, yy - 12)
                c.curve_to(x0 + bw * 0.3, yy - 18, x0 + bw * 0.6, yy - 6, x0 + (bw + 24) * q, yy - 14)
                c.set_source_rgba(*BLUE, a)
                c.set_line_width(8)
                c.set_line_cap(cairo.LINE_CAP_ROUND)
                c.stroke()
        q = eo((t - 0.9 - len(barres) * 0.6 - 0.2) / 0.4)
        if q > 0:
            yy = -h / 2 + 180 + len(barres) * 86 + 6
            c.save()
            c.translate(0, yy)
            c.rotate(math.radians(-3))
            text(c, juste, 0, 0, HAND, 54, BLUE, a * q, "c")
            c.restore()
    cv.draw(deco)


def fx_telephone(cv, t, media, dur=4.6, cx=720, cy=1180, rot=6.0, fps=30):
    """Téléphone flottant qui monte dans le cadre et lit une vidéo (exercice, extrait de Reel…)."""
    a = env(t, dur, 0.4, 0.35)
    if a <= 0:
        return
    pw, ph = 380, 780
    y = cy + 500 * (1 - eo(t / 0.5))

    def body(c):
        place(c, cx, y, rot)
        rrect(c, -pw / 2, -ph / 2, pw, ph, 58)
    cv.shadow(body, 0.4 * a, 30, 22)
    cv.paper(body, a, (0.05, 0.05, 0.06))
    img = media[int(t * fps) % len(media)]
    # écran (position approximée sans rotation du contenu au-delà de la rotation du cadre)
    sw, sh = pw - 26, ph - 26
    _paste_media(cv, img, cx - sw / 2 + (y - cy) * math.sin(math.radians(rot)) * 0,
                 y - sh / 2, sw, sh, 46, a, rot)

    def deco(c):
        place(c, cx, y, rot)
        rrect(c, -46, -ph / 2 + 26, 92, 26, 13)
        c.set_source_rgba(0, 0, 0, a)
        c.fill()
        rrect(c, -pw / 2, -ph / 2, pw, ph, 58)
        c.set_source_rgba(1, 1, 1, 0.18 * a)
        c.set_line_width(2)
        c.stroke()
    cv.draw(deco)


def fx_calendrier(cv, t, jours=("L", "M", "M", "J", "V", "S", "D"),
                  seances=((0, "BUILD"), (1, "RUN"), (3, "PERFORM"), (4, "MOVE"), (5, "RUN")),
                  repos=6, mot="repos", dur=5.4, cy=1330):
    """Calendrier papier à spirale : les séances de la semaine se posent une à une, le jour de repos
    est entouré au feutre."""
    a = env(t, dur)
    if a <= 0:
        return
    w, h = 940, 470
    cx, y = W / 2, cy + 40 * (1 - eo(t / 0.45))

    def path(c):
        place(c, cx, y, -1.5)
        rrect(c, -w / 2, -h / 2, w, h, 22)
    cv.shadow(path, 0.3 * a)
    cv.paper(path, a, PAPER)

    def deco(c):
        place(c, cx, y, -1.5)
        # spirale
        for i in range(16):
            x = -w / 2 + 60 + i * (w - 120) / 15
            c.arc(x, -h / 2 + 2, 11, math.pi, 2 * math.pi)
            c.set_source_rgba(0.15, 0.15, 0.18, a)
            c.set_line_width(5)
            c.stroke()
        colw = (w - 80) / 7
        x0 = -w / 2 + 40
        for i, j in enumerate(jours):
            text(c, j, x0 + colw * (i + 0.5), -h / 2 + 80, SANS_B, 36, NAVY, a * 0.8, "c")
            c.move_to(x0 + colw * i, -h / 2 + 105)
            c.line_to(x0 + colw * i, h / 2 - 30)
            c.set_source_rgba(*NAVY, 0.12 * a)
            c.set_line_width(1.5)
            c.stroke()
        for k, (d, lab) in enumerate(seances):
            q = eo((t - 0.6 - k * 0.32) / 0.25)
            if q <= 0:
                continue
            bx = x0 + colw * d + 8
            by = -h / 2 + 130 + (k % 2) * 40
            bh = 170
            rrect(c, bx, by + (1 - q) * 20, colw - 16, bh, 12)
            c.set_source_rgba(*BLUE, a * q)
            c.fill()
            c.save()
            c.translate(bx + (colw - 16) / 2 + 9, by + bh / 2 + (1 - q) * 20)
            c.rotate(-math.pi / 2)
            text(c, lab, 0, 0, SANS_B, 26, WHITE, a * q, "c")
            c.restore()
        q = eo((t - 0.6 - len(seances) * 0.32 - 0.2) / 0.5)
        if q > 0 and repos is not None:
            ex = x0 + colw * (repos + 0.5)
            pts = []
            for i in range(int(40 * q) + 1):
                ang = -math.pi / 2 + 2.2 * math.pi * i / 40
                pts.append((ex + 62 * math.cos(ang), 0 + 130 * math.sin(ang)))
            c.move_to(*pts[0])
            for pp in pts[1:]:
                c.line_to(*pp)
            c.set_source_rgba(*BLUE, a)
            c.set_line_width(6)
            c.stroke()
            c.save()
            c.translate(ex - 10, h / 2 - 40)
            c.rotate(math.radians(-6))
            text(c, mot, 0, 0, SERIF, 64, BLUE, a * q, "c", italic=True)
            c.restore()
    cv.draw(deco)


EFFETS.update({
    "derriere": (fx_derriere, 3.8),
    "decoupe": (fx_decoupe, 4.2),
    "split": (fx_split, 5.0),
    "macros": (fx_macros, 5.0),
    "cadran": (fx_cadran, 4.6),
    "barre": (fx_barre, 5.2),
    "telephone": (fx_telephone, 4.6),
    "calendrier": (fx_calendrier, 5.4),
})
