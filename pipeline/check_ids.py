#!/usr/bin/env python3
"""Check every DOI and PubMed ID in a submission sheet (no model).

"Invented identifiers. DOIs and PubMed IDs must correspond to real, published
sources." For each paper row: the DOI resolves at doi.org (Crossref or DataCite
metadata), the PMID exists in PubMed, and when both are given they point to the
same paper (PubMed's record carries that DOI). Prints one line per problem and
exits 1 if any.

Usage: check_ids.py submissions/H1.xlsx [...]
"""
import json
import sys
import time
import urllib.parse
import urllib.request

import openpyxl

UA = "meccog-literature-pipeline/0.1 (open-source research pipeline)"


def get_json(url, accept=None):
    h = {"User-Agent": UA}
    if accept:
        h["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
        return json.loads(r.read())


def doi_ok(doi):
    try:
        get_json("https://doi.org/" + urllib.parse.quote(doi), accept="application/vnd.citationstyles.csl+json")
        return True
    except Exception:
        return False


def pubmed_dois(pmids):
    out = {}
    for i in range(0, len(pmids), 100):
        chunk = pmids[i:i + 100]
        d = get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&tool=meccog-pipeline&id="
                     + ",".join(chunk))["result"]
        for p in chunk:
            rec = d.get(p)
            if not rec or rec.get("error"):
                out[p] = None
                continue
            ids = {x.get("idtype"): x.get("value", "").lower() for x in rec.get("articleids", [])}
            out[p] = ids.get("doi", "")
        time.sleep(0.4)
    return out


def main():
    bad = 0
    for path in sys.argv[1:]:
        ws = openpyxl.load_workbook(path)["Submission"]
        papers = [(r[4], str(r[1] or "").strip(), str(r[3] or "").strip())
                  for r in ws.iter_rows(min_row=3, values_only=True) if r[1]]
        pm = pubmed_dois([p for _, _, p in papers if p.isdigit()])
        for pid, doi, pmid in papers:
            if doi.upper() != "N/A" and not doi_ok(doi):
                print(f"{path} {pid}: DOI {doi} does not resolve"); bad += 1
            if pmid.isdigit():
                if pm.get(pmid) is None:
                    print(f"{path} {pid}: PMID {pmid} not found in PubMed"); bad += 1
                elif doi.upper() != "N/A" and pm[pmid] and pm[pmid] != doi.lower():
                    print(f"{path} {pid}: PMID {pmid} carries DOI {pm[pmid]}, sheet says {doi}"); bad += 1
            time.sleep(0.2)
        print(f"{path}: {len(papers)} papers checked")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
