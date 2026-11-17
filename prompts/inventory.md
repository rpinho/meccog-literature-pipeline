You are reading one scientific paper in full to find every experimental result that bears on a hypothesis. Missing a relevant result is the most common and most costly error, so work in two steps.

Hypothesis: "{statement}"
Form: a change in A causes a change in B.
A = {A}
B = {B}

STEP 1. Enumerate EVERY figure panel (Fig 1A, 1B, ...), every supplementary figure panel, and every table that reports the paper's own data. For each, say in a few words what was measured, in which system, and under which comparison. Do not skip panels.

STEP 2. Tag each panel with "bears":
- "direct": APOE4 is compared with APOE3 (E4 vs E3 carriers, knock-in E4 vs E3 cells or mice, recombinant apoE4 vs apoE3, apoE4 added vs not) and B, or a surrogate of B, is measured. Include it whatever the direction: higher, lower, or no difference.
- "path": a step on the A -> B path tested in an APOE4 context: e.g. a drug, knockdown or overexpression in APOE4 cells that changes B or its measured regulator; a rescue of B in APOE4 cells; the regulator of B measured in APOE4 vs APOE3 cells.
- "contrary": any result that argues against the hypothesis, including B measured in APOE4 vs APOE3 with no difference or the opposite direction, and B in a related compartment moving the other way.
- "no": does not involve B, a surrogate of B, or a step on the path in an APOE context.
Model systems all count (human iPSC-derived cells, primary cells from APOE targeted-replacement mice, immortalized APOE astrocytes, cell lines, in vitro protein, animals, human tissue).

Return ONLY a JSON array with one object per panel from STEP 1 (including the "no" ones), most direct first:
[{{"loc": "Fig 2C", "what": "<one sentence: what was compared and what was measured, in which system>", "bears": "direct" | "path" | "contrary" | "no", "direction": "supports" | "against" | "null" | "mixed" | "n/a", "basis": "<the sentence or legend fragment that reports it, copied verbatim, at most 60 words>"}}]

PAPER TEXT (section headings marked with #, figure and table legends marked [FIGURE n] / [TABLE n] when the source had them):
{text}
