#!/usr/bin/env python3
"""Stage 1: build the candidate pool for one hypothesis.

Three routes, each logged with its hit count (a search that returned nothing is
part of the method):
  1. PubMed E-utilities, one query per line in config/queries/<H>.txt
  2. Europe PMC search (adds preprints), same queries
  3. Citation snowball from the starting reference: its references and the
     papers citing it (OpenAlex)

Output: data/<H>/candidates.jsonl (one paper per line, merged by PMID/DOI) and
data/<H>/search_log.jsonl. Standard library only.
"""
import argparse
import json
import pathlib
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "meccog-literature-pipeline/0.1 (open-source research pipeline)"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
OPENALEX = "https://api.openalex.org/"


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # network hiccups and 429s: back off
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def get_json(url):
    return json.loads(get(url))


def pubmed_search(q, retmax=300):
    u = EUTILS + "esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": q, "retmax": retmax, "retmode": "json", "tool": "meccog-pipeline"})
    d = get_json(u)["esearchresult"]
    time.sleep(0.4)
    return d.get("idlist", []), int(d.get("count", 0))


def europepmc_search(q, n=300):
    out, cursor = [], "*"
    while len(out) < n:
        u = EPMC + "search?" + urllib.parse.urlencode(
            {"query": q, "format": "json", "pageSize": 100, "cursorMark": cursor, "resultType": "core"})
        d = get_json(u)
        res = d.get("resultList", {}).get("result", [])
        out += res
        nxt = d.get("nextCursorMark")
        if not res or not nxt or nxt == cursor:
            break
        cursor = nxt
    return out[:n], int(d.get("hitCount", 0))


def epmc_record(r):
    return {
        "pmid": r.get("pmid"), "pmcid": r.get("pmcid"), "doi": (r.get("doi") or "").lower() or None,
        "title": r.get("title"), "journal": (r.get("journalInfo") or {}).get("journal", {}).get("title")
        or r.get("bookOrReportDetails", {}).get("publisher"),
        "year": r.get("pubYear"), "source": r.get("source"),  # MED, PPR (preprint), PMC ...
        "pubtype": (r.get("pubTypeList") or {}).get("pubType", []),
        "abstract": r.get("abstractText"), "is_oa": r.get("isOpenAccess") == "Y",
        "has_fulltext_xml": r.get("hasTextMinedTerms") == "Y" or r.get("inEPMC") == "Y",
    }


def epmc_lookup_pmids(pmids):
    """Fetch Europe PMC core records for a list of PMIDs, 50 per query."""
    recs = []
    for i in range(0, len(pmids), 50):
        chunk = pmids[i:i + 50]
        q = "EXT_ID:(" + " OR ".join(chunk) + ") AND SRC:MED"
        res, _ = europepmc_search(q, n=len(chunk))
        recs += [epmc_record(r) for r in res]
    return recs


def openalex_work(pmid):
    return get_json(OPENALEX + f"works/pmid:{pmid}")


def openalex_ids_to_records(ids):
    recs = []
    for i in range(0, len(ids), 50):
        chunk = [x.rsplit("/", 1)[-1] for x in ids[i:i + 50]]
        u = OPENALEX + "works?" + urllib.parse.urlencode(
            {"filter": "openalex:" + "|".join(chunk), "per-page": 50,
             "select": "id,doi,ids,title,publication_year,type"})
        for w in get_json(u).get("results", []):
            ids_ = w.get("ids") or {}
            pm = (ids_.get("pmid") or "").rsplit("/", 1)[-1] or None
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower() or None
            recs.append({"pmid": pm, "doi": doi, "title": w.get("title"),
                         "year": w.get("publication_year"), "openalex": w["id"]})
    return recs


def snowball(pmid, max_citing=600):
    w = openalex_work(pmid)
    refs = openalex_ids_to_records(w.get("referenced_works", []))
    citing, page = [], 1
    while page and len(citing) < max_citing:
        # page-based paging: anonymous cursor paging past page 1 returned HTTP 401 (11-17)
        u = OPENALEX + "works?" + urllib.parse.urlencode(
            {"filter": f"cites:{w['id'].rsplit('/', 1)[-1]}", "per-page": 200, "page": page,
             "select": "id,doi,ids,title,publication_year,type"})
        d = get_json(u)
        for x in d.get("results", []):
            ids_ = x.get("ids") or {}
            citing.append({"pmid": (ids_.get("pmid") or "").rsplit("/", 1)[-1] or None,
                           "doi": (x.get("doi") or "").replace("https://doi.org/", "").lower() or None,
                           "title": x.get("title"), "year": x.get("publication_year"), "openalex": x["id"]})
        page = page + 1 if len(d.get("results", [])) == 200 else None
    return refs, citing


def key(r):
    return ("pmid", r["pmid"]) if r.get("pmid") else ("doi", r.get("doi") or r.get("title"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis", help="H1..H5")
    a = ap.parse_args()
    hyps = {h["id"]: h for h in json.load(open(ROOT / "config/hypotheses.json"))["hypotheses"]}
    h = hyps[a.hypothesis]
    out = ROOT / "data" / h["id"]
    out.mkdir(parents=True, exist_ok=True)
    queries = [q.strip() for q in open(ROOT / f"config/queries/{h['id']}.txt")
               if q.strip() and not q.startswith("#")]
    pool, log = {}, []

    def add(rec, route):
        k = key(rec)
        cur = pool.setdefault(k, dict(rec, routes=[]))
        for f, v in rec.items():
            if v and not cur.get(f):
                cur[f] = v
        if route not in cur["routes"]:
            cur["routes"].append(route)

    for q in queries:
        ids, count = pubmed_search(q)
        log.append({"route": "pubmed", "query": q, "hits": count, "kept": len(ids)})
        for r in epmc_lookup_pmids(ids):
            add(r, "pubmed:" + q)
        res, count = europepmc_search(q)
        log.append({"route": "europepmc", "query": q, "hits": count, "kept": len(res)})
        for r in res:
            add(epmc_record(r), "europepmc:" + q)

    refs, citing = snowball(h["reference"]["pmid"])
    log.append({"route": "openalex_refs", "query": h["reference"]["pmid"], "hits": len(refs)})
    log.append({"route": "openalex_citing", "query": h["reference"]["pmid"], "hits": len(citing)})
    for r in refs:
        add(r, "snowball:references")
    for r in citing:
        add(r, "snowball:citing")

    # fill abstracts for snowball-only records through Europe PMC
    missing = [r["pmid"] for r in pool.values() if r.get("pmid") and not r.get("abstract")]
    for r in epmc_lookup_pmids(missing):
        add(r, "fill")

    with open(out / "candidates.jsonl", "w") as f:
        for r in pool.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "search_log.jsonl", "w") as f:
        for r in log:
            f.write(json.dumps(r) + "\n")
    print(f"{h['id']}: {len(pool)} candidates; " + "; ".join(f"{x['route']} {x['hits']}" for x in log))


if __name__ == "__main__":
    main()
