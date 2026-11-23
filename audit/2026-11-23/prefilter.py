#!/usr/bin/env python3
"""No model. Narrow new_<H>.jsonl to records worth a screen: not a review; title/abstract name an APOE isoform;
and the hypothesis's own readout terms appear. Writes pre_<H>.jsonl. Across hypotheses a paper is screened once per H."""
import json, re, glob, collections
ISO = re.compile(r"apo\s*e\s*-?\s*(?:ε|e|epsilon)?\s*4|apoe4|apoe3|apoe isoform|apolipoprotein e4|apolipoprotein e isoform|ε4|epsilon ?4", re.I)
TERMS = {"H1": r"endosom\w*|endolysosom\w*|\bph\b|acidif\w*|alkalin\w*|nhe6|nhe9|slc9a",
         "H2": r"recycl\w*|arf6|endocyt\w*|endosom\w*|rab11|abca1|surface",
         "H3": r"aggregat\w*|oligomer\w*|molten|domain interaction|lysosom\w*|endolysosom\w*",
         "H4": r"lrp1|ldlr|apoer2|lrp8|vldlr|heparan|receptor binding|affinity|recycl\w*",
         "H5": r"lysosom\w*|late endosom\w*|endolysosom\w*|lipid droplet\w*|cholesterol|sphingolipid\w*|npc1"}
tot = {}
for H, t in TERMS.items():
    R = [json.loads(l) for l in open(f"new_{H}.jsonl")]
    keep = []
    for r in R:
        txt = re.sub("<[^>]+>", " ", f"{r.get('title') or ''} {r.get('abstract') or ''}")
        if any("review" in str(p).lower() for p in r.get("pubtype") or []) or re.search(r"\breview\b", r.get("title") or "", re.I):
            continue
        if ISO.search(txt) and len(re.findall(t, txt, re.I)) >= 2:
            keep.append(r)
    with open(f"pre_{H}.jsonl", "w") as f:
        for r in keep: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tot[H] = (len(R), len(keep), dict(collections.Counter(r["route"].split(":")[0] for r in keep)))
    print(H, "new", len(R), "kept", len(keep), tot[H][2])
    for r in keep: print("   ", r.get("pmid") or r.get("doi"), r.get("year"), (r.get("title") or "")[:100])
