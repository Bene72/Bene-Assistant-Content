"""BEN&FIT athlete v2: skinned human mesh driven by cleaned mocap signals, IK feet/hands, bar on floor."""
import sys, json, math, time, statistics
import bpy, bmesh
from mathutils import Vector, Matrix

args = dict(a.split("=", 1) for a in sys.argv[1:])
MH = json.load(open(args.get("mesh", "/home/claude/work/mh.json")))
SIG = json.load(open(args.get("sig", "/home/claude/work/sig.json")))
OUT = args.get("out", "/home/claude/work/frames2/f_")
RES = int(args.get("res", "1080")); SAMPLES = int(args.get("samples", "12"))
FRAMES = args.get("frames", "all"); SUB = float(args.get("sub", "0"))
AZ = float(args.get("az", "35")); CAM = args.get("cam", "main")
T = len(SIG["hip"])
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
J = {k: Vector(v) for k, v in MH["joints"].items()}
ARM_S = 1.14; PLATE_R = 0.225; GRIP_HW = 0.42; BALL = 0.13; ANK_H = 0.092

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
def Fr(d, h):
    y = d.normalized(); x = (h - y * h.dot(y)).normalized(); z = x.cross(y)
    return Matrix((x, y, z)).transposed()
def TR(p): return Matrix.Translation(p)
def rigid(head, R, head0): return TR(head) @ R.to_4x4() @ TR(-head0)
def rot_about(p, axis, ang): return TR(p) @ Matrix.Rotation(ang, 4, axis) @ TR(-p)

# ------------------------------------------------------------------ rest data
REST = {}
for side, s in (("l", 1), ("r", -1)):
    g = lambda n: J[f"{side}-{n}"]
    S0, E0, W0 = g("shoulder"), g("elbow"), g("hand")
    k = [sum((g(f"finger-{j}-{i}") for j in range(2, 6)), Vector()) / 4 for i in range(1, 5)]
    dir0 = (k[0] - W0).normalized()
    a0 = g("finger-5-1") - g("finger-2-1"); a0 = (a0 - dir0 * a0.dot(dir0)).normalized()
    n0 = dir0.cross(a0) * (-s)
    third0 = dir0.cross(n0).normalized()
    C0 = k[0] + n0 * 0.026 + dir0 * 0.010
    REST[side] = dict(s=s, S0=S0, E0=E0, W0=W0, k=k, dir0=dir0, n0=n0, third0=third0, C0=C0,
                      hinge0=(E0 - S0).cross(W0 - E0).normalized(), l1=(E0 - S0).length * ARM_S, l2=(W0 - E0).length * ARM_S,
                      C0cl=g("clavicle"), H0=g("upper-leg"), K0=g("knee"), A0=g("ankle"))
    print(side, "palm n0", [round(c, 2) for c in n0], "curl check", round((k[3] - k[0]).dot(n0), 3))
HM0 = (REST["l"]["H0"] + REST["r"]["H0"]) / 2
L1 = (REST["l"]["K0"] - REST["l"]["H0"]).length; L2 = (REST["l"]["A0"] - REST["l"]["K0"]).length
N0, HD0, HT0 = J["neck"], J["head"], J["head-2"]

# ------------------------------------------------------------------ cleaned signals
hipz_stand = statistics.median(h[1] for h in SIG["hip"][-15:])
KZ = 0.985 * (L1 + L2) / hipz_stand
ext_i = max(range(28, 52), key=lambda i: SIG["hip"][i][1])
w0 = statistics.median(SIG["fw"][:30]); w1 = statistics.median(SIG["fw"][60:90])
w0 = max(0.13, min(0.2, w0)); w1 = max(w0 + 0.05, min(0.3, w1))
barz_raw = [ANK_H + b[1] for b in SIG["bar"]]
z0 = statistics.median(barz_raw[:15]); y0 = statistics.median(b[0] for b in SIG["bar"][:15])
print("ext frame", ext_i, "w0", round(w0, 2), "w1", round(w1, 2), "bar z0", round(z0, 2), "KZ", round(KZ, 3))

