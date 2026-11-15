"""BEN&FIT reel compositor: zooms, split-screen, motion design, subtitles. Writes video_nosound.mp4"""
import sys, math, json, re, subprocess
import cairo, numpy as np
sys.path.insert(0, "/home/claude/work")
from data import TL, TOTAL, WORDS, SUBS, tag_range, cut_at, norm

W, H, FPS = 1080, 1920, 30
BASE_DUR = TOTAL
HOLD = 1.3                      # freeze the last frame so the end card can be read
DUR = BASE_DUR + HOLD
WHITE = (1, 1, 1); BLUE = (0.16, 0.42, 1.0); BLUE2 = (0.42, 0.66, 1.0); NAVY = (0.03, 0.07, 0.19)
NAVY2 = (0.05, 0.12, 0.30); STROKE = (0.08, 0.30, 0.92)
FONT = "Coda ExtraBold"; NUM = "Anton"

clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def eback(x):
    x = clamp(x); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def wt(tag_prefix, word, nth=0):
    hits = [w for w in WORDS if w["tag"].startswith(tag_prefix) and norm(w["w"]) == norm(word)]
    return hits[nth]["t"] if len(hits) > nth else None

# ---------------------------------------------------------------- timing
R = lambda *t: tag_range(*t)
CH_START = {1: R("B1")[0], 2: R("C1")[0], 3: R("D1")[0], 4: R("E1a")[0]}
CH_END = {1: R("B6")[1], 2: R("C4")[1], 3: R("D5")[1], 4: R("E8b")[1]}
CH_NAME = {1: ("BUILD", "FORCE & MASSE MUSCULAIRE"), 2: ("RUN", "MOTEUR CARDIOVASCULAIRE"),
           3: ("PERFORM", "INTENSITÉ & EXPLOSIVITÉ"), 4: ("MOVE", "MOBILITÉ & CONTRÔLE")}
END_T = R("endcard")[0] - 0.15
SPLITS = [("build", R("B4")[0], R("B6")[1]), ("zone2", R("C3a")[0], R("C3b")[1]),
          ("perform", R("D2a")[0], R("D4")[1]), ("move", R("E5")[0], R("E8b")[1])]
CARDS = [("km", R("C4")[0] + 0.4, R("C4")[1]), ("week", R("D5")[0] + 0.4, R("D5")[1]),
         ("mob", R("E2")[0] + 0.1, R("E2")[1])]
EVENTS = []   # for sound design: (time, kind)

def split_amount(T):
    for name, a, b in SPLITS:
        if a - 0.01 <= T <= b + 0.35:
            return name, eio((T - a) / 0.32) * (1 - eio((T - b) / 0.32)), a, b
    return None, 0.0, 0, 0

# ---------------------------------------------------------------- text helpers
def font(ctx, size, face=FONT):
    ctx.select_font_face(face, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL); ctx.set_font_size(size)

_cap = {}
def cap_h(ctx, size, face):
    k = (size, face)
    if k not in _cap:
        font(ctx, size, face); _cap[k] = ctx.text_extents("H")[3]
    return _cap[k]

def tw(ctx, s, size, face=FONT):
    font(ctx, size, face); e = ctx.text_extents(s); return e[4], e[0], e[2]

def text(ctx, s, x, y, size, face=FONT, color=WHITE, alpha=1.0, anchor="c", stroke=None, sw=0, shadow=0.0, spacing=0):
    font(ctx, size, face)
    adv, xb, w = tw(ctx, s, size, face)
    if spacing: adv += spacing * (len(s) - 1)
    ch = cap_h(ctx, size, face)
    x0 = x - adv / 2 if anchor == "c" else (x if anchor == "l" else x - adv)
    yb = y + ch / 2
    def path():
        if spacing:
            xx = x0
            for c in s:
                ctx.move_to(xx, yb); ctx.text_path(c); xx += tw(ctx, c, size, face)[0] + spacing
        else:
            ctx.move_to(x0, yb); ctx.text_path(s)
    if shadow:
        ctx.save(); ctx.translate(0, 5); path(); ctx.set_source_rgba(0, 0, 0, shadow * alpha); ctx.fill(); ctx.restore()
    if stroke:
        path(); ctx.set_source_rgba(*stroke, alpha); ctx.set_line_width(sw); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke()
    path(); ctx.set_source_rgba(*color, alpha); ctx.fill()
    return adv

def rrect(ctx, x, y, w, h, r):
    r = min(r, h / 2, w / 2)
    ctx.new_sub_path(); ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); ctx.close_path()

def chip(ctx, s, x, y, size, fill=BLUE, color=WHITE, alpha=1.0, padx=18, pady=12, anchor="l", wipe=1.0):
    adv = tw(ctx, s, size)[0]; ch = cap_h(ctx, size, FONT)
    w, h = adv + 2 * padx, ch + 2 * pady
    x0 = x if anchor == "l" else (x - w / 2 if anchor == "c" else x - w)
    if wipe < 1:
        ctx.save(); ctx.rectangle(x0, y - h / 2 - 2, w * wipe, h + 4); ctx.clip()
    rrect(ctx, x0, y - h / 2, w, h, 10); ctx.set_source_rgba(*fill, alpha); ctx.fill()
    text(ctx, s, x0 + w / 2, y, size, color=color, alpha=alpha)
    if wipe < 1: ctx.restore()
    return w

def pop(ctx, cx, cy, a, s0=0.85):
    """apply a scale-pop transform around (cx,cy); returns alpha"""
    s = s0 + (1 - s0) * eback(a)
    ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-cx, -cy)
    return clamp(a * 1.6)

# ---------------------------------------------------------------- subtitles
def draw_subs(ctx, T, y, size):
    for s in SUBS:
        if s["t0"] <= T < s["t1"]:
            break
    else:
        return
    if s["words"][0]["tag"] in ("hook", "letsgo") or T >= END_T: return
    a = eo((T - s["t0"]) / 0.13)
    # layout: words into max 2 lines of width <= 900
    space = tw(ctx, " ", size)[0] * 1.1
    lines, cur, cw = [], [], 0
    for w in s["words"]:
        ww = tw(ctx, w["w"], size)[0]
        if cur and cw + space + ww > 880:
            lines.append((cur, cw)); cur, cw = [], 0
        cur.append((w, ww)); cw += (space if len(cur) > 1 else 0) + ww
    lines.append((cur, cw))
    lh = size * 1.32
    y0 = y - (len(lines) - 1) * lh / 2 + (1 - a) * 14
    ctx.save()
    sc = 0.94 + 0.06 * a
    ctx.translate(W / 2, y); ctx.scale(sc, sc); ctx.translate(-W / 2, -y)
    for li, (ws, lw) in enumerate(lines):
        x = W / 2 - lw / 2; yy = y0 + li * lh
        for w, ww in ws:
            if w["key"]:
                k = eo((T - w["t"] + 0.04) / 0.16)
                pad = size * 0.2
                if k > 0:
                    rrect(ctx, x - pad, yy - size * 0.52, (ww + 2 * pad) * k, size * 1.04, 12)
                    ctx.set_source_rgba(*BLUE, a); ctx.fill()
                text(ctx, w["w"], x, yy, size, anchor="l", stroke=STROKE if k < 0.5 else None, sw=9, alpha=a, shadow=0.0 if k > 0.5 else 0.35)
            else:
                text(ctx, w["w"], x, yy, size, anchor="l", stroke=STROKE, sw=9, alpha=a, shadow=0.35)
            x += ww + space
    ctx.restore()

