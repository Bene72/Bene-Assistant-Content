"""Son du Reel BEN&FIT x Apocalypse : ambiance des rushs nettoyée + whooshs / impacts discrets, -14 LUFS, sans musique."""
import json, sys, subprocess, numpy as np, wave
SR = 48000
DUR = float(sys.argv[1])
rng = np.random.default_rng(7)
N = int(DUR * SR)

def write(path, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes()); w.close()
def bp_fast(x, lo, hi):
    from numpy.fft import rfft, irfft, rfftfreq
    X = rfft(x); f = rfftfreq(len(x), 1 / SR)
    h = 1 / (1 + (lo / np.maximum(f, 1)) ** 4) ** 0.5 / (1 + (f / hi) ** 4) ** 0.5
    return irfft(X * h, len(x))
S = np.zeros((N, 2))
def put(x, t, g, pan=0.0):
    i = int(t * SR)
    if i < 0 or i >= N: return
    n = min(len(x), N - i)
    S[i:i + n, 0] += g * x[:n] * (1 - pan); S[i:i + n, 1] += g * x[:n] * (1 + pan)
def whoosh(d=0.45, lo=300, hi=6000, up=True):
    n = int(d * SR); x = rng.standard_normal(n); tt = np.arange(n) / n
    a = bp_fast(x, lo, lo * 4); b = bp_fast(x, hi / 4, hi); m = tt if up else 1 - tt
    y = (a * (1 - m) + b * m) * np.sin(np.pi * tt) ** 1.5; return y / (np.abs(y).max() + 1e-9)
def thump(f0=70, d=0.35):
    n = int(d * SR); tt = np.arange(n) / SR
    fr = f0 * (0.6 + 0.8 * np.exp(-tt / 0.05))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt / 0.12)
    nz = bp_fast(rng.standard_normal(n), 1500, 8000) * np.exp(-tt / 0.01)
    y = y + 0.25 * nz / (np.abs(nz).max() + 1e-9); return y / np.abs(y).max()
def tick():
    n = int(0.05 * SR); tt = np.arange(n) / SR
    y = np.sin(2 * np.pi * 1900 * tt) * np.exp(-tt / 0.008) + 0.5 * np.sin(2 * np.pi * 3100 * tt) * np.exp(-tt / 0.005)
    return y / np.abs(y).max()

for t, kind in json.load(open("/home/claude/work/apo/events_apo.json")):
    if kind == "swoosh": put(whoosh(0.35, 500, 7000), t - 0.12, 0.12)
    elif kind == "tick": put(tick(), t, 0.08)
    elif kind == "hit": put(thump(75, 0.3), t, 0.22)
    elif kind == "end": put(whoosh(0.6, 200, 6000), t - 0.25, 0.16); put(thump(55, 0.6), t + 0.05, 0.26)
# petit whoosh discret sur les plans accélérés, impact sourd à l'entrée des ralentis
for p in json.load(open("/home/claude/work/apo/timeline.json"))["timeline"]:
    if p["speed"] > 1.05: put(whoosh(0.25, 800, 8000), p["start"] - 0.1, 0.06)
    if p["speed"] < 0.9 and p["sec"] != "end": put(thump(60, 0.4), p["start"], 0.12)
write("/home/claude/work/apo/sfx_apo.wav", S)

# ambiance : coupe-bas, réduction de souffle légère, compression douce pour équilibrer impacts / souffle
fc = ("[0:a]aresample=48000,highpass=f=60,lowpass=f=14000,afftdn=nf=-30:nr=8,"
      "acompressor=threshold=-24dB:ratio=3:attack=5:release=150:makeup=4,alimiter=limit=0.8,"
      "pan=stereo|c0=c0|c1=c1,apad,afade=t=out:st={fo:.3f}:d=1.0[v];"
      "[v][1:a]amix=inputs=2:duration=shortest:normalize=0,loudnorm=I=-14:TP=-1:LRA=9[o]").format(fo=DUR - 1.4)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "/home/claude/work/apo/ambiance_raw.wav", "-i", "/home/claude/work/apo/sfx_apo.wav",
                "-filter_complex", fc, "-map", "[o]", "-ar", "48000", "-t", f"{DUR:.3f}", "/home/claude/work/apo/mix_apo.wav"], check=True)
print("ok")
