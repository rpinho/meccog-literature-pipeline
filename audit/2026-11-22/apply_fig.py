#!/usr/bin/env python3
"""Turn the Claude check of the 11-20 figure-read values (fig_<n>_verified.json) into stage-6 corrections.
CONFIRM: nothing. ADJUST: the checker's values. REVERT: the values before the figure read. A row is corrected only
if its sheet value still equals what the figure read wrote (a later audit may already have replaced it).
Usage: apply_fig.py [--write]"""
import json, glob, sys, pathlib, collections
import openpyxl
D = pathlib.Path(__file__).resolve().parent
ROOT = next(p for p in D.parents if (p / "config").is_dir())  # repo root
COLS = {"effect_size": 11, "effect_size_provenance": 12, "p_value": 13, "p_value_provenance": 14,
        "sample_size": 15, "sample_size_provenance": 16}
meta = {}
for p in glob.glob(str(ROOT / "data/papers/*/meta.json")):
    m = json.load(open(p)); meta[m["key"]] = (m.get("doi") or "").lower()
sheets = {}
def rows(H):
    if H not in sheets:
        out = []; doi = None
        for r in openpyxl.load_workbook(ROOT / f"submissions/{H}.xlsx")["Submission"].iter_rows(min_row=3, values_only=True):
            if r[1]: doi = str(r[1]).lower(); continue
            if r[4]: out.append((doi, r))
        sheets[H] = out
    return sheets[H]
new, n = [], collections.Counter()
for vf in sorted(glob.glob(str(D / "fig_*_verified.json"))):
    items = {(i["key"], i["index"]): i for i in json.load(open(vf.replace("_verified", "")))}
    for v in json.load(open(vf)):
        it = items.get((v["key"], v["index"]))
        n[v["verdict"]] += 1
        if not it or v["verdict"] == "CONFIRM":
            continue
        s = {k: c["before"] for k, c in it["changed"].items()} if v["verdict"] == "REVERT" else dict(v.get("set") or {})
        if not s:
            continue
        # a value computed from numbers the paper prints carries no "~" (the template ties ~ to estimated_from_figure)
        if s.get("effect_size_provenance") == "printed_in_text" and str(s.get("effect_size", "")).startswith("~"):
            s["effect_size"] = s["effect_size"][1:]
        cand = [r for doi, r in rows(it["hyp"]) if doi == meta.get(it["key"]) and str(r[10]) == str(it["data_location"])
                and all(str(r[COLS[k]]) == str(c["after"]) for k, c in it["changed"].items() if k in COLS)]
        if len(cand) != 1:
            n["not_matched" if not cand else "ambiguous"] += 1
            continue
        r = cand[0]
        new.append({"key": it["key"], "hyp": it["hyp"], "stage": 6, "quote_start": str(r[6])[:70], "summary_contains": str(r[7]),
                    "description_start": str(r[5])[:60], "set": s,
                    "reason": f"Figure-read check 11-22 (Claude against the image, {v['verdict'].lower()}): {v.get('why')}",
                    "source": f"{it['data_location']} image ({it.get('image')})"})
print(dict(n), "-> corrections", len(new))
if "--write" in sys.argv:
    cf = ROOT / "config/corrections.json"
    d = json.load(open(cf))
    keep = [c for c in d["corrections"] if not (str(c.get("reason", "")).startswith("Figure-read check 11-22 (Claude against"))]
    d["corrections"] = keep + new
    json.dump(d, open(cf, "w"), indent=1, ensure_ascii=False)