# ---------------------------------------------------------------- hook (kinetic typography)
HOOK_W = [w for w in WORDS if w["tag"] == "hook"]
def draw_hook(ctx, T):
    if T > HOOK_W[-1]["te"] + 0.25: return
    t = {norm(w["w"]): w["t"] for w in HOOK_W[:5]}
    t2 = {norm(w["w"]): w["t"] for w in HOOK_W[5:]}
    si = HOOK_W[5]["t"]; end = HOOK_W[-1]["te"] + 0.25
    # legibility gradient
    g = cairo.LinearGradient(0, 900, 0, 1600); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, *NAVY, 0.55)
    ctx.save(); ctx.rectangle(0, 900, W, 700); ctx.clip(); ctx.set_source(g); ctx.paint_with_alpha(1 - eio((T - end + 0.25) / 0.25)); ctx.restore()
    if T < si + 0.12:
        out = 1 - eio((T - si) / 0.12)
        # "4"
        a = (T - HOOK_W[0]["t"] + 0.05) / 0.22
        ctx.save(); al = pop(ctx, 540, 1050, a, 0.5)
        text(ctx, "4", 540, 1050, 330, face=NUM, stroke=STROKE, sw=14, alpha=al * out, shadow=0.4); ctx.restore()
        a = (T - t["choses"]) / 0.2
        ctx.save(); al = pop(ctx, 540, 1275, a, 0.7)
        if al > 0: chip(ctx, "CHOSES", 540, 1275, 110, anchor="c", alpha=al * out, padx=26, pady=18)
        ctx.restore()
        x = 540; line = ["QUE", "JE", "FERAIS"]; sz = 84
        widths = [tw(ctx, s, sz)[0] for s in line]; sp = 26; tot = sum(widths) + sp * 2; x = 540 - tot / 2
        for s, wd, key in zip(line, widths, ["que", "je", "ferais"]):
            a = (T - t[key]) / 0.16
            if a > 0:
                ctx.save(); al = pop(ctx, x + wd / 2, 1415, a, 0.7)
                text(ctx, s, x, 1415, sz, anchor="l", stroke=STROKE, sw=9, alpha=al * out, shadow=0.35); ctx.restore()
            x += wd + sp
    else:
        out = 1 - eio((T - end + 0.15) / 0.15)
        line = ["SI", "JE", "DEVAIS"]; sz = 92
        widths = [tw(ctx, s, sz)[0] for s in line]; sp = 28; x = 540 - (sum(widths) + 2 * sp) / 2
        for s, wd, key in zip(line, widths, ["si", "je", "devais"]):
            a = (T - t2[key]) / 0.16
            if a > 0:
                ctx.save(); al = pop(ctx, x + wd / 2, 1080, a, 0.7)
                text(ctx, s, x, 1080, sz, anchor="l", stroke=STROKE, sw=10, alpha=al * out, shadow=0.35); ctx.restore()
            x += wd + sp
        a = (T - t2["tout"]) / 0.2
        if a > 0:
            ctx.save(); al = pop(ctx, 540, 1225, a, 0.6)
            text(ctx, "TOUT", 540, 1225, 170, stroke=STROKE, sw=12, alpha=al * out, shadow=0.4); ctx.restore()
        a = (T - t2["recommencer"]) / 0.22
        if a > 0:
            ctx.save(); al = pop(ctx, 540, 1385, a, 0.7)
            chip(ctx, "RECOMMENCER", 540, 1385, 104, anchor="c", alpha=al * out, padx=26, pady=18, wipe=eo(a * 1.2)); ctx.restore()

# ---------------------------------------------------------------- chapter wipe, progress, tag
def draw_wipe(ctx, T):
    for ch, tc in CH_START.items():
        u = T - (tc - 0.14)
        if 0 <= u <= 1.05:
            if u < 0.24: x = -W - 220 + (W + 220) * eo(u / 0.24)
            elif u < 0.78: x = 0
            else: x = (W + 220) * eio((u - 0.78) / 0.27)
            px = x * 0.25 if 0.24 <= u < 0.78 else x
            ctx.save()
            # panel with slanted edges
            ctx.move_to(x - 220, 0); ctx.line_to(x + W + 120, 0); ctx.line_to(x + W - 100, H); ctx.line_to(x - 440, H); ctx.close_path()
            g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgb(0, *NAVY2); g.add_color_stop_rgb(1, *NAVY)
            ctx.set_source(g); ctx.fill()
            # leading blue stripe
            ctx.move_to(x + W + 120, 0); ctx.line_to(x + W + 160, 0); ctx.line_to(x + W - 60, H); ctx.line_to(x + W - 100, H); ctx.close_path()
            ctx.set_source_rgb(*BLUE); ctx.fill()
            ctx.move_to(x + W + 190, 0); ctx.line_to(x + W + 200, 0); ctx.line_to(x + W - 20, H); ctx.line_to(x + W - 30, H); ctx.close_path()
            ctx.set_source_rgba(*BLUE2, 0.7); ctx.fill()
            # diagonal hairlines
            ctx.set_line_width(2)
            for i in range(-6, 14):
                xx = x + i * 120
                ctx.move_to(xx, 0); ctx.line_to(xx - 220, H)
            ctx.set_source_rgba(1, 1, 1, 0.04); ctx.stroke()
            name, desc = CH_NAME[ch]
            ctx.translate(px * 0.6 if u >= 0.78 else x * 0.0 + (x if u < 0.24 else 0), 0)
            text(ctx, f"0{ch}", 540, 760, 210, face=NUM, color=BLUE)
            text(ctx, "/ 04", 540 + 150, 720, 44, color=BLUE2, anchor="l")
            text(ctx, name, 540, 960, 190, stroke=None)
            ctx.rectangle(540 - 60, 1090, 120, 8); ctx.set_source_rgb(*BLUE); ctx.fill()
            text(ctx, desc, 540, 1160, 50, color=BLUE2, spacing=3)
            ctx.restore()
            return True
    return False