def feet(i):
    u = smoothstep(ext_i + 2, ext_i + 9, i)
    w = w0 + (w1 - w0) * u; lift = 0.035 * math.sin(math.pi * u); to = math.radians(12 + 10 * u)
    heel = math.radians(24) * math.exp(-((i - ext_i - 0.5) / 3.2) ** 2)
    out = {}
    for side, s in (("l", 1), ("r", -1)):
        fwd = Vector((s * math.sin(to), -math.cos(to), 0))
        ball = Vector((s * w, 0, lift)) + fwd * BALL
        M = TR(ball) @ Matrix.Rotation(math.pi + s * to, 4, "Z") @ Matrix.Rotation(-heel, 4, "X")
        out[side] = dict(M=M, A=M @ Vector((0, -BALL, ANK_H)), fwd=fwd)
    return out

def bar_target(i):
    by, bz = SIG["bar"][i][0], barz_raw[i]
    w = 1 - smoothstep(z0 + 0.05, z0 + 0.6, bz)
    bz = bz + (PLATE_R - z0) * w; by = by + (-0.11 - y0) * w
    bz = PLATE_R if bz < PLATE_R + 0.012 else bz
    return by, bz, bz <= PLATE_R + 1e-6

def arm(side, S, G):
    r = REST[side]; f = (G - S).normalized(); fp_prev = Z
    for _ in range(3):
        fp = f - X * f.dot(X)
        fp = fp.normalized() if fp.length > 1e-4 else fp_prev
        e = math.radians(55) * smoothstep(0.0, 0.8, fp.z)
        hd = Matrix.Rotation(-e, 3, "X") @ fp
        pn = X.cross(hd)
        R = Fr(hd, pn) @ Fr(r["dir0"], r["n0"]).transposed()
        Xh = rigid(G, R, r["C0"]); W = Xh @ r["W0"]; f = (W - S).normalized()
    d_full = (W - S).length; lmax = (r["l1"] + r["l2"]) * 0.9985
    d = min(d_full, lmax); n = (W - S).normalized()
    p = X * r["s"]; p = (p - n * p.dot(n)).normalized()
    a = (r["l1"] ** 2 - r["l2"] ** 2 + d * d) / (2 * d); h = math.sqrt(max(r["l1"] ** 2 - a * a, 0))
    E = S + n * a + p * h; hinge = p.cross(n)
    return dict(E=E, W=W, Xh=Xh, hinge=hinge, deficit=d_full - lmax, n=n)

def solve(i, p_fixed=None):
    ft = feet(i)
    Am = (ft["l"]["A"] + ft["r"]["A"]) / 2
    hy = SIG["hip"][i][0]; hy = hy if hy > 0.02 else 0.02 - 0.05 * (1 - math.exp((hy - 0.02) / 0.05))
    p = Vector((0, Am.y + hy, Am.z + KZ * SIG["hip"][i][1])) if p_fixed is None else p_fixed.copy()
    a = SIG["trunk"][i]; Rt = Matrix.Rotation(a, 3, "X")
    by, bz, on_floor = bar_target(i)
    res = None
    for it in range(6):
        Xt = rigid(p, Rt, HM0)
        # overhead: bar stacks over the shoulders
        Sm = Xt @ ((REST["l"]["S0"] + REST["r"]["S0"]) / 2)
        Hm = Xt @ HM0; tz = max(0.0, min(1.0, (bz - Hm.z) / max(Sm.z - Hm.z, 1e-3)))
        y_body = Hm.y + (Sm.y - Hm.y) * tz - 0.125
        k2 = smoothstep(0.5, 0.8, bz) * (1 - smoothstep(1.25, 1.6, bz))
        byy = by + (max(by, y_body) - by) * k2 if bz >= Hm.z - 0.12 else by
        k = smoothstep(1.25, 1.6, bz); byy = byy + (Sm.y + 0.03 - byy) * k
        B = Vector((0, byy, bz))
        arms = {}; sh = {}
        for side in "lr":
            r = REST[side]; G = B + X * r["s"] * GRIP_HW
            S_t = Xt @ r["S0"]
            v = Rt.transposed() @ (G - S_t); elev = math.asin(max(-1, min(1, v.z / v.length)))
            ce = 0.4 * max(0.0, elev)
            Xc = Xt @ rot_about(r["C0cl"], "Y", -r["s"] * ce)
            sh[side] = (Xc, Xc @ r["S0"]); arms[side] = arm(side, sh[side][1], G)
        res = dict(ft=ft, p=p.copy(), Xt=Xt, Rt=Rt, B=B, arms=arms, sh=sh, on_floor=on_floor)
        moved = False
        dfc = max(arms[s]["deficit"] for s in "lr")
        if dfc > 1e-4 and p_fixed is None:
            if on_floor or bz < 0.9:
                dirv = (B - Sm); dirv.x = 0; p += dirv.normalized() * dfc; moved = True
            else:
                dirv = (B - Sm); dirv.x = 0; dirv.normalize(); by -= dirv.y * dfc; bz -= dirv.z * dfc; moved = True
        elif dfc > 1e-4 and not on_floor:
            dirv = (B - Sm); dirv.x = 0; dirv.normalize(); by -= dirv.y * dfc; bz -= dirv.z * dfc; moved = True
        if p_fixed is None:
            for side in "lr":
                Hj = rigid(p, Rt, HM0) @ REST[side]["H0"]; A = ft[side]["A"]
                hxy = math.hypot(Hj.x - A.x, Hj.y - A.y); lm = (L1 + L2) * 0.997
                if (Hj - A).length > lm and hxy < lm:
                    p.z -= (Hj.z - A.z) - math.sqrt(lm * lm - hxy * hxy); moved = True
        if not moved: break
    return res

