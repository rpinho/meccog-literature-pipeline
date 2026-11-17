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

from llm import ask
from extract import load_text, code_checks

ROOT = pathlib.Path(__file__).resolve().parent.parent
REFEREE_MODEL = "gpt-6.2-astra"
FIELDS = ["description", "quote", "summary", "system", "data_location", "effect_size",
          "effect_size_provenance", "p_value", "p_value_provenance", "sample_size",
          "sample_size_provenance", "directness_class", "directness_strength", "relevance", "direction"]


def referee_paper(path, hyp, var, force=False):
    res = json.load(open(path))
    text, has_supp = load_text(res["key"])
    supp_note = ("The supplementary material is included at the end of the text." if has_supp else
                 "The supplementary material could not be obtained; a supplementary-panel value should carry "
                 "full_text_unavailable, not not_found_in_source.")
    tmpl = open(ROOT / "prompts/referee.md").read()

    def one(f):
        if f.get("error") or (f.get("referee") and not force):
            return f
        rec = {k: f.get(k) for k in FIELDS}
        p = tmpl.format(statement=hyp["statement"], A=var["A"], B=var["B"], supp_note=supp_note,
                        record=json.dumps(rec, ensure_ascii=False, indent=1), text=text)
        try:
            v = json.loads(ask(p, model=REFEREE_MODEL, effort="high").strip().strip("`").removeprefix("json").strip())
        except Exception as e:
            v = {"verdict": "ERROR", "evidence": repr(e)[:200]}
        v["model"] = REFEREE_MODEL
        f["referee"] = v
        if v.get("verdict") == "FIX" and isinstance(v.get("corrections"), dict):
            f["original"] = {k: f.get(k) for k in v["corrections"]}
            for k, val in v["corrections"].items():
                if k in FIELDS:
                    f[k] = val
            code_checks(f, text)
        return f

    with cf.ThreadPoolExecutor(3) as ex:
        res["findings"] = list(ex.map(one, res["findings"]))
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
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(lambda p: referee_paper(p, hyp, var, a.force), paths):
            c = Counter((f.get("referee") or {}).get("verdict", "none") for f in r["findings"])
            print(r["key"], dict(c), flush=True)


if __name__ == "__main__":
    main()
