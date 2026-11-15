"""Music bed + sound design, synthesised. Writes music.wav and sfx.wav at 48 kHz stereo."""
import json, numpy as np, wave, sys
SR = 48000
DUR = float(sys.argv[1])
rng = np.random.default_rng(7)
N = int(DUR * SR)

def write(path, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    w = wave.open(path, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes()); w.close()

def env(n, a, d, sustain=0.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * (sustain + (1 - sustain) * np.exp(-t / d))

def lp(x, fc):  # one-pole low-pass
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y

def lp_fast(x, fc, order=2):
    from numpy.fft import rfft, irfft, rfftfreq
    X = rfft(x); f = rfftfreq(len(x), 1 / SR)
    return irfft(X / (1 + (f / fc) ** (2 * order)) ** 0.5, len(x))

def bp_fast(x, lo, hi):
    from numpy.fft import rfft, irfft, rfftfreq
    X = rfft(x); f = rfftfreq(len(x), 1 / SR)
    h = 1 / (1 + (lo / np.maximum(f, 1)) ** 4) ** 0.5 / (1 + (f / hi) ** 4) ** 0.5
    return irfft(X * h, len(x))

# ------------------------------------------------------------- music
BPM = 96; beat = 60 / BPM; bar = 4 * beat
L = np.zeros(N); Rr = np.zeros(N)
def add(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= N or i < 0: return
    n = min(len(x), N - i); buf[i:i + n] += g * x[:n]

kick_n = int(0.45 * SR); tk = np.arange(kick_n) / SR
freq = 48 + 90 * np.exp(-tk / 0.035)
kick = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-tk / 0.16)
kick += 0.3 * np.sin(2 * np.pi * np.cumsum(freq) / SR * 2) * np.exp(-tk / 0.03)
clap = bp_fast(rng.standard_normal(int(0.25 * SR)), 900, 5000) * env(int(0.25 * SR), 0.002, 0.06)
clap /= np.abs(clap).max()
hat = bp_fast(rng.standard_normal(int(0.06 * SR)), 7000, 16000) * env(int(0.06 * SR), 0.001, 0.012)
hat /= np.abs(hat).max()

# chords (A minor feel, bright): Am9 - Fmaj7 - Cmaj7 - G6
notes = {"A2": 110.0, "F2": 87.31, "C3": 130.81, "G2": 98.0}
CH = [("A2", [220.0, 261.63, 329.63, 392.0, 493.88]), ("F2", [174.61, 220.0, 261.63, 329.63, 392.0]),
      ("C3", [196.0, 261.63, 329.63, 392.0, 493.88]), ("G2", [196.0, 246.94, 293.66, 329.63, 392.0])]

intro_end = 9.25   # chapter 1 wipe
end_t = float(sys.argv[2])
t = 0.0; k = 0
while t < DUR:
    root, chord = CH[k % 4]
    n = int(bar * SR) + int(0.4 * SR); tt = np.arange(n) / SR
    pad = np.zeros(n)
    for f in chord:
        for det in (-0.12, 0.0, 0.12):
            ph = rng.uniform(0, 2 * np.pi)
            pad += np.sin(2 * np.pi * f * (1 + det / 100) * tt + ph) + 0.25 * np.sin(2 * np.pi * 2 * f * (1 + det / 100) * tt + ph)
    pad *= np.minimum(1, tt / 0.6) * np.minimum(1, np.maximum(0, (n / SR - tt) / 0.5))
    pad = lp_fast(pad, 1800) / 30
    add(L, pad, t, 0.55); add(Rr, pad, t, 0.55)
    bass_f = notes[root]
    full = intro_end <= t < end_t - 0.2
    if full:
        for b in range(4):
            tb = t + b * beat
            add(L, kick, tb, 0.55); add(Rr, kick, tb, 0.55)
            if b in (1, 3): add(L, clap, tb, 0.18); add(Rr, clap, tb, 0.20)
            for h in range(2):
                g = 0.07 if h else 0.05
                add(L, hat, tb + h * beat / 2, g * 0.8); add(Rr, hat, tb + h * beat / 2, g)
            # sub bass pulse
            bn = int(beat * 0.9 * SR); tb_ = np.arange(bn) / SR
            bs = np.tanh(1.8 * np.sin(2 * np.pi * bass_f * tb_)) * env(bn, 0.01, 0.35, 0.2)
            add(L, bs, tb, 0.22); add(Rr, bs, tb, 0.22)
    else:
        for b in range(4):
            tb = t + b * beat
            for h in range(2):
                add(L, hat, tb + h * beat / 2, 0.035); add(Rr, hat, tb + h * beat / 2, 0.045)
            if t >= end_t - 0.2 and b == 0:
                bn = int(bar * SR); tb_ = np.arange(bn) / SR
                bs = np.sin(2 * np.pi * bass_f * tb_) * env(bn, 0.02, 1.2)
                add(L, bs, tb, 0.2); add(Rr, bs, tb, 0.2)
    t += bar; k += 1
mus = np.stack([L, Rr], 1)
fade = np.minimum(1, np.arange(N) / (0.3 * SR)) * np.minimum(1, (N - np.arange(N)) / (1.0 * SR))
mus *= fade[:, None]
mus /= np.abs(mus).max() + 1e-9
write("/home/claude/work/music.wav", mus * 0.8)

# ------------------------------------------------------------- SFX
S = np.zeros((N, 2))
def put(x, t, g, pan=0.0):
    i = int(t * SR)
    if i < 0 or i >= N: return
    n = min(len(x), N - i)
    S[i:i + n, 0] += g * x[:n] * (1 - pan) ; S[i:i + n, 1] += g * x[:n] * (1 + pan)

def whoosh(d=0.45, lo=300, hi=6000, up=True):
    n = int(d * SR); x = rng.standard_normal(n); tt = np.arange(n) / n
    # sweep by blending two band-passed versions
    a = bp_fast(x, lo, lo * 4); b = bp_fast(x, hi / 4, hi)
    m = tt if up else 1 - tt
    y = a * (1 - m) + b * m
    e = np.sin(np.pi * np.clip(tt, 0, 1)) ** 1.5
    y = y * e; return y / (np.abs(y).max() + 1e-9)

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

def clank():
    n = int(0.35 * SR); tt = np.arange(n) / SR
    y = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt / d) for f, a, d in [(420, 1, 0.12), (1130, 0.6, 0.08), (2310, 0.35, 0.05), (3720, 0.2, 0.03)])
    y += 0.4 * bp_fast(rng.standard_normal(n), 2000, 9000) * np.exp(-tt / 0.006)
    return y / np.abs(y).max()

