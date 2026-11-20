#!/usr/bin/env python3
"""Turn the Codex audit of the recall-round rows (codex_result_a.json, codex_result_b.json) into config/corrections.json entries:
value fixes as stage 3 ("Codex audit 11-20b"), directness as stage 4 ("Directness 11-20b"). Single audit, not
verified by a second model (lane budget, general 11-20); every corrected row still goes through the code checks.
Usage: codex_apply.py [--write]"""
import json, glob, sys, pathlib, re, collections
D = pathlib.Path(__file__).resolve().parent
ROOT = D.parents[1]
COL = {"Finding description": "description", "Finding quote": "quote", "Finding summary": "summary",
       "Finding relevance": "relevance", "Experimental system": "system", "Data location": "data_location",
       "Effect size": "effect_size", "Effect size provenance": "effect_size_provenance", "P value": "p_value",
       "P value provenance": "p_value_provenance", "Sample size": "sample_size",
       "Sample size provenance": "sample_size_provenance"}
rows = {}
for pk in ("packet7_a.json", "packet7_b.json"):
    for g in json.load(open(D / pk)):
        for r in g["rows"]:
            rows[(g["key"], r["Paper/Finding ID"], str(r["Finding quote"])[:40])] = (g, r)
# reviewer decisions on top of the audit: (hyp, finding id) -> columns not applied, and why
OVERRIDES = {("H3", "P18.F12"): (["Effect size", "Effect size provenance"],
                                 "a ratio of fitted species counts (6/6) is not an effect size")}
new, n = [], collections.Counter()
for rp in ("codex_result_a.json", "codex_result_b.json"):
    if not (D / rp).exists():
        continue
    for a in json.load(open(D / rp)):
        hit = [v for k, v in rows.items() if k[0] == a.get("key") and k[1] == a.get("finding_id")
               and str(a.get("quote_start", ""))[:40] == k[2]] or \
              [v for k, v in rows.items() if k[0] == a.get("key") and k[1] == a.get("finding_id")]
        if len(hit) != 1:
            n["unmatched"] += 1
            continue
        g, r = hit[0]
        n[a.get("verdict")] += 1
        base = {"key": g["key"], "hyp": g["hyp"], "quote_start": str(r["Finding quote"])[:70],
                "summary_contains": str(r["Finding summary"]), "description_start": str(r["Finding description"])[:60],
                "source": a.get("evidence", "")}
        s = {}
        o = OVERRIDES.get((g["hyp"], a.get("finding_id")))
        for col, val in (a.get("set") or {}).items():
            if o and col in o[0]:
                continue
            k = COL.get(col)
            if not k:
                continue
            if k == "effect_size":
                val = re.sub(r"^(~?)([A-Za-z]+)_([A-Za-z]+)=", r"\1\3=", str(val))
            s[k] = val
        if a.get("verdict") == "DROP":
            new.append({**base, "stage": 3, "set": {}, "drop": True,
                        "reason": f"Codex audit 11-20b (gpt-6.2-astra, {g['hyp']} {a['finding_id']}): {a.get('reason')}"})
        elif a.get("verdict") == "FIX" and s:
            new.append({**base, "stage": 3, "set": s,
                        "reason": f"Codex audit 11-20b (gpt-6.2-astra, {g['hyp']} {a['finding_id']}): {a.get('reason')}"})
        dn = a.get("directness") or {}
        if dn.get("class"):
            cls, st = int(dn["class"]), str(dn.get("strength", r["Directness strength"]))[0]
            if cls == 1:
                st = "1"
            ds = {}
            if cls != int(r["Directness class"]) or st != str(r["Directness strength"])[0]:
                ds = {"directness_class": cls, "directness_strength": st}
            desc = s.get("description", r["Finding description"])
            if cls == 5 and "Class 5" not in str(desc):
                ds["description"] = str(desc).rstrip(".") + ". Class 5 (other): " + str(dn.get("reason_for_description") or dn.get("why") or "").strip()
            if ds:
                b4 = dict(base)
                # stage 4 matches the row as stage 3 left it
                if "description" in s:
                    b4["description_start"] = str(s["description"])[:60]
                if "quote" in s:
                    b4["quote_start"] = str(s["quote"])[:70]
                if "summary" in s:
                    b4["summary_contains"] = str(s["summary"])
                new.append({**b4, "stage": 4, "set": ds,
                            "reason": f"Directness 11-20b (Codex gpt-6.2-astra, {g['hyp']} {a['finding_id']}): {dn.get('why')}",
                            "source": "organizers' directness definitions; runs/audit_1120/CONVENTIONS_1120.md"})
                n["directness_changed"] += 1
print(dict(n), "-> corrections", len(new))
if "--write" in sys.argv:
    cf = ROOT / "config/corrections.json"
    d = json.load(open(cf))
    d["corrections"] = [c for c in d["corrections"] if not str(c.get("reason", "")).startswith(("Codex audit 11-20b", "Directness 11-20b"))] + new
    json.dump(d, open(cf, "w"), indent=1, ensure_ascii=False)
