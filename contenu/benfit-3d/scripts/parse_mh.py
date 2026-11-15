import json, sys
src, out = sys.argv[1], sys.argv[2]
V = []; faces = []; groups = {}; g = None
for line in open(src):
    if line.startswith("v "):
        x, y, z = map(float, line.split()[1:4]); V.append((x, -z, y))  # Y-up -> Z-up, faces -Y
    elif line.startswith("g "):
        g = line.split()[1]
    elif line.startswith("f "):
        idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
        groups.setdefault(g, []).append(idx)
body = groups["body"]
used = sorted({i for f in body for i in f}); remap = {i: k for k, i in enumerate(used)}
bv = [V[i] for i in used]
zmin = min(v[2] for v in bv); zmax = max(v[2] for v in bv); s = 1.78 / (zmax - zmin)
T = lambda v: [round(v[0] * s, 5), round(v[1] * s, 5), round((v[2] - zmin) * s, 5)]
joints = {}
for name, fs in groups.items():
    if name.startswith("joint-"):
        ids = {i for f in fs for i in f}
        c = [sum(V[i][k] for i in ids) / len(ids) for k in range(3)]
        joints[name[6:]] = T(c)
json.dump({"verts": [T(v) for v in bv], "faces": [[remap[i] for i in f] for f in body], "joints": joints}, open(out, "w"))
print(len(bv), len(body), "scale", s)
for k in ["pelvis","spine-1","spine-2","spine-3","spine-4","neck","head","head-2","l-clavicle","l-scapula","l-shoulder","l-elbow","l-hand","l-hand-2","l-hand-3","l-finger-1-1","l-finger-1-2","l-finger-1-4","l-finger-2-1","l-finger-2-2","l-finger-2-3","l-finger-2-4","l-finger-5-1","l-finger-5-2","l-finger-5-4","l-upper-leg","l-knee","l-ankle","l-foot-1","l-foot-2","l-toe-1-1","ground"]:
    print(k, joints[k])
