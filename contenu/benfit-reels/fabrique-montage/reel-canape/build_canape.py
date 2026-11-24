"""Reel « canapé » (24 nov. 2026) : 3 effets pilotés par les gestes de Bene, sans voix (son tendance ajouté sur Insta).

  1. Carrousel au doigt : en tenue canapé, chaque balayage de la main fait tourner un carrousel 3D de ses vidéos
     d'entraînement (sélection de personnage). Les balayages sont détectés par le flux optique (mouvement horizontal
     de la main), sans modèle de suivi des mains.
  2. Claquement → tenue de sport : coupe sèche sur le claquement (détecté au son) entre deux prises cadrées pareil,
     flash blanc de 2 images.
  4. Tornade « multivers » (prise debout) : ses vidéos tournent autour de lui comme une tornade, derrière puis
     devant lui (détourage), de plus en plus vite.
  3. Mur au clap : au clap (détecté au son), un mur de ses vidéos se construit derrière lui en vague depuis ses mains ;
     Bene reste devant (détourage rembg u2net_human_seg).
Couleurs d'origine (BT.709 conservé), aucun étalonnage.

  python build_canape.py strokes | stills T… | video
"""
import os, sys, json, subprocess, math
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/canape")
os.makedirs(WORK, exist_ok=True)
W, H, FPS = 1080, 1920, 30
BLUE = (46, 107, 255)
NAVY = (10, 32, 107)

R = lambda n: os.path.join(RUSH, f"VID_2026{n}.mp4")
# Montage : (rush, début, fin) en secondes source. Les coupes « claquement » sont calées sur l'attaque du son.
SEGMENTS = [
    dict(src="1124_145737", a=13.00, b=14.20, role="intro"),        # posé, casque, téléphone
    dict(src="1124_145821", a=4.05, b=9.15, role="carrousel"),      # balayages
    dict(src="1124_145821", a=13.05, b=13.72, role="choix"),        # main levée… claquement (13,74)
    dict(src="1124_150014", a=4.51, b=5.35, role="flash"),          # claquement en tenue de sport (4,53)
    dict(src="1124_150218", a=4.55, b=8.60, role="mur", clap=5.32), # clap → mur de vidéos
    dict(src="1124_150135", a=21.80, b=27.40, role="tornade"),      # debout, il regarde autour de lui → tornade
]
# Cartes du carrousel / tuiles du mur : (rush, début, vitesse, titre)
CARTES = [  # carrousel : dans l'ordre ; 6 balayages → on finit sur la 7e (l'arraché barre)
    ("1120_112349", 6.0, 1.0, "DB SNATCH"),
    ("1119_102125", 3.0, 1.0, "RUN"),
    ("1005_111804", 9.5, 1.0, "WALL BALL"),
    ("1005_111524", 10.0, 1.0, "ROWER"),
    ("1123_103801", 12.4, 0.5, "BOX JUMP"),
    ("1120_110507", 3.1, 1.0, "SLED"),
    ("0924_105249", 21.5, 1.0, "SNATCH"),
]
# Mur au clap : 13 vidéos différentes (13 et 4 colonnes premiers entre eux → deux tuiles voisines jamais pareilles)
MUR = CARTES + [
    ("1120_112023", 10.0, 1.0, "BIKE"),
    ("0628_125056", 6.5, 1.0, "BIKE"),
    ("0806_110206", 8.0, 1.0, "PULLDOWN"),
    ("1012_104315", 38.8, 1.0, "JERK"),
    ("1117_104154", 24.0, 1.0, "PULL-UPS"),
    ("1120_104034", 29.9, 1.0, "SQUAT"),
]
CW, CH = 330, 587           # carte du centre (9:16)
CX, CY = 540, 1330          # centre du carrousel : devant les jambes, sous les mains, jamais sur le visage
RAYON, PAS = 400, 52
POLICES = os.path.join(HERE, "..", "..", "..", "polices")
CODA = os.path.join(POLICES, next(f for f in sorted(os.listdir(POLICES)) if "Coda" in f and "ExtraBold" in f)
                    if any("ExtraBold" in f for f in os.listdir(POLICES)) else
                    next(f for f in sorted(os.listdir(POLICES)) if "Coda" in f))        # rayon (px) et angle entre deux cartes (degrés)


