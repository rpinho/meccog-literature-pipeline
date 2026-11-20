#!/usr/bin/env python3
"""Audit of new rows on Codex (general, 11-20: option A, to keep the lane's Claude share small): one read-only
gpt-6.2-astra call per paper, with the paper text, its supplement, the figure images its rows cite, the audit brief
(BRIEF.md), the directness conventions (CONVENTIONS_1120.md) and the hypothesis's already-scored rows as reference.
Writes codex_result_<packet>.json in the BRIEF.md result format, plus a "directness" object per row.
Usage: codex_audit.py packet7_a.json packet7_b.json   (MECCOG_MAX_CALLS = number of papers)"""
import json, pathlib, sys, concurrent.futures as cf
import openpyxl
D = pathlib.Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from llm import ask, json_lines
from extract import load_text
from figures import figure_image
MODEL = "gpt-6.2-astra"
V = json.load(open(ROOT / "config/variables.json"))
BRIEF = (D / "BRIEF.md").read_text().split("Output:")[0]
CONV = (D / "CONVENTIONS_1120.md").read_text()

def reference(H, skip_doi):
    ws = openpyxl.load_workbook(ROOT / f"submissions/meccog_rstack_{H}_814d9f8.xlsx")["Submission"]
    out = []
    for r in ws.iter_rows(min_row=3, values_only=True):
        if not r[1] and r[4]:
            out.append(f"- {r[7]} | system: {str(r[9])[:90]} | class {r[17]}, strength {str(r[18])[0]}")
    return "\n".join(out)

def run(g):
    H = g["hyp"]
    text, _ = load_text(g["key"])
    imgs = []
    for r in g["rows"]:
        im = figure_image(g["key"], r.get("Data location") or "")
        if im and im not in imgs:
            imgs.append(im)
    imgs = imgs[:6]
    rows = [{k: v for k, v in r.items()} for r in g["rows"]]
    prompt = f"""{BRIEF}
{CONV}

Hypothesis {H}: {g['hypothesis']}
A = {V[H]['A']}
B = {V[H]['B']}
Scope: {V[H]['scope']}

Figure images attached: {', '.join(p.name for p in imgs) or 'none'} (file name = figure number; S = supplementary).

ROWS TO AUDIT (paper {g['paper_id']}, key {g['key']}):
{json.dumps(rows, ensure_ascii=False, indent=1, default=str)}

REFERENCE ROWS of {H} already scored (summary | system | class, strength):
{reference(H, g['doi'])}

PAPER TEXT (references stripped; a supplement, if any, follows its marker):
{text[:150000]}

Output ONLY a JSON array, one object per row, in this form:
{{"hyp": "{H}", "paper_id": "{g['paper_id']}", "finding_id": "...", "key": "{g['key']}", "quote_start": "<first 70 characters of the row's quote exactly>",
 "verdict": "OK"|"FIX"|"DROP", "set": {{"<exact column name>": "<new value>"}}, "reason": "...", "evidence": "<exact text or what you read on which image>",
 "directness": {{"class": n, "strength": n, "reason_for_description": "<only for class 5>", "why": "<one sentence>"}}}}
Put directness ONLY in "directness", not in "set"."""
    try:
        ans = json_lines(ask(prompt, model=MODEL, effort="high", images=imgs))
    except Exception as e:
        print(g["key"], "FAILED", repr(e)[:200], flush=True)
        return []
    print(g["key"], H, "rows", len(g["rows"]), "answered", len(ans), "images", len(imgs), flush=True)
    return ans

for pk in sys.argv[1:]:
    groups = json.load(open(D / pk))
    with cf.ThreadPoolExecutor(2) as ex:
        res = [x for part in ex.map(run, groups) for x in part]
    json.dump(res, open(D / f"codex_result_{pathlib.Path(pk).stem.split('_', 1)[1]}.json", "w"), indent=1, ensure_ascii=False)
    print(pk, "results", len(res), "of", sum(len(g["rows"]) for g in groups), flush=True)
