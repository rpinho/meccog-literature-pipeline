"""Layered quote matching against a paper's text.

A naive substring test calls most correct quotes missing: markup spacing, the
multiplication sign, curly quotes, NBSP, soft hyphens, ligatures, Greek letters
written out ("Abeta" vs "Aβ"), inline cross-references. In the organizers'
earlier collab a naive test flagged 521 of 831 quotes; a layered one, 126.
Tiers: EXACT (whitespace-normalised), PUNCT (letters and digits with spaces), ALNUM
(letters and digits only),
RECOVER (letters and digits only, after dropping short bracketed xrefs), MISS.
For every tier but MISS the matching span of the paper text is returned, so the
sheet carries the paper's own characters.
"""
import re
import unicodedata

GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "κ": "kappa",
         "λ": "lambda", "μ": "mu", "τ": "tau", "θ": "theta", "ω": "omega", "Δ": "delta"}
SUBS = {"×": "x", "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
        "−": "-", "‘": "'", "’": "'", "“": '"', "”": '"', " ": " ",
        " ": " ", " ": " ", "­": "", "​": ""}


def _norm_char(c):
    c = SUBS.get(c, c)
    c = unicodedata.normalize("NFKC", c)
    return "".join(GREEK.get(x, x) for x in c).lower()


def _normalise(s, keep):
    """Return the normalised string and, for each of its characters, the index
    in s it came from. keep(ch) decides which normalised characters survive."""
    out, idx = [], []
    prev_space = True
    for i, c in enumerate(s):
        for x in _norm_char(c):
            if x.isspace():
                if not prev_space and keep(" "):
                    out.append(" ")
                    idx.append(i)
                prev_space = True
            elif keep(x):
                out.append(x)
                idx.append(i)
                prev_space = False
    return "".join(out).strip(), idx


def _drop_xrefs(s):
    """Blank short inline cross-references with spaces of the same length, so
    indices into the text stay valid and a match can return the paper's span
    (cross-reference included)."""
    blank = lambda m: " " * len(m.group(0))
    s = re.sub(r"\((?:Fig(?:ure)?s?\.?|Supplementary|Table|SI|Extended)[^()]{0,40}\)", blank, s, flags=re.I)
    s = re.sub(r"\[[\d,\s\-\u2013]+\]", blank, s)
    s = re.sub(r"\(\s*[A-Z](?:[,\-\u2013]\s*[A-Z])*\s*\)", blank, s)
    return s


def clean(span):
    """The paper's characters, minus invisible ones a spreadsheet should not carry."""
    span = span.replace("\u00ad", "").replace("\u200b", "")
    return re.sub(r"[ \u00a0\u2009\u202f\n\t]+", " ", span).strip()


def find_quote(quote, text):
    q = quote.strip().strip('"').strip("“”").strip()
    q = re.sub(r"^\.\.\.|\.\.\.$|^…|…$", "", q).strip()
    for tier, keep in (("EXACT", lambda x: True),
                       ("PUNCT", lambda x: x.isalnum() or x == " "),
                       ("ALNUM", lambda x: x.isalnum())):
        nq, _ = _normalise(q, keep)
        nt, idx = _normalise(text, keep)
        pos = nt.find(nq)
        if nq and pos >= 0:
            start, end = idx[pos], idx[pos + len(nq) - 1] + 1
            return tier, clean(text[start:end])
    nq, _ = _normalise(_drop_xrefs(q), lambda x: x.isalnum())
    nt, idx = _normalise(_drop_xrefs(text), lambda x: x.isalnum())
    pos = nt.find(nq) if nq else -1
    if pos >= 0:
        return "RECOVER", clean(text[idx[pos]:idx[pos + len(nq) - 1] + 1])
    return "MISS", None
