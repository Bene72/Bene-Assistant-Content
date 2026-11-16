"""Mots sur la timeline montée, découpage des sous-titres et mots-clés — Reel « Cardio et perte de muscle »."""
import json, re, sys
sys.path.insert(0, "/home/claude/work")
import edl_cardio as edl

D = json.load(open("/home/claude/work/timeline_out.json"))
TL, TOTAL, SPEED = D["timeline"], D["total"], D["speed"]
for c in TL:
    c["dur"] = (c["src_out"] - c["src_in"]) / SPEED
    c["end"] = c["start"] + c["dur"]

def tag_range(*tags):
    cs = [c for c in TL if c["tag"] in tags]
    return min(c["start"] for c in cs), max(c["end"] for c in cs)

def cut_at(t):
    for c in TL:
        if c["start"] <= t < c["end"]: return c
    return TL[-1]

# corrections d'orthographe / erreurs de transcription (le sens n'est jamais modifié)
FIX = {"apport": "apports", "glucide": "glucides", "glucide,": "glucides,", "And": "Et", "function": "fonctionne",
       "principally": "principalement", "with...": "avec", "devoir...": "devoir", "lipolyse,": "lipolyse.",
       "tout.": "tout", "assez.": "assez", "grasses.": "grasses.", "ben": "ben"}
TAGFIX = {("hook", "musculaire."): "musculaire ?", ("non", "non"): "non !", ("B2", "musculaire"): "musculaire.",
          ("B5", "un"): "ingurgiter", ("B6", "d'équilibre,"): "d'équilibre.", ("D1", "intensité"): "intensité",
          ("D3", "surentraînement,"): "surentraînement.", ("E2", "manger."): "manger,", ("B0", "cas,"): "cas :",
          ("A1", "muscle,"): "muscle,", ("D2", "lundi,"): "lundi,", ("B3", "haut,"): "haut,", ("A2", "apports."): "apports"}
DROP = {("hook", "?"), ("non", "!"), ("B5", "gur"), ("B5", "JT,")}

WORDS = []
for k, c in enumerate(TL):
    if c.get("mute"): continue
    nxt = TL[k + 1] if k + 1 < len(TL) else None
    same = nxt is not None and nxt["tag"] == c["tag"]
    for w, on, last in edl.WORDS[c["file"]]:
        if (c["tag"], w) in DROP: continue
        txt = TAGFIX.get((c["tag"], w), FIX.get(w, w))
        if same and c["src_out"] - 0.04 <= on < nxt["src_in"] - 0.06:
            WORDS.append(dict(w=txt, t=round(nxt["start"], 3), te=round(nxt["start"] + 0.3, 3), tag=c["tag"], ch=c["chapter"]))
            continue
        if c["src_in"] - 0.06 <= on < c["src_out"] - 0.04:
            t = c["start"] + max(0, on - c["src_in"]) / SPEED
            te = c["start"] + (min(last + 0.25, c["src_out"]) - c["src_in"]) / SPEED
            WORDS.append(dict(w=txt, t=round(t, 3), te=round(max(te, t + 0.12), 3), tag=c["tag"], ch=c["chapter"]))
WORDS.sort(key=lambda w: w["t"])

KEYS = [["muscle"], ["non"], ["volume"], ["apports"], ["fondre"], ["haute", "intensité"], ["glucides"],
        ["fonte", "musculaire"], ["protéines"], ["50", "g"], ["déquilibre"], ["basse", "intensité"], ["lipolyse"],
        ["matières", "grasses"], ["muscles"], ["blessure"], ["surentraînement"], ["musculation"],
        ["dormir"], ["manger"], ["shydrater"], ["intelligemment"], ["programme", "adapté"]]
norm = lambda s: re.sub(r"[^\wÀ-ÿ×]", "", s.lower())
toks = [norm(w["w"]) for w in WORDS]
for w in WORDS: w["key"] = False
for k in sorted(KEYS, key=len, reverse=True):
    for i in range(len(toks) - len(k) + 1):
        if toks[i:i + len(k)] == k and not any(WORDS[i + j]["key"] for j in range(len(k))):
            for j in range(len(k)): WORDS[i + j]["key"] = True
for w in WORDS:
    if w["tag"] == "B3" and norm(w["w"]) == "apports": w["key"] = False
# un seul surlignage par expression répétée de suite : "haute intensité" reste surligné, c'est le cœur du sujet

KINETIC = {"hook"}
CHUNKS, cur = [], []
def flush():
    global cur
    if cur: CHUNKS.append(cur); cur = []
prev_tag = None
for w in WORDS:
    if w["tag"] in KINETIC: continue
    grp = re.sub(r"[ab]$", "", w["tag"])
    nchar = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
    gap = w["t"] - cur[-1]["te"] if cur else 0
    if cur and (nchar > 20 or gap > 0.75 or grp != prev_tag):
        flush()
    cur.append(w); prev_tag = grp
    if re.search(r"[.,?!:]$", w["w"]) and sum(len(x["w"]) + 1 for x in cur) > 9: flush()
flush()
merged = []
for ch in CHUNKS:
    if merged and len(ch) == 1 and len(ch[0]["w"]) <= 4 and ch[0]["t"] - merged[-1][-1]["te"] < 0.3 \
            and sum(len(x["w"]) + 1 for x in merged[-1]) < 24 and not re.search(r"[.?!]$", merged[-1][-1]["w"]):
        merged[-1] += ch
    else:
        merged.append(ch)
CHUNKS = merged
sent_start = True
for ch in CHUNKS:
    for w in ch:
        if sent_start and w["w"][0].isalpha(): w["w"] = w["w"][0].upper() + w["w"][1:]
        sent_start = bool(re.search(r"[.?!]$", w["w"]))
SUBS = []
for i, ch in enumerate(CHUNKS):
    t0 = ch[0]["t"] - 0.06
    nxt = CHUNKS[i + 1][0]["t"] - 0.06 if i + 1 < len(CHUNKS) else ch[-1]["te"] + 0.5
    t1 = min(nxt, ch[-1]["te"] + 0.55)
    SUBS.append(dict(t0=t0, t1=t1, words=ch))

if __name__ == "__main__":
    print("total", TOTAL)
    for s in SUBS:
        print(f"{s['t0']:6.2f}-{s['t1']:6.2f} {s['words'][0]['tag']:4s}", " ".join(("[" + w["w"] + "]") if w["key"] else w["w"] for w in s["words"]))
    print([(w["w"], w["t"]) for w in WORDS if w["tag"] == "hook"])
