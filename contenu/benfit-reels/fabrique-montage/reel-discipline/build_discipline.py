"""Reel « Discipline » (20 nov. 2026) : très court, très sport, montage seulement.

Une prise face caméra (Bene essoufflé, en salle) + plans de coupe d'entraînement
(squat, sled, vélo, fentes, snatch haltère). Demande de Bene :
  - coupes sèches calées sur les mots, punch-ins rythmés, recadrage ;
  - sous-titres Coda blancs bords bleus, mots-clés en bloc bleu #2E6BFF, sans reformuler ;
  - AUCUN étalonnage, aucun grain : couleurs d'origine (matrice BT.709 conservée de bout en bout) ;
  - aucun effet ni animation à part les sous-titres ;
  - son : voix seule, débruitage léger, une seule chaîne, -14 LUFS, pas de musique.
    Le son des plans de coupe n'est PAS utilisé (musique de la salle en fond).

  python build_discipline.py edl     → coupes calées sur les silences (timeline.json)
  python build_discipline.py stills T1 T2 …
  python build_discipline.py video   → vidéo finale 1080×1920 30 i/s
Entrées : rushs VID_20261120_* de la Release « rushs » dans $RUSH.
"""
import sys, os, json, re, subprocess, wave
import numpy as np
import cairo
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/work")
os.makedirs(WORK, exist_ok=True)
W, H, FPS = 1080, 1920, 30
SPEED = 1.05

CLIPS = {"face": "VID_20261120_103837", "squat": "VID_20261120_104034", "fentes": "VID_20261120_105756",
         "sled": "VID_20261120_110507", "velo": "VID_20261120_112023", "snatch": "VID_20261120_112349"}

# Morceaux de voix (prise face caméra), dans l'ordre : (début, fin) en secondes source.
VOIX = [(8.95, 10.50),   # Pas de motivation, mais
        (10.82, 11.58),  # le taf,
        (12.52, 13.45),  # il est là.
        (13.70, 16.25)]  # Et du coup, c'est la discipline sur le long terme.

# Image posée sur la voix : (morceau de voix, décalage dans le morceau, plan, début source dans le plan,
# zoom, centre x, centre y). Le plan « face » reste synchro avec la voix.
PLANS = [
    (0, 0.0, "face", None, "hook", 0.50, 0.50),
    (1, 0.0, "squat", 25.40, 1.55, 0.50, 0.47),
    (2, 0.0, "sled", 3.15, 1.15, 0.64, 0.52),
    (3, 0.0, "face", None, "push", 0.50, 0.50),
    (3, 1.35, "face", None, "punch", 0.50, 0.53),   # « discipline » : punch-in
    (3, 1.80, "velo", 11.00, 1.28, 0.56, 0.45),
]
# Fin sans voix (Bene ajoute le son tendance à la publication)
QUEUE = [("fentes", 9.55, 1.00, 1.18, 0.50, 0.50),
         ("snatch", 6.95, 1.40, 1.10, 0.50, 0.44)]

# Sous-titres : texte exact dit par Bene, groupes calés sur la voix (temps source de la prise face).
SOUS_TITRES = [
    (9.00, 10.28, ["Pas", "de", "motivation,"]),
    (10.28, 11.58, ["mais", "le", "taf,"]),
    (12.55, 13.45, ["il", "est", "là."]),
    (13.72, 14.78, ["Et", "du", "coup,"]),
    (14.78, 15.50, ["c'est", "la", "discipline"]),
    (15.50, 16.25, ["sur", "le", "long", "terme."]),
]
KEYS = {"motivation,", "taf,", "discipline"}


def energy(clip):
    w = wave.open(os.path.join(WORK, clip + ".wav"))
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    h = w.getframerate() // 100
    n = len(a) // h
    return 20 * np.log10(np.sqrt((a[:n * h].reshape(n, h) ** 2).mean(1) + 1e-12))


