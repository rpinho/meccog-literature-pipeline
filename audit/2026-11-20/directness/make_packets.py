#!/usr/bin/env python3
"""Directness packets (stage 4) for rows the 11-19 pass never scored: rows of the current sheets whose
(DOI, quote start, summary) is not in any audit/2026-11-19/directness packet. Each packet also carries the scored rows of
that hypothesis as `reference_rows` (final values in the current sheet), so new rows get the same class and
strength as earlier rows that measure the same thing the same way. Usage: make_packets.py H1 H3 H4 H5"""
import openpyxl, json, glob, pathlib, sys
D = pathlib.Path(__file__).resolve().parent
ROOT = next(p for p in D.parents if (p / "config").is_dir())  # repo root
V = json.load(open(ROOT / "config/variables.json"))
def read(path):
    ws = openpyxl.load_workbook(path)["Submission"]
    rows = list(ws.iter_rows(values_only=True)); cols = rows[0]; out = []; cur = None
    for r in rows[2:]:
        if r[1]:
            cur = {"paper_id": r[4], "doi": r[1], "rows": []}; out.append(cur)
        elif r[4]:
            cur["rows"].append({c: v for c, v in zip(cols[4:], r[4:])})
    return rows[1][0], out
sig = lambda doi, r: (str(doi).lower(), str(r["Finding quote"])[:70], str(r["Finding summary"]).strip())
scored = set()
for p in glob.glob(str(ROOT / "audit/2026-11-19/directness/packet_H*.json")):
    for paper in json.load(open(p))["papers"]:
        for r in paper["rows"]:
            scored.add(sig(paper["doi"], r))
KEEP = ("Paper/Finding ID", "Finding description", "Finding quote", "Finding summary", "Experimental system",
        "Data location", "Directness class", "Directness strength")
for H in sys.argv[1:]:
    hyp, papers = read(ROOT / f"submissions/{H}.xlsx")
    new, ref = [], []
    for p in papers:
        rows = [{k: r.get(k) for k in KEEP} for r in p["rows"] if sig(p["doi"], r) not in scored]
        if rows:
            new.append({"paper_id": p["paper_id"], "doi": p["doi"], "rows": rows})
        ref += [{"finding_id": r["Paper/Finding ID"], "summary": r["Finding summary"],
                 "system": str(r["Experimental system"])[:160], "class": r["Directness class"],
                 "strength": r["Directness strength"]} for r in p["rows"] if sig(p["doi"], r) in scored]
    n = sum(len(p["rows"]) for p in new)
    # about 45 rows per packet, whole papers only
    k = max(1, round(n / 45)); packs = [[] for _ in range(k)]; load = [0] * k
    for p in sorted(new, key=lambda p: -len(p["rows"])):
        i = load.index(min(load)); packs[i].append(p); load[i] += len(p["rows"])
    for i, pk in enumerate(packs):
        json.dump({"hyp": H, "hypothesis": hyp, **V[H], "papers": pk, "reference_rows": ref},
                  open(D / f"packet_{H}_{i}.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(H, "unscored rows", n, "packets", load, "reference rows", len(ref))
