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


def title_words(t):
    """Content words of a title: 'ApoE4 in Alzheimer Disease' and 'APOE4 in Alzheimer's Disease.' match."""
    return {w for w in norm_title(t).split() if len(w) > 2}


def same_title(a, b):
    wa, wb = title_words(a), title_words(b)
    return len(wa) >= 4 and len(wa & wb) / len(wa | wb) >= 0.85


def first_last_author(meta):
    """(first, last) author family names from Crossref, cached in meta; None if unknown."""
    if "authors_fl" not in meta:
        fl = None
        doi = str(meta.get("doi") or "")
        if doi:
            import urllib.parse
            import urllib.request
            try:
                req = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                                             headers={"User-Agent": "meccog-literature-pipeline/0.1"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    a = [x.get("family", "").lower() for x in json.loads(r.read())["message"].get("author", [])]
                fl = [a[0], a[-1]] if a else None
            except Exception:
                pass
        meta["authors_fl"] = fl
        json.dump(meta, open(ROOT / "data/papers" / meta["key"] / "meta.json", "w"), indent=1)
    return meta["authors_fl"]


def preprint_of(pre, pub):
    """A preprint is the published paper when the titles match, or when the published version was
    retitled (Research Square records no link) but half the title words and both first and last author agree."""
    if same_title(pre.get("title"), pub.get("title")):
        return True
    wa, wb = title_words(pre.get("title")), title_words(pub.get("title"))
    if not (wa and wb and len(wa & wb) / len(wa | wb) >= 0.5):
        return False
    a, b = first_last_author(pre), first_last_author(pub)
    return bool(a and b and a == b)


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def is_preprint(meta):
    return meta.get("source") == "PPR" or str(meta.get("doi") or "").startswith(("10.1101/", "10.64898/", "10.21203/", "10.2139/"))


def source_type(meta):
    if is_preprint(meta):
        return "PubMed preprint" if meta.get("pmid") else "Other"
    return "PubMed published" if meta.get("pmid") else "Other"


def load_corrections():
    """config/corrections.json: fixes from human spot-checks, each with its reason and the text it rests on.
    A correction matches one finding by paper key and the start of its quote; the code checks still run after."""
    path = ROOT / "config/corrections.json"
    return json.load(open(path))["corrections"] if path.exists() else []


def apply_corrections(key, findings, corrections):
    for c in corrections:
        if c["key"] != key:
            continue
        hits = [f for f in findings if str(f.get("quote", "")).startswith(c["quote_start"])
                and c.get("summary_contains", "") in str(f.get("summary", ""))]
        if len(hits) != 1:
            sys.exit(f"correction for {key} '{c['quote_start'][:40]}' matches {len(hits)} findings, expected 1")
        f = hits[0]
        f.setdefault("precorrection", {k: f.get(k) for k in c["set"]})
        f.update(c["set"])
        f["correction"] = c["reason"]


MEAN_ERR = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:±|\+/-)\s*\d+(?:\.\d+)?")


def effect_from_quote(f):
    """A row left "qualitative" whose quote prints exactly two group values as mean ± error
    ("0.50 ± 0.03 ... 0.37 ± 0.04"): the effect is their ratio, written unsigned as the template asks
    (direction is its own column). Not for pH values, where a ratio means nothing."""
    if str(f.get("effect_size", "")).lower() != "qualitative":
        return
    q = str(f.get("quote", ""))
    ms = list(MEAN_ERR.finditer(q))
    if len(ms) != 2 or any(re.search(r"pH\s*$", q[:m.start()]) for m in ms):
        return
    a, b = (float(m.group(1)) for m in ms)
    # the description names the row's own comparison: if it prints other values (6.4 versus 5.5 S),
    # the quote's mean ± error values measure something else
    other = set(re.findall(r"\d+\.\d+", str(f.get("description", "")))) - {x for m in ms for x in re.findall(r"\d+\.\d+", m.group(0))}
    if min(a, b) <= 0 or other:
        return
    f["pre_quote_effect"] = f["effect_size"]
    f["effect_size"] = f"{max(a, b) / min(a, b):.1f}x"
    f["effect_size_provenance"] = "printed_in_text"
    f["description"] = str(f.get("description", "")).rstrip(".") + \
        f". Effect is the ratio of the two group values printed in the quote ({ms[0].group(0)} and {ms[1].group(0)})."


def accepted(f, text):
    if f.get("error"):
        return False
    v = (f.get("referee") or {})
    code_checks(f, text)  # deterministic rules apply to every row, including rows extracted before a rule existed
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


