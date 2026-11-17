You are reading one scientific paper in full to find every experimental result that bears on a hypothesis.

Hypothesis: "{statement}"
Form: a change in A causes a change in B.
A = {A}
B = {B}

Bears on the hypothesis = the paper's OWN primary data (not cited work, not the discussion of others) where:
- APOE4 is compared with APOE3 (or E4 with E3 carriers, E4 knock-in vs E3 knock-in, recombinant apoE4 vs apoE3, or apoE4 manipulated), AND B or a surrogate of B is measured; or
- a step on the A -> B path is tested in an APOE4 context (e.g. a rescue that changes B in APOE4 cells); or
- a result that argues AGAINST the hypothesis or shows NO difference between APOE4 and APOE3 on B. These must be listed too.
Model systems all count (human iPSC-derived cells, primary mouse cells from APOE targeted-replacement mice, cell lines, in vitro protein assays, animals, human tissue).

List each result separately at the finest location the paper gives: one figure PANEL (Fig 3B), one table, or one sentence in the text. If one panel compares several conditions, list the comparison that bears on the hypothesis; list a second entry only if a second comparison in the same panel also bears on it.
Skip results that do not involve B (or its surrogate), and skip pure methods validation.

Return a JSON array only, one object per result, ordered by how directly it tests the hypothesis (most direct first):
[{{"loc": "Fig 2C", "what": "<one sentence: what was compared and what was measured>", "direction": "supports" | "against" | "null" | "mixed", "basis": "<the sentence or legend fragment in the paper that reports it, copied verbatim, at most 60 words>"}}]
Return [] if the paper has no such result.

PAPER TEXT (section headings marked with #, figure and table legends marked [FIGURE n] / [TABLE n]):
{text}
