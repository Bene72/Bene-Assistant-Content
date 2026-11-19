"""Reel « Zone 2 / HYROX » (19 nov. 2026) : format court, viral, intense, 2 effets seulement.

Tourné en courant (caméra à la main, face à Bene). Étapes, toutes dans ce script :
  python build_zone2.py edl      → liste de montage calée sur les mots (timeline.json)
  python build_zone2.py base     → assemblage, accélération ×1,08, étalonnage très léger
  python build_zone2.py stills T1 T2 …  → images de contrôle
  python build_zone2.py video    → compositing (sous-titres + 2 effets) puis son
Entrées : rushs de la Release « rushs » (VID_20261119_0941..0947) renommés c1..c6, transcript.json (transcribe.py).
"""
import sys, os, json, re, math, subprocess, wave
import numpy as np
import cairo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "effets"))
import effets as E

RUSH = os.environ.get("RUSH", "/home/claude/run/rush")
WORK = os.environ.get("WORK", "/home/claude/run/work")
os.makedirs(WORK, exist_ok=True)
W, H, FPS = 1080, 1920, 30
SPEED = 1.08
CLIPS = {"c1": "c1_094137", "c2": "c2_094412", "c3": "c3_094450", "c4": "c4_094535", "c5": "c5_094636", "c6": "c6_094730"}

# (clip, début source, fin source, tag) — fin = juste avant le mot suivant
PIECES = [
    ("c1", 1.40, 4.45, "hook"),     # Tu veux courir plus vite sur ton HYROX ?
    ("c1", 5.30, 10.00, "zone2"),   # Non. Courir une allure zone 2. Une allure où tu peux parler.
    ("c2", 0.12, 9.25, "volume"),   # Tu veux augmenter ton volume … améliorer également tes vitesses … comme à l'HYROX, fais la zone 2,
    ("c5", 11.04, 15.62, "gains"),  # tu auras une meilleure récupération, moins de fatigue, et tu pourras courir beaucoup plus vite.
    ("c5", 18.33, 25.40, "piste"),  # si tu t'épuisais à faire que de la piste … ne pas tenir le jour J.
    ("c6", 11.26, 13.10, "fin"),    # oublie pas le lièvre et la tortue.
]

# corrections de transcription (orthographe / mots mal reconnus, le sens n'est jamais changé)
FIX = {("hook", "IRO"): "HYROX ?", ("hook", "?"): None, ("volume", "Lirox,"): "l'HYROX,", ("fin", "livre"): "lièvre", ("fin", "à"): "et"}
INSERT = {("volume", "Tu"): ["Tu", "veux"]}  # « veux » avalé par la reconnaissance vocale
KEYS = ["HYROX ?", "Non.", "zone", "2.", "2,", "parler.", "volume", "cramer,", "vitesses", "piste", "moteur",
        "jour", "J.", "lièvre", "tortue."]


def words():
    d = json.load(open(os.path.join(WORK, "transcript.json")))
    out = {}
    for k, v in d.items():
        ws = []
        for tok, t in v["tokens"]:
            if tok.startswith(" ") or not ws:
                ws.append([tok.strip(), t])
            else:
                ws[-1][0] += tok
        for i, w in enumerate(ws):
            w.append(ws[i + 1][1] - 0.05 if i + 1 < len(ws) else w[1] + 0.5)
        out[k.replace(".wav", "")] = ws
    return out


def energy(clip):
    w = wave.open(os.path.join(RUSH, CLIPS[clip] + ".wav"))
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    h = 160
    n = len(a) // h
    return 20 * np.log10(np.sqrt((a[:n * h].reshape(n, h) ** 2).mean(1) + 1e-12))