def draw_progress(ctx, T):
    t0, t1 = CH_START[1], END_T
    if not (t0 + 0.6 <= T < t1): return
    a = eo((T - t0 - 0.6) / 0.3) * (1 - eo((T - t1 + 0.3) / 0.3))
    x0, x1, y, gap = 80, 1000, 236, 12
    segw = (x1 - x0 - 3 * gap) / 4
    cur = max(c for c, s in CH_START.items() if s <= T)
    for i in range(1, 5):
        xs = x0 + (i - 1) * (segw + gap)
        rrect(ctx, xs, y, segw, 7, 3.5); ctx.set_source_rgba(1, 1, 1, 0.28 * a); ctx.fill()
        if i < cur: f = 1
        elif i == cur: f = clamp((T - CH_START[i]) / (CH_END[i] - CH_START[i]))
        else: f = 0
        if f > 0:
            rrect(ctx, xs, y, segw * f, 7, 3.5); ctx.set_source_rgba(1, 1, 1, 0.95 * a); ctx.fill()
    # chapter tag
    tc = CH_START[cur]
    b = eo((T - tc - 0.75) / 0.25) * a
    if b > 0:
        name = CH_NAME[cur][0]
        w = chip(ctx, f"0{cur}", 80, 290, 34, alpha=b, padx=12, pady=9)
        text(ctx, name, 80 + w + 14, 290, 36, anchor="l", alpha=b, stroke=STROKE, sw=6, shadow=0.3, spacing=2)

# ---------------------------------------------------------------- split panel contents
def panel_bg(ctx, top):
    g = cairo.LinearGradient(0, top, 0, H); g.add_color_stop_rgb(0, *NAVY2); g.add_color_stop_rgb(0.6, *NAVY); g.add_color_stop_rgb(1, 0.01, 0.03, 0.09)
    ctx.rectangle(0, top, W, H - top); ctx.set_source(g); ctx.fill()
    ctx.set_line_width(1.5)
    for i in range(1, 18): ctx.move_to(i * 60, top); ctx.line_to(i * 60, H)
    for j in range(1, 17): ctx.move_to(0, top + j * 60); ctx.line_to(W, top + j * 60)
    ctx.set_source_rgba(1, 1, 1, 0.035); ctx.stroke()
    ctx.rectangle(0, top - 4, W, 8); ctx.set_source_rgb(*BLUE); ctx.fill()
    ctx.rectangle(0, top + 6, W, 2); ctx.set_source_rgba(*BLUE2, 0.5); ctx.fill()

def header(ctx, pillar, label, a):
    w = chip(ctx, pillar, 80, 1015, 32, alpha=a, padx=12, pady=9)
    text(ctx, label, 80 + w + 16, 1015, 32, anchor="l", color=BLUE2, alpha=a, spacing=2)

def bar_row(ctx, label, y, f, a, x0=80, x1=900, val=None):
    text(ctx, label, x0, y - 34, 34, anchor="l", alpha=a, spacing=2)
    rrect(ctx, x0, y, x1 - x0, 26, 13); ctx.set_source_rgba(1, 1, 1, 0.12 * a); ctx.fill()
    if f > 0:
        rrect(ctx, x0, y, (x1 - x0) * f, 26, 13); ctx.set_source_rgba(*BLUE, a); ctx.fill()
        rrect(ctx, x0, y, (x1 - x0) * f, 8, 4); ctx.set_source_rgba(1, 1, 1, 0.25 * a); ctx.fill()
    if val: text(ctx, val, x1, y - 34, 34, anchor="r", color=BLUE2, alpha=a)

def plate_pair(ctx, cx, cy, off, hgt, color, slide):
    for sgn in (-1, 1):
        x = cx + sgn * (off + (1 - slide) * 400)
        rrect(ctx, x - 17, cy - hgt / 2, 34, hgt, 8); ctx.set_source_rgba(*color, clamp(slide * 2)); ctx.fill()

def c_build(ctx, T, a, s0):
    header(ctx, "BUILD", "FORCE & STRUCTURE", a)
    tB = wt("B5", "mais")
    pa = 1 - eio((T - tB + 0.1) / 0.25)
    pb = eio((T - tB + 0.1) / 0.25)
    if pa > 0:
        cy = 1250; aa = a * pa
        tm = wt("B4", "masse")
        text(ctx, "MASSE MUSCULAIRE", 540, 1105, 62, alpha=aa * eo((T - tm + 0.1) / 0.25), stroke=None)
        ctx.set_line_width(14); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(130, cy); ctx.line_to(950, cy); ctx.set_source_rgba(0.85, 0.88, 0.95, aa); ctx.stroke()
        for sgn in (-1, 1):
            rrect(ctx, 540 + sgn * 230 - 8, cy - 26, 16, 52, 4); ctx.set_source_rgba(0.85, 0.88, 0.95, aa); ctx.fill()
        specs = [(260, 230, BLUE), (300, 200, WHITE), (338, 170, BLUE), (372, 140, WHITE)]
        for i, (off, hh, col) in enumerate(specs):
            sl = eback((T - s0 - 0.3 - i * 0.38) / 0.3)
            if sl > 0:
                ctx.save(); ctx.push_group(); plate_pair(ctx, 540, cy, off, hh, col, sl); ctx.pop_group_to_source(); ctx.paint_with_alpha(aa); ctx.restore()
                if 0 < T - s0 - 0.3 - i * 0.38 < 0.35 and (i, "plate") not in _ev: _ev.add((i, "plate")); EVENTS.append((s0 + 0.3 + i * 0.38 + 0.2, "clank"))
    if pb > 0:
        aa = a * pb
        text(ctx, "ADAPTATION", 80, 1090, 44, anchor="l", color=WHITE, alpha=aa, spacing=4)
        t1, t2, t3 = wt("B5", "tissulaires"), wt("B5", "tendineuses"), wt("B6", "blessures.")
        bar_row(ctx, "TISSUS", 1190, 0.82 * eo((T - t1) / 0.7), aa * eo((T - t1 + 0.2) / 0.2))
        bar_row(ctx, "TENDONS", 1300, 0.78 * eo((T - t2) / 0.7), aa * eo((T - t2 + 0.2) / 0.2))
        tev = wt("B6", "éviter") or t3 - 0.6
        f = 0.75 - 0.55 * eo((T - t3 + 0.2) / 0.8)
        bar_row(ctx, "RISQUE DE BLESSURE", 1410, f, aa * eo((T - tev) / 0.2), val=None)

