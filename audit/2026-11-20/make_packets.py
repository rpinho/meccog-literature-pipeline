#!/usr/bin/env python3
"""Audit packets for rows not yet audited: every row of a new sheet, or rows of a rebuilt sheet that are new
or whose values changed since the audited (live) version. Usage: make_packets.py H5 [H2:live.xlsx ...]"""
import openpyxl, json, glob, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
D = pathlib.Path(__file__).resolve().parent
doi_key = {}
for p in glob.glob(str(ROOT / "data/papers/*/meta.json")):
    m = json.load(open(p))
    if m.get("doi"):
        doi_key[m["doi"].lower()] = m["key"]
VALS = ("Finding quote", "Finding summary", "Data location", "Effect size", "Effect size provenance", "P value",
        "P value provenance", "Sample size", "Sample size provenance")
def read(path):
    ws = openpyxl.load_workbook(path)["Submission"]
    rows = list(ws.iter_rows(values_only=True)); cols = rows[0]; out = []; cur = None
    for r in rows[2:]:
        if r[1]:
            cur = {"paper_id": r[4], "doi": r[1], "rows": []}; out.append(cur)
        elif r[4]:
            cur["rows"].append({c: v for c, v in zip(cols[4:], r[4:])})
    return rows[1][0], out
prefix = "packet_"
args = sys.argv[1:]
if args and args[0].startswith("--prefix="):
    prefix = args.pop(0).split("=", 1)[1]
groups = []
for arg in args:
    H, _, live = arg.partition(":")
    hyp, papers = read(ROOT / f"submissions/{H}.xlsx")
    seen = set()
    if live:
        _, lp = read(live)
        seen = {(p["doi"], tuple(str(r.get(k)) for k in VALS)) for p in lp for r in p["rows"]}
    for p in papers:
        rows = [r for r in p["rows"] if (p["doi"], tuple(str(r.get(k)) for k in VALS)) not in seen]
        if not rows:
            continue
        key = doi_key[str(p["doi"]).lower()]; d = ROOT / "data/papers" / key
        groups.append({"hyp": H, "hypothesis": hyp, "paper_id": p["paper_id"], "key": key, "doi": p["doi"],
                       "text": str((d / "text.txt").resolve()) if (d / "text.txt").exists() else None,
                       "supp": str((d / "supp.txt").resolve()) if (d / "supp.txt").exists() and (d / "supp.txt").stat().st_size else None,
                       "figures": sorted(str(x.resolve()) for x in (d / "figimg").glob("*.png")) if (d / "figimg").exists() else [],
                       "pdf": str((d / "fulltext.pdf").resolve()) if (d / "fulltext.pdf").exists() else None, "rows": rows})
groups.sort(key=lambda g: -len(g["rows"]))
total = sum(len(g["rows"]) for g in groups); N = max(1, round(total / 45))
packs = [[] for _ in range(N)]; load = [0] * N
for g in groups:
    i = load.index(min(load)); packs[i].append(g); load[i] += len(g["rows"])
for i, p in enumerate(packs):
    json.dump(p, open(D / f"{prefix}{i}.json", "w"), indent=1, ensure_ascii=False, default=str)
print("rows", total, "packets", load)