def edl():
    WD = words()
    tl, t = [], 0.0
    for clip, a, b, tag in PIECES:
        e = energy(clip)
        # cale chaque coupe sur le point le plus calme à ±80 ms
        def snap(x):
            i0, i1 = int((x - 0.08) * 100), int((x + 0.08) * 100)
            return (i0 + int(np.argmin(e[i0:i1 + 1]))) / 100
        a2, b2 = snap(a), snap(b)
        tl.append(dict(clip=clip, src_in=a2, src_out=b2, start=t / SPEED, tag=tag))
        t += b2 - a2
    ws = []
    for c in tl:
        for w, on, off in WD[CLIPS[c["clip"]]]:
            if not (c["src_in"] - 0.05 <= on < c["src_out"] - 0.05):
                continue
            key = (c["tag"], w)
            rep = INSERT.get(key, [FIX.get(key, w)])
            for j, r in enumerate(rep):
                if r is None:
                    continue
                tt = c["start"] + (on - c["src_in"]) / SPEED + j * 0.12
                te = c["start"] + (min(off, c["src_out"]) - c["src_in"]) / SPEED
                ws.append(dict(w=r, t=round(tt, 3), te=round(max(te, tt + 0.12), 3), tag=c["tag"]))
    for c in tl:
        c["end"] = c["start"] + (c["src_out"] - c["src_in"]) / SPEED
    # majuscule en début de phrase (et au début du Reel)
    for i, w in enumerate(ws):
        if (i == 0 or re.search(r"[.?!]$", ws[i - 1]["w"])) and w["w"][0].isalpha():
            w["w"] = w["w"][0].upper() + w["w"][1:]
    json.dump(dict(timeline=tl, total=t / SPEED, words=ws), open(os.path.join(WORK, "timeline.json"), "w"),
              ensure_ascii=False, indent=1)
    print("total", round(t / SPEED, 2), "s")
    for c in tl:
        print(c["tag"], round(c["start"], 2), c["src_in"], c["src_out"])
    print(" ".join(w["w"] for w in ws))


GRADE = "eq=contrast=1.03:brightness=0.005:saturation=1.0,unsharp=5:5:0.25,noise=alls=3:allf=t"


def base():
    d = json.load(open(os.path.join(WORK, "timeline.json")))
    args, fc = ["ffmpeg", "-v", "error", "-y"], []
    for k, c in enumerate(d["timeline"]):
        dur = c["src_out"] - c["src_in"]
        args += ["-ss", f"{c['src_in']:.3f}", "-t", f"{dur:.3f}", "-i", os.path.join(RUSH, CLIPS[c["clip"]] + ".mp4")]
        fc.append(f"[{k}:v]fps=60,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts=PTS-STARTPTS[v{k}]")
        fc.append(f"[{k}:a]aresample=48000,asetpts=PTS-STARTPTS,afade=t=in:d=0.012,"
                  f"afade=t=out:st={max(dur - 0.03, 0):.3f}:d=0.03[a{k}]")
    n = len(d["timeline"])
    fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]setpts=PTS/{SPEED},fps={FPS},{GRADE},format=yuv420p[vo]")
    fc.append(f"[ac]atempo={SPEED}[ao]")
    args += ["-filter_complex", ";".join(fc), "-map", "[vo]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
             os.path.join(WORK, "base.mp4"), "-map", "[ao]", "-c:a", "pcm_s16le", os.path.join(WORK, "voice_raw.wav")]
    subprocess.run(args, check=True)
    print("base ok")


# ------------------------------------------------------------------ compositing
D = None
SUBS = []


def load():
    global D, SUBS
    D = json.load(open(os.path.join(WORK, "timeline.json")))
    for w in D["words"]:
        w["key"] = w["w"] in KEYS
    chunks, cur, prev = [], [], None
    for w in D["words"]:
        n = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
        if cur and (n > 18 or w["tag"] != prev or w["t"] - cur[-1]["te"] > 0.6):
            chunks.append(cur)
            cur = []
        cur.append(w)
        prev = w["tag"]
        if re.search(r"[.,?!]$", w["w"]) and sum(len(x["w"]) + 1 for x in cur) > 8:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    SUBS = []
    for i, ch in enumerate(chunks):
        t1 = chunks[i + 1][0]["t"] - 0.05 if i + 1 < len(chunks) else ch[-1]["te"] + 0.5
        SUBS.append(dict(t0=ch[0]["t"] - 0.05, t1=min(t1, ch[-1]["te"] + 0.5), words=ch))


