"""15 s test of the 'natural' design system v2 on the RUN chapter."""
import sys, math, json, subprocess, random
import numpy as np, cairo
sys.path.insert(0, "/home/claude/work")
import compose as C
from compose import text, rrect, eo, eio, clamp, wt, W, H, FPS
from data import TL

SPEED = 1.08
PIECES = [(1.70, 8.93, 27.61), (31.05, 32.43, 45.6), (32.63, 36.89, 46.88), (37.17, 37.64, 50.82)]
SRC = "/home/claude/rushs/VID_20261113_153641.mp4"
GRADE = ("eq=contrast=1.05:saturation=1.05:brightness=0.015:gamma=1.02,"
         "colorbalance=rm=0.015:bm=-0.015,unsharp=5:5:0.3,noise=alls=5:allf=t")

def build_base():
    args = ["ffmpeg", "-v", "error", "-y"]; fc = []
    for k, (a, b, _) in enumerate(PIECES):
        args += ["-ss", f"{a}", "-t", f"{b - a:.3f}", "-i", SRC]
        fc.append(f"[{k}:v]fps=60,setpts=PTS-STARTPTS[v{k}]")
        fc.append(f"[{k}:a]aresample=48000,asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.03:.3f}:d=0.03[a{k}]")
    n = len(PIECES)
    fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]setpts=PTS/{SPEED},fps=30,{GRADE},format=yuv420p[vo]")
    fc.append(f"[ac]atempo={SPEED},highpass=f=75,afftdn=nf=-28:nr=10,equalizer=f=3200:t=q:w=1.2:g=2,"
              "acompressor=threshold=-21dB:ratio=3:attack=8:release=120:makeup=3,loudnorm=I=-14:TP=-1[ao]")
    args += ["-filter_complex", ";".join(fc), "-map", "[vo]", "-map", "[ao]", "-c:v", "libx264", "-crf", "12",
             "-preset", "veryfast", "-c:a", "aac", "-b:a", "256k", "/home/claude/work/test_base.mp4"]
    subprocess.run(args, check=True)

LOCAL = []
t = 0
for a, b, T0 in PIECES:
    d = (b - a) / SPEED; LOCAL.append((t, t + d, T0)); t += d
DUR = t
def T_of(t):
    for l0, l1, T0 in LOCAL:
        if t < l1: return T0 + (t - l0)
    return LOCAL[-1][2] + (t - LOCAL[-1][0])
def t_of(T):
    for l0, l1, T0 in LOCAL:
        if T0 <= T < T0 + (l1 - l0): return l0 + (T - T0)
    return None

MARK = "Permanent Marker"; BLUE = C.BLUE; WHITE = C.WHITE; INK = (0.04, 0.125, 0.42)
rnd = random.Random(3)
JIT = [rnd.uniform(-1, 1) for _ in range(400)]

def marker_path(ctx, pts, prog, width, color, alpha=1.0):
    """hand-drawn stroke: polyline revealed progressively, with tapered double pass"""
    n = max(2, int(len(pts) * clamp(prog)))
    if n < 2: return
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for pass_, (w, a) in enumerate([(width, 0.9), (width * 0.55, 0.5)]):
        ctx.move_to(pts[0][0] + JIT[pass_], pts[0][1] + JIT[pass_ + 1])
        for i, (x, y) in enumerate(pts[1:n]):
            ctx.line_to(x + JIT[(i + pass_ * 7) % 400] * 1.2, y + JIT[(i * 3 + pass_) % 400] * 1.2)
        ctx.set_line_width(w); ctx.set_source_rgba(*color, a * alpha); ctx.stroke()
    ctx.restore()

def underline_pts(x0, x1, y):
    return [(x0 + (x1 - x0) * u, y + 5 * math.sin(u * 3.2) - 6 * u) for u in np.linspace(0, 1, 40)]

def ellipse_pts(cx, cy, rx, ry):
    return [(cx + rx * (1 + 0.05 * math.sin(3 * a)) * math.cos(a), cy + ry * math.sin(a))
            for a in np.linspace(-2.6, -2.6 + 2 * math.pi * 1.08, 70)]

GIF = C.Gif("cardio.2.gif", crop=(0, 0, 498, 252))

