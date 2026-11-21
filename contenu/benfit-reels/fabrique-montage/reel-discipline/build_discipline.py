"""Reel « Discipline » (20 nov. 2026) : court (15 s), très sport, montage seulement.

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
         "sled": "VID_20261120_110507", "velo": "VID_20261120_112023", "velo2": "VID_20261120_112113",
         "snatch": "VID_20261120_112349", "snatch2": "VID_20261120_112308"}

# Déroulé du Reel, dans l'ordre. Deux sortes d'éléments :
#  ("voix", plan parlé, début, fin, [(décalage, plan, début source | None = synchro, zoom, cx, cy), …])
#      → la voix du plan parlé, avec l'image posée dessus (None = l'image du plan parlé, synchro) ;
#  ("plan", plan, début source, durée, zoom, cx, cy) → plan d'entraînement sans voix.
# Temps en secondes source. zoom : nombre (recadrage) ou "hook" / "push" / "punch".
SEQUENCE = [
    ("voix", "face", 8.95, 10.50, [(0.0, "face", None, "hook", 0.50, 0.50)]),        # Pas de motivation, mais
    ("voix", "face", 10.82, 11.58, [(0.0, "squat", 25.40, 1.55, 0.50, 0.47)]),       # le taf,
    ("voix", "face", 12.52, 13.45, [(0.0, "sled", 3.15, 1.15, 0.64, 0.52)]),         # il est là.
    ("voix", "face", 13.70, 16.25, [(0.0, "face", None, "push", 0.50, 0.50),         # Et du coup, c'est la
                                    (1.35, "face", None, "punch", 0.50, 0.53),       # discipline
                                    (1.80, "velo", 11.00, 1.28, 0.56, 0.45)]),       # sur le long terme.
    # montage d'entraînement (sans voix : Bene ajoute le son tendance à la publication)
    ("plan", "squat", 29.95, 2.05, 1.55, 0.50, 0.50),
    ("plan", "sled", 23.75, 1.45, 1.35, 0.50, 0.42),
    ("plan", "velo2", 2.00, 1.05, 1.10, 0.62, 0.50),
    ("plan", "fentes", 22.90, 1.10, 1.18, 0.45, 0.50),
    ("plan", "snatch2", 9.90, 1.20, 1.10, 0.52, 0.45),
    ("plan", "snatch", 6.95, 1.40, 1.10, 0.50, 0.44),
    # chute : Bene vient face à l'objectif
    ("voix", "squat", 6.15, 7.45, [(0.0, "squat", None, 1.10, 0.50, 0.40)]),     # Discipline is everything.
]

# Version courte (8 s, la v1) : la phrase face caméra puis fentes + snatch, sans la chute.
SEQUENCE_COURTE = SEQUENCE[:4] + [
    ("plan", "fentes", 9.55, 1.00, 1.18, 0.50, 0.50),
    ("plan", "snatch", 6.95, 1.40, 1.10, 0.50, 0.44),
]
COURT = os.environ.get("VERSION") == "court"   # VERSION=court python build_discipline.py edl / video
if COURT:
    SEQUENCE = SEQUENCE_COURTE

# Sous-titres : texte exact dit par Bene, groupes calés sur la voix (plan parlé, temps source).
SOUS_TITRES = [
    ("face", 9.00, 10.28, ["Pas", "de", "motivation,"]),
    ("face", 10.28, 11.58, ["mais", "le", "taf,"]),
    ("face", 12.55, 13.45, ["il", "est", "là."]),
    ("face", 13.72, 14.78, ["Et", "du", "coup,"]),
    ("face", 14.78, 15.50, ["c'est", "la", "discipline"]),
    ("face", 15.50, 16.25, ["sur", "le", "long", "terme."]),
    ("squat", 6.20, 6.72, ["Discipline"]),
    ("squat", 6.72, 7.45, ["is", "everything."]),
]
KEYS = {"motivation,", "taf,", "discipline", "Discipline", "everything."}
FIN_TENUE = 0.08  # quelques images de plus après le dernier mot (temps source)

# Traitement de la voix. Retour de Bene (21 nov.) : voix « un peu moins isolée », traitement réduit de 20 %
# (v1 : coupe-bas 80 Hz, débruitage nr 8, présence +1,5 dB, compresseur 2,5:1 → valeurs ci-dessous).
# Toujours UNE seule chaîne : jamais de mélange voix nettoyée + voix d'origine (écho métallique).
VOIX_FILTRE = ("highpass=f=65,afftdn=nf=-30:nr=6.4,equalizer=f=3000:t=q:w=1.2:g=1.2,"
               "acompressor=threshold=-20dB:ratio=2:attack=10:release=140:makeup=1.6")


def energy(clip):
    w = wave.open(os.path.join(WORK, clip + ".wav"))
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    h = w.getframerate() // 100
    n = len(a) // h
    return 20 * np.log10(np.sqrt((a[:n * h].reshape(n, h) ** 2).mean(1) + 1e-12))


def edl():
    parles = sorted({it[1] for it in SEQUENCE if it[0] == "voix"})
    for clip in parles:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(RUSH, CLIPS[clip] + ".mp4"), "-ac", "1",
                        "-ar", "48000", os.path.join(WORK, clip + ".wav")], check=True)
    E_ = {c: energy(c) for c in parles}

    def snap(clip, x):  # coupe sur le point le plus calme à ±60 ms
        e = E_[clip]
        i0, i1 = int((x - 0.06) * 100), int((x + 0.06) * 100)
        return (i0 + int(np.argmin(e[i0:i1 + 1]))) / 100

    voix, segs, t = [], [], 0.0
    for k, it in enumerate(SEQUENCE):
        if it[0] == "plan":
            _, clip, s_in, dur, zoom, cx, cy = it
            segs.append(dict(clip=clip, src_in=s_in, dur=dur, start=round(t, 3), zoom=zoom, cx=cx, cy=cy))
            t += dur
            continue
        _, clip, a, b, plans = it
        a2, b2 = snap(clip, a), snap(clip, b)
        if k == len(SEQUENCE) - 1 and not COURT:
            b2 = b + FIN_TENUE
        voix.append(dict(clip=clip, src_in=a2, src_out=b2, start=round(t, 3)))
        L = b2 - a2
        for j, (off, pc, s_in, zoom, cx, cy) in enumerate(plans):
            end = plans[j + 1][0] if j + 1 < len(plans) else L
            segs.append(dict(clip=pc, src_in=round(a2 + off if s_in is None else s_in, 3), dur=round(end - off, 3),
                             start=round(t + off, 3), zoom=zoom, cx=cx, cy=cy))
        t += L
    subs = []
    parles_ici = {v["clip"] for v in voix}
    for clip, a, b, ws in SOUS_TITRES:
        if clip not in parles_ici:
            continue
        def conv(x):
            for v in voix:
                if v["clip"] == clip and v["src_in"] - 0.1 <= x <= v["src_out"] + 0.1:
                    return (v["start"] + min(max(x, v["src_in"]), v["src_out"]) - v["src_in"]) / SPEED
            raise ValueError(x)
        subs.append(dict(t0=round(conv(a), 3), t1=round(conv(b), 3), words=ws))
    for i in range(len(subs) - 1):  # pas de trou entre deux groupes de la même phrase
        if 0 <= subs[i + 1]["t0"] - subs[i]["t1"] < 0.25:
            subs[i]["t1"] = subs[i + 1]["t0"]
    d = dict(voix=voix, segs=segs, subs=subs, total=t / SPEED)
    json.dump(d, open(os.path.join(WORK, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print("durée", round(t / SPEED, 2), "s")
    for x in segs:
        print(x)
    for x in subs:
        print(x)


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
    while True:  # la ligne doit tenir dans 920 px (marges Instagram), sinon police plus petite
        E.font(c, E.SANS_B, size)
        space = c.text_extents(" ").x_advance * 1.1
        ws = [(w, c.text_extents(w).x_advance) for w in s["words"]]
        lw = sum(x for _, x in ws) + space * (len(ws) - 1) + size * 0.36 * sum(w in KEYS for w in s["words"])
        if lw <= 920 or size <= 56:
            break
        size -= 2
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
    # voix seule, une seule chaîne (jamais de mélange voix nettoyée + voix d'origine) ;
    # chaque morceau de voix est posé à sa place, silence entre (montage d'entraînement).
    SR = 48000
    buf = np.zeros(int((d["total"] * SPEED + 0.5) * SR), np.float32)
    for v in d["voix"]:
        dur = v["src_out"] - v["src_in"]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{v['src_in']:.3f}", "-t", f"{dur:.3f}", "-i",
                              os.path.join(RUSH, CLIPS[v["clip"]] + ".mp4"), "-af",
                              f"pan=mono|c0=0.5*c0+0.5*c1,aresample={SR},afade=t=in:d=0.012,"
                              f"afade=t=out:st={max(dur - 0.025, 0):.3f}:d=0.025",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32)
        i0 = int(v["start"] * SR)
        buf[i0:i0 + len(x)] += x[:len(buf) - i0]
    src = os.path.join(WORK, "voix_assemblee.wav")
    with wave.open(src, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    tmp = os.path.join(WORK, "voix_tmp.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    f"atempo={SPEED},{VOIX_FILTRE},pan=stereo|c0=c0|c1=c0",
                    "-ar", str(SR), tmp], check=True)
    # volume mesuré sur les passages parlés seulement, puis correction pour -14 LUFS (limiteur -1 dB)
    parts = ";".join(f"[0:a]atrim={v['start'] / SPEED:.3f}:{(v['start'] + v['src_out'] - v['src_in']) / SPEED:.3f},"
                     f"asetpts=PTS-STARTPTS[p{i}]" for i, v in enumerate(d["voix"]))
    n = len(d["voix"])
    m = subprocess.run(["ffmpeg", "-i", tmp, "-filter_complex",
                        parts + ";" + "".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,ebur128",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", m)[-1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    f"volume={-14 - I:.2f}dB,alimiter=limit=0.89:level=false", "-ar", str(SR),
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
    final = os.path.join(WORK, "BENFIT_reel_discipline_8s.mp4" if COURT else "BENFIT_reel_discipline_15s.mp4")
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
