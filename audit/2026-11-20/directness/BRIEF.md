# Directness pass (stage 4): class and strength for rows not yet scored

The organizers' definitions are in DIRECTNESS_RULES.txt next to this file (verbatim from the challenge rules). Read them first; they are the only standard.

Input: a packet JSON for one hypothesis: `hypothesis` (verbatim), `A` and `B` (the two system variables), `scope` (what counts as B and its surrogates), `papers` (each with its sheet rows: finding id, description, quote, summary, experimental system, data location, current class, current strength), and `reference_rows`: rows of the same hypothesis already scored and checked on 11-19, with their final class and strength. Where a new row measures the same thing the same way as a reference row, give it the same class and strength.

For EVERY row in `papers` decide the class (1-5) and strength (1-5) from the definitions:
- Class is about the FORM of the experiment relative to THIS hypothesis's A and B: is A itself varied (APOE genotype or isoform, including natural variation like carriers vs non-carriers: that is A itself), or a surrogate A' assumed to change A? Is B itself measured, or a surrogate B'?
- "B itself was measured" means B exactly as the packet defines it, including any location or context in the definition (e.g. "in the endosome/lysosome"). A readout that matches B except for that context is a surrogate B' (class 3), with strength set by how misleading that surrogate can be.
- Rows whose A is the APOE genotype/isoform and whose readout IS B are class 1, whatever the cell type or model. The model system (mouse, cell line, non-brain cells) never lowers the class, and observing A rather than manipulating it never lowers the class.
- Class 2 needs a surrogate A' assumed to change A. Manipulations that do not act on APOE at all (a drug, an NHE6 knockdown, a receptor knockdown, a lipid manipulation such as cyclodextrin) within one genotype are class 5 (Other); give the reason in one sentence in "reason_for_description".
- Strength: 1 usually for class 1; class 4 is unlikely below 3; class 1 with 4-5 is an error. Write strength as a single digit.
- Rows in the same paper or across papers that measure the same thing in the same way must get the same class and strength. Make that true within your packet and against `reference_rows`.

Output: write `result_<packet name without "packet_">.json` next to the packet: a list of {"finding_id": "P3.F2", "quote_start": "<first 70 chars of the row's quote exactly>", "summary": "<the row's summary exactly>", "class": n, "strength": n, "changed": true|false, "why": "<one sentence; required when changed>", "reason_for_description": "<only for class 5>"}. One object per row, changed or not. No other files, no network, no model CLIs.
