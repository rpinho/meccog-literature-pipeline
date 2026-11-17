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
MAX_BYTES = 25_000_000
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


def collect(d):
    files = []
    z = d / "supplementary.zip"
    if z.exists():
        zf = zipfile.ZipFile(z)
        for n in zf.namelist():
            if n.lower().endswith(TEXT_EXT) and zf.getinfo(n).file_size < MAX_BYTES:
                files.append((pathlib.Path(n).name, zf.read(n)))
    h = d / "fulltext.html"
    if not files and h.exists():
        html = h.read_text(errors="replace")
        links = sorted(set(re.findall(r'href="(/articles/instance/\d+/bin/[^"]+)"', html)))
        need_browser = []
        for l in links:
            if not l.lower().endswith(TEXT_EXT):
                continue
            url, name = "https://pmc.ncbi.nlm.nih.gov" + l, pathlib.Path(l).name
            try:
                b, _, _ = get(url)
            except Exception:
                b = b""
            if b[:4] == b"%PDF" or b[:2] == b"PK" or name.lower().endswith((".csv", ".txt", ".tsv")) and b:
                files.append((name, b))
            else:  # PMC's JavaScript download wall: retry in headless Chrome for Testing
                need_browser.append((url, d / "supp" / name, "file"))
        if need_browser:
            import browser
            got = browser.fetch(need_browser)
            for url, out, _ in need_browser:
                if str(got.get(url, "")).startswith("ok") and out.exists() and out.stat().st_size < MAX_BYTES:
                    files.append((out.name, out.read_bytes()))
    return files


def run(key):
    d = PAPERS / key
    m = json.load(open(d / "meta.json"))
    if m.get("status") != "ok":
        return key, None
    out = d / "supp.txt"
    if out.exists():
        return key, out.stat().st_size
    parts = []
    for name, b in collect(d):
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
    a = ap.parse_args()
    keys = a.keys.split(",") if a.keys else sorted(p.name for p in PAPERS.iterdir() if p.is_dir())
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(4) as ex:
        for k, size in ex.map(run, keys):
            if size is not None:
                print(k, size, flush=True)


if __name__ == "__main__":
    main()