def piece(tag):
    return next(c for c in D["timeline"] if c["tag"] == tag)


def wt(tag, word):
    return next(w["t"] for w in D["words"] if w["tag"] == tag and w["w"].startswith(word))


def windows():
    z = piece("zone2")
    g = piece("gains")
    return dict(
        derriere=(wt("zone2", "zone") - 0.1, z["end"] - 0.45),          # effet 1 : ZONE 2 derrière Bene
        toggles=(g["start"] - 0.1, g["end"] + 0.5),                      # effet 2 : les 3 bénéfices
        toggle_on=[wt("gains", "meilleure"), wt("gains", "moins"), wt("gains", "plus")],
    )


STROKE = (0.08, 0.30, 0.92)


def draw_subs(c, T, y=1330, size=76):
    for s in SUBS:
        if s["t0"] <= T < s["t1"]:
            break
    else:
        return
    a = E.eo((T - s["t0"]) / 0.1)
    E.font(c, E.SANS_B, size)
    space = c.text_extents(" ").x_advance * 1.1
    lines, cur, cw = [], [], 0
    for w in s["words"]:
        ww = c.text_extents(w["w"]).x_advance
        if cur and cw + space + ww > 900:
            lines.append((cur, cw))
            cur, cw = [], 0
        cur.append((w, ww))
        cw += (space if len(cur) > 1 else 0) + ww
    lines.append((cur, cw))
    lh = size * 1.3
    sc = 0.9 + 0.1 * E.eo((T - s["t0"]) / 0.12)
    c.save()
    c.translate(W / 2, y)
    c.scale(sc, sc)
    c.translate(-W / 2, -y)
    for li, (ws, lw) in enumerate(lines):
        x = W / 2 - lw / 2
        yy = y + (li - (len(lines) - 1) / 2) * lh
        for w, ww in ws:
            on = T >= w["t"] - 0.03
            if w["key"] and on:
                pad = size * 0.18
                E.rrect(c, x - pad, yy - size * 0.78, ww + 2 * pad, size * 1.02, 10)
                c.set_source_rgba(*E.BLUE, a)
                c.fill()
            c.move_to(x, yy)
            c.text_path(w["w"])
            if not (w["key"] and on):
                c.set_source_rgba(*STROKE, a)
                c.set_line_width(9)
                c.set_line_join(cairo.LINE_JOIN_ROUND)
                c.stroke_preserve()
            c.set_source_rgba(1, 1, 1, a)
            c.fill()
            x += ww + space
    c.restore()


FOCUS_X = {"hook": 0.12}  # cadrage : sur l'accroche Bene est sur le bord gauche de l'image


def tag_at(T):
    for c in D["timeline"]:
        if c["start"] <= T < c["end"]:
            return c["tag"]
    return D["timeline"][-1]["tag"]


def scale_at(T):
    """Rythme : léger punch-in un plan sur deux + poussée lente, gros punch-in sur l'accroche."""
    for i, c in enumerate(D["timeline"]):
        if c["start"] <= T < c["end"] or i == len(D["timeline"]) - 1:
            p = (T - c["start"]) / max(c["end"] - c["start"], 0.5)
            s = (1.0 if i % 2 == 0 else 1.07) + 0.03 * E.clamp(p)
            if c["tag"] == "hook":
                s = 1.10 + 0.14 * (1 - E.eo((T - c["start"]) / 0.5))
            if c["tag"] == "fin":
                s = 1.0 + 0.10 * E.eio(p)
            return s
    return 1.0


