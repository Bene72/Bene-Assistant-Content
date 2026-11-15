"""Edit decision list for the BEN&FIT reel 'Les 4 étapes'."""
import json, subprocess

R = "/home/claude/rushs/"
F = {k: f"VID_20261113_{k}" for k in ["153440", "153503", "153526", "153641", "153732", "153831"]}

# (file, in, out, chapter, tag)  -- chapters: 0 hook, 1 BUILD, 2 RUN, 3 PERFORM, 4 MOVE, 5 end
PIECES = [
    ("153440", 6.60, 10.62, 0, "hook"),
    ("153503", 11.42, 16.20, 0, "perf"),
    ("153503", 16.30, 17.30, 0, "letsgo"),
    ("153526", 33.42, 36.25, 1, "B1"),
    ("153526", 36.33, 39.65, 1, "B2"),
    ("153526", 39.78, 42.82, 1, "B3"),
    ("153526", 42.82, 47.10, 1, "B4"),
    ("153526", 49.27, 49.58, 1, "B5a"),
    ("153526", 49.90, 53.85, 1, "B5"),
    ("153526", 54.84, 57.30, 1, "B6"),
    ("153641", 1.66, 8.85, 2, "C1"),
    ("153641", 15.33, 16.48, 2, "C3a"),
    ("153641", 17.42, 28.30, 2, "C3b"),
    ("153641", 30.95, 37.45, 2, "C4"),
    ("153732", 1.76, 3.55, 3, "D1"),
    ("153732", 10.43, 12.60, 3, "D2a"),
    ("153732", 15.10, 18.05, 3, "D2b"),
    ("153732", 20.45, 21.20, 3, "D3a"),
    ("153732", 21.58, 22.75, 3, "D3b"),
    ("153732", 23.02, 26.35, 3, "D4"),
    ("153732", 36.14, 40.55, 3, "D5"),
    ("153831", 1.12, 2.45, 4, "E1a"),
    ("153831", 5.12, 7.20, 4, "E1b"),
    ("153831", 9.88, 15.95, 4, "E2"),
    ("153831", 25.58, 28.75, 4, "E4a"),
    ("153831", 28.95, 32.30, 4, "E4b"),
    ("153831", 32.60, 37.40, 4, "E5"),
    ("153831", 37.50, 39.95, 4, "E6a"),
    ("153831", 40.70, 41.95, 4, "E6b"),
    ("153831", 50.08, 54.10, 4, "E7"),
    ("153831", 54.15, 55.25, 4, "E8a"),
    ("153831", 56.98, 57.83, 4, "E8b"),
    ("153831", 68.20, 70.45, 5, "F1"),
]
END_CARD = ("153831", 70.45, 4.2)  # silent b-roll under the end card (file, in, duration)

import wave, numpy as np
def pauses(f, thr=-42.0, minlen=0.30):
    w = wave.open(f"/home/claude/work/audio/VID_20261113_{f}.wav")
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    h = 320; n = len(a) // h
    db = 20 * np.log10(np.sqrt((a[:n*h].reshape(n, h) ** 2).mean(1) + 1e-12))
    low = db < thr; out = []; i = 0
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]: j += 1
            if (j - i) * 0.02 >= minlen: out.append((i * 0.02, j * 0.02))
            i = j
        else: i += 1
    return out
sil = {k: pauses(k) for k in F}

def split_piece(f, a, b, maxgap=0.30, keep=0.09):
    """Remove internal pauses longer than maxgap, keeping `keep` s of air on each side."""
    segs = [[a, b]]
    for s, e in sil[f]:
        if e - s < maxgap: continue
        cs, ce = s + keep, e - keep
        new = []
        for x, y in segs:
            if cs > x + 0.05 and ce < y - 0.05:
                new += [[x, cs], [ce, y]]
            else:
                new.append([x, y])
        segs = new
    return segs

_db = {}
def energy(f):
    if f not in _db:
        w = wave.open(f"/home/claude/work/audio/VID_20261113_{f}.wav")
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
        h = 160; n = len(a) // h
        e = 20 * np.log10(np.sqrt((a[:n*h].reshape(n, h) ** 2).mean(1) + 1e-12))
        _db[f] = np.convolve(e, np.ones(3) / 3, mode="same")  # 10 ms hop, smoothed
    return _db[f]

def snap(f, t, lo, hi):
    e = energy(f); i0, i1 = max(0, int((t + lo) * 100)), min(len(e) - 1, int((t + hi) * 100))
    i = i0 + int(np.argmin(e[i0:i1 + 1]))
    return i / 100, e[i]

WARN = []
OVERRIDE = {"C3a": (15.43, 16.60), "E8b": (56.92, 57.92)}
def snapw(f, t0, t1):
    e = energy(f); i0, i1 = int(t0 * 100), int(t1 * 100)
    i = i0 + int(np.argmin(e[i0:i1 + 1]))
    return i / 100, e[i]

def load_words():
    a = json.load(open("/home/claude/work/transcript.json")); a.update(json.load(open("/home/claude/work/t4.json")))
    out = {}
    for name, d in a.items():
        W = []
        for tok, t in d["tokens"]:
            if tok.startswith(" ") or not W: W.append([tok.strip(), t, t])
            else: W[-1][0] += tok; W[-1][2] = t
        out[name.replace(".wav", "")[-6:]] = W
    return out
WORDS = load_words()
def build():
    tl = []  # list of dict(file,in,out,start,chapter,tag,sub)
    t = 0.0
    for f, a, b, ch, tag in PIECES:
        W = WORDS[f]
        fi = next(i for i, w in enumerate(W) if w[1] >= a - 0.02)
        li = max(i for i, w in enumerate(W) if w[1] <= b - 0.05)
        lo = W[fi - 1][2] + 0.12 if fi > 0 else W[fi][1] - 0.4
        hi = W[fi][1] + 0.03
        a2, ea = snapw(f, min(lo, hi - 0.02), hi)
        lo = W[li][2] + 0.10
        hi = W[li + 1][1] + 0.03 if li + 1 < len(W) else W[li][2] + 0.6
        b2, eb = snapw(f, lo, max(hi, lo + 0.02))
        if ea > -36 or eb > -36: WARN.append((tag, W[fi][0], a2, round(ea), W[li][0], b2, round(eb)))
        a, b = a2, b2
        if tag in OVERRIDE: a, b = OVERRIDE[tag]
        for i, (x, y) in enumerate([s_ for s_ in split_piece(f, a, b) if s_[1] - s_[0] > 0.15]):
            tl.append(dict(file=f, src_in=round(x, 3), src_out=round(y, 3), start=round(t, 3), chapter=ch, tag=tag, sub=i))
            t += y - x
    f, a, d = END_CARD
    tl.append(dict(file=f, src_in=a, src_out=a + d, start=round(t, 3), chapter=6, tag="endcard", sub=0, mute=True))
    t += d
    return tl, t

if __name__ == "__main__":
    tl, total = build()
    json.dump(dict(timeline=tl, total=total), open("/home/claude/work/timeline.json", "w"), indent=1)
    print(len(tl), "cuts, total", round(total, 2))
    for w in WARN: print("WARN", w)
    for p in tl: print(p["tag"], p["sub"], p["start"], p["src_in"], p["src_out"])
