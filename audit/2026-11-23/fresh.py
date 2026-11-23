#!/usr/bin/env python3
"""No model. Two recall gaps in the query route, per hypothesis:
 A. fresh: papers indexed since the 11-17 search (PubMed EDAT >= 2026/11/10; Europe PMC FIRST_IDATE >= 2026-11-10)
 B. cap: the original search kept the first 300 ids per query; fetch all PubMed ids and count those not in candidates
Writes new_<H>.jsonl (Europe PMC records with abstracts, route noted) and summary.json. Does not touch data/."""
import json, pathlib, sys, time, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from search import get_json, EUTILS, europepmc_search, epmc_record, epmc_lookup_pmids
OUT = pathlib.Path(__file__).parent
FAILED = []
def retry(f, *a, **k):
    for t in range(4):
        try:
            return f(*a, **k)
        except Exception:
            if t == 3: raise
            time.sleep(15 * (t + 1))
def lookup(pmids):
    """epmc_lookup_pmids in chunks of 50; a chunk that fails twice is recorded, not fatal."""
    out = []
    for i in range(0, len(pmids), 50):
        for t in range(3):
            try:
                out += epmc_lookup_pmids(pmids[i:i + 50]); break
            except Exception as e:
                time.sleep(10 * (t + 1))
        else:
            FAILED.extend(pmids[i:i + 50])
    return out
summ = {}
for H in (sys.argv[1:] or ["H1", "H2", "H3", "H4", "H5"]):
    have_p, have_d = set(), set()
    for f in ("candidates.jsonl",):
        for l in open(ROOT / f"data/{H}/{f}"):
            r = json.loads(l)
            if r.get("pmid"): have_p.add(str(r["pmid"]))
            if r.get("doi"): have_d.add(r["doi"].lower())
    qs = [q.strip() for q in open(ROOT / f"config/queries/{H}.txt") if q.strip() and not q.startswith("#")]
    new, s = {}, {"queries": []}
    for q in qs:
        u = EUTILS + "esearch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "term": q, "retmax": 10000, "retmode": "json"})
        ids = retry(get_json, u)["esearchresult"].get("idlist", []); time.sleep(0.4)
        miss = [i for i in ids if i not in have_p]
        u = EUTILS + "esearch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "term": f"({q}) AND (\"2026/11/10\"[EDAT] : \"3000\"[EDAT])", "retmax": 500, "retmode": "json"})
        fresh_ids = retry(get_json, u)["esearchresult"].get("idlist", []); time.sleep(0.4)
        res, _ = retry(europepmc_search, f"({q}) AND FIRST_IDATE:[2026-11-10 TO 2026-12-31]", n=500)
        fresh_epmc = [epmc_record(r) for r in res]
        fresh_epmc = [r for r in fresh_epmc if not ((r.get("pmid") and r["pmid"] in have_p) or (r.get("doi") and r["doi"] in have_d))]
        s["queries"].append({"q": q, "pubmed_all": len(ids), "pubmed_not_in_candidates": len(miss),
                             "fresh_pubmed": len([i for i in fresh_ids if i not in have_p]), "fresh_epmc_new": len(fresh_epmc)})
        for r in lookup(miss):
            new.setdefault(("p", r["pmid"]), dict(r, route=f"cap:{q}"))
        for r in lookup([i for i in fresh_ids if i not in have_p]):
            new.setdefault(("p", r["pmid"]), dict(r, route=f"fresh_pubmed:{q}"))
        for r in fresh_epmc:
            new.setdefault(("p", r["pmid"]) if r.get("pmid") else ("d", r.get("doi") or r.get("title")), dict(r, route=f"fresh_epmc:{q}"))
    s["new_records"] = len(new)
    summ[H] = s
    with open(OUT / f"new_{H}.jsonl", "w") as f:
        for r in new.values(): f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(H, json.dumps(s)[:600], flush=True)
summ["failed_lookups"] = FAILED
json.dump(summ, open(OUT / ("summary_" + "_".join(summ) + ".json"), "w"), indent=1)
print("DONE")
