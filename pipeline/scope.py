#!/usr/bin/env python3
"""Stage 5b: scope check. Per paper, the referee model decides keep/drop for
each accepted finding against an explicit statement of what counts as B, its
surrogates and its path for this hypothesis (config/variables.json "scope").
Writes f["scope"] = {"keep": bool, "why": str, "model": ...}."""
import argparse
import concurrent.futures as cf
import json
import pathlib

from llm import ask, json_lines
from referee import REFEREE_MODEL

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(path, hyp, var, force=False):
    res = json.load(open(path))
    meta = json.load(open(ROOT / "data/papers" / res["key"] / "meta.json"))
    todo = [(i, f) for i, f in enumerate(res["findings"])
            if (f.get("referee") or {}).get("verdict") in ("PASS", "FIX") and (force or "scope" not in f)]
    if not todo:
        return res
    lines = "\n".join(f"id: f{i}\nlocation: {f.get('data_location')}\ndescription: {f.get('description')}\nsystem: {f.get('system')}\n"
                      for i, f in todo)
    p = open(ROOT / "prompts/scope.md").read().format(statement=hyp["statement"], A=var["A"], B=var["B"],
                                                      scope=var["scope"], title=meta.get("title"), findings=lines)
    ans = {x.get("id"): x for x in json_lines(ask(p, model=REFEREE_MODEL, effort="medium"))}
    for i, f in todo:
        a = ans.get(f"f{i}")
        if a is not None:
            f["scope"] = {"keep": bool(a.get("keep")), "why": a.get("why"), "model": REFEREE_MODEL}
    json.dump(res, open(path, "w"), indent=1, ensure_ascii=False)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    hyp = {h["id"]: h for h in json.load(open(ROOT / "config/hypotheses.json"))["hypotheses"]}[a.hypothesis]
    var = json.load(open(ROOT / "config/variables.json"))[a.hypothesis]
    paths = sorted((ROOT / f"data/{a.hypothesis}/findings").glob("*.json"))

    def safe(p):
        try:
            return run(p, hyp, var, a.force)
        except Exception as e:
            print(p.name, "FAILED", repr(e)[:200], flush=True)
            return {"key": p.stem, "findings": []}

    with cf.ThreadPoolExecutor(3) as ex:
        for r in ex.map(safe, paths):
            fs = [f for f in r["findings"] if "scope" in f]
            if fs:
                print(r["key"], "keep", sum(f["scope"]["keep"] for f in fs), "drop", sum(not f["scope"]["keep"] for f in fs), flush=True)


if __name__ == "__main__":
    main()