P1 = [solve(i)["p"] for i in range(T)]
for _ in range(2):
    P1 = [P1[i] if i in (0, T - 1) else (P1[i - 1] + 2 * P1[i] + P1[i + 1]) / 4 for i in range(T)]
SOL = [solve(i, P1[i]) for i in range(T)]
print("max arm deficit after smoothing", round(max(max(s["arms"][k]["deficit"] for k in "lr") for s in SOL), 4))

# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
NAVY = (0.0032, 0.011, 0.11, 1)
def mat(name, color, rough=0.5, coat=0.0, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color; b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = emit; b.inputs["Emission Strength"].default_value = strength
    return m
SKIN = mat("skin", (0.012, 0.012, 0.014, 1), 0.42, coat=0.25)
CLOTH = mat("cloth", NAVY, 0.75); CLOTH2 = mat("cloth2", NAVY, 0.75)
WHITE = mat("white", (0.8, 0.8, 0.82, 1), 0.5); SOLE = mat("sole", NAVY, 0.6)
STEEL = mat("steel", (0.75, 0.76, 0.78, 1), 0.25, metal=1.0)
PLATE_N = mat("plateN", NAVY, 0.55); PLATE_W = mat("plateW", (0.85, 0.86, 0.88, 1), 0.5)
WOOD = mat("wood", (0.33, 0.2, 0.11, 1), 0.55); RUBBER = mat("rubber", (0.015, 0.015, 0.017, 1), 0.85)
FLOOR = mat("floor", (0.004, 0.004, 0.006, 1), 0.65); WALL = mat("wall", (0.02, 0.022, 0.028, 1), 0.9)
STRIP = mat("strip", (0, 0, 0, 1), 0.5, emit=(0.08, 0.25, 1.0, 1), strength=6.0)

def link(o): sc.collection.objects.link(o); return o
def mesh_obj(name, build, mats, smooth=True):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); build(bm); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]): o.data.materials.append(m)
    return link(o)
def box(name, m, size, loc):
    o = mesh_obj(name, lambda bm: bmesh.ops.create_cube(bm, size=1.0), m, False); o.scale = size; o.location = loc; return o
def cyl(name, m, r, depth, seg=32, off=0.0):
    return mesh_obj(name, lambda bm: bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth,
                                                          matrix=Matrix.Translation((0, 0, off))), m)
box("floor", FLOOR, (40, 40, 0.02), (0, 0, -0.06))
box("platform_wood", WOOD, (1.2, 2.4, 0.05), (0, 0, -0.025))
box("platform_rubL", RUBBER, (0.6, 2.4, 0.049), (-0.9, 0, -0.025)); box("platform_rubR", RUBBER, (0.6, 2.4, 0.049), (0.9, 0, -0.025))
for i, x in enumerate((-1.21, 1.21)): box(f"strip{i}", STRIP, (0.015, 2.4, 0.012), (x, 0, 0.005))
for i, y in enumerate((-1.21, 1.21)): box(f"stripb{i}", STRIP, (2.43, 0.015, 0.012), (0, y, 0.005))
box("backdrop", WALL, (40, 0.1, 20), (0, 7, 10)); box("backdropX", WALL, (0.1, 40, 20), (6, 0, 10))

