"""BEN&FIT reel v3 — DA « naturelle » + a selection of the v1 animations. Writes video_v3_nosound.mp4"""
import sys, math, json, random, subprocess
import numpy as np, cairo
sys.path.insert(0, "/home/claude/work")
import compose as C
from compose import text, rrect, eo, eio, clamp, wt, W, H, FPS, R

MARK = "Permanent Marker"; BLUE = C.BLUE; WHITE = C.WHITE; INK = (0.04, 0.125, 0.42)
rnd = random.Random(3); JIT = [rnd.uniform(-1, 1) for _ in range(400)]
EV = []

# keep only the v1 cards Bene liked (km bars) + mobilité ≠ souplesse
C.CARDS = [c for c in C.CARDS if c[0] in ("km", "mob")]
C.PUNCH.update({"D2b": 0.08, "E7": 0.06, "B6": 0.04})

def marker_path(ctx, pts, prog, width, color, alpha=1.0):
    n = max(2, int(len(pts) * clamp(prog)))
    if prog <= 0: return
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for p, (w, a) in enumerate([(width, 0.9), (width * 0.55, 0.5)]):
        ctx.move_to(pts[0][0] + JIT[p], pts[0][1] + JIT[p + 1])
        for i, (x, y) in enumerate(pts[1:n]):
            ctx.line_to(x + JIT[(i + p * 7) % 400] * 1.2, y + JIT[(i * 3 + p) % 400] * 1.2)
        ctx.set_line_width(w); ctx.set_source_rgba(*color, a * alpha); ctx.stroke()
    ctx.restore()

def underline_pts(x0, x1, y):
    return [(x0 + (x1 - x0) * u, y + 5 * math.sin(u * 3.2) - 6 * u) for u in np.linspace(0, 1, 40)]

def ellipse_pts(cx, cy, rx, ry):
    return [(cx + rx * (1 + 0.05 * math.sin(3 * a)) * math.cos(a), cy + ry * math.sin(a))
            for a in np.linspace(-2.6, -2.6 + 2 * math.pi * 1.08, 70)]

def win(T, t0, t1, fin=0.3, fout=0.3):
    if T < t0 or T > t1 + fout: return 0.0
    return eo((T - t0) / fin) * (1 - eio((T - t1) / fout))

GIFS = {"cardio": C.Gif("cardio.2.gif", crop=(0, 0, 498, 252)), "lift": C.G["lift"]}

def polaroid(ctx, g, t, cx, cy, pw, ph, a, tilt, caption):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(math.radians(tilt))
    bw, top, bot = 14, 14, 70
    w, h = pw + 2 * bw, ph + top + bot
    ctx.rectangle(-w / 2 + 6, -h / 2 + 12, w, h); ctx.set_source_rgba(0, 0, 0, 0.28 * a); ctx.fill()
    ctx.rectangle(-w / 2, -h / 2, w, h); ctx.set_source_rgba(0.97, 0.96, 0.93, a); ctx.fill()
    ctx.save(); ctx.rectangle(-pw / 2, -h / 2 + top, pw, ph); ctx.clip()
    sc = max(pw / g.w, ph / g.h); ctx.translate(0, -h / 2 + top + ph / 2); ctx.scale(sc, sc)
    ctx.set_source_surface(g.at(t), -g.w / 2, -g.h / 2); ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(a); ctx.restore()
    text(ctx, caption, 0, h / 2 - bot / 2 + 4, 38, face=MARK, color=(0.12, 0.14, 0.22), alpha=a)
    ctx.save(); ctx.translate(0, -h / 2 + 2); ctx.rotate(math.radians(-6))
    ctx.rectangle(-70, -20, 140, 40); ctx.set_source_rgba(0.93, 0.89, 0.78, 0.75 * a); ctx.fill(); ctx.restore()
    ctx.restore()

def put_polaroid(ctx, T, key, t0, t1, caption, cx=870, cy=640, pw=300, ph=205, tilt=5):
    a = win(T, t0, t1, 0.35, 0.3)
    if a <= 0: return
    k = eo((T - t0) / 0.35)
    polaroid(ctx, GIFS[key], T - t0, cx, cy + (1 - k) * 50 + 3 * math.sin(T * 2.1), pw, ph, a,
             tilt + 0.6 * math.sin(T * 1.3), caption)
    if (key, t0) not in seen: seen.add((key, t0)); EV.append((t0, "swoosh"))