def decode(path, a, dur, size=(W, H), speed=1.0, crop=None):
    n = int(round(dur * FPS))
    vf = f"setpts=(PTS-STARTPTS)/{speed},fps={FPS},"
    if crop:
        vf += crop + ","
    vf += f"scale={size[0]}:{size[1]}:in_color_matrix=bt709:in_range=tv:flags=lanczos+accurate_rnd+full_chroma_int"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-i", path, "-t", f"{dur * speed + 0.3:.3f}",
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    fs = []
    sz = size[0] * size[1] * 3
    while len(fs) < n:
        b = p.stdout.read(sz)
        if len(b) < sz:
            break
        fs.append(np.frombuffer(b, np.uint8).reshape(size[1], size[0], 3))
    p.stdout.close()
    p.wait()
    while len(fs) < n:
        fs.append(fs[-1])
    return fs


# ------------------------------------------------------------------ 1. balayages → position du carrousel
def strokes(seg, seuil=1.2, mini=7, trou=2, debut=0.6):
    """Flux optique horizontal dans la zone des mains → liste des balayages (début, fin) en secondes source."""
    w, h = 270, 480
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(seg["a"]), "-t", str(seg["b"] - seg["a"]), "-i",
                          R(seg["src"]), "-vf", f"fps={FPS},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE)
    prev, vx = None, []
    while True:
        b = p.stdout.read(w * h)
        if len(b) < w * h:
            break
        g = np.frombuffer(b, np.uint8).reshape(h, w)
        if prev is not None:
            f = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            r = f[int(h * .25):int(h * .62), :int(w * .8)]
            m = np.hypot(r[..., 0], r[..., 1]) > 1.5
            vx.append(float(r[..., 0][m].mean()) if m.sum() > 30 else 0.0)
        else:
            vx.append(0.0)
        prev = g
    vx = np.array(vx)
    act = np.abs(vx) > seuil
    out, i = [], 0
    while i < len(act):
        if act[i]:
            j = i
            while True:  # fusionne deux bouts de geste séparés de moins de `trou` images
                nxt = [k for k in range(j + 1, min(j + 2 + trou, len(act))) if act[k]]
                if not nxt:
                    break
                j = nxt[-1] if all(act[j + 1:nxt[-1] + 1]) else nxt[0]
            if j - i + 1 >= mini and i / FPS >= debut:  # on ignore la main qui se lève au début
                out.append((seg["a"] + i / FPS, seg["a"] + (j + 1) / FPS))
            i = j + 1
        else:
            i += 1
    return out


def position(t_src, strokes_):
    """Chaque balayage fait avancer le carrousel d'une carte, au rythme de la main (courbe sans rebond)."""
    pos = 0.0
    for a, b in strokes_:
        if t_src >= b:
            pos += 1
        elif t_src > a:
            pos += E.eio((t_src - a) / (b - a))
    return pos


# ------------------------------------------------------------------ rendu des cartes
def card_media(liste):
    out = []
    for src, a, sp, titre in liste:
        # recadrage 9:16 au centre puis taille carte (×2 pour les tuiles du mur)
        fs = decode(R(src), a, 2.5, size=(CW, CH), speed=sp, crop="crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'")
        out.append((fs, titre))
    return out


def rounded_mask(w, h, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for x, y in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (x, y), r, 255, -1, cv2.LINE_AA)
    return m


MASK_CARTE = rounded_mask(CW, CH, 24)


def card_rgba(img, titre, front):
    """Carte = vidéo + filet blanc (verre) + titre en chip bleu si c'est la carte du centre."""
    c = img.astype(np.float32).copy()
    c *= 0.45 + 0.55 * front                      # cartes du fond plus sombres
    c = c.astype(np.uint8)
    cv2.rectangle(c, (2, 2), (CW - 3, CH - 3), (255, 255, 255), 4, cv2.LINE_AA)
    rgba = np.dstack([c, MASK_CARTE])
    if front > 0.85:
        from PIL import ImageDraw, ImageFont
        im = Image.fromarray(rgba, "RGBA")
        d = ImageDraw.Draw(im)
        f = ImageFont.truetype(CODA, 30)
        tw = d.textlength(titre, font=f)
        x, y = CW / 2 - tw / 2, CH - 70
        d.rounded_rectangle((x - 16, y - 6, x + tw + 16, y + 42), 8, fill=BLUE + (255,))
        d.text((x, y), titre, font=f, fill=(255, 255, 255, 255))
        rgba = np.array(im)
    return rgba


