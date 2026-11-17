"""Base étalonnée (DA naturelle, mêmes réglages que build_base_naturel.py) avec vitesse par plan.
Écrit base_apo.mp4 (1080x1920, 30 fps) + ambiance_raw.wav (son des rushs)."""
import json, subprocess
d = json.load(open("/home/claude/work/apo/timeline.json"))
tl = d["timeline"]
GRADE = ("eq=contrast=1.05:saturation=1.05:brightness=0.015:gamma=1.02,"
         "colorbalance=rm=0.015:bm=-0.015,"
         "unsharp=5:5:0.3,noise=alls=5:allf=t")
# lumière retravaillée par rush (contre-jour sur le superset KB : on relève les ombres sans brûler le fond)
RELIGHT = {"758649051": "curves=all='0/0 0.25/0.33 0.6/0.68 1/0.97',eq=saturation=1.04,"}
args = ["ffmpeg", "-v", "error", "-y"]
fc = []
for k, p in enumerate(tl):
    dur = p["src_out"] - p["src_in"]; sp = p["speed"]
    args += ["-ss", f"{p['src_in']:.3f}", "-t", f"{dur:.3f}", "-i", f"/home/claude/rushs/a_{p["file"]}.mp4"]
    relight = RELIGHT.get(p["file"], "")
    fc.append(f"[{k}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{relight}fps=60,"
              f"setpts=(PTS-STARTPTS)/{sp},fps=30,setsar=1[v{k}]")
    od = dur / sp
    fc.append(f"[{k}:a]aresample=48000,atempo={sp},asetpts=PTS-STARTPTS,atrim=0:{od:.4f},apad=whole_dur={od:.4f},"
              f"afade=t=in:d=0.015,afade=t=out:st={max(od - 0.03, 0):.3f}:d=0.03[a{k}]")
n = len(tl)
fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
fc.append(f"[vc]{GRADE},format=yuv420p[vo]")
args += ["-filter_complex", ";".join(fc), "-map", "[vo]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
         "/home/claude/work/apo/base_apo.mp4", "-map", "[ac]", "-c:a", "pcm_s16le", "/home/claude/work/apo/ambiance_raw.wav"]
subprocess.run(args, check=True)
print("ok")