# ---- body mesh
verts = [Vector(v) for v in MH["verts"]]
def region(c):
    ax = abs(c.x)
    waist = 1.02
    if c.z < 0.075: return -1
    if 1.0 <= c.z <= 1.035 and ax < 0.3: return 3
    if 0.70 < c.z < 1.0 and ax < 0.3: return 2
    if 1.035 < c.z < 1.47 and ax < 0.3:
        s = 1 if c.x > 0 else -1; r = REST["l" if s > 0 else "r"]
        ab = r["E0"] - r["S0"]; t = max(0, min(1, (c - r["S0"]).dot(ab) / ab.length_squared))
        d_arm = (c - (r["S0"] + ab * t)).length
        if c.z > 1.30 and (d_arm < 0.085 or ax > 0.165): return 0
        if c.z <= 1.30 and ax > 0.2: return 0
        if c.z > 1.40 and ax < 0.075 - (1.47 - c.z) * 0.3: return 0   # neckline
        return 1
    return 0
me = bpy.data.meshes.new("body")
me.from_pydata([tuple(v) for v in verts], [], [f for f in MH["faces"]]); me.update()
bm = bmesh.new(); bm.from_mesh(me)
for zc in (0.075, 0.70, 1.0, 1.035):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, zc), plane_no=(0, 0, 1))
bmesh.ops.delete(bm, geom=[f for f in bm.faces if region(f.calc_center_median()) < 0], context="FACES")
bm.faces.ensure_lookup_table(); fmat = [region(f.calc_center_median()) for f in bm.faces]
bm.to_mesh(me); bm.free()
for p, m in zip(me.polygons, fmat): p.material_index = m; p.use_smooth = True
body = link(bpy.data.objects.new("body", me))
for m in (SKIN, CLOTH, CLOTH2, WHITE): me.materials.append(m)
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS"); bm.to_mesh(me); bm.free()

# ---- armature
arm_d = bpy.data.armatures.new("rig"); rig = link(bpy.data.objects.new("rig", arm_d))
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode="EDIT")
BONES = {"hips": (HM0, J["spine-3"]), "spine": (J["spine-3"], J["spine-1"]), "chest": (J["spine-1"], N0),
         "neck": (N0, HD0), "head": (HD0, HT0)}
for side in "lr":
    r = REST[side]
    BONES.update({f"clav_{side}": (r["C0cl"], r["S0"]), f"uparm_{side}": (r["S0"], r["E0"]), f"fore_{side}": (r["E0"], r["W0"]),
                  f"hand_{side}": (r["W0"], r["k"][0]), f"f1_{side}": (r["k"][0], r["k"][1]), f"f2_{side}": (r["k"][1], r["k"][2]),
                  f"f3_{side}": (r["k"][2], r["k"][3]), f"thigh_{side}": (r["H0"], r["K0"]), f"shin_{side}": (r["K0"], r["A0"])})
for n, (h, t) in BONES.items():
    b = arm_d.edit_bones.new(n); b.head = h; b.tail = t
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
print("vertex groups", len(body.vertex_groups), "weighted verts", sum(1 for v in body.data.vertices if v.groups))
sub = body.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 1

