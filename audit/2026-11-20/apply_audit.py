#!/usr/bin/env python3
"""Turn audited AND verified proposals into config/corrections.json entries.
Only CONFIRM (auditor's set) and ADJUST (verifier's set) are applied; REJECT and unverified items are skipped.
Usage: apply_audit.py [--write]"""
import json, glob, sys, pathlib, collections, re
D = pathlib.Path(__file__).resolve().parent
ROOT = D.parents[1]
COL = {"Finding description": "description", "Finding quote": "quote", "Finding summary": "summary",
       "Finding relevance": "relevance", "Experimental system": "system", "Data location": "data_location",
       "Effect size": "effect_size", "Effect size provenance": "effect_size_provenance", "P value": "p_value",
       "P value provenance": "p_value_provenance", "Sample size": "sample_size",
       "Sample size provenance": "sample_size_provenance", "Directness class": "directness_class",
       "Directness strength": "directness_strength"}
# reviewer decisions on top of the verified set: (hyp, finding_id) -> fields to drop from the set / to add, and why
OVERRIDES = {
    ("H5", "P2.F1"): {"unset": ["directness_strength"],
                      "why": "strength 4 not applied: strength says how misleading a surrogate is, not how strong the "
                             "statistics are; class and strength come from the directness pass."},
}
new, n = [], collections.Counter()
for vp in sorted(glob.glob(str(D / "verify_*.json"))):
    name = pathlib.Path(vp).stem.split("_", 1)[1]
    vf = D / f"verified_{name}.json"
    items = json.load(open(vp))
    ver = {v["item"]: v for v in json.load(open(vf))} if vf.exists() else {}
    for it in items:
        v = ver.get(it["item"])
        dec = v["decision"] if v else "UNVERIFIED"
        n[dec] += 1
        if dec not in ("CONFIRM", "ADJUST"):
            continue
        a, r = it["proposal"], it["row"]
        s = (v.get("set") if dec == "ADJUST" else a.get("set")) or {}
        c = {"key": it["paper"]["key"], "hyp": a["hyp"], "stage": 3, "quote_start": str(r["Finding quote"])[:70],
             "summary_contains": str(r["Finding summary"]), "description_start": str(r["Finding description"])[:60], "set": {},
             "reason": f"Claude audit 11-20 ({a['hyp']} {a['finding_id']}), {dec.lower()}ed by a second Claude check: {a['reason']}"
                       + (f" Verifier: {v.get('why')}" if dec == "ADJUST" else ""),
             "source": a.get("evidence", "")}
        for col, val in s.items():
            k = COL.get(col, col)
            if k == "directness_strength":
                val = str(val)[0]
            if k == "effect_size":
                val = re.sub(r"^(~?)([A-Za-z]+)_([A-Za-z]+)=", r"\1\3=", str(val))  # names are letters only: diff_pp=11 -> pp=11
            c["set"][k] = val
        o = OVERRIDES.get((a["hyp"], a["finding_id"]))
        if o:
            for k in o.get("unset", []):
                c["set"].pop(k, None)
            c["set"].update(o.get("set", {}))
            c["reason"] += " Reviewer: " + o["why"]
        if a["verdict"] == "DROP":
            c["drop"] = True
        if c["set"] or c.get("drop"):
            new.append(c)
print(dict(n), "-> corrections", len(new))
if "--write" in sys.argv:
    cf = ROOT / "config/corrections.json"
    d = json.load(open(cf))
    d["corrections"] = [c for c in d["corrections"] if not c["reason"].startswith("Claude audit 11-20")] + new
    json.dump(d, open(cf, "w"), indent=1, ensure_ascii=False)
