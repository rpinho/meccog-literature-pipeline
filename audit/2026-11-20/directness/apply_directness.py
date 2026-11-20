#!/usr/bin/env python3
"""Turn verified directness changes (11-20 pass, rows the 11-19 pass never scored) into stage-4 entries of
config/corrections.json. ACCEPT takes the proposal, ADJUST the verifier's values, REJECT keeps the row. A final
class 5 row gets the verifier's reason appended to its Finding description, as the rules require.
Usage: apply_directness.py [--write]"""
import json, glob, sys, pathlib, collections
D = pathlib.Path(__file__).resolve().parent
ROOT = next(p for p in D.parents if (p / "config").is_dir())  # repo root
doi_key = {}
for p in glob.glob(str(ROOT / "data/papers/*/meta.json")):
    m = json.load(open(p))
    if m.get("doi"):
        doi_key[m["doi"].lower()] = m["key"]
# reviewer decisions on top of the verified set: (hyp, finding id) -> (class, strength, why)
DEX = ("dextran loaded and left to accumulate (24 h chase in P3; non-degradable dextran in late endosomes/lysosomes, "
       "framed by the authors as lysosomal acidification, in P2) reads the late endosome/lysosome, the same compartment "
       "as H1 P5.F2 and P7.F1 (3/4), and lysosomal pH can move opposite to endosomal pH (H1 P6): class 3, strength 4. "
       "The 11-19 verifier had set P3.F1 to 3/4; that correction stopped matching when dedupe kept the row's numeric twin.")
OVERRIDES = {("H1", f"P{p}.F{f}"): (3, "4", DEX) for p, f in ((2, 1), (2, 2), (2, 3), (3, 1))}
new, n = [], collections.Counter()
for vp in sorted(glob.glob(str(D / "verify_H*_*.json"))):
    name = pathlib.Path(vp).stem.split("_", 1)[1]
    vf = D / f"verified_{name}.json"
    pk = json.load(open(vp))
    ver = {v["item"]: v for v in json.load(open(vf))} if vf.exists() else {}
    for it in pk["items"]:
        v = ver.get(it["item"])
        dec = v["decision"] if v else "UNVERIFIED"
        n[dec] += 1
        row = it["row"]
        if dec == "REJECT":
            cls, st = int(row["Directness class"]), str(row["Directness strength"])[0]
        elif dec == "ADJUST":
            cls, st = int(v["class"]), str(v["strength"])[0]
        elif dec == "ACCEPT":
            cls, st = int(it["proposed"]["class"]), str(it["proposed"]["strength"])[0]
        else:
            continue
        o = OVERRIDES.get((pk["hyp"], it["finding_id"]))
        if o:
            cls, st = o[0], o[1]
        s = {}
        if cls != int(row["Directness class"]) or st != str(row["Directness strength"])[0]:
            s = {"directness_class": cls, "directness_strength": st}
        if cls == 5 and "Class 5" not in str(row["Finding description"]):
            why = ((v or {}).get("reason_for_description") or it["proposed"].get("reason_for_description")
                   or it["proposed"].get("why") or "").strip()
            s["description"] = str(row["Finding description"]).rstrip(".") + f". Class 5 (other): {why}"
        if not s:
            continue
        new.append({"key": doi_key[str(it["paper_doi"]).lower()], "hyp": pk["hyp"], "stage": 4,
                    "quote_start": str(row["Finding quote"])[:70], "summary_contains": str(row["Finding summary"]),
                    "description_start": str(row["Finding description"])[:60], "set": s,
                    "reason": f"Directness pass 11-20 ({pk['hyp']} {it['finding_id']}), {dec.lower()}ed by a second Claude check: "
                              f"{it['proposed'].get('why')}" + (f" Verifier: {v.get('why')}" if dec != "ACCEPT" else "")
                              + (f" Reviewer: {o[2]}" if o else ""),
                    "source": "organizers' directness definitions (audit/2026-11-20/directness/DIRECTNESS_RULES.txt)"})
print(dict(n), "-> corrections", len(new))
if "--write" in sys.argv:
    cf = ROOT / "config/corrections.json"
    d = json.load(open(cf))
    d["corrections"] = [c for c in d["corrections"] if c.get("stage", 1) != 4] + new
    json.dump(d, open(cf, "w"), indent=1, ensure_ascii=False)
