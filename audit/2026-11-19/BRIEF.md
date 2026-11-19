# Audit brief: MecCog Step 1 sheet rows vs the papers

You check extracted findings against the source papers, as the challenge's manual inspection will. Precision matters more than anything: a wrong number is worse than "qualitative".

Input: one packet JSON (list of papers). Each paper has `hypothesis` (verbatim), `text` (path to the paper's full text, references stripped), `supp` (supplement text or null), `figures` (PNG figure images, file name = figure number, `S6.png` = supplementary Fig 6), `pdf` (or null), and `rows` (the sheet rows: Finding description, quote, summary, relevance, system, Data location, Effect size, its provenance, P value, its provenance, Sample size, its provenance, Directness class, strength).

For EVERY row, read the cited place in the text (and the figure image when the location is a figure) and check:
1. Quote: verbatim in the text (minor markup/Unicode differences are fine), the paper's OWN result (not a cited study, not the intro/discussion restating others), and it supports the description.
2. Description/summary: what the experiment showed, correct direction, correct comparison groups.
3. Effect size: matches what the paper prints. Shapes allowed: "40%" (percent change, no sign), "2.5x" (fold/ratio), "name=num" (e.g. dpH=0.6, OR=1.8), "qualitative", "N/A". A leading "~" ONLY with provenance estimated_from_figure. If the text prints both group values and the row says qualitative, give the ratio or difference (provenance printed_in_text).
4. P value: matches the text/legend for THIS comparison. Number or inequality ("0.013", "<0.001"). Never estimated. Stars count only with the legend's own key (provenance visual_only), and only if you can see on the image that the star is over this comparison; a single key for the whole figure with no visible mark for this panel = ambiguous_panel.
5. Sample size: n for this comparison (integer or range "23-27"); counted points on a figure carry "~" and estimated_from_figure.
6. Provenance codes: printed_in_text, visual_only, estimated_from_figure, supplement_only, not_found_in_source, full_text_unavailable, ambiguous_panel. They must match where the value actually came from.
7. Data location: the right figure/panel/table.
8. Directness class (1-5) and strength: class 1 = direct test of the hypothesis's A->B in its stated system; do not argue scope at length, flag only clear errors.
9. Qualitative rows with a figure image: if you can read the value off the image defensibly (axis readable, the two bars/points of this comparison identifiable), propose "~X%"/"~Yx" with estimated_from_figure, and the n if points are clearly countable. Read the axis carefully (non-zero baselines). If not defensible, leave it.

Output: write `result_<packet number>.json` next to the packet: a JSON list with one object per row:
{"hyp": "H3", "paper_id": "P3", "finding_id": "P3.F2", "key": "<paper key>", "quote_start": "<first 70 characters of the row's quote, exactly as in the packet>",
 "verdict": "OK" | "FIX" | "DROP",
 "set": {"<sheet column name>": "<new value>", ...},   // only for FIX; use exact column names from the packet rows
 "reason": "<one or two sentences>",
 "evidence": "<exact text you relied on, or what you read on which panel of which image>"}
DROP only for: quote not the paper's own result, wrong paper, or the finding is not supported by the paper at all. Everything else is FIX or OK. Be literal and concrete; never guess a number. Do not edit any other file.
