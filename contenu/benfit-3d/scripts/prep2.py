"""Reduce the mocap track to clean sagittal signals scaled to the mesh (symmetric lift)."""
import json, sys, numpy as np
from scipy.ndimage import gaussian_filter1d as gf
P = np.array(json.load(open(sys.argv[1]))["P"]); out = sys.argv[2]
LEG = 0.450 + 0.408
T = len(P)
def mid(a, b): return (P[:, a] + P[:, b]) / 2
def L(a, b): return np.linalg.norm(P[:, a] - P[:, b], axis=1)
leg_m = np.median((L(23, 25) + L(25, 27) + L(24, 26) + L(26, 28)) / 2)
r = LEG / leg_m
ank = mid(27, 28); hip = mid(23, 24); sh = mid(11, 12); ear = mid(7, 8)
S = lambda a, s=1.5: gf(a, s, axis=0, mode="nearest")
hip_rel = S((hip - ank)[:, 1:] * r)
tr = S(sh - hip)[:, 1:]; trunk = np.arctan2(-tr[:, 0], tr[:, 1])          # lean forward (toward -Y) positive
hd = S(ear - sh, 2.5)[:, 1:]; head = np.arctan2(-hd[:, 0], hd[:, 1])
fore = ((P[:, 15] - P[:, 13]) + (P[:, 16] - P[:, 14])) / 2
fore /= np.linalg.norm(fore, axis=1, keepdims=True)
grip = mid(15, 16) + fore * (0.085 / r)
bar = S((grip - ank)[:, 1:] * r, 1.2)
# heel raise
def raise_(h, t):
    v = P[:, h] - P[:, t]; return np.degrees(np.arctan2(v[:, 2], np.linalg.norm(v[:, :2], axis=1)))
hr = (raise_(29, 31) + raise_(30, 32)) / 2; hr = S(hr - np.median(hr[:15]), 1.2)
hr = np.clip(np.where(hr < 4, 0, hr - 4), 0, 35); hr = S(hr, 1.0)
fw = S(np.abs(P[:, 27, 0] - P[:, 28, 0]) / 2 * r, 4)
ww = np.abs(P[:, 15, 0] - P[:, 16, 0]) / 2 * r
json.dump(dict(r=r, hip=hip_rel.tolist(), trunk=trunk.tolist(), head=head.tolist(), bar=bar.tolist(),
               heel=np.radians(hr).tolist(), fw=fw.tolist()), open(out, "w"))
print("ratio", round(r, 3), "leg_m", round(leg_m, 3))
for t in range(0, T, 8):
    print(t, "hip", hip_rel[t].round(2), "trunk", round(np.degrees(trunk[t])), "head", round(np.degrees(head[t])), "bar", bar[t].round(2), "heel", round(hr[t]), "fw", round(fw[t], 2), "ww", round(ww[t], 2), "ankz", round(ank[t, 2], 2))
