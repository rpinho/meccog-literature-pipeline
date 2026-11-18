#!/usr/bin/env python3
"""Stage 3: get full text (and supplements) for screened papers.

Routes, in order, each recorded per paper:
  1. Europe PMC fullTextXML (needs a PMCID), plus its supplementaryFiles zip
  2. PMC OA package (figures as images) when the article is in the OA subset
  3. OpenAlex open-access locations (the Unpaywall data): PDF, else landing HTML
  4. bioRxiv/medRxiv full text for preprints via their DOI
A paper none of these reach is marked unreached, with every route tried, so the
sheet can say full_text_unavailable honestly.

Output: data/papers/<key>/ {meta.json, fulltext.xml|fulltext.pdf|fulltext.html,
supplementary.zip, text.txt}. Papers are shared across hypotheses.
"""
import argparse
import concurrent.futures as cf
import io
import json
import pathlib
import re
import tarfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAPERS = ROOT / "data" / "papers"
UA = "Mozilla/5.0 (meccog-literature-pipeline; open-source research)"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/"


def get(url, tries=3, accept=None):
    last = None
    for i in range(tries):
        try:
            h = {"User-Agent": UA}
            if accept:
                h["Accept"] = accept
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=90) as r:
                return r.read(), r.headers.get("Content-Type", ""), r.geturl()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 404, 410):
                break
            time.sleep(2 * (i + 1))
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


import threading
_BIORXIV_LOCK = threading.Lock()
_BIORXIV_LAST = [0.0]


def biorxiv_get(url):
    """biorxiv.org answers HTTP 429 / Cloudflare 1015 to bursts: one request per 10 s, all threads."""
    with _BIORXIV_LOCK:
        wait = 10 - (time.time() - _BIORXIV_LAST[0])
        if wait > 0:
            time.sleep(wait)
        try:
            return get(url, tries=1)
        finally:
            _BIORXIV_LAST[0] = time.time()


def paper_key(r):
    if r.get("pmid"):
        return "pmid" + r["pmid"]
    if r.get("doi"):
        return "doi_" + re.sub(r"[^A-Za-z0-9]+", "_", r["doi"])
    return "t_" + re.sub(r"[^A-Za-z0-9]+", "_", (r.get("title") or "untitled"))[:60]


def resolve_ids(r):
    """Fill pmcid/doi/pmid from Europe PMC when one is missing."""
    if r.get("pmcid") and r.get("doi") and r.get("pmid"):
        return r
    q = f"EXT_ID:{r['pmid']} AND SRC:MED" if r.get("pmid") else (f'DOI:"{r["doi"]}"' if r.get("doi") else None)
    if not q:
        return r
    try:
        d = json.loads(get(EPMC + "search?" + urllib.parse.urlencode({"query": q, "format": "json", "resultType": "core"}))[0])
        res = d.get("resultList", {}).get("result", [])
        if res:
            x = res[0]
            r.setdefault("pmcid", x.get("pmcid"))
            r["pmcid"] = r.get("pmcid") or x.get("pmcid")
            r["doi"] = r.get("doi") or (x.get("doi") or "").lower() or None
            r["pmid"] = r.get("pmid") or x.get("pmid")
    except Exception:
        pass
    return r