seen = set()

def stacked(ctx, T, items, t_end, x=90, y0=470, gap=120):
    """items: (label, time, kind) kind: 'big' Anton / 'mark' marker / 'mid' Coda"""
    for i, (lab, t, kind) in enumerate(items):
        if t is None: continue
        a = win(T, t - 0.05, t_end, 0.3, 0.35)
        if a <= 0: continue
        dx = -(1 - eo((T - t + 0.05) / 0.3)) * 25
        y = y0 + i * gap
        if kind == "big": text(ctx, lab, x + dx, y, 104, face=C.NUM, color=INK, alpha=a, anchor="l")
        elif kind == "mid": text(ctx, lab, x + dx, y, 62, face=C.FONT, color=INK, alpha=a, anchor="l")
        else: text(ctx, lab, x + dx, y, 46, face=MARK, color=INK, alpha=a, anchor="l")

def chapter_tag(ctx, T):
    for ch, tc in C.CH_START.items():
        u = T - tc
        if -0.05 <= u <= 3.4:
            a = eo(u / 0.35) * (1 - eio((u - 3.0) / 0.4))
            ctx.save(); ctx.translate(-(1 - eo(u / 0.35)) * 30, 0)
            text(ctx, f"0{ch}", 80, 330, 64, face=C.NUM, color=INK, alpha=a, anchor="l")
            name = C.CH_NAME[ch][0]
            adv = text(ctx, name, 160, 330, 58, face=C.FONT, color=INK, alpha=a, anchor="l")
            ctx.restore()
            marker_path(ctx, underline_pts(78, 170 + adv, 382), (u - 0.3) / 0.45, 9, BLUE, a)
            if ("ch", ch) not in seen: seen.add(("ch", ch)); EV.append((tc, "tick"))

def stickers(ctx, T):
    # Let's go
    a0, a1 = R("letsgo"); a1 += 0.35
    k = C.sticker_window(a0 - 0.05, a1, T)
    if k > 0:
        C.draw_media(ctx, C.G["letsgo"], T - a0 + 0.6, 540, 1120, 760, 504, a=clamp(k * 1.5), tilt=-3)
    # OH YEAH on "pas pour être beau"
    tb = wt("B3", "beau") or R("B3")[0]
    k = C.sticker_window(tb - 0.1, R("B3")[1], T)
    if k > 0: C.draw_media(ctx, C.G["ohyeah"], T - tb, 840, 520, 300, 300, a=clamp(k * 1.5), tilt=6)
    # confused corgi on "deux choses différentes"
    td = wt("E2", "deux") or wt("E2", "différentes.")
    t_out = (wt("E2", "négliger,") or td + 2.2) - 0.1
    k = C.sticker_window(td - 0.05, t_out, T)
    if k > 0: C.draw_media(ctx, C.G["corgi"], T - td, 845, 500, 300, 270, a=clamp(k * 1.5), tilt=-5)
    for name, t in [("lg", a0 - 0.05), ("oy", tb - 0.1), ("cg", td - 0.05)]:
        if name not in seen: seen.add(name); EV.append((t, "swoosh"))

