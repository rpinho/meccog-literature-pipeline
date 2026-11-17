#!/usr/bin/env python3
"""Stage 5: independent referee.

A second model (different from the extractor) re-reads the full text and the
supplement and checks every field of every record. PASS records go on; FIX
records take the referee's corrections and are re-checked by code; REJECT
records are dropped from the sheet but kept in the file with the reason.

Writes the verdicts into data/<H>/findings/<key>.json (key "referee").
"""
import argparse
import concurrent.futures as cf
import json
import pathlib

from llm import ask, json_lines
from extract import load_text, code_checks

ROOT = pathlib.Path(__file__).resolve().parent.parent
REFEREE_MODEL = "gpt-6.2-astra"
REFEREE_BATCH = 20  # all of a paper's findings in one call (budget, 11-17)
FIELDS = ["description", "quote", "summary", "system", "data_location", "effect_size",
          "effect_size_provenance", "p_value", "p_value_provenance", "sample_size",
          "sample_size_provenance", "directness_class", "directness_strength", "relevance", "direction"]


def referee_paper(path, hyp, var, force=False):
    res = json.load(open(path))
    text, has_supp = load_text(res["key"])
    supp_note = ("The supplementary material is included at the end of the text." if has_supp else
                 "The supplementary material could not be obtained; a supplementary-panel value should carry "
                 "full_text_unavailable, not not_found_in_source.")
    tmpl = open(ROOT / "prompts/referee_paper.md").read()

    def apply(f, v):
        v["model"] = REFEREE_MODEL
        f["referee"] = v
        if v.get("verdict") == "FIX" and isinstance(v.get("corrections"), dict):
            f["original"] = {k: f.get(k) for k in v["corrections"]}
            for k, val in v["corrections"].items():
                if k in FIELDS:
                    f[k] = val
            code_checks(f, text)

    todo = [f for f in res["findings"] if not f.get("error") and
            (force or not f.get("referee") or f["referee"].get("verdict") == "ERROR")]

    def batch(fs):
        recs = [dict({k: f.get(k) for k in FIELDS}, item=n + 1) for n, f in enumerate(fs)]
        p = tmpl.format(statement=hyp["statement"], A=var["A"], B=var["B"], scope=var["scope"], supp_note=supp_note,
                        record=json.dumps(recs, ensure_ascii=False, indent=1), text=text)
        try:
            vs = json_lines(ask(p, model=REFEREE_MODEL, effort="high"))
        except Exception as e:
            vs = []
            err = repr(e)[:200]
        else:
            err = "no verdict returned"
        by_item = {int(v.get("item", 0)): v for v in vs if isinstance(v, dict) and str(v.get("item", "")).isdigit()}
        for n, f in enumerate(fs):
            apply(f, by_item.get(n + 1) or {"verdict": "ERROR", "evidence": err})

    chunks = [todo[i:i + REFEREE_BATCH] for i in range(0, len(todo), REFEREE_BATCH)]
    for c in chunks:  # sequential within a paper; papers run in parallel under the 2-call cap
        batch(c)
    json.dump(res, open(path, "w"), indent=1, ensure_ascii=False)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis")
    ap.add_argument("--keys")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    hyp = {h["id"]: h for h in json.load(open(ROOT / "config/hypotheses.json"))["hypotheses"]}[a.hypothesis]
    var = json.load(open(ROOT / "config/variables.json"))[a.hypothesis]
    d = ROOT / f"data/{a.hypothesis}/findings"
    paths = [d / f"{k}.json" for k in a.keys.split(",")] if a.keys else sorted(d.glob("*.json"))
    from collections import Counter
    def safe(p):
        try:
            return referee_paper(p, hyp, var, a.force)
        except Exception as e:
            print(p.name, "FAILED", repr(e)[:200], flush=True)
            return {"key": p.stem, "findings": []}

    with cf.ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(safe, paths):
            c = Counter((f.get("referee") or {}).get("verdict", "none") for f in r["findings"])
            print(r["key"], dict(c), flush=True)


if __name__ == "__main__":
    main()
