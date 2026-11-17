#!/usr/bin/env python3
"""Stage 2: screen candidates by title and abstract.

Tier 0 (code): keep a paper if its title/abstract names APOE4 (any common
spelling) or it came from the citation snowball of the starting reference;
drop records Europe PMC types as reviews only.
Tier 1 (model): batches of 20 titles+abstracts, decision yes/maybe/no.

Output: data/<H>/screened.jsonl (every tier-0 paper with its decision).
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import re

from llm import ask, json_lines, MODEL

ROOT = pathlib.Path(__file__).resolve().parent.parent
E4 = re.compile(r"apo ?e ?4|apoe[- ]?ε4|ε4|epsilon ?4|e4 allele|apoe-?e4|\bE4\b|apolipoprotein e ?\(?ε?4", re.I)


def is_review(r):
    pt = [p.lower() for p in (r.get("pubtype") or [])]
    return any("review" in p for p in pt) and not any("research" in p for p in pt)


def tier0(r):
    text = (r.get("title") or "") + " " + (r.get("abstract") or "")
    snow = any(x.startswith("snowball") for x in r.get("routes", []))
    return (E4.search(text) or snow) and not is_review(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    H = a.hypothesis
    hyp = {h["id"]: h for h in json.load(open(ROOT / "config/hypotheses.json"))["hypotheses"]}[H]
    var = json.load(open(ROOT / "config/variables.json"))[H]
    tmpl = open(ROOT / "prompts/screen.md").read()
    rs = [json.loads(l) for l in open(ROOT / f"data/{H}/candidates.jsonl")]
    keep = [r for r in rs if tier0(r)]
    for i, r in enumerate(keep):
        r["sid"] = f"c{i}"
    out_p = ROOT / f"data/{H}/screened.jsonl"
    done = {}
    if out_p.exists():  # resume
        for l in open(out_p):
            x = json.loads(l)
            done[(x.get("pmid"), x.get("doi"))] = x
    todo = [r for r in keep if (r.get("pmid"), r.get("doi")) not in done]

    def run(batch):
        papers = "\n\n".join(
            f"id: {r['sid']}\ntitle: {r.get('title')}\nyear: {r.get('year')}\nabstract: {(r.get('abstract') or 'N/A')[:2500]}"
            for r in batch)
        prompt = tmpl.format(statement=hyp["statement"], A=var["A"], B=var["B"], papers=papers)
        ans = {x["id"]: x for x in json_lines(ask(prompt, effort="low"))}
        return [dict(r, screen=ans.get(r["sid"]), screen_model=MODEL) for r in batch]

    batches = [todo[i:i + a.batch] for i in range(0, len(todo), a.batch)]
    with open(out_p, "a") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for res in ex.map(run, batches):
            for r in res:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
    rows = [json.loads(l) for l in open(out_p)]
    from collections import Counter
    c = Counter((r.get("screen") or {}).get("decision", "missing") for r in rows)
    print(H, "candidates", len(rs), "tier0", len(keep), dict(c))


if __name__ == "__main__":
    main()