def published_doi(meta):
    """For a bioRxiv/medRxiv preprint, the DOI of its published version (bioRxiv API), cached in meta."""
    if "published_doi" in meta:
        return meta["published_doi"]
    doi = str(meta.get("doi") or "")
    pub = None
    if doi.startswith(("10.1101/", "10.64898/")):
        import urllib.request
        for server in ("biorxiv", "medrxiv"):
            try:
                with urllib.request.urlopen(f"https://api.biorxiv.org/pubs/{server}/{doi}", timeout=30) as r:
                    c = json.loads(r.read()).get("collection") or []
                if c and c[0].get("published_doi"):
                    pub = c[0]["published_doi"].lower()
                    break
            except Exception:
                pass
    meta["published_doi"] = pub
    json.dump(meta, open(ROOT / "data/papers" / meta["key"] / "meta.json", "w"), indent=1)
    return pub


def loc_norm(loc):
    l = str(loc).lower()
    l = re.sub(r"supplementary|supp\.?|extended data", "s", l)
    l = re.sub(r"figure|fig\.?", "f", l)
    return re.sub(r"[^a-z0-9]", "", l.split(";")[0].split("(")[0])


def comparison(f):
    """The cause side of the summary, '(APOE3 -> APOE4)': two rows on one panel that compare
    different groups (controls vs AD, e3/e4 vs e4/e4) are different findings, however alike the wording."""
    m = re.match(r"\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", str(f.get("summary", "")))
    return re.sub(r"[^a-z0-9>]+", "", (m.group(1) if m else str(f.get("summary", ""))).lower())


def dedupe_findings(fs):
    """Same panel, same quote or near-identical description -> keep the most relevant one."""
    kept = []
    for f in fs:  # fs sorted by relevance, highest first
        words = set(re.findall(r"[a-z0-9]+", str(f.get("description")).lower()))
        dup = False
        for k in kept:
            if k.get("quote") not in (None, "", "N/A") and k.get("quote") == f.get("quote") \
                    and k.get("direction") == f.get("direction") and k.get("effect_size") == f.get("effect_size"):
                dup = True  # same sentence, same result: e.g. a quantification panel and its representative images
                break
            if loc_norm(k.get("data_location")) != loc_norm(f.get("data_location")):
                continue
            kw = set(re.findall(r"[a-z0-9]+", str(k.get("description")).lower()))
            if k.get("quote") == f.get("quote") and k.get("direction") == f.get("direction") \
                    or len(words & kw) / max(1, len(words | kw)) > 0.5 and comparison(k) == comparison(f):
                dup = True
                break
        if not dup:
            kept.append(f)
    return kept


def cellval(x):
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    if x is None or str(x).strip() == "":
        return "N/A"
    return ILLEGAL_CHARACTERS_RE.sub("", str(x)).strip()  # control characters from PDF text are not allowed in xlsx


def build(H, out):
    corrections = load_corrections()
    hyp = {h["id"]: h for h in json.load(open(ROOT / "config/hypotheses.json"))["hypotheses"]}[H]
    papers = []
    for p in sorted((ROOT / f"data/{H}/findings").glob("*.json")):
        r = json.load(open(p))
        meta = json.load(open(ROOT / "data/papers" / r["key"] / "meta.json"))
        text, _ = load_text(r["key"])
        apply_corrections(r["key"], r["findings"], corrections)
        for f in r["findings"]:
            effect_from_quote(f)
        fs = [f for f in r["findings"] if accepted(f, text) and float(f.get("relevance") or 0) >= MIN_RELEVANCE
              and (f.get("scope") or {}).get("keep", True)]
        if not fs:
            continue
        for f in fs:
            f["_score"] = float(f.get("relevance") or 0)
        fs.sort(key=lambda f: -f["_score"])
        fs = dedupe_findings(fs)
        papers.append({"meta": meta, "findings": fs, "score": fs[0]["_score"]})
    # preprint vs published duplicates: keep the published one
    published = [p["meta"] for p in papers if not is_preprint(p["meta"])]
    reached = [json.loads(l) for l in open(ROOT / f"data/{H}/fetched.jsonl")]
    pub_dois = {str(json.load(open(ROOT / "data/papers" / x["key"] / "meta.json")).get("doi") or "").lower()
                for x in reached if x["status"] == "ok"}  # every published paper we could read, findings or not
    papers = [p for p in papers if not (is_preprint(p["meta"]) and (
        any(preprint_of(p["meta"], m) for m in published) or published_doi(p["meta"]) in pub_dois))]
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