def xml_to_text(xml_bytes):
    """Body text with section headings, figure/table captions marked, and
    supplementary material captions. Keeps the words as printed."""
    root = ET.fromstring(xml_bytes)
    out = []

    def txt(el):
        return re.sub(r"\s+", " ", "".join(el.itertext())).strip()

    t = root.find(".//article-title")
    if t is not None:
        out.append("# " + txt(t))
    ab = root.find(".//abstract")
    if ab is not None:
        out.append("## Abstract\n" + txt(ab))
    body = root.find(".//body")

    def walk(el, depth=2):
        for ch in el:
            tag = ch.tag
            if tag == "sec":
                title = ch.find("title")
                if title is not None:
                    out.append("#" * min(depth, 5) + " " + txt(title))
                walk(ch, depth + 1)
            elif tag == "p":
                nested = [x for x in ch.iter() if x.tag in ("fig", "table-wrap") and x is not ch]
                if not nested:
                    out.append(txt(ch))
                else:  # figures inside a paragraph: paragraph text first, then each legend marked
                    def para_text(el):
                        parts = [el.text or ""]
                        for c in el:
                            if c.tag not in ("fig", "table-wrap"):
                                parts.append(para_text(c))
                            parts.append(c.tail or "")
                        return "".join(parts)
                    out.append(re.sub(r"\s+", " ", para_text(ch)).strip())
                    for x in nested:
                        lab, cap = x.find("label"), x.find("caption")
                        out.append(f"[{'FIGURE' if x.tag == 'fig' else 'TABLE'} {txt(lab) if lab is not None else ''}] "
                                   + (txt(cap) if cap is not None else ""))
                        if x.tag == "table-wrap":
                            tb = x.find(".//table")
                            if tb is not None:
                                for tr in tb.iter("tr"):
                                    out.append(" | ".join(txt(c) for c in tr if c.tag in ("td", "th")))
            elif tag in ("fig", "table-wrap"):
                lab = ch.find("label")
                cap = ch.find("caption")
                out.append(f"[{'FIGURE' if tag == 'fig' else 'TABLE'} {txt(lab) if lab is not None else ''}] "
                           + (txt(cap) if cap is not None else ""))
                if tag == "table-wrap":
                    tb = ch.find(".//table")
                    if tb is not None:
                        for tr in tb.iter("tr"):
                            out.append(" | ".join(txt(c) for c in tr if c.tag in ("td", "th")))
            elif tag in ("list",):
                out.append(txt(ch))
            elif tag != "title":
                walk(ch, depth)

    if body is not None:
        walk(body)
    # figures and tables outside <body>: <floats-group> (common in Europe PMC XML) and <back>
    seen = set(id(x) for x in body.iter()) if body is not None else set()
    for el in root.iter():
        if id(el) in seen or el.tag not in ("fig", "table-wrap"):
            continue
        lab, cap = el.find("label"), el.find("caption")
        out.append(f"[{'FIGURE' if el.tag == 'fig' else 'TABLE'} {txt(lab) if lab is not None else ''}] "
                   + (txt(cap) if cap is not None else ""))
        if el.tag == "table-wrap":
            tb = el.find(".//table")
            if tb is not None:
                for tr in tb.iter("tr"):
                    out.append(" | ".join(txt(c) for c in tr if c.tag in ("td", "th")))
    for sm in root.iter("supplementary-material"):
        out.append("[SUPPLEMENT] " + txt(sm))
    return "\n\n".join(x for x in out if x)


def html_to_text(raw):
    """Readable text from an article HTML page. Accepted as full text only when
    it carries a Results section and figure legends (landing pages do not)."""
    import html as H
    t = raw.decode("utf-8", "replace")
    m = re.search(r"(?is)<article\b.*</article>", t)  # main article only, when the page marks it
    if m:
        t = m.group(0)
    t = re.sub(r"(?is)<(script|style|nav|header|footer|noscript|svg)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<(h[1-6])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)[1]) + " ", t)
    t = re.sub(r"(?i)</?(p|div|li|tr|section|figcaption|figure|table|br)[^>]*>", "\n", t)
    t = re.sub(r"(?i)</t[dh]>", " | ", t)
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t\u00a0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t).strip()
    ok = len(t) > 20000 and re.search(r"\bResults\b|\bRESULTS\b", t) and re.search(r"\b(Fig\.?|Figure) ?\d", t)
    return t if ok else None


def pdf_to_text(path):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        return "\n\n".join(f"[PAGE {i + 1}]\n" + p.get_text() for i, p in enumerate(doc))
    except ImportError:
        from pypdf import PdfReader
        return "\n\n".join(f"[PAGE {i + 1}]\n" + (p.extract_text() or "") for i, p in enumerate(PdfReader(path).pages))


