"""Reel « séance à deux » BEN&FIT × Apocalypse Training (26 nov. 2026), ~1 min, sans sous-titres.

Séance haltéro filmée avec son ami d'Apocalypse Training : échauffement → bloc 1 → bloc 2 → bloc 3 → renfort.
Montage très dynamique pour qu'on regarde jusqu'au bout :
  - chapitres animés (titre Anton dans un bandeau bleu qui balaie) ; PAS de barre de progression (Bene : « vraiment moche ») ;
  - zooms plafonnés à ~1,45× et agrandissement Lanczos (au-delà, l'image devient molle) ; export CRF 10 ;
  - rampes de vitesse : vitesse réelle sur la tirée, **ralenti 0,4–0,5 sur la réception** (rushs 60 i/s = vraies images),
    punch-in sur la réception, petit flash sur les plus belles ;
  - écran partagé Bene | Apocalypse sur la même répétition ;
  - transitions « coup de fouet » (flou de mouvement) entre les chapitres ;
  - deux répliques gardées avec leur son (« passation de pouvoir », « sponsorisé par Apocalypse ») ;
  - carte de fin co-branding.
Couleurs d'origine (BT.709 conservé). Son : ambiance des rushs basse (musique de la salle), répliques à -14 LUFS,
whooshs discrets sur les transitions ; Bene ajoute son son tendance.

  python build_seance.py plan | stills T… | video
"""
import os, sys, json, math, subprocess, wave
import numpy as np
import cairo
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/seance")
os.makedirs(WORK, exist_ok=True)
W, H, FPS, SRC_FPS = 1080, 1920, 30, 60
R = lambda n: os.path.join(RUSH, f"VID_20261126_{n}.mp4")
NAVY = (0.04, 0.125, 0.42)
CHAPITRES = ["ÉCHAUFFEMENT", "BLOC 1", "BLOC 2", "BLOC 3", "RENFORT"]


def S(clip, a, b, chap, vit=1.0, ramp=None, zoom=1.0, zk=None, cx=0.5, cy=0.5, flash=(), voix=False, titre=None,
      sous=None, split=None):
    """Un plan. ramp = [(t_source, vitesse), …] (vitesse constante par morceaux) ; zk = [(t_source, zoom), …]."""
    return dict(clip=clip, a=a, b=b, chap=chap, ramp=ramp or [(a, vit)], zoom=zoom, zk=zk, cx=cx, cy=cy,
                flash=list(flash), voix=voix, titre=titre, sous=sous, split=split)


