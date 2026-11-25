#!/usr/bin/env python3
"""Stage 3b: supplementary material as text.

Many panel-level numbers (P values, n) live only in the supplement. Writing
not_found_in_source for a value the supplement prints is one of the rule-book's
misconduct cases, so extraction reads the supplement too.

Sources: the Europe PMC supplementaryFiles zip (fetched in stage 3), else the
files the PMC article page links under /bin/. Converts PDF, DOCX, XLSX/CSV and
TXT; large tabular files are capped. Output: data/papers/<key>/supp.txt with a
[SUPPLEMENTARY FILE name] marker before each file.
"""
import argparse
import io
import json
import pathlib
import re
import zipfile

from fetch import get, PAPERS

MAX_PER_FILE = 60_000
MAX_BYTES = 100_000_000
TEXT_EXT = (".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt", ".tsv")


def pdf_text(b):
    import pymupdf as fitz
    doc = fitz.open(stream=b, filetype="pdf")
    return "\n".join(f"[SUPP PAGE {i + 1}]\n" + p.get_text() for i, p in enumerate(doc))


def docx_text(b):
    z = zipfile.ZipFile(io.BytesIO(b))
    x = z.read("word/document.xml").decode("utf-8", "replace")
    x = re.sub(r"</w:p>", "\n", x)
    return re.sub(r"<[^>]+>", "", x)


def xlsx_text(b):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"[SHEET {ws.title}]")
        for row in ws.iter_rows(values_only=True):
            if any(v is not None for v in row):
                out.append(" | ".join("" if v is None else str(v) for v in row))
            if sum(len(x) for x in out) > MAX_PER_FILE:
                break
    return "\n".join(out)


def to_text(name, b):
    n = name.lower()
    if n.endswith(".pdf") and b[:4] != b"%PDF":
        return None  # an HTML interstitial ("Preparing to download"), not the file
    if n.endswith((".docx", ".xlsx")) and b[:2] != b"PK":
        return None
    try:
        if n.endswith(".pdf"):
            return pdf_text(b)
        if n.endswith(".docx"):
            return docx_text(b)
        if n.endswith((".xlsx", ".xls")):
            return xlsx_text(b)
        if n.endswith((".csv", ".txt", ".tsv")):
            return b.decode("utf-8", "replace")
    except Exception as e:
        return f"[could not convert: {type(e).__name__}]"
    return None


def _xml_supp_names(d):
    x = d / "fulltext.xml"
    if not x.exists():
        return set()
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(x.read_bytes())
        xl = "{http://www.w3.org/1999/xlink}href"
        names = set()
        for el in root.iter():
            if el.tag in ("supplementary-material", "media"):
                for sub in el.iter():
                    h = sub.get(xl)
                    if h and h.lower().endswith(TEXT_EXT):
                        names.add(pathlib.Path(h).name)
        return names
    except Exception:
        return set()


def _valid_bytes(name, b):
    n = name.lower()
    if n.endswith(".pdf"):
        return b[:4] == b"%PDF"
    if n.endswith((".docx", ".xlsx")):
        return b[:2] == b"PK"
    return bool(b) and not b.lstrip().startswith(b"<")


def collect(d, pmcid=None):
    files = []
    seen = set()
    z = d / "supplementary.zip"
    if z.exists():
        zf = zipfile.ZipFile(z)
        for n in zf.namelist():
            name = pathlib.Path(n).name
            if name.lower().endswith(TEXT_EXT) and zf.getinfo(n).file_size < MAX_BYTES:
                b = zf.read(n)
                if _valid_bytes(name, b):
                    files.append((name, b))
                    seen.add(name)
    html = None
    h = d / "fulltext.html"
    xml_names = _xml_supp_names(d)
    need_pmc_html = (not files) or bool(xml_names - seen)
    if h.exists() and need_pmc_html:
        html = h.read_text(errors="replace")
    elif pmcid and need_pmc_html:
        try:
            body, _, _ = get(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/")
            html = body.decode("utf-8", "replace")
        except Exception:
            html = None
    if html:
        links = sorted(set(re.findall(r'href="(/articles/instance/\d+/bin/[^"]+)"', html)))
        need_browser = []
        for l in links:
            name = pathlib.Path(l).name
            if not name.lower().endswith(TEXT_EXT) or name in seen:
                continue
            cached = d / "supp" / name
            if cached.exists() and cached.stat().st_size < MAX_BYTES and _valid_bytes(name, cached.read_bytes()):
                files.append((name, cached.read_bytes()))
                seen.add(name)
                continue
            url = "https://pmc.ncbi.nlm.nih.gov" + l
            try:
                b, _, _ = get(url)
            except Exception:
                b = b""
            if _valid_bytes(name, b) and len(b) < MAX_BYTES:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(b)
                files.append((name, b))
                seen.add(name)
            else:  # PMC's JavaScript download wall: retry in headless Chrome for Testing
                need_browser.append((url, cached, "file"))
        if need_browser:
            import browser
            got = browser.fetch(need_browser)
            for url, out, _ in need_browser:
                if str(got.get(url, "")).startswith("ok") and out.exists() and out.stat().st_size < MAX_BYTES:
                    b = out.read_bytes()
                    if _valid_bytes(out.name, b):
                        files.append((out.name, b))
                        seen.add(out.name)
    return files


def run(key, retry_empty=False):
    d = PAPERS / key
    m = json.load(open(d / "meta.json"))
    if m.get("status") != "ok":
        return key, None
    out = d / "supp.txt"
    if out.exists() and not (retry_empty and out.stat().st_size == 0):
        return key, out.stat().st_size
    parts = []
    for name, b in collect(d, pmcid=m.get("pmcid")):
        t = to_text(name, b)
        if t:
            parts.append(f"[SUPPLEMENTARY FILE {name}]\n" + t[:MAX_PER_FILE])
    out.write_text("\n\n".join(parts))
    m["supp_files"] = [p.split("\n", 1)[0] for p in parts]
    json.dump(m, open(d / "meta.json", "w"), indent=1)
    return key, out.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys")
    ap.add_argument("--retry-empty", action="store_true", help="re-collect papers whose supp.txt is 0 bytes")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    keys = a.keys.split(",") if a.keys else sorted(p.name for p in PAPERS.iterdir() if p.is_dir())
    import concurrent.futures as cf
    if a.workers <= 1:
        for k in keys:
            _, size = run(k, retry_empty=a.retry_empty)
            if size is not None:
                print(k, size, flush=True)
    else:
        with cf.ThreadPoolExecutor(a.workers) as ex:
            for k, size in ex.map(lambda k: run(k, retry_empty=a.retry_empty), keys):
                if size is not None:
                    print(k, size, flush=True)


if __name__ == "__main__":
    main()
