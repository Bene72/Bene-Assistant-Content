"""Reel d'entraînement « Acteur principal » (23 nov. 2026) : < 30 s, dynamique, motivant.

Voix off = phrase dite par Bene en footing (rush 102125), posée sur ses séances de la semaine
(box jumps, kipping pull-ups, sled, squat, snatch, vélo, fentes), puis montage sans voix,
puis la photo « résultat » (vestiaire). Couleurs d'origine (BT.709 conservé), pas d'étalonnage.
Ralentis : rushs filmés en 60 i/s lus à 0,5 (images réelles, aucune image inventée).

  python build_semaine.py edl | stills T… | video
Entrées : $RUSH (rushs de la Release « rushs »), $PHOTO (photo résultat).
"""
import sys, os, json, re, subprocess, wave
import numpy as np
import cairo
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/semaine")
PHOTO = os.environ.get("PHOTO", "/mnt/user-data/uploads/ed56ec4c-image.jpg")
os.makedirs(WORK, exist_ok=True)
W, H, FPS = 1080, 1920, 30

CLIPS = {"run": "VID_20261119_102125", "box": "VID_20261123_103801", "pull": "VID_20261117_104154",
         "squat": "VID_20261120_104034", "fentes": "VID_20261120_105756", "sled": "VID_20261120_110507",
         "velo": "VID_20261120_112023", "snatch": "VID_20261120_112349", "snatch2": "VID_20261120_112308"}

# Voix off (rush footing) : morceaux (début, fin) en secondes source, avec l'image posée dessus.
# image : (décalage dans le morceau, plan, début source | None = synchro, vitesse, zoom, cx, cy)
VOIX = [
    (2.20, 4.90, [(0.0, "box", 12.45, 0.5, 1.15, 0.60, 0.50)]),        # Certains vont être narrateurs de ta vie,
    (4.90, 8.55, [(0.0, "run", None, 1.0, 1.10, 0.45, 0.45),           # d'autres spectateurs. Mais c'est toi
                  (2.40, "run", None, 1.0, 1.28, 0.45, 0.40)]),        # l'acteur principal. (punch-in)
    (8.62, 10.40, [(0.0, "pull", 24.00, 1.0, 1.12, 0.45, 0.45)]),      # C'est à toi de faire tes choix.
    (10.40, 11.85, [(0.0, "sled", 3.15, 1.0, 1.15, 0.64, 0.52)]),      # De les assumer.
]
# Montage sans voix : (plan, début source, durée source, vitesse, zoom, cx, cy, chip)
MONTAGE = [
    ("squat", 29.95, 1.60, 1.0, 1.55, 0.50, 0.50, "BACK SQUAT"),
    ("snatch2", 9.90, 1.10, 1.0, 1.10, 0.52, 0.45, "DB SNATCH"),
    ("velo", 11.00, 0.80, 1.0, 1.28, 0.56, 0.45, "BIKE"),
    ("fentes", 22.90, 1.10, 1.0, 1.18, 0.45, 0.50, "FENTES SAUTÉES"),
    ("box", 18.85, 1.25, 0.5, 1.15, 0.58, 0.50, "BOX JUMP"),
    ("pull", 25.90, 1.30, 1.0, 1.12, 0.48, 0.45, "KIPPING PULL-UPS"),
    ("snatch", 6.95, 1.40, 1.0, 1.10, 0.50, 0.44, None),
]
PHOTO_DUREE = 2.4

SOUS_TITRES = [  # texte exact (temps source du footing)
    (2.20, 3.40, ["Certains", "vont", "être"]),
    (3.40, 4.90, ["narrateurs", "de", "ta", "vie,"]),
    (4.90, 6.55, ["d'autres", "spectateurs."]),
    (6.55, 7.30, ["Mais", "c'est", "toi"]),
    (7.30, 8.55, ["l'acteur", "principal."]),
    (8.62, 9.33, ["C'est", "à", "toi"]),
    (9.33, 10.40, ["de", "faire", "tes", "choix."]),
    (10.40, 11.85, ["De", "les", "assumer."]),
]
KEYS = {"narrateurs", "spectateurs.", "principal.", "choix.", "assumer."}
NAVY = (0.04, 0.125, 0.42)
STROKE = (0.08, 0.30, 0.92)
VOIX_FILTRE = ("highpass=f=65,afftdn=nf=-30:nr=6.4,equalizer=f=3000:t=q:w=1.2:g=1.2,"
               "acompressor=threshold=-20dB:ratio=2:attack=10:release=140:makeup=1.6")