# ------------------------------------------------------------------ montage (temps source en secondes)
PLANS = [
    # ACCROCHE : la plus belle réception de Bene, tirée en vitesse réelle puis ralenti sur la réception
    S("144615", 42.20, 44.60, 0, ramp=[(42.20, 1.0), (42.85, 0.4), (43.60, 1.0)],
      zk=[(42.2, 1.12), (42.95, 1.12), (43.15, 1.42), (44.6, 1.34)], cy=0.42, flash=[43.10], titre="hook"),
    S("155337", 14.45, 16.15, 0, voix=True, zoom=1.0),                      # « …sponsorisé par Apocalypse. »
    # ÉCHAUFFEMENT : mobilité accélérée, barre à vide
    S("142850", 19.6, 22.0, 0, vit=1.8, zoom=1.3, cx=0.45, cy=0.55, titre="chap", sous="MOBILITÉ"),
    S("142735", 28.0, 30.4, 0, vit=1.8, zoom=1.7, cx=0.36, cy=0.6),
    S("142850", 13.0, 15.4, 0, vit=1.8, zoom=1.3, cx=0.48),
    S("143001", 7.8, 10.2, 0, vit=1.25, zoom=1.15, cy=0.45),
    S("143137", 4.4, 6.4, 0, vit=1.25, zoom=1.15, cy=0.45),
    # BLOC 1 : arraché
    S("143649", 9.6, 11.6, 1, ramp=[(9.6, 1.0), (10.15, 0.45), (10.8, 1.0)],
      zk=[(9.6, 1.12), (10.2, 1.12), (10.4, 1.38), (11.6, 1.3)], cy=0.42, titre="chap", sous="ARRACHÉ"),
    S("143824", 8.9, 10.9, 1, ramp=[(8.9, 1.0), (9.35, 0.45), (10.0, 1.0)],
      zk=[(8.9, 1.12), (9.4, 1.12), (9.6, 1.38), (10.9, 1.3)], cy=0.42),
    S("144615", 31.3, 33.9, 1, ramp=[(31.3, 1.0), (31.95, 0.5), (32.6, 1.0)],
      zk=[(31.3, 1.1), (32.15, 1.1), (32.35, 1.4), (33.9, 1.32)], cy=0.42, flash=[32.3]),
    S("144752", 9.20, 10.80, 1, voix=True, zoom=1.2, cy=0.5),              # « Ouais il est pas mal de passer au-dessus »
    S("144752", 18.10, 19.35, 1, voix=True, zoom=1.25, cy=0.45),          # « …passation de pouvoir »
    S("144752", 25.0, 27.0, 1, ramp=[(25.0, 1.0), (25.5, 0.5), (26.1, 1.0)],
      zk=[(25.0, 1.12), (25.6, 1.12), (25.8, 1.4), (27.0, 1.32)], cy=0.42),
    S("144615", 37.1, 39.0, 1, split=dict(clip="144752", a=35.3, cxs=(0.50, 0.50)), zoom=1.0),  # écran partagé
    # BLOC 2 : autre plateau, autre angle
    S("145519", 1.6, 3.6, 2, zoom=1.35, cy=0.45, titre="chap", sous="ARRACHÉ"),
    S("145519", 14.2, 16.8, 2, ramp=[(14.2, 1.0), (14.7, 0.5), (15.3, 1.0)],
      zk=[(14.2, 1.3), (14.8, 1.3), (15.0, 1.42), (16.8, 1.38)], cy=0.42, flash=[15.0]),
    S("145519", 23.0, 24.6, 2, zoom=1.0),                                   # Bene revient vers la caméra
    S("145519", 31.05, 32.6, 2, voix=True, zoom=1.3, cy=0.48),             # « Oh, tu passes »
    S("145519", 32.6, 34.6, 2, ramp=[(32.6, 1.0), (33.1, 0.5), (33.7, 1.0)],
      zk=[(32.6, 1.3), (33.2, 1.3), (33.4, 1.42), (34.6, 1.38)], cy=0.42),
    # BLOC 3 : épaulé-jeté
    S("151817", 52.9, 55.0, 3, ramp=[(52.9, 1.0), (53.5, 0.45), (54.3, 1.0)],
      zk=[(52.9, 1.1), (53.6, 1.1), (53.8, 1.38), (55.0, 1.3)], cy=0.45, titre="chap", sous="ÉPAULÉ-JETÉ"),
    S("152712", 25.15, 28.25, 3, voix=True, zk=[(25.15, 1.15), (28.25, 1.3)], cy=0.45),  # Bene explique le tirage lourd
    S("151407", 33.0, 36.4, 3, ramp=[(33.0, 1.0), (34.6, 0.5), (35.4, 1.0)],
      zk=[(33.0, 1.3), (34.7, 1.3), (34.9, 1.4), (36.4, 1.38)], cy=0.45),  # épaulé, autre angle
    S("151631", 50.9, 53.0, 3, ramp=[(50.9, 1.0), (51.9, 0.45), (52.6, 1.0)],
      zk=[(50.9, 1.1), (51.95, 1.1), (52.15, 1.38), (53.0, 1.3)], cy=0.45),
    S("151817", 58.2, 61.3, 3, ramp=[(58.2, 1.0), (58.9, 0.4), (59.6, 1.0)],
      zk=[(58.2, 1.1), (59.0, 1.1), (59.25, 1.42), (61.3, 1.34)], cy=0.42, flash=[59.3]),
    S("151631", 62.5, 65.2, 3, ramp=[(62.5, 1.0), (63.0, 0.45), (63.7, 1.0)],
      zk=[(62.5, 1.1), (63.1, 1.1), (63.3, 1.4), (65.2, 1.32)], cy=0.42, flash=[63.3]),
    # RENFORT : rowing haltère
    S("155452", 5.0, 7.6, 4, vit=1.3, zoom=1.1, titre="chap", sous="ROWING HALTÈRE"),
    S("155753", 8.5, 11.1, 4, vit=1.3, zoom=1.1),                           # rowing, autre angle
    S("155337", 56.0, 58.6, 4, vit=1.3, zoom=1.1),
    S("155520", 10.0, 12.6, 4, vit=1.3, zoom=1.2, cy=0.55),
    S("155337", 34.0, 36.6, 4, vit=1.3, zoom=1.3, cy=0.55),
    S("155337", 5.85, 8.70, 4, voix=True, zoom=1.0),                       # Apocalypse rigole : « Il est trop fort, mais n'importe quoi »
    S("155452", 11.0, 13.4, 4, vit=1.0, zk=[(11.0, 1.1), (13.4, 1.25)], titre="fin"),
]
FIN_GEL = 1.6     # secondes d'image figée sous la carte de fin


