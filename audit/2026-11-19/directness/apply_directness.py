#!/usr/bin/env python3
"""Turn verified directness changes into stage-2 entries of config/corrections.json.
ACCEPT takes the proposal, ADJUST the verifier's values, REJECT keeps the row. A final class 5 row gets
the verifier's reason appended to its Finding description, as the rules require. Usage: apply_directness.py [--write]"""
import json, glob, sys, pathlib, collections
D = pathlib.Path(__file__).resolve().parent
ROOT = D.parents[2]  # audit/2026-11-19/directness -> repo root
doi_key = {}
for p in glob.glob(str(ROOT / "data/papers/*/meta.json")):
    m = json.load(open(p))
    if m.get("doi"):
        doi_key[m["doi"].lower()] = m["key"]
pid_doi = {}
for p in glob.glob(str(D / "packet_H*.json")):
    pk = json.load(open(p))
    for paper in pk["papers"]:
        pid_doi[(pk["hyp"], paper["paper_id"])] = paper["doi"]
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
        if dec not in ("ACCEPT", "ADJUST"):
            continue
        row = it["row"]
        cls, st = (v["class"], v["strength"]) if dec == "ADJUST" else (it["proposed"]["class"], it["proposed"]["strength"])
        if int(cls) == int(row["Directness class"]) and str(st)[0] == str(row["Directness strength"])[0]:
            continue
        key = doi_key[str(pid_doi[(pk["hyp"], it["finding_id"].split(".")[0])]).lower()]
        c = {"key": key, "hyp": pk["hyp"], "stage": 2, "quote_start": str(row["Finding quote"])[:70],
             "summary_contains": str(row["Finding summary"]), "description_start": str(row["Finding description"])[:60],
             "set": {"directness_class": int(cls), "directness_strength": str(st)[0]},
             "reason": f"Directness pass 11-19 ({pk['hyp']} {it['finding_id']}), {dec.lower()}ed by a second Claude check: "
                       f"{it['proposed'].get('why')}" + (f" Verifier: {v.get('why')}" if dec == "ADJUST" else ""),
             "source": "organizers' directness definitions (runs/directness_1119/DIRECTNESS_RULES.txt)"}
        if int(cls) == 5:
            why = (v.get("reason_for_description") or it["proposed"].get("why") or "").strip()
            c["set"]["description"] = str(row["Finding description"]).rstrip(".") + f". Class 5 (other): {why}"
        new.append(c)
# rows that were class 5 before this pass, whose description gave no reason: (hyp, finding id) -> reason
MANUAL_REASONS = {
    ("H2", "P2.F4"): "CS-6253, an apoE-mimetic peptide, is applied within APOE4 cells; the APOE genotype or isoform is not varied.",
    ("H2", "P2.F5"): "CS-6253, an apoE-mimetic peptide, is applied within APOE4 cells; the APOE genotype or isoform is not varied.",
    ("H3", "P15.F2"): "bafilomycin inhibits lysosomal acidification in ApoE4-treated neurons; the apoE isoform is not varied.",
    ("H4", "P6.F2"): "the comparison is apoE2 versus apoE4 in Abeta40 complexes, not APOE4 versus APOE3.",
}
for p in glob.glob(str(D / "packet_H*.json")):
    pk = json.load(open(p))
    for paper in pk["papers"]:
        for row in paper["rows"]:
            why = MANUAL_REASONS.get((pk["hyp"], row["Paper/Finding ID"]))
            if why and "Class 5" not in str(row["Finding description"]):
                new.append({"key": doi_key[str(paper["doi"]).lower()], "hyp": pk["hyp"], "stage": 2,
                            "quote_start": str(row["Finding quote"])[:70], "summary_contains": str(row["Finding summary"]),
                            "description_start": str(row["Finding description"])[:60],
                            "set": {"description": str(row["Finding description"]).rstrip(".") + f". Class 5 (other): {why}"},
                            "reason": "Directness pass 11-19: class 5 rows must say why in the description (rules).",
                            "source": "organizers' directness definitions"})
print(dict(n), "-> corrections", len(new))
if "--write" in sys.argv:
    cf = ROOT / "config/corrections.json"
    d = json.load(open(cf))
    d["corrections"] = [c for c in d["corrections"] if c.get("stage", 1) != 2] + new
    json.dump(d, open(cf, "w"), indent=1, ensure_ascii=False)