def edl():
    src = os.path.join(RUSH, CLIPS["face"] + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "48000",
                    os.path.join(WORK, "face.wav")], check=True)
    e = energy("face")

    def snap(x):  # coupe sur le point le plus calme à ±60 ms
        i0, i1 = int((x - 0.06) * 100), int((x + 0.06) * 100)
        return (i0 + int(np.argmin(e[i0:i1 + 1]))) / 100

    voix, t = [], 0.0
    for a, b in VOIX:
        a2, b2 = snap(a), snap(b)
        voix.append(dict(src_in=a2, src_out=b2, start=t))
        t += b2 - a2
    total_voix = t
    # segments vidéo (temps source cumulés, avant accélération)
    segs = []
    for k, (vi, off, clip, s_in, zoom, cx, cy) in enumerate(PLANS):
        v = voix[vi]
        nxt = PLANS[k + 1] if k + 1 < len(PLANS) else None
        end = (voix[nxt[0]]["start"] + nxt[1]) if nxt else total_voix
        st = v["start"] + off
        dur = end - st
        sin = v["src_in"] + off if clip == "face" else s_in
        segs.append(dict(clip=clip, src_in=round(sin, 3), dur=round(dur, 3), start=round(st, 3),
                         zoom=zoom, cx=cx, cy=cy))
    t = total_voix
    for clip, s_in, dur, zoom, cx, cy in QUEUE:
        segs.append(dict(clip=clip, src_in=s_in, dur=dur, start=round(t, 3), zoom=zoom, cx=cx, cy=cy))
        t += dur
    # sous-titres en temps de sortie
    subs = []
    for a, b, ws in SOUS_TITRES:
        def conv(x):
            for v in voix:
                if v["src_in"] - 0.1 <= x <= v["src_out"] + 0.1:
                    return (v["start"] + min(max(x, v["src_in"]), v["src_out"]) - v["src_in"]) / SPEED
            raise ValueError(x)
        subs.append(dict(t0=round(conv(a), 3), t1=round(conv(b), 3), words=ws))
    for i in range(len(subs) - 1):  # pas de trou entre deux groupes de la même phrase
        if subs[i + 1]["t0"] - subs[i]["t1"] < 0.25:
            subs[i]["t1"] = subs[i + 1]["t0"]
    d = dict(voix=voix, segs=segs, subs=subs, total=t / SPEED, total_voix=total_voix / SPEED)
    json.dump(d, open(os.path.join(WORK, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print("durée", round(t / SPEED, 2), "s (voix", round(total_voix / SPEED, 2), "s)")
    for s in segs:
        print(s)
    for s in subs:
        print(s)


# ------------------------------------------------------------------ image
def decode(clip, s_in, dur):
    """Images du plan, ralenties/accélérées en même temps que la voix, en RVB (matrice BT.709, plage TV)."""
    n = int(round(dur / SPEED * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s_in:.3f}", "-i", os.path.join(RUSH, CLIPS[clip] + ".mp4"),
                          "-t", f"{dur + 0.2:.3f}", "-vf",
                          f"setpts=(PTS-STARTPTS)/{SPEED},fps={FPS},"
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


def zoom_of(seg, p, T):
    z = seg["zoom"]
    if z == "hook":   # accroche : punch-in serré qui se relâche vite
        return 1.22 - 0.10 * E.eo(p * 2.2)
    if z == "push":   # poussée lente
        return 1.0 + 0.05 * p
    if z == "punch":  # mot-clé : punch-in sec
        return 1.24 + 0.03 * p
    return z + 0.04 * p  # plans de coupe : zoom de recadrage + légère poussée


def reframe(frame, s, cx, cy):
    if s <= 1.0:
        return frame
    cw, ch = W / s, H / s
    x0 = E.clamp(cx * W - cw / 2, 0, W - cw)
    y0 = E.clamp(cy * H - ch / 2, 0, H - ch)
    im = Image.fromarray(frame).resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
    return np.asarray(im)


STROKE = (0.08, 0.30, 0.92)


def draw_subs(c, T, subs, y=1450, size=82):
    for s in subs:
        if s["t0"] <= T < s["t1"]:
            break
    else:
        return
    E.font(c, E.SANS_B, size)
    space = c.text_extents(" ").x_advance * 1.1
    ws = [(w, c.text_extents(w).x_advance) for w in s["words"]]
    lw = sum(x for _, x in ws) + space * (len(ws) - 1)
    sc = 0.92 + 0.08 * E.eo((T - s["t0"]) / 0.1)   # légère arrivée du sous-titre (seule animation)
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


def frames(d, only=None):
    """Génère (T, image) pour toute la vidéo (ou seulement les temps demandés)."""
    for seg in d["segs"]:
        t0 = seg["start"] / SPEED
        n = int(round(seg["dur"] / SPEED * FPS))
        idx = range(n)
        if only is not None:
            idx = [i for i in idx if any(abs((t0 + i / FPS) - T) < 0.5 / FPS for T in only)]
            if not idx:
                continue
        fr = decode(seg["clip"], seg["src_in"], seg["dur"])
        for i in idx:
            T = t0 + i / FPS
            p = i / max(n - 1, 1)
            f = reframe(fr[min(i, len(fr) - 1)], zoom_of(seg, p, T), seg["cx"], seg["cy"])
            cv = E.Canvas(np.array(f))
            cv.draw(lambda c: draw_subs(c, T, d["subs"]))
            yield T, cv.out()


def audio(d):
    # voix seule, une seule chaîne (jamais de mélange voix nettoyée + voix d'origine)
    src = os.path.join(RUSH, CLIPS["face"] + ".mp4")
    args, fc = ["ffmpeg", "-v", "error", "-y"], []
    for k, v in enumerate(d["voix"]):
        dur = v["src_out"] - v["src_in"]
        args += ["-ss", f"{v['src_in']:.3f}", "-t", f"{dur:.3f}", "-i", src]
        fc.append(f"[{k}:a]aresample=48000,pan=mono|c0=0.5*c0+0.5*c1,asetpts=PTS-STARTPTS,"
                  f"afade=t=in:d=0.012,afade=t=out:st={max(dur - 0.025, 0):.3f}:d=0.025[a{k}]")
    n = len(d["voix"])
    tail = d["total"] - d["total_voix"]
    fc.append("".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1,atempo={SPEED},"
              "highpass=f=80,afftdn=nf=-30:nr=8,equalizer=f=3000:t=q:w=1.2:g=1.5,"
              "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,"
              f"apad=pad_dur={tail + 0.2:.3f},pan=stereo|c0=c0|c1=c0[o]")
    tmp = os.path.join(WORK, "voix_tmp.wav")
    subprocess.run(args + ["-filter_complex", ";".join(fc), "-map", "[o]", "-ar", "48000", tmp], check=True)
    # volume mesuré sur la partie parlée seulement, puis correction pour tomber à -14 LUFS (limiteur -1 dB)
    m = subprocess.run(["ffmpeg", "-t", f"{d['total_voix']:.3f}", "-i", tmp, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", m)[-1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    f"volume={-14 - I:.2f}dB,alimiter=limit=0.89:level=false", "-ar", "48000",
                    os.path.join(WORK, "voix.wav")], check=True)


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
    final = os.path.join(WORK, "BENFIT_reel_discipline.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "voix.wav"), "-c:v", "copy",
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