# ---- shoes
def build_shoe(bm):
    prof = [(0.0, 0.026, 0.085), (0.06, 0.036, 0.125), (0.2, 0.039, 0.135), (0.33, 0.041, 0.115), (0.45, 0.044, 0.088),
            (0.62, 0.051, 0.066), (0.8, 0.05, 0.054), (0.93, 0.04, 0.045), (1.0, 0.022, 0.032)]
    y_a, y_b = -BALL - 0.075, 0.105; n = 16; rings = []
    for u, hw, h in prof:
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n; cx, sz = math.cos(a), math.sin(a)
            x = hw * math.copysign(abs(cx) ** 0.7, cx)
            z = h * (0.5 + 0.5 * math.copysign(abs(sz) ** (0.45 if sz < 0 else 0.8), sz))
            ring.append(bm.verts.new((x, y_a + (y_b - y_a) * u, z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(n): bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
shoes = {}
for side in "lr":
    o = mesh_obj("shoe_" + side, build_shoe, [WHITE, SOLE])
    for p in o.data.polygons:
        if p.center.z < 0.02: p.material_index = 1
    m = o.modifiers.new("sub", "SUBSURF"); m.levels = 2; m.render_levels = 2
    o.rotation_mode = "QUATERNION"; shoes[side] = o

# ---- barbell (axis X)
RY = Matrix.Rotation(math.pi / 2, 4, "Y")
bar = cyl("bar", STEEL, 0.014, 2.2, 24); bar.data.transform(RY)
for sgn in (-1, 1):
    acc = 0.0
    for i, (w, r, m) in enumerate([(0.065, PLATE_R, PLATE_N), (0.045, PLATE_R, PLATE_W), (0.03, 0.17, PLATE_N)]):
        p = cyl(f"plate{sgn}_{i}", m, r, w, 64, sgn * (0.82 + acc + w / 2)); p.data.transform(RY); p.parent = bar; acc += w
        hub = cyl(f"hub{sgn}_{i}", STEEL, 0.05, w + 0.004, 32, sgn * (0.82 + acc - w / 2)); hub.data.transform(RY); hub.parent = bar
    sl = cyl(f"sleeve{sgn}", STEEL, 0.025, 0.42, 24, sgn * 0.88); sl.data.transform(RY); sl.parent = bar
    c = cyl(f"collar{sgn}", STEEL, 0.04, 0.04, 24, sgn * 0.79); c.data.transform(RY); c.parent = bar

# ------------------------------------------------------------------ animation
prevq = {}
def key_pb(name, Xf, fr):
    pb = rig.pose.bones[name]; pb.matrix = Xf @ rig.data.bones[name].matrix_local
    q = pb.rotation_quaternion.copy(); pq = prevq.get(name)
    if pq is not None and pq.dot(q) < 0: q.negate(); pb.rotation_quaternion = q
    prevq[name] = q
    for dp in ("location", "rotation_quaternion", "scale"): pb.keyframe_insert(dp, frame=fr)
CURL = [math.radians(a) for a in (62, 78, 50)]
for i, s in enumerate(SOL):
    fr = i + 1; Xt, Rt = s["Xt"], s["Rt"]
    for n in ("hips", "spine", "chest"): key_pb(n, Xt, fr)
    b = SIG["head"][i]; a = SIG["trunk"][i]; b = max(a - math.radians(35), min(a + math.radians(15), b))
    Xn = rigid(Xt @ N0, Matrix.Rotation((a + b) / 2, 3, "X"), N0); key_pb("neck", Xn, fr)
    key_pb("head", rigid(Xn @ HD0, Matrix.Rotation(b, 3, "X"), HD0), fr)
    for side in "lr":
        r = REST[side]; ar = s["arms"][side]; Xc, S = s["sh"][side]
        key_pb(f"clav_{side}", Xc, fr)
        key_pb(f"uparm_{side}", rigid(S, Fr(ar["E"] - S, ar["hinge"]) @ Fr(r["E0"] - r["S0"], r["hinge0"]).transposed(), r["S0"]) @ rot_about(r["S0"], X, 0) @ TR(r["S0"]) @ Matrix.Scale(ARM_S, 4, (r["E0"] - r["S0"]).normalized()) @ TR(-r["S0"]), fr)
        key_pb(f"fore_{side}", rigid(ar["E"], Fr(ar["W"] - ar["E"], ar["hinge"]) @ Fr(r["W0"] - r["E0"], r["hinge0"]).transposed(), r["E0"]) @ TR(r["E0"]) @ Matrix.Scale(ARM_S, 4, (r["W0"] - r["E0"]).normalized()) @ TR(-r["E0"]), fr)
        Xh = ar["Xh"]; key_pb(f"hand_{side}", Xh, fr)
        Xf = Xh
        for j in range(3):
            Xf = Xf @ rot_about(r["k"][j], r["third0"], CURL[j]); key_pb(f"f{j + 1}_{side}", Xf, fr)
        # leg IK
        Hj = Xt @ r["H0"]; A = s["ft"][side]["A"]; v = A - Hj; d = min(v.length, (L1 + L2) * 0.9995); n = v.normalized()
        pole = s["ft"][side]["fwd"].copy(); pole = (pole - n * pole.dot(n)).normalized()
        aa = (L1 * L1 - L2 * L2 + d * d) / (2 * d); h = math.sqrt(max(L1 * L1 - aa * aa, 0)); K = Hj + n * aa + pole * h
        hinge = pole.cross(n)
        key_pb(f"thigh_{side}", rigid(Hj, Fr(K - Hj, hinge) @ Fr(r["K0"] - r["H0"], X).transposed(), r["H0"]), fr)
        key_pb(f"shin_{side}", rigid(K, Fr(A - K, hinge) @ Fr(r["A0"] - r["K0"], X).transposed(), r["K0"]), fr)
        o = shoes[side]; M = s["ft"][side]["M"]; o.location = M.to_translation(); q = M.to_quaternion()
        pq = prevq.get(o.name)
        if pq is not None and pq.dot(q) < 0: q.negate()
        prevq[o.name] = q; o.rotation_quaternion = q
        o.keyframe_insert("location", frame=fr); o.keyframe_insert("rotation_quaternion", frame=fr)
    bar.location = s["B"]; bar.keyframe_insert("location", frame=fr)

# ------------------------------------------------------------------ lights, camera, render
def area(name, loc, target, power, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.energy = power; l.size = size; l.color = color
    o = link(bpy.data.objects.new(name, l)); o.location = loc
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
area("key", (-3.0, -3.2, 3.6), (0, 0, 1.0), 520, 2.0, (1, 0.97, 0.93))
area("rim", (2.6, 3.0, 3.0), (0, 0, 1.2), 1400, 1.5, (0.75, 0.85, 1.0))
area("rim2", (-2.6, 3.0, 2.5), (0, 0, 1.2), 700, 1.5, (0.75, 0.85, 1.0))
area("fill", (3.5, -3.0, 1.6), (0, 0, 1.2), 70, 2.0)
area("top", (0, 0, 5.0), (0, 0, 0), 60, 2.0)
area("wallwash", (0, 2.5, 0.3), (1.5, 7, 3.5), 260, 3.0, (0.55, 0.65, 1.0))
area("wallwash2", (1.0, -1.0, 0.3), (6, 1.5, 3.5), 140, 3.0, (0.55, 0.65, 1.0))
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.004, 0.005, 0.008, 1)
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 55
cam = link(bpy.data.objects.new("cam", cam_d)); sc.camera = cam
a = math.radians(AZ); dist = 5.7; tgt = Vector((0, 0, 1.08))
if CAM == "hand": dist, tgt, cam_d.lens = 1.6, Vector((0.43, -0.1, float(args.get("tz", "0.3")))), 70
if CAM == "side": a = 0.0
cam.location = (-dist * math.cos(a), -dist * math.sin(a), 0.85 if CAM != "hand" else tgt.z + 0.3)
if CAM == "hand": cam.location = (dist * 0.8, -dist * 0.6, tgt.z + 0.35)
cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (tgt - cam.location).to_track_quat("-Z", "Y")
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.render.resolution_x = int(RES * 9 / 16) // 2 * 2; sc.render.resolution_y = RES; sc.render.fps = 30
sc.view_settings.view_transform = "AgX"; sc.view_settings.exposure = -0.6
try: sc.view_settings.look = "AgX - Medium High Contrast"
except Exception: pass
sc.render.image_settings.file_format = "PNG"; sc.frame_start, sc.frame_end = 1, T
frames = range(1, T + 1) if FRAMES == "all" else [int(x) for x in FRAMES.split(",")] if "," in FRAMES or "-" not in FRAMES else range(int(FRAMES.split("-")[0]), int(FRAMES.split("-")[1]) + 1)
for f in frames:
    t = time.time(); sc.frame_set(f, subframe=SUB); sc.render.filepath = f"{OUT}{f:04d}.png"
    bpy.ops.render.render(write_still=True); print("frame", f, round(time.time() - t, 1), "s", flush=True)
