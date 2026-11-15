import sys, json, re, subprocess, wave, numpy as np, sherpa_onnx, glob, os

M = "/home/claude/work/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
if not os.path.isdir(M):
    M = glob.glob("/home/claude/work/models/*/")[0] if glob.glob("/home/claude/work/models/*/") else "/home/claude/work/models"
rec = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=f"{M}/encoder.int8.onnx", decoder=f"{M}/decoder.int8.onnx",
    joiner=f"{M}/joiner.int8.onnx", tokens=f"{M}/tokens.txt",
    model_type="nemo_transducer", num_threads=2)

def load(p):
    w = wave.open(p); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return a

def silences(p):
    out = subprocess.run(["ffmpeg", "-i", p, "-af", "silencedetect=n=-35dB:d=0.25", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(s, e))

res = {}
for p in sys.argv[1:]:
    a = load(p); sr = 16000; dur = len(a) / sr
    sil = silences(p)
    # cut points = middle of silences
    cuts = [0.0]
    mids = [(s + e) / 2 for s, e in sil]
    last = 0.0
    for m in mids:
        if m - last > float(os.environ.get("CH","12")):
            cuts.append(m); last = m
    cuts.append(dur)
    words = []
    for i in range(len(cuts) - 1):
        t0, t1 = cuts[i], cuts[i + 1]
        st = rec.create_stream(); st.accept_waveform(sr, a[int(t0 * sr):int(t1 * sr)]); rec.decode_stream(st)
        r = st.result
        for tok, ts in zip(r.tokens, r.timestamps):
            words.append([tok, round(t0 + ts, 3)])
    name = os.path.basename(p)
    res[name] = {"duration": dur, "silences": sil, "tokens": words}
    text = "".join(t for t, _ in words)
    print("=====", name, round(dur, 1)); print(text); sys.stdout.flush()
json.dump(res, open(os.environ.get("OUT","/home/claude/work/transcript.json"), "w"), ensure_ascii=False)
