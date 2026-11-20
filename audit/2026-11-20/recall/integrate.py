#!/usr/bin/env python3
"""Add the second-snowball papers the Claude pre-screen kept (yes/maybe, after the second look at flagged "no"s)
to data/<H>/candidates.jsonl and data/<H>/screened.jsonl, so fetch.py / extract.py / referee.py treat them like
any other screened paper. Appends only; a PMID already present is skipped. Originals are copied to backup_<H>_*.
Note: search.py rewrites candidates.jsonl and screen.py re-screens it; a fresh search drops these records.
Usage: integrate.py [--write]"""
import json, glob, pathlib, sys, shutil
D = pathlib.Path(__file__).resolve().parent
ROOT = next(p for p in D.parents if (p / "config").is_dir())  # repo root
SCREEN_MODEL = {"first": "claude-sonnet-5-5 (pre-screen, runs/recall_1120)", "second": "claude-opus-5-5 (second look, runs/recall_1120)"}
items, dec = {}, {}
for f in glob.glob(str(D / "screen_H*_*.json")):
    pk = json.load(open(f))
    for it in pk["items"]:
        items[it["id"]] = (pk["hyp"], it)
for f in glob.glob(str(D / "screened_H*_*.json")):
    for d in json.load(open(f)):
        dec[d["id"]] = (d, "first")
sl = D / "second_look.json"
if sl.exists():
    for d in json.load(open(sl)):
        dec[d["id"]] = (d, "second")
recs = {}
for f in glob.glob(str(D / "new_H*.jsonl")):
    H = pathlib.Path(f).stem.split("_")[1]
    for l in open(f):
        r = json.loads(l)
        recs[(H, r["pmid"])] = r
# papers the second look found closer to another hypothesis: also offered to that one (it decides at extraction)
CROSS = {"H2-0-7": "H5", "H4-2-194": "H3"}
add = {}
for i, to in CROSS.items():
    H0, it = items[i]
    d, who = dec[i]
    if d["decision"] == "no" or True:
        r = recs[(H0, it["pmid"])]
        add.setdefault(to, []).append((r, {**d, "decision": "maybe", "id": i + "x" + to,
                                           "why": f"second look: fits {to} better than {H0}"}, "second"))
for i, (d, who) in dec.items():
    if d["decision"] not in ("yes", "maybe"):
        continue
    H, it = items[i]
    add.setdefault(H, []).append((recs[(H, it["pmid"])], d, who))
for H in sorted(add):
    have = {str(json.loads(l).get("pmid")) for l in open(ROOT / f"data/{H}/candidates.jsonl")}
    rows = [x for x in add[H] if str(x[0]["pmid"]) not in have]
    print(H, "kept", len(add[H]), "new to candidates", len(rows))
    if "--write" not in sys.argv:
        continue
    for name in ("candidates.jsonl", "screened.jsonl"):
        shutil.copy(ROOT / f"data/{H}/{name}", D / f"backup_{H}_{name}")
    with open(ROOT / f"data/{H}/candidates.jsonl", "a") as c, open(ROOT / f"data/{H}/screened.jsonl", "a") as s:
        for r, d, who in rows:
            base = {k: v for k, v in r.items() if k != "seeds"}
            base["routes"] = ["snowball2:references/citations of sheet papers (" + ",".join(r["seeds"][:5]) + ")"]
            c.write(json.dumps(base, ensure_ascii=False) + "\n")
            sid = "s2_" + d["id"]
            s.write(json.dumps({**base, "sid": sid, "screen": {**{k: d.get(k) for k in ("decision", "relevance", "primary_data", "why")}, "id": sid},
                                "screen_model": SCREEN_MODEL[who]}, ensure_ascii=False) + "\n")
