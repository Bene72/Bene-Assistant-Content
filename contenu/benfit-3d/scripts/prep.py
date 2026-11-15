"""Convert MediaPipe world landmarks into Blender-space joint tracks (Z up, metres)."""
import sys, json, numpy as np
from scipy.ndimage import gaussian_filter1d

src, out, f0, f1, hold = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
d = json.load(open(src))
W = np.array([f["world"] for f in d["frames"]], dtype=float)[f0:f1 + 1, :, :3]  # T,33,3
# MediaPipe world: x right, y down, z toward camera negative. Blender: X, Y depth, Z up
P = np.stack([W[..., 0], W[..., 2], -W[..., 1]], axis=-1)
P = gaussian_filter1d(P, sigma=1.2, axis=0, mode="nearest")

# Orient: average hip lateral axis -> +X
lat = (P[:, 24] - P[:, 23]).mean(0); lat[2] = 0; lat /= np.linalg.norm(lat)
ang = -np.arctan2(lat[1], lat[0])
R = np.array([[np.cos(ang), -np.sin(ang), 0], [np.sin(ang), np.cos(ang), 0], [0, 0, 1]])
P = P @ R.T
# facing: nose relative to hip mid at frame 0, want facing -Y
hipmid = (P[:, 23] + P[:, 24]) / 2
face = (P[0, 0] - hipmid[0])[1]
if face > 0:  # rotate 180
    P[..., 0] *= -1; P[..., 1] *= -1

# Root: anchor ankle midpoint horizontally, lowest foot point on floor
ank = (P[:, 27] + P[:, 28]) / 2
P[..., 0] -= ank[:, None, 0]; P[..., 1] -= ank[:, None, 1]
feet = P[:, [27, 28, 29, 30, 31, 32]]
low = gaussian_filter1d(feet[..., 2].min(1), 1.0)
P[..., 2] -= low[:, None] - 0.04  # ankle/heel landmarks sit slightly above sole

if hold > 0:
    P = np.concatenate([P, np.repeat(P[-1:], hold, 0)], 0)
json.dump({"fps": d["fps"], "P": P.round(4).tolist()}, open(out, "w"))
print("frames", len(P), "height range", P[..., 2].min().round(2), P[..., 2].max().round(2))