def render(T, frame, WIN):
    s = scale_at(T)
    if s != 1.0:
        from PIL import Image
        im = Image.fromarray(frame)
        w2, h2 = int(W * s), int(H * s)
        im = im.resize((w2, h2), Image.BICUBIC)
        fx = 0.5
        if tag_at(T) == "hook":  # Bene démarre sur le bord gauche, puis se recentre
            fx = 0.12 + 0.38 * E.eio((T - 0.7) / 0.6)
        x0, y0 = int((w2 - W) * fx), int((h2 - H) * 0.42)
        frame = np.asarray(im.crop((x0, y0, x0 + W, y0 + H)))
    cv = E.Canvas(frame)
    a0, a1 = WIN["derriere"]
    if a0 <= T <= a1:
        E.fx_derriere(cv, T - a0, lignes=("ZONE 2",), face=E.NUM, y=880, max_size=460, dur=a1 - a0, step=0.22)
    b0, b1 = WIN["toggles"]
    in_toggles = b0 <= T <= b1
    if in_toggles:
        E.fx_toggles(cv, T - b0, rows=("Meilleure récup", "Moins de fatigue", "Plus vite"), dur=b1 - b0,
                     cy=1250, on_times=[x - b0 for x in WIN["toggle_on"]])
    if not in_toggles:
        cv.draw(lambda c: draw_subs(c, T))
    return cv.out()


def frames_iter():
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(WORK, "base.mp4"), "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        b = rd.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


def remix():
    """Refaire seulement le son (sans recalculer l'image) puis réassembler la vidéo finale."""
    audio()
    out = os.path.join(WORK, "video_nosound.mp4")
    final = os.path.join(WORK, "BENFIT_reel_zone2_hyrox_v2.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "mix.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("ok", final)


def video():
    load()
    WIN = windows()
    out = os.path.join(WORK, "video_nosound.mp4")
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i, f in enumerate(frames_iter()):
        wr.stdin.write(render(i / FPS, np.array(f), WIN).tobytes())
    wr.stdin.close()
    wr.wait()
    audio()
    final = os.path.join(WORK, "BENFIT_reel_zone2_hyrox.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-i", os.path.join(WORK, "mix.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("ok", final)


def audio():
    # voix tournée en courant : coupe-bas plus haut et réduction de bruit plus forte (vent), sans musique
    # v2 (retour de Bene) : réduction de bruit moins forte (nr 16 → 11) et 20 % de son d'origine remélangé,
    # pour une voix plus naturelle (la v1 sonnait un peu robotique) ; on garde un peu d'ambiance de course.
    fc = ("[0:a]aresample=48000,highpass=f=90,asplit=2[a][b];"
          "[a]afftdn=nf=-30:nr=11[den];"
          "[den][b]amix=inputs=2:weights='0.8 0.2':normalize=0,equalizer=f=3000:t=q:w=1.2:g=1.5,"
          "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,pan=stereo|c0=c0|c1=c0,"
          "loudnorm=I=-14:TP=-1:LRA=9[o]")
    tmp = os.path.join(WORK, "mix_tmp.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WORK, "voice_raw.wav"), "-filter_complex", fc,
                    "-map", "[o]", "-ar", "48000", tmp], check=True)
    # 2e passe : on mesure et on corrige le volume pour tomber pile à -14 LUFS (limiteur à -1 dB)
    m = subprocess.run(["ffmpeg", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", m)[-1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", f"volume={-14 - I:.2f}dB,alimiter=limit=0.89:level=false",
                    "-ar", "48000", os.path.join(WORK, "mix.wav")], check=True)


def stills(ts):
    load()
    WIN = windows()
    from PIL import Image
    for T in ts:
        f = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{T:.3f}", "-i", os.path.join(WORK, "base.mp4"),
                            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        fr = np.frombuffer(f, np.uint8).reshape(H, W, 3)
        Image.fromarray(render(T, np.array(fr), WIN)).resize((360, 640)).save(os.path.join(WORK, f"st_{T:05.2f}.png"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "edl":
        edl()
    elif cmd == "base":
        base()
    elif cmd == "video":
        video()
    elif cmd == "remix":
        remix()
    elif cmd == "stills":
        stills([float(x) for x in sys.argv[2:]])
    elif cmd == "subs":
        load()
        print(windows())
        for s in SUBS:
            print(f"{s['t0']:5.2f}-{s['t1']:5.2f}", " ".join(("[" + w["w"] + "]") if w["key"] else w["w"] for w in s["words"]))