ev = json.load(open("/home/claude/work/events.json"))
seen = set()
for t, kind in ev:
    key = (round(t, 2), kind)
    if key in seen: continue
    seen.add(key)
    if kind == "wipe":
        put(whoosh(0.5, 250, 7000), t - 0.12, 0.30, -0.3); put(thump(60, 0.5), t + 0.12, 0.40)
        put(whoosh(0.45, 300, 6000, up=False), t + 0.72, 0.18, 0.3)
    elif kind == "whoosh_up": put(whoosh(0.4, 400, 5000), t - 0.05, 0.16)
    elif kind == "swoosh": put(whoosh(0.3, 600, 7000), t - 0.05, 0.11)
    elif kind == "tick": put(tick(), t, 0.10)
    elif kind == "hit": put(thump(80, 0.3), t, 0.28)
    elif kind == "clank": put(clank(), t, 0.07, 0.2)
    elif kind == "end": put(whoosh(0.6, 200, 6000), t - 0.2, 0.22); put(thump(55, 0.7), t + 0.2, 0.40)
# hook impact on the "4"
put(thump(65, 0.5), 0.0, 0.45); put(whoosh(0.35, 500, 8000, up=False), 0.0, 0.12)
write("/home/claude/work/sfx.wav", S)
print("ok")