def edl():
    w = os.path.join(WORK, "run.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(RUSH, CLIPS["run"] + ".mp4"), "-ac", "1",
                    "-ar", "48000", w], check=True)
    wv = wave.open(w)
    a = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float) / 32768
    n = len(a) // 480
    e = 20 * np.log10(np.sqrt((a[:n * 480].reshape(n, 480) ** 2).mean(1) + 1e-12))

    def snap(x):
        i0, i1 = int((x - 0.06) * 100), int((x + 0.06) * 100)
        return (i0 + int(np.argmin(e[i0:i1 + 1]))) / 100

    segs, voix, t = [], [], 0.0
    for a_, b_, plans in VOIX:
        a2, b2 = snap(a_), snap(b_)
        L = b2 - a2
        voix.append(dict(src_in=a2, src_out=b2, start=round(t, 3)))
        for j, (off, clip, s_in, sp, z, cx, cy) in enumerate(plans):
            end = plans[j + 1][0] if j + 1 < len(plans) else L
            segs.append(dict(clip=clip, src_in=round(a2 + off if s_in is None else s_in, 3), out_dur=round(end - off, 3),
                             speed=sp, start=round(t + off, 3), zoom=z, cx=cx, cy=cy, chip=None, push=(j == 0)))
        t += L
    t_voix = t
    for clip, s_in, dur, sp, z, cx, cy, chip in MONTAGE:
        od = dur / sp
        segs.append(dict(clip=clip, src_in=s_in, out_dur=round(od, 3), speed=sp, start=round(t, 3), zoom=z,
                         cx=cx, cy=cy, chip=chip, push=True))
        t += od
    segs.append(dict(clip="photo", src_in=0, out_dur=PHOTO_DUREE, speed=1, start=round(t, 3), zoom=1.0, cx=0.56,
                     cy=0.5, chip=None, push=True))
    t += PHOTO_DUREE
    subs = []
    for a_, b_, ws in SOUS_TITRES:
        def conv(x):
            for v in voix:
                if v["src_in"] - 0.1 <= x <= v["src_out"] + 0.1:
                    return v["start"] + min(max(x, v["src_in"]), v["src_out"]) - v["src_in"]
            raise ValueError(x)
        subs.append(dict(t0=round(conv(a_), 3), t1=round(conv(b_), 3), words=ws))
    for i in range(len(subs) - 1):
        if 0 <= subs[i + 1]["t0"] - subs[i]["t1"] < 0.25:
            subs[i]["t1"] = subs[i + 1]["t0"]
    d = dict(voix=voix, segs=segs, subs=subs, total=round(t, 3), t_voix=round(t_voix, 3))
    json.dump(d, open(os.path.join(WORK, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print("durée", round(t, 2), "s (voix", round(t_voix, 2), "s)")
    for s in segs:
        pass


def decode(seg):
    n = int(round(seg["out_dur"] * FPS))
    if seg["clip"] == "photo":
        im = Image.open(PHOTO).convert("RGB")
        s = H / im.height
        im = im.resize((int(im.width * s), H), Image.LANCZOS)
        x0 = int(E.clamp(seg["cx"] * im.width - W / 2, 0, im.width - W))
        return [np.asarray(im.crop((x0, 0, x0 + W, H)))] * n
    sp = seg["speed"]
    # 60 i/s lu à 0,5 → vraies images (pas d'interpolation) ; sinon 30 i/s normal
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{seg['src_in']:.3f}", "-i",
                          os.path.join(RUSH, CLIPS[seg["clip"]] + ".mp4"), "-t", f"{seg['out_dur'] * sp + 0.2:.3f}",
                          "-vf", f"setpts=(PTS-STARTPTS)/{sp},fps={FPS},"
                          f"scale={W}:{H}:in_color_matrix=bt709:in_range=tv:flags=lanczos+accurate_rnd+full_chroma_int",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    out = []
    while len(out) < n:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        out.append(np.frombuffer(b, np.uint8).reshape(H, W, 3))
    p.stdout.close()
    p.wait()
    while len(out) < n:
        out.append(out[-1])
    return out


def reframe(frame, s, cx, cy):
    if s <= 1.0:
        return frame
    cw, ch = W / s, H / s
    x0 = E.clamp(cx * W - cw / 2, 0, W - cw)
    y0 = E.clamp(cy * H - ch / 2, 0, H - ch)
    return np.asarray(Image.fromarray(frame).resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)))


def draw_subs(c, T, subs, y=1450, size=80):
    for s in subs:
        if s["t0"] <= T < s["t1"]:
            break
    else:
        return
    while True:
        E.font(c, E.SANS_B, size)
        space = c.text_extents(" ").x_advance * 1.1
        ws = [(w, c.text_extents(w).x_advance) for w in s["words"]]
        lw = sum(x for _, x in ws) + space * (len(ws) - 1) + size * 0.36 * sum(w in KEYS for w in s["words"])
        if lw <= 920 or size <= 56:
            break
        size -= 2
    sc = 0.92 + 0.08 * E.eo((T - s["t0"]) / 0.1)
    c.save()
    c.translate(W / 2, y)
    c.scale(sc, sc)
    c.translate(-W / 2, -y)
    x = W / 2 - lw / 2
    for w, ww in ws:
        key = w in KEYS
        if key:
            pad = size * 0.18
            E.rrect(c, x - pad, y - size * 0.80, ww + 2 * pad, size * 1.05, 10)
            c.set_source_rgba(*E.BLUE, 1)
            c.fill()
        c.move_to(x, y)
        c.text_path(w)
        if not key:
            c.set_source_rgba(*STROKE, 1)
            c.set_line_width(10)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.stroke_preserve()
        c.set_source_rgba(1, 1, 1, 1)
        c.fill()
        x += ww + space
    c.restore()


def draw_chip(c, txt, age):
    """Nom de l'exercice dans un chip bleu (en bas, zone des sous-titres, il n'y a pas de voix ici)."""
    E.font(c, E.SANS_B, 54)
    tw = c.text_extents(txt).x_advance
    x, y = W / 2 - tw / 2, 1460
    a = E.clamp(age / 0.08, 0, 1)
    E.rrect(c, x - 24, y - 50, tw + 48, 72, 10)
    c.set_source_rgba(*E.BLUE, a)
    c.fill()
    c.move_to(x, y)
    c.set_source_rgba(1, 1, 1, a)
    c.show_text(txt)


def draw_fin(c, age):
    a = E.clamp(age / 0.12, 0, 1)
    mot, size = "C'EST TOI", 200
    E.font(c, E.NUM, size)
    mw = c.text_extents(mot).x_advance
    c.move_to(W / 2 - mw / 2, 1430)
    c.text_path(mot)
    c.set_source_rgba(*NAVY, a)
    c.set_line_width(14)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke_preserve()
    c.set_source_rgba(1, 1, 1, a)
    c.fill()
    tag = "L'ACTEUR PRINCIPAL."
    E.font(c, E.SANS_B, 66)
    tw = c.text_extents(tag).x_advance
    bx, by = W / 2 - tw / 2, 1560
    E.rrect(c, bx - 26, by - 58, tw + 52, 86, 12)
    c.set_source_rgba(*E.BLUE, a)
    c.fill()
    c.move_to(bx, by)
    c.set_source_rgba(1, 1, 1, a)
    c.show_text(tag)


def frames(d, only=None):
    for seg in d["segs"]:
        n = int(round(seg["out_dur"] * FPS))
        idx = list(range(n))
        if only is not None:
            idx = [i for i in idx if any(abs(seg["start"] + i / FPS - T) < 0.5 / FPS for T in only)]
            if not idx:
                continue
        fr = decode(seg)
        for i in idx:
            T = seg["start"] + i / FPS
            p = i / max(n - 1, 1)
            z = seg["zoom"] + (0.04 * p if seg["push"] else 0)
            f = reframe(fr[min(i, len(fr) - 1)], z, seg["cx"], seg["cy"])
            cv = E.Canvas(np.array(f))
            age = T - seg["start"]

            def deco(c):
                draw_subs(c, T, d["subs"])
                if seg["chip"]:
                    draw_chip(c, seg["chip"], age)
                if seg["clip"] == "photo":
                    draw_fin(c, age)
            cv.draw(deco)
            yield T, cv.out()


def audio(d):
    """Voix off seule (une chaîne, traitement léger) + son ambiant des plans du montage, plus bas.
    Rien sous la photo de fin."""
    SR = 48000
    buf_v = np.zeros(int((d["total"] + 0.5) * SR), np.float32)
    buf_a = np.zeros_like(buf_v)

    def grab(clip, s_in, dur, sp=1.0):
        af = "pan=mono|c0=0.5*c0+0.5*c1,aresample=48000"
        if sp != 1.0:
            af += f",atempo={sp}"
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{s_in:.3f}", "-t", f"{dur * sp:.3f}", "-i",
                              os.path.join(RUSH, CLIPS[clip] + ".mp4"), "-af", af, "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).copy()
        f = min(len(x) // 4, int(0.015 * SR))
        if f:
            x[:f] *= np.linspace(0, 1, f)
            x[-f:] *= np.linspace(1, 0, f)
        return x

    for v in d["voix"]:
        x = grab("run", v["src_in"], v["src_out"] - v["src_in"])
        i0 = int(v["start"] * SR)
        buf_v[i0:i0 + len(x)] += x[:len(buf_v) - i0]
    for s in d["segs"]:
        if s["start"] >= d["t_voix"] - 0.01 and s["clip"] != "photo":
            x = grab(s["clip"], s["src_in"], s["out_dur"], s["speed"])
            i0 = int(s["start"] * SR)
            buf_a[i0:i0 + len(x)] += x[:len(buf_a) - i0]

    def wr(path, x):
        with wave.open(path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

    def lufs(path, t0, t1):
        m = subprocess.run(["ffmpeg", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", path, "-af", "ebur128",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
        return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", m)[-1])

    wr(os.path.join(WORK, "v_raw.wav"), buf_v)
    wr(os.path.join(WORK, "a_raw.wav"), buf_a)
    vt = os.path.join(WORK, "v.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WORK, "v_raw.wav"), "-af", VOIX_FILTRE, vt],
                   check=True)
    at = os.path.join(WORK, "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WORK, "a_raw.wav"), "-af",
                    "highpass=f=50,afftdn=nf=-30:nr=6", at], check=True)
    gv = -14 - lufs(vt, 0, d["t_voix"])
    ga = -18 - lufs(at, d["t_voix"], d["total"] - PHOTO_DUREE)   # ambiance 4 dB sous la voix
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vt, "-i", at, "-filter_complex",
                    f"[0:a]volume={gv:.2f}dB[v];[1:a]volume={ga:.2f}dB[a];[v][a]amix=inputs=2:normalize=0,"
                    "pan=stereo|c0=0.708*c0|c1=0.708*c0,alimiter=limit=0.89:level=false",  # mono→stéréo : -3 dB pour rester à -14 LUFS
                    "-ar", str(SR), os.path.join(WORK, "mix.wav")], check=True)


def video():
    d = json.load(open(os.path.join(WORK, "timeline.json")))
    out = os.path.join(WORK, "video_nosound.mp4")
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-vf",
                           "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high",
                           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                           "-color_range", "tv", out], stdin=subprocess.PIPE)
    for _, f in frames(d):
        wr.stdin.write(f.tobytes())
    wr.stdin.close()
    wr.wait()
    audio(d)
    final = os.path.join(WORK, "BENFIT_reel_acteur_principal.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "mix.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("ok", final)


def stills(ts):
    d = json.load(open(os.path.join(WORK, "timeline.json")))
    for T, f in frames(d, only=ts):
        Image.fromarray(f).resize((360, 640)).save(os.path.join(WORK, f"st_{T:05.2f}.png"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "edl":
        edl()
    elif cmd == "video":
        video()
    elif cmd == "audio":
        audio(json.load(open(os.path.join(WORK, "timeline.json"))))
    elif cmd == "stills":
        stills([float(x) for x in sys.argv[2:]])
