#!/usr/bin/env python3
"""Stage 5c: read values off figures, one model call per figure (image + legend + rows).

Only rows that will be in a sheet (referee PASS/FIX, scope kept, relevance >= the
floor) and that miss something a figure can give: effect "qualitative"/N/A,
P value N/A, sample size N/A. A value printed in the text is never replaced.
- group means printed ON the figure -> difference/ratio, provenance printed_in_text
  (the README says these were read from numbers printed on the figure)
- measured off bars/points -> leading ~, estimated_from_figure
- stars -> the legend's own key, visual_only; never an estimated P value
- n by counting plotted points -> ~n, estimated_from_figure
Every returned value goes back through the code checks; a value the validator
would reject is dropped. Originals are kept in f["prefig"].
"""
import argparse
import concurrent.futures as cf
import json
import pathlib
import re

from llm import ask, json_lines
from extract import load_text, code_checks
from figures import figure_image, parse_loc
from build_sheet import MIN_RELEVANCE

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG_MODEL = "gpt-6.1-sol"


def in_sheet(f):
    v = (f.get("referee") or {}).get("verdict")
    return (v in ("PASS", "FIX") and not f.get("code_problems") and not f.get("error")
            and float(f.get("relevance") or 0) >= MIN_RELEVANCE and (f.get("scope") or {}).get("keep", True))


def wants(f):
    return (str(f.get("effect_size", "")).lower() in ("qualitative", "n/a")
            or str(f.get("p_value", "")).upper() == "N/A" or str(f.get("sample_size", "")).upper() == "N/A")


def legend_for(text, kind, num):
    pats = [rf"\[FIGURE[^\]]*?{'S' if kind else ''}{num}\b[^\]]*\]", rf"\n#+ *(?:Figure|Fig\.?) *{'S' if kind else ''}{num}\.",
            rf"\n(?:Figure|Fig\.?) *{'S' if kind else ''}{num}[.:]"]
    for p in pats:
        m = re.search(p, text)
        if m:
            return text[m.start():m.start() + 2500]
    return "(legend not found in the text)"


def apply(f, a):
    f["prefig"] = {k: f.get(k) for k in ("effect_size", "effect_size_provenance", "p_value", "p_value_provenance",
                                         "sample_size", "sample_size_provenance")}
    f["figure_read"] = {"model": FIG_MODEL, **a}
    if a.get("panel_ok") is False:
        return
    # group values already printed in the quote come from the text, not the figure: leave those for a person
    # (unless the figure prints the same numbers as the text, e.g. bars labelled 5.38 and 5.74)
    quote_nums = set(re.findall(r"\d+\.\d+", str(f.get("quote", ""))))
    text_values = len(quote_nums) >= 2 and not quote_nums & set(re.findall(r"\d+\.\d+", str(a.get("note", ""))))
    if text_values and a.get("effect_size_provenance") == "printed_on_figure":
        f["figure_read"]["skipped_effect"] = "the quote prints group values; compute the effect from the text"
    elif str(f.get("effect_size", "")).lower() in ("qualitative", "n/a") and a.get("effect_size") not in (None, "", "N/A", "qualitative"):
        prov = a.get("effect_size_provenance")
        f["effect_size"] = a["effect_size"]
        f["effect_size_provenance"] = "printed_in_text" if prov == "printed_on_figure" else prov
        if prov == "printed_on_figure" and a.get("note"):
            f["description"] = str(f.get("description", "")).rstrip(".") + f". Group values printed on the figure: {a['note']}"
    if str(f.get("p_value", "")).upper() == "N/A" and a.get("p_value") not in (None, "", "N/A") \
            and a.get("p_value_provenance") == "visual_only":
        f["p_value"], f["p_value_provenance"] = a["p_value"], "visual_only"
    if str(f.get("sample_size", "")).upper() == "N/A" and a.get("sample_size") not in (None, "", "N/A"):
        f["sample_size"] = a["sample_size"]
        f["sample_size_provenance"] = a.get("sample_size_provenance") or "estimated_from_figure"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis")
    ap.add_argument("--dry-run", action="store_true", help="count figures and rows, no model calls")
    a = ap.parse_args()
    groups = {}
    for p in sorted((ROOT / f"data/{a.hypothesis}/findings").glob("*.json")):
        res = json.load(open(p))
        for i, f in enumerate(res["findings"]):
            if in_sheet(f) and wants(f) and "figure_read" not in f and parse_loc(f.get("data_location")):
                kind, num = parse_loc(f["data_location"])
                groups.setdefault((p, res["key"], kind, num), []).append(i)
    jobs = []
    for (p, key, kind, num), idx in groups.items():
        img = figure_image(key, f"{'S' if kind else ''}Fig {num}")
        if img:
            jobs.append((p, key, kind, num, idx, img))
    print(a.hypothesis, "figures", len(groups), "with image", len(jobs), "rows", sum(len(j[4]) for j in jobs), flush=True)
    if a.dry_run:
        return
    tmpl = open(ROOT / "prompts/figure_read.md").read()

    def run(job):
        p, key, kind, num, idx, img = job
        res = json.load(open(p))
        text, _ = load_text(key)
        rows = [{"item": n + 1, **{k: res["findings"][i].get(k) for k in (
            "data_location", "description", "effect_size", "effect_size_provenance", "p_value",
            "p_value_provenance", "sample_size", "sample_size_provenance")}} for n, i in enumerate(idx)]
        prompt = tmpl.format(legend=legend_for(text, kind, num), rows=json.dumps(rows, ensure_ascii=False, indent=1))
        try:
            ans = {int(x.get("item", 0)): x for x in json_lines(ask(prompt, model=FIG_MODEL, effort="medium", images=[img]))
                   if isinstance(x, dict)}
        except Exception as e:
            print(key, kind + num, "FAILED", repr(e)[:150], flush=True)
            return
        res = json.load(open(p))  # re-read: another figure of the same paper may have written it
        for n, i in enumerate(idx):
            f = res["findings"][i]
            if n + 1 in ans:
                apply(f, ans[n + 1])
                code_checks(f, text)
                if f.get("code_problems"):  # a value the validator would reject: back to what we had
                    f.update(f["prefig"])
                    code_checks(f, text)
                    f["figure_read"]["reverted"] = True
        json.dump(res, open(p, "w"), indent=1, ensure_ascii=False)
        print(key, kind + num, "rows", len(idx), flush=True)

    # one paper at a time per worker, so two figures of one paper never write the same file at once
    by_paper = {}
    for j in jobs:
        by_paper.setdefault(j[0], []).append(j)
    with cf.ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda js: [run(j) for j in js], by_paper.values()))


if __name__ == "__main__":
    main()
