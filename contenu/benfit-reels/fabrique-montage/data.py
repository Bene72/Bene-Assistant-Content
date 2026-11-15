"""Words on the output timeline, subtitle chunks and keyword marks."""
import json, re, sys
sys.path.insert(0, "/home/claude/work")
import edl

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

FIX = {"ferai": "ferais", "bénet,": "Bene,", "donnerai": "donnerais", "ou...": "ou", "tissulaire": "tissulaires",
       "tendineuse": "tendineuses", "adaptations.": "adaptations", "commencerai": "commencerais",
       "movement": "mouvement", "d'où": "ou", "x": "×", "intensité,": "intensité,", "maximaux": "maximaux.",
       "lever": "lever", "rien": "rien.", "blessure": "blessure", "spécifiques,": "spécifiques.",
       "l'haltérophilie,": "l'haltérophilie.", "séance.": "séance,", "Mais": "mais", "Travailler": "travailler"}
TAGFIX = {("B6", "blessure"): "blessures.", ("C4", "km."): "km."}

# words
WORDS = []
for k, c in enumerate(TL):
    if c.get("mute"): continue
    nxt = TL[k + 1] if k + 1 < len(TL) else None
    same = nxt is not None and nxt["tag"] == c["tag"]
    for w, on, last in edl.WORDS[c["file"]]:
        if same and c["src_out"] - 0.04 <= on < nxt["src_in"] - 0.06:
            WORDS.append(dict(w=TAGFIX.get((c["tag"], w), FIX.get(w, w)), t=round(nxt["start"], 3), te=round(nxt["start"] + 0.3, 3), tag=c["tag"], ch=c["chapter"]))
            continue
        if c["src_in"] - 0.06 <= on < c["src_out"] - 0.04:
            txt = TAGFIX.get((c["tag"], w), FIX.get(w, w))
            t = c["start"] + max(0, on - c["src_in"]) / SPEED
            te = c["start"] + min(last + 0.25, c["src_out"]) / SPEED - c["src_in"] / SPEED
            WORDS.append(dict(w=txt, t=round(t, 3), te=round(max(te, t + 0.12), 3), tag=c["tag"], ch=c["chapter"]))
# dedupe the repeated "une" in D3
DROP = {("D3a", "une"), ("C3a", "on"), ("E8b", "et")}
WORDS = [w for w in WORDS if (w["tag"], w["w"]) not in DROP]
WORDS.sort(key=lambda w: w["t"])

KEYS = [["recommencer"], ["performer"], ["musculation"], ["masse", "musculaire"], ["tissulaires"], ["tendineuses"],
        ["blessures"], ["blessure"], ["cardio"], ["cardiovasculaires"], ["zone", "2"], ["récupération"], ["volume"],
        ["5", "km"], ["10"], ["bases"], ["haute", "intensité"], ["efforts", "maximaux"], ["barre", "lourde"],
        ["explosif"], ["l'haltérophilie"], ["mobilité"], ["souplesse"], ["séances", "spécifiques"],
        ["20", "minutes"], ["10", "minutes"], ["squat"], ["force"], ["intensité"], ["abonner"]]
norm = lambda s: re.sub(r"[^\wÀ-ÿ'×]", "", s.lower()).replace("t'abonner", "abonner")
toks = [norm(w["w"]) for w in WORDS]
for w in WORDS: w["key"] = False
for k in sorted(KEYS, key=len, reverse=True):
    for i in range(len(toks) - len(k) + 1):
        if toks[i:i + len(k)] == k and not any(WORDS[i + j]["key"] for j in range(len(k))):
            for j in range(len(k)): WORDS[i + j]["key"] = True

# chunks (hook + end handled by kinetic typography)
KINETIC = {"hook"}
CHUNKS = []
cur = []
def flush():
    global cur
    if cur: CHUNKS.append(cur); cur = []
prev_tag = None
for i, w in enumerate(WORDS):
    if w["tag"] in KINETIC: continue
    grp = re.sub(r"[ab]$", "", w["tag"])
    nchar = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
    gap = w["t"] - cur[-1]["te"] if cur else 0
    if cur and (nchar > 20 or gap > 0.75 or grp != prev_tag):
        flush()
    cur.append(w); prev_tag = grp
    if re.search(r"[.,?!:]$", w["w"]) and sum(len(x["w"]) + 1 for x in cur) > 9: flush()
flush()
# merge orphan single short words into previous chunk when tight
merged = []
for ch in CHUNKS:
    if merged and len(ch) == 1 and len(ch[0]["w"]) <= 4 and ch[0]["t"] - merged[-1][-1]["te"] < 0.3 \
            and sum(len(x["w"]) + 1 for x in merged[-1]) < 24 and not re.search(r"[.?!]$", merged[-1][-1]["w"]):
        merged[-1] += ch
    else:
        merged.append(ch)
CHUNKS = merged
# sentence-case
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
        print(f"{s['t0']:6.2f}-{s['t1']:6.2f} ", " ".join(("[" + w["w"] + "]") if w["key"] else w["w"] for w in s["words"]))
    print([ (w["w"], w["t"]) for w in WORDS if w["tag"] == "hook"])
