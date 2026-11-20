#!/usr/bin/env python3
"""Recall check, no model: second-level citation snowball from the papers already in each live sheet.
For every sheet paper with a PMID: its references (NCBI elink pubmed_pubmed_refs) and the papers citing it
(Europe PMC citations). OpenAlex was the first choice, but its anonymous daily budget ran out on 11-20.
Keep records that are not already candidates of that hypothesis, are not reviews, and name APOE4 in title or
abstract (screen.py's E4 pattern; stricter than tier0, which keeps every snowball record).
Writes new_<H>.jsonl and prints counts. Usage: measure.py H1 H2 H3 H4 H5"""
import json, pathlib, sys, time, urllib.parse
import openpyxl
D = pathlib.Path(__file__).resolve().parent
ROOT = next(p for p in D.parents if (p / "config").is_dir())  # repo root
sys.path.insert(0, str(ROOT / "pipeline"))
from search import get_json, EPMC, EUTILS, epmc_lookup_pmids
from screen import E4, is_review
CACHE = D / "cache"; CACHE.mkdir(exist_ok=True)

def refs(pmid):
    u = EUTILS + "elink.fcgi?" + urllib.parse.urlencode({"dbfrom": "pubmed", "db": "pubmed", "id": pmid,
                                                         "linkname": "pubmed_pubmed_refs", "retmode": "json", "tool": "meccog-pipeline"})
    time.sleep(0.4)
    out = []
    for ls in get_json(u).get("linksets", []):
        for db in ls.get("linksetdbs", []):
            out += [str(x) for x in db.get("links", [])]
    return out

def citing(pmid, maxn=1000):
    out, page = [], 1
    while len(out) < maxn:
        d = get_json(EPMC + f"MED/{pmid}/citations?" + urllib.parse.urlencode({"format": "json", "pageSize": 1000, "page": page}))
        res = (d.get("citationList") or {}).get("citation", [])
        out += [r["id"] for r in res if r.get("source") == "MED"]
        if len(res) < 1000:
            break
        page += 1
    return out

def one(pmid):
    c = CACHE / f"{pmid}.json"
    if c.exists():
        return json.load(open(c))
    got = {"refs": refs(pmid), "citing": citing(pmid)}
    json.dump(got, open(c, "w"))
    return got

for H in sys.argv[1:]:
    ws = openpyxl.load_workbook(ROOT / f"submissions/{H}.xlsx")["Submission"]
    seeds = [str(r[3] or "").strip() for r in ws.iter_rows(min_row=3, values_only=True) if r[1]]
    seeds = [s for s in seeds if s.isdigit()]
    have = set()
    for l in open(ROOT / f"data/{H}/candidates.jsonl"):
        have.add(str(json.loads(l).get("pmid")))
    pool = {}
    for s in seeds:
        g = one(s)
        for p in g["refs"] + g["citing"]:
            pool.setdefault(p, set()).add(s)
    new = [p for p in pool if p not in have]
    recs = epmc_lookup_pmids(new)
    kept = [r for r in recs if not is_review(r) and E4.search((r.get("title") or "") + " " + (r.get("abstract") or ""))]
    for r in kept:
        r["seeds"] = sorted(pool[r["pmid"]])
    with open(D / f"new_{H}.jsonl", "w") as f:
        for r in sorted(kept, key=lambda r: -len(r["seeds"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(H, "seeds with PMID", len(seeds), "pool", len(pool), "not yet candidates", len(new), "looked up", len(recs),
          "APOE4-named non-reviews", len(kept), "linked to >=2 seeds", sum(len(r["seeds"]) >= 2 for r in kept), flush=True)
