import json, subprocess
SPEED = 1.08
d = json.load(open("/home/claude/work/timeline.json"))
tl = d["timeline"]
GRADE = ("eq=contrast=1.05:saturation=1.05:brightness=0.015:gamma=1.02,"
         "colorbalance=rm=0.015:bm=-0.015,"
         "unsharp=5:5:0.3,noise=alls=5:allf=t")
args = ["ffmpeg", "-v", "error", "-y"]
fc = []
for k, p in enumerate(tl):
    dur = p["src_out"] - p["src_in"]
    args += ["-ss", f"{p['src_in']:.3f}", "-t", f"{dur:.3f}", "-i", f"/home/claude/rushs/VID_20261113_{p['file']}.mp4"]
    fc.append(f"[{k}:v]fps=60,setpts=PTS-STARTPTS[v{k}]")
    vol = "volume=0," if p.get("mute") else ""
    fc.append(f"[{k}:a]aresample=48000,{vol}asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={max(dur-0.03,0):.3f}:d=0.03[a{k}]")
n = len(tl)
fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
fc.append(f"[vc]setpts=PTS/{SPEED},fps=30,{GRADE},format=yuv420p[vo]")
fc.append(f"[ac]atempo={SPEED}[ao]")
args += ["-filter_complex", ";".join(fc), "-map", "[vo]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
         "/home/claude/work/base_v2.mp4", "-map", "[ao]", "-c:a", "pcm_s16le", "/home/claude/work/voice_raw_v2.wav"]
subprocess.run(args, check=True)
# scaled timeline for the compositor
for p in tl:
    p["start"] = round(p["start"] / SPEED, 4)
d["total"] = d["total"] / SPEED; d["speed"] = SPEED
json.dump(d, open("/home/claude/work/timeline_out.json", "w"), indent=1)
print("done", d["total"])