def paste_quad(dst, rgba, quad, alpha=1.0):
    h, w = rgba.shape[:2]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    x0, y0 = np.floor(np.min(quad, 0)).astype(int)
    x1, y1 = np.ceil(np.max(quad, 0)).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64) @ M
    warped = cv2.warpPerspective(rgba, T, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
    a = warped[..., 3:4].astype(np.float32) / 255 * alpha
    reg = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (reg * (1 - a) + warped[..., :3] * a).astype(np.uint8)


def shadow(dst, quad, alpha):
    m = np.zeros((H, W), np.uint8)
    q = np.int32(quad + np.array([0, 18]))
    cv2.fillConvexPoly(m, q, 255, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 18).astype(np.float32) / 255 * 0.35 * alpha
    dst[:] = (dst.astype(np.float32) * (1 - m[..., None])).astype(np.uint8)


def draw_carousel(frame, media, pos, k, appear):
    N = len(media)
    items = []
    for i in range(N):
        d = ((i - pos + N / 2) % N) - N / 2
        if abs(d) > 1.45:   # une carte de chaque côté, pas plus
            continue
        ang = math.radians(d * PAS)
        z = math.cos(ang)
        x = CX + RAYON * math.sin(ang)
        s = (0.62 + 0.38 * (z + 1) / 2) * (0.7 + 0.3 * appear)
        w, h = CW * s, CH * s
        squash = 0.55 + 0.45 * abs(z)                    # carte vue de biais
        near = 1.0 + 0.10 * math.sin(ang) * np.sign(d)  # bord le plus proche un peu plus grand
        hw = w * squash / 2
        lh, rh = h / 2 * (2 - near if d > 0 else near), h / 2 * (near if d > 0 else 2 - near)
        if d == 0:
            lh = rh = h / 2
        quad = np.float32([[x - hw, CY - lh], [x + hw, CY - rh], [x + hw, CY + rh], [x - hw, CY + lh]])
        front = max(0.0, 1 - abs(d))
        items.append((z, i, quad, front))
    items.sort()
    for z, i, quad, front in items:
        fs, titre = media[i]
        img = fs[k % len(fs)]
        rgba = card_rgba(img, titre, front)
        shadow(frame, quad, appear * (0.4 + 0.6 * front))
        paste_quad(frame, rgba, quad, alpha=appear * (0.55 + 0.45 * front))


# ------------------------------------------------------------------ 3. mur au clap
def person_masks(frames):
    from rembg import remove, new_session
    sess = new_session("u2net_human_seg")
    out = []
    for f in frames:
        m = np.asarray(remove(Image.fromarray(f).resize((540, 960)), session=sess, only_mask=True), np.float32) / 255
        m = cv2.resize(cv2.GaussianBlur(m, (0, 0), 1.2), (W, H))
        out.append(np.clip((m - 0.15) / 0.7, 0, 1))
    return out


def draw_wall(frame, mask, media, t_since, origin):
    cols, gap = 4, 16
    bas = int(H * 0.62)   # le mur reste derrière Bene (mur + dossier), pas sur ses jambes
    tw = (W - gap * (cols + 1)) // cols
    th = tw
    rows = (H - gap) // (th + gap) + 1
    wall = frame.copy()
    ox = (W - (cols * tw + (cols + 1) * gap)) // 2
    for r in range(rows):
        for c in range(cols):
            x = ox + gap + c * (tw + gap)
            y = gap + r * (th + gap)
            if y + th > bas:
                continue
            d = math.hypot(x + tw / 2 - origin[0], y + th / 2 - origin[1])
            p = E.clamp((t_since - d / 2200) / 0.16, 0, 1)
            if p <= 0:
                continue
            p = E.eo(p)
            fs, _ = media[(r * cols + c) % len(media)]
            img = fs[(int(t_since * FPS) + r * 7 + c * 3) % len(fs)]
            sq = img[(CH - CW) // 2:(CH - CW) // 2 + CW]
            s = 0.65 + 0.35 * p
            w2, h2 = int(tw * s), int(th * s)
            tile = cv2.resize(sq, (w2, h2), interpolation=cv2.INTER_AREA)
            m = rounded_mask(w2, h2, max(6, int(16 * s)))
            cv2.rectangle(tile, (1, 1), (w2 - 2, h2 - 2), (255, 255, 255), 3, cv2.LINE_AA)
            x2, y2 = int(x + (tw - w2) / 2), int(y + (th - h2) / 2)
            xa, ya, xb, yb = max(x2, 0), max(y2, 0), min(x2 + w2, W), min(y2 + h2, H)
            if xb <= xa or yb <= ya:
                continue
            tt = tile[ya - y2:yb - y2, xa - x2:xb - x2].astype(np.float32)
            mm = m[ya - y2:yb - y2, xa - x2:xb - x2, None].astype(np.float32) / 255 * p
            reg = wall[ya:yb, xa:xb].astype(np.float32)
            wall[ya:yb, xa:xb] = (reg * (1 - mm) + tt * mm).astype(np.uint8)
    a = mask[..., None]
    return (wall * (1 - a) + frame * a).astype(np.uint8)


# ------------------------------------------------------------------ 4. tornade (multivers)
TORNADE_N = 20
VISAGE = (0.36 * W, 0.25 * H, 0.64 * W, 0.45 * H)   # zone du visage (prise debout) : jamais couverte
TCX = 0.50 * W          # axe de la tornade = Bene debout au centre


def zone_tete(mask, haut=200, marge=40):
    """Boîte de la tête de Bene, retrouvée à chaque image dans le détourage (haut du corps)."""
    rows = np.where((mask > 0.5).sum(1) > 25)[0]
    if not len(rows):
        return (0.36 * W, 0.25 * H, 0.64 * W, 0.45 * H)
    top = rows[0]
    band = mask[top:top + haut] > 0.5
    cols = np.where(band.sum(0) > 3)[0]
    return (cols[0] - marge, top - marge, cols[-1] + marge, top + haut + marge)


def draw_tornado(frame, mask, media, t):
    """Cartes vidéo en orbite autour de Bene, à différentes hauteurs, de plus en plus vite.
    Derrière lui (z < 0) : masquées par son corps ; devant (z > 0) : par-dessus."""
    back, front = [], []
    tete = zone_tete(mask)
    entree = E.eo(E.clamp(t / 0.6, 0, 1))
    tourne = 1.3 * t + 0.35 * t * t                    # accélère
    for i in range(TORNADE_N):
        th = i * 2 * math.pi / TORNADE_N * 2.0 + tourne * (1.0 + 0.15 * (i % 3))   # 2 tours de spirale
        u = (i * 0.618) % 1.0                            # hauteurs bien réparties (nombre d'or)
        hy = H * (0.10 + 0.78 * u)
        rx = (520 - 300 * u + 30 * math.sin(i * 1.7)) * (1 + 1.2 * (1 - entree))   # entonnoir : large en haut
        z = math.sin(th)
        x = TCX + rx * math.cos(th)
        y = hy + 70 * z + 20 * math.sin(t * 2 + i)
        s = (0.55 + 0.35 * (z + 1) / 2)
        w, h = 210 * s, 373 * s
        largeur = 0.25 + 0.75 * abs(z)                   # vue de face quand elle passe devant/derrière, tranche sur les côtés
        hw = w * largeur / 2
        quad = np.float32([[x - hw, y - h / 2], [x + hw, y - h / 2], [x + hw, y + h / 2], [x - hw, y + h / 2]])
        vx0, vy0, vx1, vy1 = tete
        if not (x + hw < vx0 or x - hw > vx1 or y + h / 2 < vy0 or y - h / 2 > vy1):
            continue                                     # jamais sur la tête : la carte « disparaît » derrière
        (front if z > 0 else back).append((z, i, quad))
    def dessine(dst, items):
        for z, i, quad in sorted(items):
            fs, _ = media[i % len(media)]
            img = fs[(int(t * FPS) + i * 5) % len(fs)].copy()
            cv2.rectangle(img, (2, 2), (CW - 3, CH - 3), (255, 255, 255), 5, cv2.LINE_AA)
            rgba = np.dstack([img, MASK_CARTE])
            fade = 0.55 + 0.45 * (z + 1) / 2
            paste_quad(dst, (rgba.astype(np.float32) * [fade, fade, fade, 1]).astype(np.uint8), quad, alpha=entree)
    bg = frame.copy()
    dessine(bg, back)
    a = mask[..., None]
    out = (bg * (1 - a) + frame * a).astype(np.uint8)
    dessine(out, front)
    return out


# ------------------------------------------------------------------ montage
def plan():
    st = strokes(SEGMENTS[1])
    json.dump(st, open(os.path.join(WORK, "strokes.json"), "w"))
    t = 0.0
    for s in SEGMENTS:
        s["start"] = round(t, 3)
        t += s["b"] - s["a"]
    return st, t


def render(only=None):
    st, total = plan()
    media = card_media(CARTES)
    media_mur = card_media(MUR)
    pos_fin = position(1e9, st)
    k_global = 0
    for s in SEGMENTS:
        n = int(round((s["b"] - s["a"]) * FPS))
        idx = range(n)
        if only is not None:
            idx = [i for i in idx if any(abs(s["start"] + i / FPS - T) < 0.5 / FPS for T in only)]
            if not idx:
                k_global += n
                continue
        fs = decode(R(s["src"]), s["a"], s["b"] - s["a"])
        masks = person_masks(fs) if s["role"] in ("mur", "tornade") else None
        for i in idx:
            T = s["start"] + i / FPS
            t_src = s["a"] + i / FPS
            f = fs[i].copy()
            if s["role"] == "carrousel":
                appear = E.eo(E.clamp((t_src - s["a"]) / 0.25, 0, 1))
                draw_carousel(f, media, position(t_src, st), k_global + i, appear)
            elif s["role"] == "choix":
                draw_carousel(f, media, pos_fin, k_global + i, 1.0)
            elif s["role"] == "flash" and i < 3:
                f = (f.astype(np.float32) * (1 - (0.75, 0.4, 0.15)[i]) + 255 * (0.75, 0.4, 0.15)[i]).astype(np.uint8)
            elif s["role"] == "mur":
                ts = t_src - s["clap"]
                if ts > 0:
                    f = draw_wall(f, masks[i], media_mur, ts, (W * 0.52, H * 0.42))
            elif s["role"] == "tornade":
                f = draw_tornado(f, masks[i], media_mur, t_src - s["a"])
            yield T, f
        k_global += n


def audio(total):
    # son d'origine des prises (claquement, clap, ambiance) ; pas de musique (son tendance ajouté sur Insta)
    args, fc = ["ffmpeg", "-v", "error", "-y"], []
    for k, s in enumerate(SEGMENTS):
        d = s["b"] - s["a"]
        args += ["-ss", f"{s['a']:.3f}", "-t", f"{d:.3f}", "-i", R(s["src"])]
        fc.append(f"[{k}:a]aresample=48000,asetpts=PTS-STARTPTS,afade=t=in:d=0.01,"
                  f"afade=t=out:st={d - 0.015:.3f}:d=0.015[a{k}]")
    n = len(SEGMENTS)
    fc.append("".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1,highpass=f=60,"
              "loudnorm=I=-16:TP=-1.5:LRA=11[o]")
    subprocess.run(args + ["-filter_complex", ";".join(fc), "-map", "[o]", "-ar", "48000",
                           os.path.join(WORK, "son.wav")], check=True)


def video():
    st, total = plan()
    out = os.path.join(WORK, "v.mp4")
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-vf",
                           "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high",
                           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                           "-color_range", "tv", out], stdin=subprocess.PIPE)
    for _, f in render():
        wr.stdin.write(np.ascontiguousarray(f).tobytes())
    wr.stdin.close()
    wr.wait()
    audio(total)
    final = os.path.join(WORK, "BENFIT_reel_canape.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "son.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("ok", final, round(total, 2), "s")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "strokes":
        print(plan())
    elif cmd == "stills":
        for T, f in render(only=[float(x) for x in sys.argv[2:]]):
            Image.fromarray(f).resize((360, 640)).save(os.path.join(WORK, f"st_{T:05.2f}.png"))
    elif cmd == "video":
        video()
