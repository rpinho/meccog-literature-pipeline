#!/usr/bin/env python3
"""Stage 4: extract findings from full text.

Pass A (inventory, recall): one call per paper lists every panel/table/text
result that bears on the hypothesis, supporting, contrary or null.
Pass B (extraction, few fields): one call per listed result fills the record.
Pass C (code checks, no model): quote found in the paper text (layered
matcher), value shapes the validator accepts, provenance consistent with the
value, P never estimated. Failures are kept with their reasons for the referee.

Output: data/<H>/findings/<paper key>.json
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import re
import sys

from llm import ask, json_lines, json_obj, MODEL
from quotes import find_quote

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import validate_submission as V  # noqa: E402  the organizers' own shape rules

PROV = {"printed_in_text", "visual_only", "estimated_from_figure", "supplement_only",
        "not_found_in_source", "full_text_unavailable", "ambiguous_panel"}
ABSENT = {"not_found_in_source", "full_text_unavailable", "ambiguous_panel"}
MAX_TEXT = 180_000
EXTRACT_BATCH = 4  # findings per call: few enough to keep per-field accuracy, few enough calls to fit the allowance


def shape_ok(field, v):
    v = str(v).strip()
    if v.upper() == "N/A":
        return True
    if field == "effect_size":
        return bool(V.RE_PERCENT.match(v) or V.RE_FOLD.match(v) or V.RE_STANDARDISED.match(v)
                    or V.RE_QUALITATIVE.match(v))
    if field == "p_value":
        return bool(V.RE_P_EXACT.match(v) or V.RE_P_INEQ.match(v))
    if field == "sample_size":
        return bool(V.RE_N_ONE.match(v) or V.RE_N_RANGE.match(v))
    return True


def code_checks(rec, text):
    problems = []
    q = rec.get("quote", "N/A")
    if q and q != "N/A":
        tier, span = find_quote(q, text)
        rec["quote_tier"] = tier
        if tier == "MISS":
            problems.append("quote not found in paper text")
        elif span:
            rec["quote"] = span
    if str(rec.get("effect_size", "")).strip().upper() == "N/A" and \
            rec.get("effect_size_provenance") in ("printed_in_text", "supplement_only", "visual_only"):
        rec["effect_size"] = "qualitative"  # e.g. ">1 pH unit": printed, but no accepted numeric shape
    for f in ("effect_size", "p_value", "sample_size"):
        v, p = str(rec.get(f, "")).strip(), str(rec.get(f + "_provenance", "")).strip()
        if not shape_ok(f, v):
            problems.append(f"{f} '{v}' is not a shape the validator accepts")
        if p not in PROV:
            problems.append(f"{f}_provenance '{p}' is not a code")
        if p in ABSENT and v.upper() != "N/A":
            problems.append(f"{f} has a value but provenance {p}")
        if p not in ABSENT and v.upper() == "N/A":
            problems.append(f"{f} is N/A but provenance {p}")
        if v.startswith("~") != (p == "estimated_from_figure"):
            problems.append(f"{f}: ~ and estimated_from_figure must go together")
    if str(rec.get("p_value_provenance")) == "estimated_from_figure":
        problems.append("P value estimated from a figure")
    try:
        c, s = int(rec["directness_class"]), int(str(rec["directness_strength"])[0])
        if c == 1 and s >= 4:
            problems.append("class 1 with strength 4-5 (scale read upside down?)")
    except Exception:
        problems.append("directness class/strength missing")
    loc = str(rec.get("data_location", ""))
    if re.fullmatch(r"(fig(ure)?\.?\s*\d+)", loc.strip(), re.I):
        problems.append("location lacks a panel")
    rec["code_problems"] = problems
    return rec


MAX_SUPP = 90_000


def load_text(key):
    """Main text, then the supplement (marked), and whether a supplement was read."""
    d = ROOT / "data/papers" / key
    t = (d / "text.txt").read_text()[:MAX_TEXT]
    supp = (d / "supp.txt").read_text()[:MAX_SUPP] if (d / "supp.txt").exists() else ""
    if supp.strip():
        t += "\n\n# SUPPLEMENTARY MATERIAL (text extracted from the supplement files)\n\n" + supp
    return t, bool(supp.strip())


def run_paper(key, hyp, var, force=False):
    out = ROOT / f"data/{hyp['id']}/findings/{key}.json"
    if out.exists() and not force:
        return json.load(open(out))
    text, has_supp = load_text(key)
    supp_note = ("The supplementary material IS included at the end of the text." if has_supp else
                 "The supplementary material could NOT be obtained. For a value that would be in a supplementary "
                 "panel, use provenance full_text_unavailable (not not_found_in_source).")
    inv_prompt = open(ROOT / "prompts/inventory.md").read().format(
        statement=hyp["statement"], A=var["A"], B=var["B"], text=text)
    panels = json_lines(ask(inv_prompt, effort="high"))
    inventory = [x for x in panels if str(x.get("bears", "")).lower() not in ("no", "")]
    tmpl = open(ROOT / "prompts/extract.md").read()

    def batch(items):
        listing = "\n".join(f"{n + 1}. location {it.get('loc')}: {it.get('what')}" for n, it in enumerate(items))
        p = tmpl.format(statement=hyp["statement"], A=var["A"], B=var["B"], items=listing, text=text, supp_note=supp_note)
        try:
            recs = json_lines(ask(p, effort="high"))
        except Exception as e:
            return [{"inventory": it, "error": repr(e)[:300]} for it in items]
        by_item = {int(r.get("item", 0)): r for r in recs if isinstance(r, dict) and str(r.get("item", "")).isdigit()}
        out = []
        for n, it in enumerate(items):
            rec = by_item.get(n + 1) or (recs[n] if len(recs) == len(items) else None)
            if not rec:
                out.append({"inventory": it, "error": "no record returned"})
                continue
            rec.pop("item", None)
            rec["inventory"] = it
            out.append(code_checks(rec, text))
        return out

    chunks = [inventory[i:i + EXTRACT_BATCH] for i in range(0, len(inventory), EXTRACT_BATCH)]
    with cf.ThreadPoolExecutor(3) as ex:
        findings = [f for part in ex.map(batch, chunks) for f in part]
    res = {"key": key, "hypothesis": hyp["id"], "model": MODEL, "panels_n": len(panels), "inventory_n": len(inventory),
           "findings": findings}
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis")
    ap.add_argument("--keys", help="comma-separated paper keys (default: all fetched yes/maybe)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stale", action="store_true", help="only missing or first-prompt papers")
    a = ap.parse_args()
    hyp = {h["id"]: h for h in json.load(open(ROOT / "config/hypotheses.json"))["hypotheses"]}[a.hypothesis]
    var = json.load(open(ROOT / "config/variables.json"))[a.hypothesis]
    if a.keys:
        keys = a.keys.split(",")
    else:
        rows = [json.loads(l) for l in open(ROOT / f"data/{a.hypothesis}/fetched.jsonl")]
        rows.sort(key=lambda r: -(r.get("relevance") or 0))  # most relevant first, in case the allowance runs out
        keys = [r["key"] for r in rows if r["status"] == "ok"]
    if a.stale:  # only papers never extracted, or extracted with the first inventory prompt
        def stale(k):
            f = ROOT / f"data/{a.hypothesis}/findings/{k}.json"
            return not f.exists() or "panels_n" not in json.load(open(f))
        keys = [k for k in keys if stale(k)]
        a.force = True
    def safe(k):
        try:
            return run_paper(k, hyp, var, a.force)
        except Exception as e:  # one bad answer must not stop the hypothesis
            print(k, "FAILED", repr(e)[:200], flush=True)
            return {"key": k, "inventory_n": -1, "findings": []}

    with cf.ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(safe, keys):
            n = len(r["findings"])
            bad = sum(bool(f.get("code_problems") or f.get("error")) for f in r["findings"])
            print(r["key"], "inventory", r["inventory_n"], "findings", n, "with problems", bad, flush=True)


if __name__ == "__main__":
    main()
