# Directness pass: class and strength, consistent across rows

The organizers' definitions are in DIRECTNESS_RULES.txt next to this file (verbatim from the challenge rules). Read them first; they are the only standard.

Input: a packet JSON with one hypothesis: `hypothesis` (verbatim), `A` and `B` (the two system variables, with the scope note saying what counts as B and its surrogates), and `papers`, each with its sheet rows (finding id, description, quote, summary, experimental system, data location, current class, current strength).

For EVERY row decide the class (1-5) and strength (1-5) from the definitions:
- Class is about the FORM of the experiment relative to THIS hypothesis's A and B: is A itself varied (genotype or isoform, including natural variation like carriers vs non-carriers: that is A itself), or a surrogate A' (e.g. a drug or knockdown assumed to act on A)? Is B itself measured, or a surrogate B'?
- Rows whose A is the APOE genotype/isoform and whose readout IS B are class 1, whatever the cell type or model; the system (mouse, cell line, non-brain) does not change the class. Doubts about the system belong in strength only where the definitions allow it ("how misleading the surrogates might be"), not as a penalty for model systems.
- Experiments that manipulate something other than APOE (a rescue drug, an NHE6 knockdown) are about a path variable: decide honestly which class fits, or 5 (Other) with the reason in one sentence.
- Strength: 1 usually for class 1; class 4 is unlikely below 3; class 1 with 4-5 is an error.
- Rows in the same paper or across papers that measure the same thing in the same way must get the same class and strength. Make that true.

Output: write `result_<name>.json` next to the packet: list of {"finding_id": "P3.F2", "quote_start": "<first 70 chars of the row's quote exactly>", "summary": "<the row's summary exactly>", "class": n, "strength": n, "changed": true|false, "why": "<one sentence; required when changed>"}. One object per row, changed or not. No other files, no network, no model CLIs.