def c_zone2(ctx, T, a, s0):
    header(ctx, "RUN", "ENDURANCE · ZONE 2", a)
    x0, x1, yt, bh = 150, 600, 1070, 74
    tz = wt("C3a", "zone")
    for i in range(5):
        z = 5 - i; y = yt + i * bh
        hl = z == 2
        k = eo((T - tz) / 0.3) if hl else 0
        ctx.rectangle(x0, y + 3, x1 - x0, bh - 6)
        ctx.set_source_rgba(*(BLUE if hl else WHITE), (0.08 + 0.5 * k if hl else 0.06) * a); ctx.fill()
        text(ctx, f"Z{z}", x0 - 22, y + bh / 2, 32, anchor="r", color=BLUE2 if hl and k > 0.5 else WHITE, alpha=a * (0.9 if hl else 0.55))
    # heart-rate line drawn progressively, settling in zone 2
    prog = eo((T - s0 - 0.2) / 2.2)
    zc = yt + 3 * bh + bh / 2
    pts = []
    n = 90
    for j in range(n + 1):
        u = j / n
        if u > prog: break
        x = x0 + u * (x1 - x0)
        base = (yt + 5 * bh) + (zc - (yt + 5 * bh)) * eo(u / 0.25)
        y = base + 14 * math.sin(u * 23 + T * 2.0) * min(1, u * 4) + 6 * math.sin(u * 61 + T * 3.1)
        pts.append((x, y))
    if len(pts) > 1:
        ctx.set_line_width(7); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(*pts[0])
        for p in pts[1:]: ctx.line_to(*p)
        ctx.set_source_rgba(1, 1, 1, a); ctx.stroke()
        ctx.arc(pts[-1][0], pts[-1][1], 12, 0, 2 * math.pi); ctx.set_source_rgba(*BLUE2, a); ctx.fill()
    if T > tz:
        chip(ctx, "ZONE 2", x0 + 14, zc, 30, alpha=a * eo((T - tz) / 0.25), padx=10, pady=7)
    items = [("RÉCUPÉRATION", wt("C3b", "récupération,")), ("VOLUME", wt("C3b", "volume")),
             ("SANS BLESSURE", wt("C3b", "blessure."))]
    for i, (lab, t) in enumerate(items):
        if t is None or T < t - 0.05: continue
        k = (T - t + 0.05) / 0.25
        y = 1130 + i * 115
        ctx.save(); al = pop(ctx, 650, y, k, 0.6)
        ctx.arc(668, y, 24, 0, 2 * math.pi); ctx.set_source_rgba(*BLUE, a * al); ctx.fill()
        ctx.set_line_width(6); ctx.move_to(656, y + 1); ctx.line_to(665, y + 10); ctx.line_to(681, y - 9)
        ctx.set_source_rgba(1, 1, 1, a * al); ctx.stroke()
        text(ctx, lab, 704, y, 30, anchor="l", alpha=a * al)
        ctx.restore()
        if ("chk", i) not in _ev: _ev.add(("chk", i)); EVENTS.append((t, "tick"))

def c_perform(ctx, T, a, s0):
    header(ctx, "PERFORM", "HAUTE INTENSITÉ", a)
    tsw = wt("D3a", "donc") or R("D3a")[0]
    pa = 1 - eio((T - tsw + 0.05) / 0.25); pb = eio((T - tsw + 0.05) / 0.25)
    if pa > 0:
        aa = a * pa; cx, cy, r = 540, 1400, 300
        segs = 24
        th, tm = wt("D2b", "haute"), wt("D2b", "maximaux.")
        lvl = 0.25 + 0.72 * eio((T - th) / max(0.4, tm - th + 0.2))
        for i in range(segs):
            a0 = math.pi + i * math.pi / segs + 0.01; a1 = a0 + math.pi / segs - 0.03
            on = (i + 0.5) / segs <= lvl
            ctx.arc(cx, cy, r, a0, a1); ctx.arc_negative(cx, cy, r - 56, a1, a0); ctx.close_path()
            col = BLUE if on else WHITE
            ctx.set_source_rgba(*col, aa * (1.0 if on else 0.12)); ctx.fill()
        ang = math.pi + lvl * math.pi
        ctx.set_line_width(10); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(cx, cy); ctx.line_to(cx + (r - 80) * math.cos(ang), cy + (r - 80) * math.sin(ang))
        ctx.set_source_rgba(1, 1, 1, aa); ctx.stroke()
        ctx.arc(cx, cy, 22, 0, 2 * math.pi); ctx.fill()
        lab = "MAX" if lvl > 0.9 else "INTENSITÉ"
        text(ctx, lab, cx, cy - 120, 74 if lab == "MAX" else 50, color=BLUE2 if lab == "MAX" else WHITE, alpha=aa)
        if tm and ("max",) not in _ev: _ev.add(("max",)); EVENTS.append((tm, "hit"))
    if pb > 0:
        aa = a * pb
        tb, te_, tha = wt("D3b", "barre"), wt("D4", "explosif"), wt("D4", "l'haltérophilie.")
        # lifting path
        px, ylow, yhigh = 720, 1440, 1085
        ctx.set_line_width(4); ctx.set_dash([10, 14])
        ctx.move_to(px, ylow); ctx.line_to(px, yhigh); ctx.set_source_rgba(1, 1, 1, 0.25 * aa * (0 if (tha and T > tha) else 1)); ctx.stroke(); ctx.set_dash([])
        per = 1.5; u = ((T - tsw) % per) / per
        if u < 0.22: y = ylow + (yhigh - ylow) * eo(u / 0.22); v = 1 - u / 0.22
        elif u < 0.6: y = yhigh; v = 0
        else: y = yhigh + (ylow - yhigh) * eio((u - 0.6) / 0.4); v = 0
        if u < 0.3:
            for k in range(1, 6):   # speed streaks
                ctx.rectangle(px - 95 + k * 30, y + 40 + k * 18, 8, 120 * v + 20)
                ctx.set_source_rgba(*BLUE2, 0.35 * aa * (1 - k / 7) * (1 - (eo((T - tha + 0.1) / 0.3) if tha else 0))); ctx.fill()
        kk = eo((T - tha + 0.1) / 0.3) if tha else 0
        if kk < 1:
            ctx.save(); ctx.push_group()
            ctx.arc(px, y, 115, 0, 2 * math.pi); ctx.set_source_rgba(*BLUE, aa); ctx.fill()
            ctx.arc(px, y, 115, 0, 2 * math.pi); ctx.set_line_width(8); ctx.set_source_rgba(1, 1, 1, 0.9 * aa); ctx.stroke()
            ctx.arc(px, y, 70, 0, 2 * math.pi); ctx.set_line_width(4); ctx.set_source_rgba(1, 1, 1, 0.35 * aa); ctx.stroke()
            ctx.arc(px, y, 22, 0, 2 * math.pi); ctx.set_source_rgba(0.9, 0.92, 0.97, aa); ctx.fill()
            ctx.pop_group_to_source(); ctx.paint_with_alpha(1 - kk); ctx.restore()
        if kk > 0:
            draw_media(ctx, G["lift"], T - tha + 0.1, 720, 1265, 290, 380, a=aa * kk, loop=False, border=6, radius=18)
        labs = [("BARRE LOURDE", tb), ("EXPLOSIF", te_), ("HALTÉRO", tha)]
        for i, (lab, t) in enumerate(labs):
            if t is None or T < t - 0.05: continue
            k = (T - t + 0.05) / 0.22
            y = 1140 + i * 120
            ctx.save(); al = pop(ctx, 100, y, k, 0.7)
            if i == 1: chip(ctx, lab, 80, y, 50, alpha=aa * al, padx=16, pady=12)
            else: text(ctx, lab, 80, y, 50, anchor="l", alpha=aa * al)
            ctx.restore()

