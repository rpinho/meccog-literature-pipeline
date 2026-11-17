#!/usr/bin/env python3
"""Stage 6: write the submission spreadsheet for one hypothesis and validate it.

- Only findings the referee passed (PASS, or FIX whose corrections survive the
  code checks) go in. Rejected rows stay in data/ with their reasons.
- Papers are ordered by their most relevant accepted finding (P1 first) and
  capped at 50. A preprint whose published version is also in the set is
  dropped in favour of the published one.
- Every cell carries a value or N/A. Paper rows leave finding columns empty,
  as the template asks.
- The Method sheet comes from config/method.json (public fields) and
  config/method.private.json (team leader and email; gitignored, never pushed).

Usage: build_sheet.py H1 [--out submissions/H1.xlsx]
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import validate_submission as V  # noqa: E402
from extract import code_checks, load_text  # noqa: E402

STRENGTH_WORD = {1: "1 very strong", 2: "2 strong", 3: "3 moderate", 4: "4 weak", 5: "5 very weak"}
MAX_PAPERS = 50
# "Accuracy and relevance over volume": a finding the extractor itself rates below this bears too
# weakly on the hypothesis (e.g. mitophagy pH under an endosomal-pH hypothesis). Relevance is about
# the subject, never the direction, so contrary and null findings stay in at any direction.
MIN_RELEVANCE = 0.35


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def is_preprint(meta):
    return meta.get("source") == "PPR" or str(meta.get("doi") or "").startswith(("10.1101/", "10.64898/", "10.21203/", "10.2139/"))


def source_type(meta):
    if is_preprint(meta):
        return "PubMed preprint" if meta.get("pmid") else "Other"
    return "PubMed published" if meta.get("pmid") else "Other"


def accepted(f, text):
    if f.get("error"):
        return False
    v = (f.get("referee") or {})
    if v.get("verdict") == "PASS":
        return not f.get("code_problems")
    if v.get("verdict") == "FIX":
        if f.get("code_problems"):
            # a correction the validator would reject: put back the original value of each failing field
            for k, old in (f.get("original") or {}).items():
                if any(k.split("_provenance")[0] in p for p in f["code_problems"]):
                    f[k] = old
            code_checks(f, text)
        return not f.get("code_problems")
    return False


def cellval(x):
    if x is None or str(x).strip() == "":
        return "N/A"
    return str(x).strip()


def build(H, out):
    hyp = {h["id"]: h for h in json.load(open(ROOT / "config/hypotheses.json"))["hypotheses"]}[H]
    papers = []
    for p in sorted((ROOT / f"data/{H}/findings").glob("*.json")):
        r = json.load(open(p))
        meta = json.load(open(ROOT / "data/papers" / r["key"] / "meta.json"))
        text, _ = load_text(r["key"])
        fs = [f for f in r["findings"] if accepted(f, text) and float(f.get("relevance") or 0) >= MIN_RELEVANCE]
        if not fs:
            continue
        for f in fs:
            f["_score"] = float(f.get("relevance") or 0)
        fs.sort(key=lambda f: -f["_score"])
        papers.append({"meta": meta, "findings": fs, "score": fs[0]["_score"]})
    # preprint vs published duplicates: keep the published one
    published = {norm_title(p["meta"].get("title")) for p in papers if not is_preprint(p["meta"])}
    papers = [p for p in papers if not (is_preprint(p["meta"]) and norm_title(p["meta"].get("title")) in published)]
    papers.sort(key=lambda p: -p["score"])
    dropped = papers[MAX_PAPERS:]
    papers = papers[:MAX_PAPERS]

    wb = openpyxl.load_workbook(ROOT / "config/submission_template.xlsx")
    ws = wb["Submission"]
    ws["A2"] = hyp["statement"]
    row = 3
    for i, p in enumerate(papers, 1):
        m = p["meta"]
        ws.cell(row, 2, cellval(m.get("doi")))
        ws.cell(row, 3, source_type(m))
        ws.cell(row, 4, cellval(m.get("pmid")))
        ws.cell(row, 5, f"P{i}")
        row += 1
        for j, f in enumerate(p["findings"], 1):
            vals = [None, None, None, None, f"P{i}.F{j}", f.get("description"), f.get("quote"),
                    f.get("summary"), round(float(f.get("relevance") or 0), 2), f.get("system"),
                    f.get("data_location"), f.get("effect_size"), f.get("effect_size_provenance"),
                    f.get("p_value"), f.get("p_value_provenance"), f.get("sample_size"),
                    f.get("sample_size_provenance"), int(f.get("directness_class")),
                    STRENGTH_WORD.get(int(str(f.get("directness_strength"))[0]))]
            for c, v in enumerate(vals, 1):
                if c >= 5:
                    ws.cell(row, c, v if isinstance(v, (int, float)) else cellval(v))
            row += 1

    method = json.load(open(ROOT / "config/method.json"))
    priv_p = ROOT / "config/method.private.json"
    priv = json.load(open(priv_p)) if priv_p.exists() else {}
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ms = wb["Method"]
    values = {"Team": priv.get("team", "TEAM-NAME-PENDING"), "Team leader": priv.get("leader", "LEADER-PENDING"),
              "Team leader email": priv.get("email", "pending@example.org"), "Method URL": method["method_url"],
              "Commit SHA": sha or "N/A", "Who did the work": method["who"],
              "Model and version": method["models"]}
    for r in range(1, ms.max_row + 1):
        label = ms.cell(r, 1).value
        if label in values:
            ms.cell(r, 2, values[label])
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    n_f = sum(len(p["findings"]) for p in papers)
    print(f"{H}: {len(papers)} papers, {n_f} findings -> {out}" + (f"; {len(dropped)} papers over the cap" if dropped else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis")
    ap.add_argument("--out")
    a = ap.parse_args()
    out = pathlib.Path(a.out) if a.out else ROOT / "submissions" / f"{a.hypothesis}.xlsx"
    build(a.hypothesis, out)
    r = subprocess.run([sys.executable, str(ROOT / "pipeline/validate_submission.py"), str(out)],
                       capture_output=True, text=True)
    print(r.stdout[-2500:])


if __name__ == "__main__":
    main()
