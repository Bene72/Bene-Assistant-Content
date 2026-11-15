"""12 s loopable reel: real-time clean pass, then annotated slow-motion with freezes."""
import os, subprocess, sys
import os as _o; FR = _o.environ.get("FR", "/home/claude/work/frames"); SEQ = FR + "_seq"; TXT = "/home/claude/work/txt"
OUT = sys.argv[1]
B = "/home/claude/fonts/Coda-ExtraBold.ttf"; R = "/home/claude/fonts/Coda-Regular.ttf"
os.makedirs(SEQ, exist_ok=True); os.makedirs(TXT, exist_ok=True)
FPS = 30
seq = []  # list of (path, source_frame)
def real(f): return (f"{FR}/f_{int(f):04d}.png", f)
def half(f): return (f"{FR}/h_{int(f):04d}.png", f + 0.5)
# part 1: real time, no text
for f in range(1, 116): seq.append(real(f))
seq += [real(115)] * 4
p2 = len(seq)
FREEZE = {43: 15, 76: 18, 115: 15}
for f in range(19, 116):
    seq.append(real(f)); seq += [real(f)] * FREEZE.get(f, 0)
    if f < 115: seq.append(half(f))
for i, (p, _) in enumerate(seq):
    d = f"{SEQ}/s_{i:04d}.png"
    if os.path.lexists(d): os.unlink(d)
    os.symlink(p, d)
def t_of(src):  # first time in part 2 where source frame >= src
    for i in range(p2, len(seq)):
        if seq[i][1] >= src: return i / FPS
    return len(seq) / FPS
T2 = p2 / FPS; END = len(seq) / FPS
phases = [
    (19, 30, "1 · DÉPART", "Dos plat, épaules au-dessus de la barre"),
    (30, 43.6, "2 · EXTENSION", "Barre près du corps, bras tendus"),
    (43.6, 57, "3 · PASSAGE SOUS LA BARRE", "Tire-toi vite sous la barre"),
    (57, 76.6, "4 · RÉCEPTION", "Bras verrouillés, buste droit, talons au sol"),
    (76.6, 999, "5 · REDRESSEMENT", "Pousse dans la barre, reste gainé"),
]
def tf(name, text):
    p = f"{TXT}/{name}.txt"; open(p, "w").write(text); return p
def alpha(a, b): return f"if(lt(t,{a:.3f}),0,if(lt(t,{a + .15:.3f}),(t-{a:.3f})/0.15,if(lt(t,{b - .12:.3f}),1,if(lt(t,{b:.3f}),({b:.3f}-t)/0.12,0))))"
F = ["scale=1080:1920:flags=lanczos"]
al = alpha(T2, END)
F.append(f"drawtext=fontfile={R}:textfile={tf('brand', 'BEN&FIT')}:fontsize=34:fontcolor=white@0.85:x=(w-tw)/2:y=150:alpha='{al}'")
F.append(f"drawtext=fontfile={B}:textfile={tf('title', 'ARRACHÉ')}:fontsize=118:fontcolor=white:x=(w-tw)/2:y=205:alpha='{al}'")
F.append(f"drawtext=fontfile={R}:textfile={tf('sub', 'au ralenti')}:fontsize=44:fontcolor=white:box=1:boxcolor=0x0a206b:boxborderw=14:x=(w-tw)/2:y=368:alpha='{al}'")
for i, (a, b, head, cue) in enumerate(phases):
    ta, tb = t_of(a), (END if b > 900 else t_of(b))
    al = alpha(ta, tb)
    F.append(f"drawtext=fontfile={B}:textfile={tf(f'h{i}', head)}:fontsize=56:fontcolor=white:box=1:boxcolor=0x0a206b:boxborderw=26:x=(w-tw)/2:y=h-400:alpha='{al}'")
    F.append(f"drawtext=fontfile={R}:textfile={tf(f'c{i}', cue)}:fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=14:x=(w-tw)/2:y=h-290:alpha='{al}'")
    print(head, round(ta, 2), round(tb, 2))
open(f"{TXT}/filter.txt", "w").write(",".join(F))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{SEQ}/s_%04d.png",
                "-filter_script:v", f"{TXT}/filter.txt", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], check=True)
print("part2 starts", round(T2, 2), "total", round(END, 2))