def squat_pose(d, ax, ay):
    shin, thigh, torso = 118, 128, 150
    a_s = math.radians(8 + 30 * d)                 # shin forward lean
    knee = (ax + shin * math.sin(a_s), ay - shin * math.cos(a_s))
    th = math.radians(85 - 100 * d)                # thigh angle above horizontal, going back
    hip = (knee[0] - thigh * math.cos(th), knee[1] - thigh * math.sin(th))
    lean = math.radians(8 + 38 * d)
    sh = (hip[0] + torso * math.sin(lean), hip[1] - torso * math.cos(lean))
    head = (sh[0] + 22 * math.sin(lean), sh[1] - 48)
    hand = (sh[0] + 100, sh[1] + 8)
    return knee, hip, sh, head, hand

def c_move(ctx, T, a, s0):
    t7 = R("E7")[0]
    pa = 1 - eio((T - t7 + 0.1) / 0.25); pb = eio((T - t7 + 0.1) / 0.25)
    if pa > 0:
        aa = a * pa
        header(ctx, "MOVE", "SÉANCES SPÉCIFIQUES", aa)
        rings = [(300, 1245, 150, "20", "MIN / JOUR", wt("E5", "20")),
                 (760, 1245, 130, "10", "MIN / 2 JOURS", wt("E6a", "10"))]
        for cx, cy, r, num, lab, t in rings:
            if t is None or T < t - 0.15: continue
            k = eo((T - t + 0.15) / 0.25)
            f = eo((T - t) / 1.1)
            ctx.set_line_width(22)
            ctx.arc(cx, cy, r, 0, 2 * math.pi); ctx.set_source_rgba(1, 1, 1, 0.12 * aa * k); ctx.stroke()
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            if f > 0.01:
                ctx.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * f); ctx.set_source_rgba(*BLUE, aa * k); ctx.stroke()
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)
            text(ctx, num, cx, cy - 18, 110 if r > 140 else 96, face=NUM, alpha=aa * k)
            text(ctx, lab, cx, cy + 58, 26, color=BLUE2, alpha=aa * k, spacing=1)
        to = wt("E6a", "ou")
        if to and T > to: text(ctx, "OU", 540, 1245, 44, alpha=aa * eo((T - to) / 0.2), color=WHITE)
        tm = wt("E6b", "mieux")
        if tm and T > tm - 0.05:
            k = (T - tm + 0.05) / 0.22
            ctx.save(); al = pop(ctx, 540, 1450, k, 0.7)
            chip(ctx, "MIEUX QUE RIEN", 540, 1450, 40, anchor="c", alpha=aa * al); ctx.restore()
        for t in [wt("E5", "20"), wt("E6a", "10")]:
            if t and ("ring", t) not in _ev: _ev.add(("ring", t)); EVENTS.append((t, "tick"))
    if pb > 0:
        aa = a * pb
        header(ctx, "MOVE", "AMPLITUDE", aa)
        tmob = wt("E7", "mobile,") or t7 + 1.0
        tf = wt("E8b", "force")
        ax, ay = 300, 1480
        deep = eio((T - tmob) / 0.6)
        amp = 0.45 + 0.55 * deep
        per = 1.6; u = ((T - t7) % per) / per
        d = amp * (math.sin(u * math.pi) ** 1.4)
        ctx.set_line_width(4)
        ctx.move_to(90, ay + 4); ctx.line_to(620, ay + 4); ctx.set_source_rgba(1, 1, 1, 0.3 * aa); ctx.stroke()
        # parallel reference (hip at knee height when d~0.85)
        k_ref, h_ref, *_ = squat_pose(0.85, ax, ay)
        ctx.set_dash([12, 12]); ctx.move_to(90, k_ref[1]); ctx.line_to(620, k_ref[1]); ctx.set_source_rgba(*BLUE2, 0.45 * aa); ctx.stroke(); ctx.set_dash([])
        knee, hip, sh, head, hand = squat_pose(d, ax, ay)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(34)
        ctx.move_to(ax + 50, ay - 6); ctx.line_to(ax, ay - 6)       # foot
        ctx.move_to(ax, ay - 10); ctx.line_to(*knee); ctx.line_to(*hip); ctx.line_to(*sh)
        ctx.set_source_rgba(1, 1, 1, aa); ctx.stroke()
        ctx.set_line_width(24); ctx.move_to(*sh); ctx.line_to(*hand); ctx.stroke()
        ctx.arc(head[0], head[1], 30, 0, 2 * math.pi); ctx.fill()
        ctx.arc(sh[0] + 6, sh[1] - 4, 22, 0, 2 * math.pi); ctx.set_source_rgba(*BLUE, aa); ctx.fill()   # bar
        # depth arc at hip
        text(ctx, "PROFONDEUR", 660, 1130, 40, anchor="l", alpha=aa)
        bar_row(ctx, "", 1185, amp * (math.sin(u * math.pi) ** 1.4) if True else 0, aa, x0=660, x1=910)
        if tf and T > tf - 0.05:
            k = (T - tf + 0.05) / 0.22
            ctx.save(); al = pop(ctx, 780, 1330, k, 0.6)
            chip(ctx, "+ DE FORCE", 660, 1330, 52, alpha=aa * al, padx=18, pady=14); ctx.restore()
            if ("force",) not in _ev: _ev.add(("force",)); EVENTS.append((tf, "hit"))
        if T > tmob:
            text(ctx, "+ MOBILE", 660, 1250, 36, anchor="l", color=BLUE2, alpha=aa * eo((T - tmob) / 0.25))


