"""Liste de montage du Reel BEN&FIT « Cardio et perte de muscle »."""
import json, subprocess

R = "/home/claude/rushs/"
F = {k: f"VID_20261113_{k}" for k in ["154019", "154045", "154118", "154245"]}

# (fichier, début, fin, chapitre, tag) -- chapitres : 0 accroche, 1 mythe, 2 gestion, 3 modalités, 4 bien programmé, 5 conclusion
PIECES = [
    ("154019", 10.64, 14.12, 0, "hook"),
    ("154045", 3.20, 5.15, 0, "non"),
    ("154045", 6.08, 8.80, 0, "dep"),
    ("154045", 9.28, 11.90, 1, "A1"),
    ("154045", 12.40, 16.30, 2, "A2"),
    ("154045", 17.39, 20.25, 2, "A3"),
    ("154118", 3.04, 4.05, 3, "B0"),
    ("154118", 5.36, 5.90, 3, "B1a"),
    ("154118", 6.80, 9.60, 3, "B1b"),
    ("154118", 16.24, 24.60, 3, "B2"),
    ("154118", 36.36, 39.30, 3, "B3"),
    ("154118", 47.21, 55.55, 3, "B5"),
    ("154118", 56.14, 57.40, 3, "B6"),
    ("154245", 13.10, 15.50, 3, "C1"),
    ("154245", 16.94, 19.90, 3, "C2"),
    ("154245", 26.69, 31.40, 3, "C4"),
    ("154245", 63.38, 64.95, 3, "D1"),
    ("154245", 71.67, 77.35, 3, "D2"),
    ("154245", 77.52, 79.50, 3, "D3"),
    ("154245", 34.06, 36.36, 4, "E1a"),
    ("154245", 39.84, 41.30, 4, "E1b"),
    ("154245", 54.32, 59.10, 4, "E2"),
    ("154245", 61.38, 63.30, 4, "E3"),
    ("154245", 98.98, 106.40, 5, "F1"),
]
END_CARD = ("154245", 106.9, 4.6)  # plan muet sous la carte de fin (fichier, début, durée)

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
OVERRIDE = {"B0": (3.02, 4.28)}
def snapw(f, t0, t1):
    e = energy(f); i0, i1 = int(t0 * 100), int(t1 * 100)
    i = i0 + int(np.argmin(e[i0:i1 + 1]))
    return i / 100, e[i]

def load_words():
    return json.load(open("/home/claude/work/words.json"))
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
        if tl and tl[-1]['file'] == f and tl[-1]['src_in'] < a < tl[-1]['src_out']:
            d_ = tl[-1]['src_out'] - a; tl[-1]['src_out'] = a; t -= d_
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