# ------------------------------------------------------------------ temps
def src_times(p):
    """Temps source de chaque image de sortie (30 i/s), selon la rampe de vitesse."""
    out, t = [], p["a"]
    rk = sorted(p["ramp"])
    while t < p["b"] - 1e-6:
        out.append(t)
        sp = [v for (tt, v) in rk if tt <= t + 1e-6][-1]
        t += sp / FPS
    return out


def interp(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, z0), (t1, z1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 1
            return z0 + (z1 - z0) * E.eio(u)
    return keys[-1][1]


def plan():
    t = 0.0
    for p in PLANS:
        p["ts"] = src_times(p)
        p["start"] = round(t, 4)
        t += len(p["ts"]) / FPS
    total = t + FIN_GEL
    chap_start = {}
    for p in PLANS:
        chap_start.setdefault(p["chap"], p["start"])
    return total, chap_start


# ------------------------------------------------------------------ images
def decode(clip, a, b, size=(W, H)):
    """Toutes les images 60 i/s entre a et b (vraies images, pour les ralentis)."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-i", R(clip), "-t", f"{b - a + 0.1:.3f}", "-vf",
                          f"fps={SRC_FPS},scale={size[0]}:{size[1]}:in_color_matrix=bt709:in_range=tv:flags=lanczos+accurate_rnd+full_chroma_int",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    fs, sz = [], size[0] * size[1] * 3
    while True:
        bb = p.stdout.read(sz)
        if len(bb) < sz:
            break
        fs.append(np.frombuffer(bb, np.uint8).reshape(size[1], size[0], 3))
    p.wait()
    return fs


def pick(fs, a, t):
    return fs[min(len(fs) - 1, max(0, int(round((t - a) * SRC_FPS))))]


def reframe(frame, s, cx, cy):
    if s <= 1.0:
        return frame
    cw, ch = W / s, H / s
    x0 = E.clamp(cx * W - cw / 2, 0, W - cw)
    y0 = E.clamp(cy * H - ch / 2, 0, H - ch)
    return np.asarray(Image.fromarray(frame).resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)))


def split_frame(fl, fr, cxs):
    """Écran partagé vertical : Bene à gauche, Apocalypse à droite (chacun recadré au centre)."""
    out = np.zeros((H, W, 3), np.uint8)
    for k, (f, cx) in enumerate(zip((fl, fr), cxs)):
        x0 = int(E.clamp(cx * W - W / 4, 0, W / 2))
        out[:, k * (W // 2):(k + 1) * (W // 2)] = f[:, x0:x0 + W // 2]
    out[:, W // 2 - 3:W // 2 + 3] = 255
    return out


def whip(frame, force, sens):
    """Flou de mouvement horizontal (transition coup de fouet)."""
    if force <= 0.01:
        return frame
    acc = np.zeros_like(frame, np.float32)
    n = 7
    for k in range(n):
        acc += np.roll(frame, int(sens * force * 120 * k / n), axis=1)
    return (acc / n).astype(np.uint8)


# ------------------------------------------------------------------ habillage
def draw_progress(c, T, total, chap_start):
    """Barre des 5 chapitres en haut : faits = blanc, en cours = se remplit en bleu, à venir = blanc 30 %."""
    n = len(CHAPITRES)
    x0, y0, gap, h = 70, 178, 12, 9
    w = (W - 2 * x0 - gap * (n - 1)) / n
    starts = [chap_start.get(i, total) for i in range(n)] + [total - FIN_GEL]
    for i in range(n):
        x = x0 + i * (w + gap)
        E.rrect(c, x, y0, w, h, h / 2)
        c.set_source_rgba(1, 1, 1, 0.32)
        c.fill()
        u = E.clamp((T - starts[i]) / max(starts[i + 1] - starts[i], 0.1), 0, 1)
        if u > 0:
            E.rrect(c, x, y0, max(w * u, h), h, h / 2)
            c.set_source_rgba(*((1, 1, 1) if u >= 1 else E.BLUE), 1)
            c.fill()


def draw_chapter(c, num, sous, age):
    """Bandeau bleu qui balaie depuis la gauche + titre Anton + sous-titre Coda ; 1,2 s puis repart à droite."""
    dur = 1.25
    if age > dur:
        return
    inn = E.eo(E.clamp(age / 0.18, 0, 1))
    out = E.eio(E.clamp((age - (dur - 0.2)) / 0.2, 0, 1))
    titre = CHAPITRES[num]
    E.font(c, E.NUM, 150)
    tw = c.text_extents(titre).x_advance
    y = 420
    bw = tw + 90
    bx = -bw + (bw + (W - bw) / 2) * inn + (W + bw) * out
    c.save()
    E.rrect(c, bx, y - 140, bw, 175, 14)
    c.set_source_rgba(*E.BLUE, 1)
    c.fill()
    c.move_to(bx + 45, y)
    c.set_source_rgba(1, 1, 1, 1)
    c.show_text(titre)
    if sous:
        E.font(c, E.SANS_B, 52)
        sw = c.text_extents(sous).x_advance
        sx = bx + bw / 2 - sw / 2
        E.rrect(c, sx - 20, y + 30, sw + 40, 70, 10)
        c.set_source_rgba(*NAVY, 1)
        c.fill()
        c.move_to(sx, y + 82)
        c.set_source_rgba(1, 1, 1, 1)
        c.show_text(sous)
    num_txt = f"{num + 1:02d}/{len(CHAPITRES):02d}"
    E.font(c, E.NUM, 54)
    c.move_to(bx + 45, y - 160)
    c.set_source_rgba(1, 1, 1, 0.95)
    c.show_text(num_txt)
    c.restore()


def draw_hook(c, age):
    # visible pendant la tirée, disparaît avant le punch-in sur la réception (sinon il cache le visage)
    a = E.eo(E.clamp(age / 0.15, 0, 1)) * (1 - E.eio(E.clamp((age - 0.85) / 0.2, 0, 1)))
    if a <= 0:
        return
    c.save()
    c.translate(W / 2, 1400)
    s = 1.0 + 0.25 * (1 - a)
    c.scale(s, s)
    c.translate(-W / 2, -1400)
    for k, (txt, size, y) in enumerate((("SÉANCE", 190, 1300), ("À DEUX", 190, 1480))):
        E.font(c, E.NUM, size)
        tw = c.text_extents(txt).x_advance
        c.move_to(W / 2 - tw / 2, y)
        c.text_path(txt)
        c.set_source_rgba(*NAVY, a)
        c.set_line_width(16)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke_preserve()
        c.set_source_rgba(1, 1, 1, a)
        c.fill()
    tag = "BEN&FIT × APOCALYPSE TRAINING"
    E.font(c, E.SANS_B, 46)
    tw = c.text_extents(tag).x_advance
    E.rrect(c, W / 2 - tw / 2 - 22, 1540, tw + 44, 70, 10)
    c.set_source_rgba(*E.BLUE, a)
    c.fill()
    c.move_to(W / 2 - tw / 2, 1590)
    c.set_source_rgba(1, 1, 1, a)
    c.show_text(tag)
    c.restore()


def draw_split_labels(c):
    for k, txt in enumerate(("BEN&FIT", "APOCALYPSE")):
        E.font(c, E.SANS_B, 40)
        tw = c.text_extents(txt).x_advance
        x = k * W / 2 + W / 4 - tw / 2
        E.rrect(c, x - 16, 1480, tw + 32, 58, 8)
        c.set_source_rgba(*(E.BLUE if k == 0 else NAVY), 1)
        c.fill()
        c.move_to(x, 1522)
        c.set_source_rgba(1, 1, 1, 1)
        c.show_text(txt)


def draw_fin(c, age):
    a = E.eo(E.clamp(age / 0.25, 0, 1))
    c.rectangle(0, 0, W, H)
    c.set_source_rgba(0.012, 0.04, 0.10, 0.55 * a)
    c.fill()
    for txt, size, y in (("BEN&FIT", 170, 780), ("×", 90, 900), ("APOCALYPSE", 150, 1050), ("TRAINING", 150, 1190)):
        E.font(c, E.NUM, size)
        tw = c.text_extents(txt).x_advance
        c.move_to(W / 2 - tw / 2, y + 40 * (1 - a))
        c.set_source_rgba(1, 1, 1, a)
        c.show_text(txt)
    q = "Tu tiens la séance ?"
    E.font(c, E.SANS_B, 60)
    tw = c.text_extents(q).x_advance
    E.rrect(c, W / 2 - tw / 2 - 26, 1290, tw + 52, 88, 12)
    c.set_source_rgba(*E.BLUE, a)
    c.fill()
    c.move_to(W / 2 - tw / 2, 1352)
    c.set_source_rgba(1, 1, 1, a)
    c.show_text(q)


# ------------------------------------------------------------------ rendu
def render(only=None):
    total, chap_start = plan()
    bounds = sorted(set(chap_start.values()) - {0.0})
    last = None
    for p in PLANS:
        n = len(p["ts"])
        idx = [i for i in range(n) if only is None or any(abs(p["start"] + i / FPS - T) < 0.5 / FPS for T in only)]
        if not idx and not (p is PLANS[-1] and only is None):
            continue
        fs = decode(p["clip"], p["a"], p["b"] + 0.05)
        fs2 = None
        if p["split"]:
            sp = p["split"]
            fs2 = decode(sp["clip"], sp["a"], sp["a"] + (p["b"] - p["a"]) + 0.05)
        for i in idx:
            T = p["start"] + i / FPS
            t = p["ts"][i]
            if fs2 is not None:
                f = split_frame(pick(fs, p["a"], t), pick(fs2, p["split"]["a"], p["split"]["a"] + t - p["a"]),
                                p["split"]["cxs"])
            else:
                z = interp(p["zk"], t) if p["zk"] else p["zoom"]
                f = reframe(pick(fs, p["a"], t), z, p["cx"], p["cy"])
            for tf in p["flash"]:
                d = int(round((t - tf) * FPS))
                if 0 <= d < 3:
                    k = (0.45, 0.22, 0.08)[d]
                    f = (f.astype(np.float32) * (1 - k) + 255 * k).astype(np.uint8)
            for bt in bounds:                         # coup de fouet autour des débuts de chapitre
                d = T - bt
                if -0.1 <= d < 0.1:
                    f = whip(f, 1 - abs(d) / 0.1, -1 if d < 0 else 1)
            cv = E.Canvas(np.array(f))
            age = T - p["start"]

            def deco(c):
                if p["titre"] == "hook":
                    draw_hook(c, age)
                if p["titre"] == "chap":
                    draw_chapter(c, p["chap"], p["sous"], age)
                if fs2 is not None:
                    draw_split_labels(c)
            cv.draw(deco)
            last = f
            yield T, cv.out()
    if only is None:                                  # image figée + carte de fin
        t0 = PLANS[-1]["start"] + len(PLANS[-1]["ts"]) / FPS
        for i in range(int(round(FIN_GEL * FPS))):
            cv = E.Canvas(np.array(last))
            cv.draw(lambda c: draw_fin(c, i / FPS))
            yield t0 + i / FPS, cv.out()


def audio(total):
    """Ambiance des rushs (basse) sur les plans à vitesse réelle, répliques fortes, silence sur les ralentis,
    whooshs discrets aux changements de chapitre."""
    SR = 48000
    amb = np.zeros(int((total + 0.5) * SR), np.float32)
    vox = np.zeros_like(amb)
    for p in PLANS:
        ts = p["ts"]
        runs, cur = [], None
        for i, t in enumerate(ts):
            sp = [v for (tt, v) in sorted(p["ramp"]) if tt <= t + 1e-6][-1]
            if abs(sp - 1.0) < 1e-3 and not p["split"]:
                if cur and abs(t - (cur[1] + 1 / FPS)) < 1e-3:
                    cur[1] = t
                else:
                    cur = [t, t, i]
                    runs.append(cur)
            else:
                cur = None
        for a, b, i0 in runs:
            dur = b - a + 1 / FPS
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", R(p["clip"]),
                                  "-af", f"pan=mono|c0=0.5*c0+0.5*c1,aresample={SR}", "-f", "f32le", "-"],
                                 capture_output=True, check=True).stdout
            x = np.frombuffer(raw, np.float32).copy()
            f = min(len(x) // 4, int(0.012 * SR))
            if f:
                x[:f] *= np.linspace(0, 1, f)
                x[-f:] *= np.linspace(1, 0, f)
            j = int((p["start"] + i0 / FPS) * SR)
            dst = vox if p["voix"] else amb
            dst[j:j + len(x)] += x[:len(dst) - j]
        # accélérés (échauffement, renfort) : le son à ×vitesse fait « chipmunk » → on garde le silence
    _, chap_start = plan()
    wh = np.zeros_like(amb)
    rng = np.random.default_rng(1)
    L = int(0.32 * SR)
    noise = rng.standard_normal(L).astype(np.float32)
    env = np.sin(np.linspace(0, np.pi, L)) ** 2
    # whoosh : bruit filtré dont la fréquence monte (filtre passe-bas glissant simple)
    y, st = np.zeros(L, np.float32), 0.0
    for k in range(L):
        a_ = 0.02 + 0.25 * k / L
        st += a_ * (noise[k] - st)
        y[k] = st
    y = y * env
    y /= np.abs(y).max() + 1e-9
    for t in sorted(set(chap_start.values()) - {0.0}):
        j = int((t - 0.18) * SR)
        wh[j:j + L] += y * 0.25

    def wr(path, x):
        with wave.open(path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

    import re

    def lufs(path):
        m = subprocess.run(["ffmpeg", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True,
                           text=True).stderr
        return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", m)[-1])
    for name, x in (("amb", amb), ("vox", vox), ("wh", wh)):
        wr(os.path.join(WORK, name + ".wav"), x)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WORK, "vox.wav"), "-af",
                    "highpass=f=65,afftdn=nf=-30:nr=6.4,equalizer=f=3000:t=q:w=1.2:g=1.2,"
                    "acompressor=threshold=-20dB:ratio=2:attack=10:release=140:makeup=1.6",
                    os.path.join(WORK, "vox_t.wav")], check=True)
    # niveaux mesurés sur les seuls passages non vides
    def active_lufs(path):
        tmp = os.path.join(WORK, "act.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-af",
                        "silenceremove=stop_periods=-1:stop_duration=0.05:stop_threshold=-60dB", tmp], check=True)
        return lufs(tmp)
    gv = -14 - active_lufs(os.path.join(WORK, "vox_t.wav"))
    ga = -26 - active_lufs(os.path.join(WORK, "amb.wav"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WORK, "vox_t.wav"), "-i",
                    os.path.join(WORK, "amb.wav"), "-i", os.path.join(WORK, "wh.wav"), "-filter_complex",
                    f"[0:a]volume={gv:.2f}dB[v];[1:a]volume={ga:.2f}dB[a];[2:a]volume=-6dB[w];"
                    "[v][a][w]amix=inputs=3:normalize=0,pan=stereo|c0=0.708*c0|c1=0.708*c0,"
                    "alimiter=limit=0.89:level=false", "-ar", str(SR), os.path.join(WORK, "mix.wav")], check=True)


def video():
    total, _ = plan()
    out = os.path.join(WORK, "v.mp4")
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-vf",
                           "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-profile:v", "high", "-tune", "film",
                           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                           "-color_range", "tv", out], stdin=subprocess.PIPE)
    for _, f in render():
        wr.stdin.write(np.ascontiguousarray(f).tobytes())
    wr.stdin.close()
    wr.wait()
    audio(total)
    final = os.path.join(WORK, "BENFIT_x_APOCALYPSE_seance.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "mix.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("ok", final, round(total, 2), "s")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        total, cs = plan()
        print("durée", round(total, 2), "s ; chapitres", {CHAPITRES[k]: round(v, 2) for k, v in cs.items()})
        for p in PLANS:
            print(p["clip"], p["a"], p["b"], "→", p["start"], round(len(p["ts"]) / FPS, 2))
    elif cmd == "stills":
        for T, f in render(only=[float(x) for x in sys.argv[2:]]):
            Image.fromarray(f).resize((360, 640)).save(os.path.join(WORK, f"st_{T:05.2f}.png"))
    elif cmd == "video":
        video()
