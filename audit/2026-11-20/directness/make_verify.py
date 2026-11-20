#!/usr/bin/env python3
"""Verify packets: every row whose proposed class or strength differs from the sheet, every proposed class 5
(its reason goes into the description), and every proposed class 1 with strength above 1. Usage: make_verify.py [--all=H5]  (--all: every row of that hypothesis, one packet, for a cross-packet consistency check)"""
import json, glob, pathlib, collections, sys
ALL = set(a.split("=",1)[1] for a in sys.argv[1:] if a.startswith("--all="))  # hypotheses verified whole, in one packet
D = pathlib.Path(__file__).resolve().parent
by_h = collections.defaultdict(list); meta = {}
for rp in sorted(glob.glob(str(D / "result_H*_*.json"))):
    name = pathlib.Path(rp).stem.split("_", 1)[1]
    pk = json.load(open(D / f"packet_{name}.json"))
    meta[pk["hyp"]] = {k: pk[k] for k in ("hyp", "hypothesis", "A", "B", "scope", "reference_rows")}
    rows = {(r["Paper/Finding ID"], str(r["Finding quote"])[:70]): (p, r) for p in pk["papers"] for r in p["rows"]}
    for x in json.load(open(rp)):
        p, r = rows[(x["finding_id"], x["quote_start"][:70])]
        diff = int(x["class"]) != int(r["Directness class"]) or str(x["strength"])[0] != str(r["Directness strength"])[0]
        if pk["hyp"] in ALL or diff or int(x["class"]) == 5 or (int(x["class"]) == 1 and str(x["strength"])[0] != "1"):
            by_h[pk["hyp"]].append({"finding_id": x["finding_id"], "paper_doi": p["doi"], "row": r,
                                    "proposed": {**{k: x.get(k) for k in ("class", "strength", "why", "reason_for_description")}, "changed": diff}})
# rows scored on 11-19 that sit at class 1 with strength above 1 (the rule in VERIFY_BRIEF.md) go in too
import openpyxl
ROOT = next(p for p in D.parents if (p / "config").is_dir())  # repo root
for H in list(by_h):
    ws = openpyxl.load_workbook(ROOT / f"submissions/{H}.xlsx")["Submission"]
    rows = list(ws.iter_rows(values_only=True)); cols = rows[0]; doi = None
    have = {(it["paper_doi"], str(it["row"]["Finding quote"])[:70]) for it in by_h[H]}
    for r in rows[2:]:
        if r[1]:
            doi = r[1]; continue
        if r[4] and r[17] == 1 and str(r[18])[0] != "1" and (doi, str(r[6])[:70]) not in have:
            row = {c: v for c, v in zip(cols[4:], r[4:])}
            by_h[H].append({"finding_id": r[4], "paper_doi": doi, "row": row,
                            "proposed": {"class": 1, "strength": str(r[18])[0], "why": "scored 11-19; class 1 with strength above 1, see the class 1 rule"}})
for H, items in by_h.items():
    k = 1 if H in ALL else max(1, round(len(items) / 45))
    for i in range(k):
        part = items[i::k]
        for n, it in enumerate(part, 1):
            it["item"] = n
        json.dump({**meta[H], "items": part}, open(D / f"verify_{H}_{i}.json", "w"), indent=1, ensure_ascii=False, default=str)
        print(H, i, len(part))
