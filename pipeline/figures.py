#!/usr/bin/env python3
"""Find the image of a cited figure, for reading values off it later.

No model here: this only maps a sheet row's data_location ("Fig 3B",
"Supplementary Fig S6H") to an image file. Sources, in order:
  1. figure images that came with the paper (PMC S3 bucket, Europe PMC
     supplementaryFiles zip), matched by figure number in the file name
  0. (first) the PDF, see 2: highest resolution
  3. JATS <graphic> hrefs fetched from Europe PMC; 4. figure <img> on the PMC article page
  2. the PDF (ours or the manual one): the page whose text starts the legend
     "Figure N" / "Fig. N", rendered at 200 dpi (PDF images are ~3x the
     resolution of PMC web JPGs)
Writes data/papers/<key>/figimg/<fig-id>.png and returns its path.
"""
import io
import json
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAPERS = ROOT / "data" / "papers"


def parse_loc(loc):
    """'Supplementary Fig. S6H' -> ('S', '6'); 'Fig 3B' -> ('', '3'); None if no figure."""
    l = str(loc)
    m = re.search(r"(Supp\w*\.?\s*|Extended Data\s*|S\s*)?(?:Fig(?:ure)?s?\.?)\s*(S?)(\d+)", l, re.I)
    if not m:
        return None
    supp = bool(m.group(1) or m.group(2)) or bool(re.match(r"\s*(Supp|Extended)", l, re.I))
    return ("S" if supp else "", m.group(3))


def _from_files(d, kind, num):
    cands = []
    for p in list((d / "figures").glob("*")) if (d / "figures").exists() else []:
        cands.append((p.name, p.read_bytes))
    z = d / "supplementary.zip"
    if z.exists():
        zf = zipfile.ZipFile(z)
        for n in zf.namelist():
            if re.search(r"\.(jpe?g|png|gif|tiff?)$", n, re.I):
                cands.append((pathlib.Path(n).name, (lambda n=n: zf.read(n))))
    pats = ([rf"(?:^|[^0-9a-z])(?:fig|f|gr)0*{num}(?:[^0-9]|$)", rf"g0*{num}\.(?:jpe?g|png|gif)$"] if not kind else
            [rf"(?:fig|f)s0*{num}(?:[^0-9]|$)", rf"supp\w*fig\w*0*{num}(?:[^0-9]|$)"])
    for name, read in sorted(cands, key=lambda x: -len(x[0])):
        low = name.lower()
        if any(re.search(p, low) for p in pats) and not re.search(r"thumb|_t\.|icon", low):
            return name, read()
    return None


def _get(url):
    from fetch import get
    body, _, _ = get(url)
    return body


def _from_xml(d, kind, num):
    """JATS <fig><label>Figure 3</label>...<graphic xlink:href="x"/>: fetch the image from Europe PMC."""
    x = d / "fulltext.xml"
    meta = json.load(open(d / "meta.json"))
    if not x.exists() or not meta.get("pmcid"):
        return None
    import xml.etree.ElementTree as ET
    root = ET.fromstring(x.read_bytes())
    XL = "{http://www.w3.org/1999/xlink}href"
    for fig in root.iter("fig"):
        lab = "".join(fig.find("label").itertext()) if fig.find("label") is not None else ""
        if not re.search(rf"(?:Fig(?:ure)?\.?)\s*{'S' if kind else ''}{num}\b", lab, re.I):
            continue
        if bool(re.search(r"\bS\d", lab)) != bool(kind):
            continue
        g = fig.find(".//graphic")
        if g is None or not g.get(XL):
            continue
        href = g.get(XL)
        for ext in ("", ".jpg", ".png", ".gif"):
            try:
                b = _get(f"https://europepmc.org/articles/{meta['pmcid']}/bin/{href}{ext}")
                if b[:3] == b"\xff\xd8\xff" or b[:4] == b"\x89PNG" or b[:3] == b"GIF":
                    return href + (ext or ".jpg"), b
            except Exception:
                pass
    return None


def _from_html(d, kind, num):
    """PMC article page: <img src=...> inside the figure whose caption starts 'Figure N'."""
    h = d / "fulltext.html"
    if not h.exists():
        return None
    html = h.read_text(errors="replace")
    for m in re.finditer(r'<figure[^>]*>(.*?)</figure>', html, re.S | re.I):
        block = m.group(1)
        cap = re.sub(r"<[^>]+>", " ", block)
        if not re.search(rf"(?:Figure|Fig\.?)\s*{'S' if kind else ''}{num}\b", cap):
            continue
        src = re.search(r'<img[^>]+src="([^"]+)"', block)
        if src:
            url = src.group(1)
            url = url if url.startswith("http") else "https://pmc.ncbi.nlm.nih.gov" + url
            try:
                b = _get(url)
                if b[:3] == b"\xff\xd8\xff" or b[:4] == b"\x89PNG" or b[:3] == b"GIF":
                    return pathlib.Path(url).name, b
            except Exception:
                pass
    return None


def _from_pdf(d, kind, num):
    pdf = d / "fulltext.pdf"
    if not pdf.exists():
        return None
    import pymupdf
    doc = pymupdf.open(pdf)
    head = rf"^\s*(?:Supplementary\s+)?(?:Figure|Fig\.?)\s*{'S' if kind else ''}{num}[.:|\s]"
    for i, page in enumerate(doc):
        if any(re.match(head, line) for line in page.get_text().splitlines()):
            pix = page.get_pixmap(dpi=200)
            return f"page{i + 1}.png", pix.tobytes("png")
    return None


def figure_image(key, loc):
    d = PAPERS / key
    parsed = parse_loc(loc)
    if not parsed:
        return None
    kind, num = parsed
    out_dir = d / "figimg"
    out = out_dir / f"{kind}{num}.png"
    if out.exists():
        return out
    got = _from_pdf(d, kind, num) or _from_files(d, kind, num) or _from_xml(d, kind, num) or _from_html(d, kind, num)
    if not got:
        return None
    out_dir.mkdir(exist_ok=True)
    name, data = got
    if name.lower().endswith(".png"):
        out.write_bytes(data)
    else:
        from PIL import Image
        Image.open(io.BytesIO(data)).convert("RGB").save(out)
    json.dump({"source": name}, open(out_dir / f"{kind}{num}.json", "w"))
    return out


if __name__ == "__main__":
    import sys
    import openpyxl
    for H in sys.argv[1:]:
        ws = openpyxl.load_workbook(ROOT / f"submissions/{H}.xlsx")["Submission"]
        doi_key = {}
        for p in PAPERS.glob("*/meta.json"):
            m = json.load(open(p))
            if m.get("doi"):
                doi_key[m["doi"].lower()] = m["key"]
        cur, n, hit, need, need_hit = None, 0, 0, 0, 0
        for r in ws.iter_rows(min_row=3, values_only=True):
            if r[1]:
                cur = doi_key.get(str(r[1]).lower())
                continue
            if not cur:
                continue
            n += 1
            img = figure_image(cur, r[10])
            hit += bool(img)
            if str(r[11]).lower() == "qualitative" or r[14] == "ambiguous_panel":
                need += 1
                need_hit += bool(img)
        print(f"{H}: rows {n}, figure image found {hit}; rows that would gain from a figure read {need}, image found {need_hit}")