def fetch_one(r):
    r = resolve_ids(dict(r))
    k = paper_key(r)
    d = PAPERS / k
    d.mkdir(parents=True, exist_ok=True)
    meta_p = d / "meta.json"
    if meta_p.exists():
        m = json.load(open(meta_p))
        if m.get("status") == "ok":
            return m
    for old in ("text.txt", "fulltext.pdf", "fulltext.xml", "fulltext.html"):
        (d / old).unlink(missing_ok=True)  # a refetch must not mix files from two versions
    tried = []
    m = {"key": k, "pmid": r.get("pmid"), "pmcid": r.get("pmcid"), "doi": r.get("doi"),
         "title": r.get("title"), "year": r.get("year"), "source": r.get("source")}
    text = None
    manual = ROOT / "data" / "manual_pdfs" / f"{k}.pdf"
    if manual.exists() and manual.read_bytes()[:4] == b"%PDF":
        # downloaded by hand in a browser (publisher pages that block scripts); same document as the DOI
        (d / "fulltext.pdf").write_bytes(manual.read_bytes())
        text = pdf_to_text(d / "fulltext.pdf")
        m["route"] = "manual_pdf"
        tried.append("manual_pdf:ok")
    if text is None and r.get("pmcid"):
        try:
            x, _, _ = get(EPMC + f"{r['pmcid']}/fullTextXML")
            (d / "fulltext.xml").write_bytes(x)
            text = xml_to_text(x)
            m["route"] = "europepmc_fullTextXML"
            tried.append("europepmc_fullTextXML:ok")
        except Exception as e:
            tried.append(f"europepmc_fullTextXML:{type(e).__name__}:{getattr(e, 'code', '')}")
        if text is None:  # PMC Cloud S3 (OA + author manuscripts): JATS XML, figures, PDF
            try:
                lst, _, _ = get(f"https://pmc-oa-opendata.s3.amazonaws.com/?list-type=2&prefix={r['pmcid']}.&max-keys=200")
                keys = re.findall(rb"<Key>([^<]+)</Key>", lst)
                keys = [k.decode() for k in keys]
                if keys:
                    ver = sorted({k.split("/")[0] for k in keys})[-1]
                    for k in keys:
                        if not k.startswith(ver + "/"):
                            continue
                        name = k.split("/")[-1]
                        url = "https://pmc-oa-opendata.s3.amazonaws.com/" + k
                        if name.endswith(".xml"):
                            x, _, _ = get(url)
                            (d / "fulltext.xml").write_bytes(x)
                            text = xml_to_text(x)
                            m["route"] = "pmc_s3_xml"
                        elif name.endswith(".pdf"):
                            (d / "fulltext.pdf").write_bytes(get(url)[0])
                        elif re.search(r"\.(jpg|jpeg|png|gif|tif)$", name, re.I):
                            (d / "figures").mkdir(exist_ok=True)
                            (d / "figures" / name).write_bytes(get(url)[0])
                    tried.append("pmc_s3:ok" if text else "pmc_s3:no_xml")
                else:
                    tried.append("pmc_s3:absent")
            except Exception as e:
                tried.append(f"pmc_s3:{getattr(e, 'code', type(e).__name__)}")
        if text is None:  # PMC article page (covers author manuscripts outside the OA bucket)
            try:
                body, _, final = get(f"https://pmc.ncbi.nlm.nih.gov/articles/{r['pmcid']}/")
                (d / "fulltext.html").write_bytes(body)
                text = html_to_text(body)
                if text:
                    m["route"] = "pmc_html"
                tried.append("pmc_html:" + ("ok" if text else "not_fulltext"))
            except Exception as e:
                tried.append(f"pmc_html:{getattr(e, 'code', type(e).__name__)}")
        if text is None:  # Europe PMC rendered PDF of the PMC copy
            try:
                body, _, _ = get(f"https://europepmc.org/articles/{r['pmcid']}?pdf=render")
                if body[:4] == b"%PDF":
                    (d / "fulltext.pdf").write_bytes(body)
                    text = pdf_to_text(d / "fulltext.pdf")
                    m["route"] = "europepmc_pdf_render"
                tried.append("europepmc_pdf_render:" + ("ok" if text else "not_pdf"))
            except Exception as e:
                tried.append(f"europepmc_pdf_render:{getattr(e, 'code', type(e).__name__)}")
        try:
            z, _, _ = get(EPMC + f"{r['pmcid']}/supplementaryFiles")
            if z[:2] == b"PK":
                (d / "supplementary.zip").write_bytes(z)
                m["supplementary"] = zipfile.ZipFile(io.BytesIO(z)).namelist()
                tried.append("europepmc_supplementaryFiles:ok")
        except Exception as e:
            tried.append(f"europepmc_supplementaryFiles:{getattr(e, 'code', type(e).__name__)}")
        try:  # PMC OA package: figure images
            oa, _, _ = get("https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=" + r["pmcid"])
            link = re.search(rb'href="([^"]+\.tar\.gz)"', oa)
            if link:
                url = link.group(1).decode().replace("ftp://", "https://")
                tgz, _, _ = get(url)
                figdir = d / "figures"
                figdir.mkdir(exist_ok=True)
                with tarfile.open(fileobj=io.BytesIO(tgz)) as tf:
                    for mem in tf.getmembers():
                        if mem.isfile() and re.search(r"\.(jpg|jpeg|png|gif|tif|tiff)$", mem.name, re.I):
                            (figdir / pathlib.Path(mem.name).name).write_bytes(tf.extractfile(mem).read())
                        elif mem.isfile() and mem.name.lower().endswith(".pdf") and not (d / "fulltext.pdf").exists():
                            (d / "fulltext.pdf").write_bytes(tf.extractfile(mem).read())
                m["figures"] = sorted(p.name for p in figdir.iterdir())
                tried.append("pmc_oa_package:ok")
            else:
                tried.append("pmc_oa_package:not_in_oa_subset")
        except Exception as e:
            tried.append(f"pmc_oa_package:{getattr(e, 'code', type(e).__name__)}")
    if text is None and r.get("doi"):
        try:
            w = json.loads(get("https://api.openalex.org/works/doi:" + urllib.parse.quote(r["doi"]))[0])
            locs = [w.get("best_oa_location") or {}] + (w.get("oa_locations") or [])
            is_preprint = (r.get("source") == "PPR") or str(r.get("doi", "")).startswith(("10.1101/", "10.64898/", "10.21203/", "10.2139/"))
            for loc in locs:
                if loc.get("version") == "submittedVersion" and not is_preprint:
                    # a preprint copy is a different document: its figures and numbers can differ
                    tried.append(f"oa_location:{loc.get('landing_page_url')}:skipped_preprint_version")
                    continue
                for url in (loc.get("pdf_url"), loc.get("landing_page_url")):
                    if not url or text:
                        continue
                    try:
                        body, ctype, final = get(url)
                        if body[:4] == b"%PDF":
                            (d / "fulltext.pdf").write_bytes(body)
                            text = pdf_to_text(d / "fulltext.pdf")
                            m["route"] = "openalex_oa_pdf"
                            m["url"] = final
                        elif "html" in ctype and len(body) > 30000:
                            ht = html_to_text(body)  # None for abstract-only landing pages
                            if ht:
                                (d / "fulltext.html").write_bytes(body)
                                text = ht
                                m["route"] = "oa_html"
                                m["url"] = final
                        tried.append(f"oa_location:{url}:ok")
                    except Exception as e:
                        tried.append(f"oa_location:{url}:{getattr(e, 'code', type(e).__name__)}")
        except Exception as e:
            tried.append(f"openalex:{getattr(e, 'code', type(e).__name__)}")
    if text is None and r.get("doi", "") and r["doi"].startswith(("10.1101/", "10.64898/")):
        for server in ("biorxiv", "medrxiv"):  # JATS XML of the latest version, via the bioRxiv API
            try:
                c = json.loads(get(f"https://api.biorxiv.org/details/{server}/{r['doi']}")[0]).get("collection") or []
                if not c:
                    continue
                m["preprint_version"] = c[-1].get("version")
                m["published_doi"] = (c[-1].get("published") or "").lower() or None
                x, _, _ = biorxiv_get(c[-1]["jatsxml"])
                (d / "fulltext.xml").write_bytes(x)
                text = xml_to_text(x)
                m["route"] = f"{server}_jats"
                tried.append(f"{server}_jats:ok")
                break
            except Exception as e:
                tried.append(f"{server}_jats:{getattr(e, 'code', type(e).__name__)}")
        if text is None:
            try:
                body, _, final = biorxiv_get(f"https://www.biorxiv.org/content/{r['doi']}.full.pdf")
                if body[:4] == b"%PDF":
                    (d / "fulltext.pdf").write_bytes(body)
                    text = pdf_to_text(d / "fulltext.pdf")
                    m["route"] = "biorxiv_pdf"
                tried.append("biorxiv_pdf:" + ("ok" if text else "not_pdf"))
            except Exception as e:
                tried.append(f"biorxiv_pdf:{getattr(e, 'code', type(e).__name__)}")
    m["tried"] = tried
    if text and len(text) > 5000:
        (d / "text.txt").write_text(text)
        m["status"] = "ok"
        m["chars"] = len(text)
    else:
        m["status"] = "unreached"
    json.dump(m, open(meta_p, "w"), indent=1)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hypothesis")
    ap.add_argument("--decisions", default="yes,maybe")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    want = set(a.decisions.split(","))
    rows = [json.loads(l) for l in open(ROOT / f"data/{a.hypothesis}/screened.jsonl")]
    rows = [r for r in rows if (r.get("screen") or {}).get("decision") in want]
    with cf.ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(fetch_one, rows))
    idx = ROOT / f"data/{a.hypothesis}/fetched.jsonl"
    with open(idx, "w") as f:
        for r, m in zip(rows, res):
            f.write(json.dumps({"key": m["key"], "status": m["status"], "route": m.get("route"),
                                "decision": r["screen"]["decision"], "relevance": r["screen"]["relevance"],
                                "title": r.get("title")}) + "\n")
    from collections import Counter
    print(a.hypothesis, len(rows), Counter(m["status"] for m in res), Counter(m.get("route") for m in res))


if __name__ == "__main__":
    main()
