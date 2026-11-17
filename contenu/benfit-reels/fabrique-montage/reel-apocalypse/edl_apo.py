"""Reel BEN&FIT x Apocalypse Training — liste de montage (reel d'entraînement, sans parole).
Chaque plan : rush, entrée, sortie (s, temps source), vitesse, zoom (punch-in), section."""
import json

RUSH = "/home/claude/rushs/a_{}.mp4"  # ids complets
# rushs : 758653973 tractions · 656280 / 660244 wall walk + handstand · 649051 KB press + rowing · 645847 complexe disques
EDL = [
    # accroche : handstand tenu, plan large (le sol reste libre pour le titre)
    ("758660244", 30.00, 32.60, 1.00, 1.00, "hook"),
    # 01 strict pull-ups + butterfly chest to bar
    ("758653973", 6.00, 7.80, 1.00, 1.00, "pull"),
    ("758653973", 24.00, 25.80, 1.00, 1.08, "pull"),
    ("758653973", 25.80, 26.60, 0.50, 1.12, "pull"),      # ralenti butterfly
    ("758653973", 29.80, 30.60, 1.00, 1.00, "pull"),
    ("758653973", 31.50, 33.00, 1.00, 1.12, "pull_r"),    # réaction
    # 02 wall walks + wall facing HSPU
    ("758656280", 16.30, 18.30, 1.00, 1.00, "hspu"),
    ("758656280", 19.60, 21.10, 1.40, 1.00, "hspu"),
    ("758656280", 46.10, 47.40, 1.00, 1.05, "hspu"),
    ("758656280", 47.80, 49.30, 1.00, 1.15, "hspu_r"),    # réaction (souffle)
    # 03 superset KB push press + gorilla row (lumière retravaillée)
    ("758649051", 8.20, 9.70, 1.30, 1.00, "kb"),
    ("758649051", 10.40, 12.00, 1.00, 1.08, "kb"),
    ("758649051", 18.40, 19.30, 0.50, 1.15, "kb"),        # ralenti verrouillage
    ("758649051", 21.90, 23.40, 1.20, 1.00, "kb"),
    ("758649051", 31.80, 33.40, 1.00, 1.10, "row"),
    ("758649051", 44.40, 46.40, 1.25, 1.18, "row"),
    # 04 complexe épaules (poids noirs)
    ("759226351", 22.00, 23.70, 1.00, 1.00, "plate"),
    ("759226351", 26.20, 27.90, 1.10, 1.08, "plate"),
    ("759226351", 33.30, 34.80, 1.00, 1.00, "plate"),
    ("759226351", 36.90, 38.60, 1.10, 1.06, "plate"),
    ("759226351", 39.60, 40.50, 0.50, 1.00, "end"),
]

tl, t = [], 0.0
for f, a, b, sp, z, sec in EDL:
    d = (b - a) / sp
    tl.append(dict(file=f, src_in=a, src_out=b, speed=sp, zoom=z, sec=sec, start=round(t, 4), dur=round(d, 4)))
    t += d
json.dump({"timeline": tl, "total": t}, open("/home/claude/work/apo/timeline.json", "w"), indent=1)
print(f"{len(tl)} plans, {t:.2f} s")