def polaroid(ctx, t, T, cx, cy, pw, ph, a, tilt, caption):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(math.radians(tilt))
    bw, top, bot = 14, 14, 70
    w, h = pw + 2 * bw, ph + top + bot
    ctx.rectangle(-w / 2 + 6, -h / 2 + 12, w, h); ctx.set_source_rgba(0, 0, 0, 0.28 * a); ctx.fill()
    ctx.rectangle(-w / 2, -h / 2, w, h); ctx.set_source_rgba(0.97, 0.96, 0.93, a); ctx.fill()
    ctx.save(); ctx.rectangle(-pw / 2, -h / 2 + top, pw, ph); ctx.clip()
    sc = max(pw / GIF.w, ph / GIF.h); ctx.translate(0, -h / 2 + top + ph / 2); ctx.scale(sc, sc)
    ctx.set_source_surface(GIF.at(t), -GIF.w / 2, -GIF.h / 2); ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(a); ctx.restore()
    text(ctx, caption, 0, h / 2 - bot / 2 + 4, 38, face=MARK, color=(0.12, 0.14, 0.22), alpha=a)
    # tape
    ctx.save(); ctx.translate(0, -h / 2 + 2); ctx.rotate(math.radians(-6))
    ctx.rectangle(-70, -20, 140, 40); ctx.set_source_rgba(0.93, 0.89, 0.78, 0.75 * a); ctx.fill(); ctx.restore()
    ctx.restore()

def overlays(ctx, t):
    T = T_of(t)
    # chapter tag, top-left, written in
    a = eo(t / 0.35) * (1 - eio((t - 3.0) / 0.4))
    if a > 0:
        ctx.save(); ctx.translate(-(1 - eo(t / 0.35)) * 30, 0)
        text(ctx, "02", 80, 330, 64, face=C.NUM, color=INK, alpha=a, anchor="l")
        text(ctx, "RUN", 160, 330, 58, face=C.FONT, color=INK, alpha=a, anchor="l")
        ctx.restore()
        marker_path(ctx, underline_pts(78, 300, 382), (t - 0.3) / 0.45, 9, BLUE, a)
    # polaroid on "cardio"
    tc = t_of(wt("C1", "cardio,")) or 2.5
    t_end = LOCAL[0][1]
    if tc - 0.05 <= t <= t_end + 0.3:
        k = eo((t - tc + 0.05) / 0.35); out = 1 - eio((t - t_end) / 0.3)
        tilt = -4 + 0.6 * math.sin(t * 1.3)
        y = 640 + (1 - k) * 50 + 3 * math.sin(t * 2.1)
        polaroid(ctx, t - tc, T, 870, y, 300, 205, k * out, tilt + 9, "cardio !")
    # stacked numbers on C4
    vals = [("5 km", wt("C4", "5")), ("7", wt("C4", "7,")), ("8", wt("C4", "8,")), ("10", wt("C4", "10"))]
    t2 = wt("C4", "2")
    endT = 50.82 + 0.47 / SPEED + 0.6
    for i, (v, Tw) in enumerate(vals):
        if Tw is None: continue
        tw_ = t_of(Tw)
        if tw_ is None or t < tw_ - 0.05: continue
        k = eo((t - tw_ + 0.05) / 0.3) * (1 - eio((T - endT) / 0.3))
        y = 470 + i * 135
        big = v == "10"
        col = INK
        text(ctx, v, 90 - (1 - k) * 25, y, 128 if big else 104, face=C.NUM, color=col, alpha=k * (1 if big or i == 3 else 0.85), anchor="l")
        if i < 3 and t > tw_ + 0.3:
            pass
        if big:
            marker_path(ctx, ellipse_pts(150, y, 110, 74), (t - tw_ - 0.25) / 0.5, 8, BLUE, k)
            if t2 is not None and t_of(t2) is not None and t > t_of(t2):
                kk = eo((t - t_of(t2)) / 0.3) * (1 - eio((T - endT) / 0.3))
                text(ctx, "(2 × 5 km)", 280, y + 8, 40, face=MARK, color=INK, alpha=kk, anchor="l")

def main():
    build_base()
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "/home/claude/work/test_base.mp4", "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                           "-i", "/home/claude/work/test_base.mp4", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16",
                           "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "/home/claude/work/test_v2_naturel.mp4"],
                          stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    n = int(DUR * FPS); last = None
    for i in range(n):
        t = i / FPS; T = T_of(t)
        buf = rd.stdout.read(W * H * 4)
        if len(buf) == W * H * 4: last = bytearray(buf)
        ctx = cairo.Context(surf)
        src = cairo.ImageSurface.create_for_data(last, cairo.FORMAT_ARGB32, W, H, W * 4)
        # gentle punch-in on the second part, slow push overall
        s = 1.0 + 0.025 * (t / DUR) + (0.07 if t >= LOCAL[1][0] and t < LOCAL[2][0] else 0)
        ctx.save(); ctx.translate(540, 760); ctx.scale(s, s); ctx.translate(-540, -760)
        ctx.set_source_surface(src, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.paint(); ctx.restore()
        overlays(ctx, t)
        C.draw_subs(ctx, T, 1300, 74)
        surf.flush(); wr.stdin.write(bytes(surf.get_data()))
    rd.kill(); wr.stdin.close(); wr.wait()
    print("ok", DUR)

if __name__ == "__main__":
    main()
