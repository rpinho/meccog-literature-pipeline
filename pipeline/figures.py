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
    # PMC packages carry each figure twice: a full-size .jpg and a ~100 px .gif thumbnail. Prefer the
    # non-GIF file, and never return an image too small to read (see big_enough)
    for name, read in sorted(cands, key=lambda x: (x[0].lower().endswith(".gif"), -len(x[0]))):
        low = name.lower()
        if any(re.search(p, low) for p in pats) and not re.search(r"thumb|_t\.|icon", low):
            data = read()
            if big_enough(data):
                return name, data
    return None


def big_enough(data, min_width=400):
    """A figure image a person (or model) can read values off: at least 400 px wide."""
    try:
        from PIL import Image
        return Image.open(io.BytesIO(data)).size[0] >= min_width
    except Exception:
        return False


def _is_image_bytes(b):
    return (
        b[:3] == b"\xff\xd8\xff"
        or b[:4] == b"\x89PNG"
        or b[:3] == b"GIF"
        or (b[:4] == b"RIFF" and b[8:12] == b"WEBP")
    )


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
        for ext in ("", ".jpg", ".png", ".gif", ".webp"):
            try:
                b = _get(f"https://europepmc.org/articles/{meta['pmcid']}/bin/{href}{ext}")
                if _is_image_bytes(b) and big_enough(b):
                    return href + (ext or ".jpg"), b
            except Exception:
                pass
    return None


def _from_html(d, kind, num):
    """PMC article page: <img src=...> inside the figure whose caption starts 'Figure N'.
    Uses local fulltext.html if present; else fetches and caches pmc_page.html from PMC when pmcid is known."""
    h = d / "fulltext.html"
    if h.exists():
        html = h.read_text(errors="replace")
    else:
        cache = d / "pmc_page.html"
        if cache.exists():
            html = cache.read_text(errors="replace")
        else:
            meta_p = d / "meta.json"
            pmcid = json.load(open(meta_p)).get("pmcid") if meta_p.exists() else None
            if not pmcid:
                return None
            try:
                html = _get(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/").decode("utf-8", "replace")
                cache.write_text(html)
            except Exception:
                return None
    for m in re.finditer(r'<figure[^>]*>(.*?)</figure>', html, re.S | re.I):
        block = m.group(1)
        cap = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", block)).strip()
        # the figure's own label opens its caption ("FIGURE 5." in JBC); a later caption that merely mentions
        # "Figure 5" must not match
        if kind:
            pat = rf"(?:Supplementary|Extended\s+Data)\s+(?:Figure|Fig\.?)\s*S?\s*{num}\b|(?:Figure|Fig\.?)\s*S\s*{num}\b"
        else:
            pat = rf"(?:Figure|Fig\.?)\s*{num}\b"
        if not re.match(pat, cap, re.I):
            continue
        src = re.search(r'<img[^>]+src="([^"]+)"', block)
        if src:
            url = src.group(1)
            url = url if url.startswith("http") else "https://pmc.ncbi.nlm.nih.gov" + url
            try:
                b = _get(url)
                if _is_image_bytes(b) and big_enough(b):
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
    any_head = r"^\s*(?:(?:Supplementary|Extended\s+Data)\s+)?(?:Figure|Fig\.?)\s*S?\s*\d+(?:\s*$|[.:|]|\s+(?=[A-Z(]))"
    if kind:
        head = rf"^\s*(?:(?:Supplementary|Extended\s+Data)\s+(?:Figure|Fig\.?)\s*S?\s*{num}|(?:Figure|Fig\.?)\s*S\s*{num})(?:\s*$|[.:|]|\s+(?=[A-Z(]))"
        label = rf"(?:(?:Supplementary|Extended\s+Data)\s+(?:Figure|Fig\.?)\s*S?\s*{num}|(?:Figure|Fig\.?)\s*S\s*{num})\b"
    else:
        head = rf"^\s*(?:Figure|Fig\.?)\s*{num}(?:\s*$|[.:|]|\s+(?=[A-Z(]))"
        label = rf"(?<!Supplementary\s)(?<!Extended\sData\s)\b(?:Figure|Fig\.?)\s*{num}\b"

    def has_figure(page):
        # embedded images covering a meaningful share of the page, or vector drawings
        area = page.rect.width * page.rect.height
        img_area = sum((info["bbox"][2] - info["bbox"][0]) * (info["bbox"][3] - info["bbox"][1])
                       for info in page.get_image_info())
        return img_area > 0.10 * area or len(page.get_drawings()) > 120

    def has_other_head(page):
        return any(re.match(any_head, l, re.I) and not re.match(head, l, re.I)
                   for l in page.get_text().splitlines())

    pages = list(doc)
    legend = [i for i, pg in enumerate(pages) if any(re.match(head, l, re.I) for l in pg.get_text().splitlines())]
    # 1. the legend or labelled figure page itself carries the figure (journal layout, labelled manuscript pages)
    # 2. full-page figure immediately before its legend page (e.g. Cell Press, Springer, bioRxiv)
    # 3. full-page figure immediately after its legend page (skip pages carrying another figure's legend)
    # 4. author manuscripts: figure page carrying the label elsewhere in its text
    order = [i for i in legend if has_figure(pages[i])] \
        + [i - 1 for i in legend if i - 1 >= 0 and has_figure(pages[i - 1]) and not has_other_head(pages[i - 1])] \
        + [i + 1 for i in legend if i + 1 < len(pages) and has_figure(pages[i + 1]) and not has_other_head(pages[i + 1])] \
        + [i for i, pg in enumerate(pages) if i not in legend and has_figure(pg) and not has_other_head(pg) and re.search(label, pg.get_text(), re.I)]
    # 5. unlabelled figure pages after a legends section: main figure N is the N-th page with a figure
    if legend and not kind:
        after = [i for i in range(legend[0] + 1, len(pages)) if has_figure(pages[i]) and not has_other_head(pages[i])]
        if len(after) >= int(num):
            order.append(after[int(num) - 1])
    order += legend
    for i in order:
        pix = pages[i].get_pixmap(dpi=200)
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