def overlays(ctx, T):
    C.draw_hook(ctx, T)
    stickers(ctx, T)
    chapter_tag(ctx, T)
    # BUILD: tissues & tendons, then fewer injuries
    stacked(ctx, T, [("TISSUS", wt("B5", "tissulaires"), "mid"), ("TENDONS", wt("B5", "tendineuses"), "mid"),
                     ("= moins de blessures", wt("B6", "blessures."), "mark")], R("B6")[1], y0=520, gap=95)
    tb6 = wt("B6", "blessures.")
    if tb6: marker_path(ctx, underline_pts(86, 300, 548), (T - wt("B5", "tissulaires") - 0.2) / 0.4, 7, BLUE,
                        win(T, wt("B5", "tissulaires"), R("B6")[1]))
    # RUN: cardio polaroid, zone 2 notes, km bars (v1 card)
    put_polaroid(ctx, T, "cardio", wt("C1", "cardio,"), R("C1")[1], "cardio !")
    tz = wt("C3a", "zone")
    stacked(ctx, T, [("ZONE 2", tz, "big"), ("récup", wt("C3b", "récupération,"), "mark"),
                     ("volume", wt("C3b", "volume"), "mark"), ("sans blessure", wt("C3b", "blessure."), "mark")],
            R("C3b")[1], y0=470, gap=95)
    if tz: marker_path(ctx, underline_pts(86, 380, 532), (T - tz - 0.25) / 0.45, 9, BLUE, win(T, tz, R("C3b")[1], 0.3, 0.35))
    # PERFORM: real lift in a polaroid
    put_polaroid(ctx, T, "lift", wt("D3b", "barre") or R("D3b")[0], R("D4")[1], "haltéro", pw=230, ph=300, cy=600)
    # MOVE: 20 min / 10 min
    t20, t10, tm = wt("E5", "20"), wt("E6a", "10"), wt("E6b", "mieux")
    stacked(ctx, T, [("20 MIN", t20, "big"), ("par jour", t20 and t20 + 0.3, "mark"),
                     ("10 MIN", t10, "big"), ("tous les 2 jours", t10 and t10 + 0.3, "mark")], R("E6b")[1], y0=440, gap=100)
    if t20: marker_path(ctx, ellipse_pts(200, 440, 150, 70), (T - t20 - 0.3) / 0.5, 8, BLUE, win(T, t20, R("E6b")[1], 0.3, 0.35))
    if tm and T > tm - 0.05:
        a = win(T, tm - 0.05, R("E6b")[1] + 0.3, 0.3, 0.35)
        text(ctx, "mieux que rien !", 90, 860, 50, face=MARK, color=BLUE, alpha=a, anchor="l")
    C.draw_cards(ctx, T)

def render_frame(T, fb, surf):
    ctx = cairo.Context(surf)
    src = cairo.ImageSurface.create_for_data(fb, cairo.FORMAT_ARGB32, W, H, W * 4)
    s = C.base_scale(T)
    ctx.save(); ctx.translate(540, 760); ctx.scale(s, s); ctx.translate(-540, -760)
    ctx.set_source_surface(src, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.paint(); ctx.restore()
    overlays(ctx, T)
    if T >= C.END_T - 0.01:
        C.draw_end(ctx, T)
    else:
        y = 1340 if any(a0 <= T <= a1 for _, a0, a1 in C.CARDS) else 1300
        C.draw_subs(ctx, T, y, 74)

def main(t_from=0.0, t_to=None, stills=None):
    t_to = C.DUR if t_to is None else t_to
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t_from:.3f}", "-i", "/home/claude/work/base_v2.mp4",
                           "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    wr = None
    if stills is None:
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", "30",
                               "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-pix_fmt", "yuv420p",
                               "/home/claude/work/video_v3_nosound.mp4"], stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    n = int(round((t_to - t_from) * FPS)); last = None
    for i in range(n):
        T = t_from + i / FPS
        buf = rd.stdout.read(W * H * 4) if T < C.BASE_DUR - 0.5 / FPS else b""
        if len(buf) == W * H * 4: last = bytearray(buf)
        render_frame(T, last, surf); surf.flush()
        if wr: wr.stdin.write(bytes(surf.get_data()))
        elif i == 0:
            import PIL.Image as I
            I.frombuffer("RGBA", (W, H), bytes(surf.get_data()), "raw", "BGRA", 0, 1).convert("RGB").save(f"/home/claude/work/frames3/t_{T:06.2f}.jpg", quality=85)
        if i % 300 == 0 and wr: print(f"{T:.1f}s", flush=True)
    rd.kill()
    if wr: wr.stdin.close(); wr.wait()
    if stills is None:
        ev = EV + [(t, k) for t, k in C.EVENTS if k in ("tick", "end")] + [(0.0, "hit")]
        json.dump(sorted(ev), open("/home/claude/work/events_v3.json", "w"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        import os; os.makedirs("/home/claude/work/frames3", exist_ok=True)
        for t in map(float, sys.argv[2:]): main(t, t + 0.04, stills=True)
    else:
        main()