# ---------------------------------------------------------------- GIF library (Bibliothèque)
import PIL.Image as PImage
BIB = "/home/claude/biblio/"
class Gif:
    def __init__(self, name, crop=None, max_s=None):
        im = PImage.open(BIB + name); self.frames = []; self.durs = []
        n = getattr(im, "n_frames", 1); i = 0
        while i < n and (max_s is None or sum(self.durs) < max_s):
            im.seek(i); fr = im.convert("RGBA")
            if crop: fr = fr.crop(crop)
            a = np.asarray(fr).astype(np.float32); al = a[..., 3:4] / 255.0
            bgra = np.concatenate([a[..., 2:3] * al, a[..., 1:2] * al, a[..., 0:1] * al, a[..., 3:4]], 2).astype(np.uint8)
            h, w = bgra.shape[:2]; stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
            buf = np.zeros((h, stride // 4, 4), np.uint8); buf[:, :w] = bgra
            self.frames.append(cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_ARGB32, w, h, stride))
            self.durs.append(max(im.info.get("duration", 80), 40) / 1000); i += 1
        self.w, self.h = self.frames[0].get_width(), self.frames[0].get_height(); self.total = sum(self.durs)
    def at(self, t, loop=True):
        t = t % self.total if loop else min(t, self.total - 1e-3)
        for f, d in zip(self.frames, self.durs):
            if t < d: return f
            t -= d
        return self.frames[-1]

def draw_media(ctx, g, t, cx, cy, bw, bh, a=1.0, tilt=0.0, border=10, radius=26, loop=True, bg=None, contain=False):
    """image fitted (cover) in a rounded box centred on cx,cy"""
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(math.radians(tilt))
    rrect(ctx, -bw / 2 - border, -bh / 2 - border + 10, bw + 2 * border, bh + 2 * border, radius + border)
    ctx.set_source_rgba(0, 0, 0, 0.35 * a); ctx.fill()
    rrect(ctx, -bw / 2 - border, -bh / 2 - border, bw + 2 * border, bh + 2 * border, radius + border)
    ctx.set_source_rgba(1, 1, 1, a); ctx.fill()
    rrect(ctx, -bw / 2, -bh / 2, bw, bh, radius); ctx.clip()
    if bg: ctx.set_source_rgba(*bg, a); ctx.paint()
    sc = (min if contain else max)(bw / g.w, bh / g.h) * (0.94 if contain else 1)
    ctx.scale(sc, sc); ctx.set_source_surface(g.at(t, loop), -g.w / 2, -g.h / 2)
    ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.paint_with_alpha(a)
    ctx.restore()

G = {"letsgo": Gif("let.s.go.gif"), "ohyeah": Gif("happy2.gif", crop=(0, 0, 469, 470)),
     "corgi": Gif("confused.gif"), "jog": Gif("jogging.gif"), "row": Gif("row.erg.gif"),
     "lift": Gif("happyb.lift.gif", crop=(0, 0, 220, 290), max_s=3.2)}

def sticker_window(t0, t1, T):
    if not (t0 <= T <= t1 + 0.2): return 0
    return eback((T - t0) / 0.28) * (1 - eio((T - t1) / 0.2))

def draw_stickers(ctx, T):
    # "Let's go" — kid in his car
    a0, a1 = R("letsgo"); a1 += 0.35
    k = sticker_window(a0 - 0.05, a1, T)
    if k > 0:
        ctx.save(); s = 0.6 + 0.4 * k; ctx.translate(540, 1120); ctx.scale(s, s); ctx.translate(-540, -1120)
        draw_media(ctx, G["letsgo"], T - a0 + 0.6, 540, 1120, 760, 504, a=clamp(k * 1.5), tilt=-3); ctx.restore()
        if ("st", "letsgo") not in _ev: _ev.add(("st", "letsgo")); EVENTS.append((a0 - 0.05, "swoosh"))
    # "pas pour être beau" — OH YEAH
    tb = wt("B3", "beau") or R("B3")[0]
    a1 = R("B3")[1]
    k = sticker_window(tb - 0.1, a1, T)
    if k > 0:
        ctx.save(); s = 0.5 + 0.5 * k; ctx.translate(840, 520); ctx.scale(s, s); ctx.translate(-840, -520)
        draw_media(ctx, G["ohyeah"], T - tb, 840, 520, 300, 300, a=clamp(k * 1.5), tilt=6); ctx.restore()
        if ("st", "ohyeah") not in _ev: _ev.add(("st", "ohyeah")); EVENTS.append((tb - 0.1, "swoosh"))
    # "deux choses différentes" — confused corgi
    td = wt("E2", "deux") or wt("E2", "différentes.")
    a1 = (wt("E2", "négliger,") or td + 2.2) - 0.1
    k = sticker_window(td - 0.05, a1, T)
    if k > 0:
        ctx.save(); s = 0.5 + 0.5 * k; ctx.translate(845, 500); ctx.scale(s, s); ctx.translate(-845, -500)
        draw_media(ctx, G["corgi"], T - td, 845, 500, 300, 270, a=clamp(k * 1.5), tilt=-5); ctx.restore()
        if ("st", "corgi") not in _ev: _ev.add(("st", "corgi")); EVENTS.append((td - 0.05, "swoosh"))
    # cardio card: running then rowing
    tc = wt("C1", "cardio,") or R("C1")[0] + 3
    tcv = wt("C1", "cardiovasculaires") or tc + 1.2
    a1 = R("C1")[1]
    k = sticker_window(tc - 0.1, a1, T)
    if k > 0:
        a = clamp(k * 1.5); y = 1010 + (1 - eo((T - tc + 0.1) / 0.3)) * 50
        sw = eio((T - tcv + 0.1) / 0.3)
        ctx.save()
        if sw < 1: draw_media(ctx, G["jog"], T - tc, 540, y, 640, 360, a=a * (1 - sw), bg=(1, 1, 1), contain=True)
        if sw > 0: draw_media(ctx, G["row"], T - tcv, 540, y, 640, 360, a=a * sw, bg=(0.99, 0.97, 0.94), contain=True)
        lab = "COURSE" if sw < 0.5 else "RAMEUR"
        chip(ctx, lab, 540 - 320 + 18, y - 180 + 40, 30, alpha=a, padx=12, pady=8)
        ctx.restore()
        if ("st", "cardio") not in _ev: _ev.add(("st", "cardio")); EVENTS.append((tc - 0.1, "swoosh"))

CONTENT = {"build": c_build, "zone2": c_zone2, "perform": c_perform, "move": c_move}
_ev = set()

# ---------------------------------------------------------------- floating cards
def card_frame(ctx, y, h, a):
    ctx.save()
    rrect(ctx, 70, y + 8, 940, h, 28); ctx.set_source_rgba(0, 0, 0, 0.3 * a); ctx.fill()
    rrect(ctx, 70, y, 940, h, 28)
    g = cairo.LinearGradient(0, y, 0, y + h); g.add_color_stop_rgba(0, *NAVY2, 0.94 * a); g.add_color_stop_rgba(1, *NAVY, 0.94 * a)
    ctx.set_source(g); ctx.fill()
    rrect(ctx, 70, y, 940, h, 28); ctx.set_line_width(3); ctx.set_source_rgba(*BLUE, 0.9 * a); ctx.stroke()
    ctx.restore()

def draw_cards(ctx, T):
    for name, a0, a1 in CARDS:
        if not (a0 <= T <= a1 + 0.3): continue
        a = eo((T - a0) / 0.28) * (1 - eio((T - a1) / 0.3))
        dy = (1 - eo((T - a0) / 0.35)) * 60
        ctx.save(); ctx.translate(0, dy)
        if name == "km":
            y, h = 870, 360; card_frame(ctx, y, h, a)
            text(ctx, "COURSE · KM / SEMAINE", 110, y + 48, 32, anchor="l", color=BLUE2, alpha=a, spacing=2)
            vals = [("5", wt("C4", "5")), ("7", wt("C4", "7,")), ("8", wt("C4", "8,")), ("10", wt("C4", "10"))]
            base = y + h - 50; xs = [190, 390, 590, 790]
            for (v, t), x in zip(vals, xs):
                if t is None or T < t - 0.05: continue
                k = eo((T - t + 0.05) / 0.35)
                hh = int(v) / 10 * 200 * k
                if v == "10" and T > (wt("C4", "2") or 1e9):
                    s = eo((T - wt("C4", "2")) / 0.25) * 10
                    rrect(ctx, x - 55, base - hh, 110, hh / 2 - s / 2, 10); ctx.set_source_rgba(*BLUE, a); ctx.fill()
                    rrect(ctx, x - 55, base - hh / 2 + s / 2, 110, hh / 2 - s / 2, 10); ctx.fill()
                    text(ctx, "2×5", x, base - hh / 2, 30, alpha=a * eo((T - wt("C4", "2")) / 0.25))
                else:
                    rrect(ctx, x - 55, base - hh, 110, hh, 10); ctx.set_source_rgba(*BLUE, a); ctx.fill()
                text(ctx, f"{v} KM", x, base - hh - 28, 34, alpha=a * k)
                if ("km", v) not in _ev: _ev.add(("km", v)); EVENTS.append((t, "tick"))
            ctx.rectangle(110, base, 860, 3); ctx.set_source_rgba(1, 1, 1, 0.3 * a); ctx.fill()
        elif name == "week":
            y, h = 900, 300; card_frame(ctx, y, h, a)
            text(ctx, "HAUTE INTENSITÉ", 110, y + 48, 32, anchor="l", color=BLUE2, alpha=a, spacing=2)
            tp = wt("D5", "pas") or a0 + 1
            days = "LMMJVSD"; hot = {1, 4}
            for i, dch in enumerate(days):
                x = 150 + i * 130; cy = y + 150
                lit = i in hot and T > tp
                k = eo((T - tp - (0.12 * list(hot).index(i) if i in hot else 0)) / 0.25) if i in hot else 0
                ctx.arc(x, cy, 46, 0, 2 * math.pi)
                if lit: ctx.set_source_rgba(*BLUE, a * k); ctx.fill_preserve()
                ctx.set_line_width(4); ctx.set_source_rgba(1, 1, 1, a * (0.35 + 0.65 * k)); ctx.stroke()
                text(ctx, dch, x, cy, 38, alpha=a)
            text(ctx, "PAS À CHAQUE SÉANCE", 540, y + 250, 38, alpha=a * eo((T - tp) / 0.3))
        elif name == "mob":
            y, h = 930, 230; card_frame(ctx, y, h, a)
            t1, t2, t3 = wt("E2", "mobilité"), wt("E2", "souplesse,"), wt("E2", "différentes.")
            cy = y + h / 2
            if T > t1 - 0.05:
                k = (T - t1 + 0.05) / 0.22; ctx.save(); al = pop(ctx, 290, cy, k, 0.7)
                chip(ctx, "MOBILITÉ", 290, cy, 50, anchor="c", alpha=a * al, padx=20, pady=16); ctx.restore()
            if T > t2 - 0.05:
                k = (T - t2 + 0.05) / 0.22; ctx.save(); al = pop(ctx, 790, cy, k, 0.7)
                chip(ctx, "SOUPLESSE", 790, cy, 50, fill=WHITE, color=NAVY, anchor="c", alpha=a * al, padx=20, pady=16); ctx.restore()
            if t3 and T > t3 - 0.1:
                k = (T - t3 + 0.1) / 0.22; ctx.save(); al = pop(ctx, 540, cy, k, 0.4)
                text(ctx, "≠", 540, cy, 90, color=BLUE2, alpha=a * al); ctx.restore()
        ctx.restore()

# ---------------------------------------------------------------- end card
def draw_end(ctx, T):
    if T < END_T: return
    u = T - END_T
    a = eo(u / 0.35)
    ctx.rectangle(0, 0, W, H); ctx.set_source_rgba(*NAVY, 0.84 * a); ctx.fill()
    ctx.set_line_width(2)
    for i in range(-6, 16): ctx.move_to(i * 120, 0); ctx.line_to(i * 120 - 300, H)
    ctx.set_source_rgba(1, 1, 1, 0.035 * a); ctx.stroke()
    lines = [("LAQUELLE", 112, 0.15, None), ("DE CES 4 QUALITÉS", 64, 0.35, None),
             ("EST TON PLUS GROS", 64, 0.55, None), ("POINT FAIBLE ?", 100, 0.8, "chip")]
    ys = [520, 640, 725, 860]
    for (s, sz, d, kind), y in zip(lines, ys):
        k = (u - d) / 0.25
        if k <= 0: continue
        ctx.save(); al = pop(ctx, 540, y, k, 0.75)
        if kind: chip(ctx, s, 540, y, sz, anchor="c", alpha=al, padx=28, pady=20)
        else: text(ctx, s, 540, y, sz, alpha=al, stroke=STROKE, sw=8)
        ctx.restore()
    pills = ["BUILD", "RUN", "PERFORM", "MOVE"]
    pos = [(310, 1060), (770, 1060), (310, 1190), (770, 1190)]
    for i, (p, (x, y)) in enumerate(zip(pills, pos)):
        k = (u - 1.15 - i * 0.16) / 0.22
        if k <= 0: continue
        ctx.save(); al = pop(ctx, x, y, k, 0.6)
        rrect(ctx, x - 200, y - 50, 400, 100, 50); ctx.set_line_width(4); ctx.set_source_rgba(*BLUE2, al); ctx.stroke()
        text(ctx, f"0{i + 1}", x - 150, y, 36, face=NUM, color=BLUE2, alpha=al, anchor="l")
        text(ctx, p, x + 30, y, 48, alpha=al)
        ctx.restore()
        if ("pill", i) not in _ev: _ev.add(("pill", i)); EVENTS.append((END_T + 1.15 + i * 0.16, "tick"))
    k = (u - 2.0) / 0.3
    if k > 0:
        text(ctx, "DIS-LE MOI EN COMMENTAIRE", 540, 1335, 38, color=WHITE, alpha=eo(k), spacing=2)
        text(ctx, "BEN&FIT", 540, 1420, 34, color=BLUE2, alpha=eo(k) * 0.9, spacing=10)

# ---------------------------------------------------------------- base transform
TAGS = []
for c in TL:
    if c["tag"] not in TAGS: TAGS.append(c["tag"])
PUNCH = {"B3": 0.14, "letsgo": 0.10, "D3b": 0.12, "D3a": 0.06, "E1b": 0.08, "F1": 0.05, "perf": 0.03, "E7": 0.0}
def base_scale(T):
    c = cut_at(min(T, BASE_DUR - 0.01))
    ti = TAGS.index(c["tag"]); a, b = tag_range(c["tag"])
    s = (1.0 if ti % 2 == 0 else 1.055) + 0.06 * (c["sub"] % 2) + PUNCH.get(c["tag"], 0)
    s += 0.035 * clamp((T - a) / max(b - a, 0.5))
    if c["tag"] == "hook":
        s = 1.04 + 0.03 * clamp(T / 4) + 0.2 * (1 - eo(T / 0.55))
    return s

def vignette(ctx):
    g = cairo.RadialGradient(540, 820, 450, 540, 900, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0.05, 0.02, 0, 0.42)
    ctx.rectangle(0, 0, W, H); ctx.set_source(g); ctx.fill()
    # warm sun glow, top-left
    g = cairo.RadialGradient(120, 120, 0, 120, 120, 900)
    g.add_color_stop_rgba(0, 1.0, 0.78, 0.45, 0.16); g.add_color_stop_rgba(1, 1.0, 0.7, 0.4, 0)
    ctx.rectangle(0, 0, W, H); ctx.set_source(g); ctx.fill()

# ---------------------------------------------------------------- main loop
def render_frame(T, frame_bytes, out_surf):
    ctx = cairo.Context(out_surf)
    src = cairo.ImageSurface.create_for_data(frame_bytes, cairo.FORMAT_ARGB32, W, H, W * 4)
    name, k, s0, s1 = split_amount(T)
    s = base_scale(T); s = s + (1.0 - s) * k
    ctx.save()
    cx, cy = 540, 760
    ctx.translate(cx, cy - 230 * k); ctx.scale(s, s); ctx.translate(-cx, -cy)
    ctx.set_source_surface(src, 0, 0); ctx.get_source().set_filter(cairo.FILTER_GOOD); ctx.paint()
    ctx.restore()
    vignette(ctx)
    if k > 0:
        top = 960 + 960 * (1 - k)
        ctx.save(); ctx.translate(0, 0)
        panel_bg(ctx, top)
        ctx.translate(0, top - 960)
        CONTENT[name](ctx, T, 1.0, s0)
        ctx.restore()
        if ("split", s0) not in _ev: _ev.add(("split", s0)); EVENTS.append((s0, "whoosh_up"))
    draw_cards(ctx, T)
    draw_stickers(ctx, T)
    for nm, a0, a1 in CARDS:
        if ("card", a0) not in _ev: _ev.add(("card", a0)); EVENTS.append((a0, "swoosh"))
    draw_hook(ctx, T)
    if T >= END_T - 0.01:
        draw_end(ctx, T)
    else:
        draw_progress(ctx, T)
        y = 1300 + (865 - 1300) * k
        size = 74 + (62 - 74) * k
        if any(a0 <= T <= a1 for _, a0, a1 in CARDS): y = 1340 if k == 0 else y
        draw_subs(ctx, T, y, size)
    draw_wipe(ctx, T)
    for chn, tc in CH_START.items():
        if ("wipe", chn) not in _ev: _ev.add(("wipe", chn)); EVENTS.append((tc - 0.14, "wipe"))
    if ("end",) not in _ev: _ev.add(("end",)); EVENTS.append((END_T, "end"))

def main(t_from=0.0, t_to=None, out="/home/claude/work/video_nosound.mp4", only=None):
    t_to = DUR if t_to is None else t_to
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t_from:.3f}", "-i", "/home/claude/work/base.mp4",
                           "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    if only is None:
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                               "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    out_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    n = int(round((t_to - t_from) * FPS)); last = None
    for i in range(n):
        T = t_from + i / FPS
        buf = rd.stdout.read(W * H * 4) if T < BASE_DUR - 0.5 / FPS else b""
        if len(buf) == W * H * 4: last = bytearray(buf)
        fb = last
        render_frame(T, fb, out_surf)
        out_surf.flush()
        data = bytes(out_surf.get_data())
        if only is not None:
            if i in only:
                import PIL.Image as I
                im = I.frombuffer("RGBA", (W, H), data, "raw", "BGRA", 0, 1).convert("RGB"); im.save(f"/home/claude/work/frames2/t_{T:06.2f}.jpg", quality=88)
        else:
            wr.stdin.write(data)
        if i % 300 == 0: print(f"{T:.1f}s", flush=True)
    rd.kill()
    if only is None:
        wr.stdin.close(); wr.wait()
    json.dump(sorted(EVENTS), open("/home/claude/work/events.json", "w"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        ts = [float(x) for x in sys.argv[2:]]
        for t in ts:
            main(t, t + 1 / FPS + 0.001, only={0})
    else:
        main()
