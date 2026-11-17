You are extracting experimental findings from a paper into structured records, one record per listed finding. Accuracy matters more than anything: every value must be checkable against the paper. Never invent a number.

Hypothesis: "{statement}"   (A = {A}; B = {B})
The findings to extract (one record each, in this order):
{items}

For EACH finding fill these fields:
- description: one plain-English sentence: what was done and what was observed (include the direction, and say "no significant difference" for nulls).
- quote: a sentence (or contiguous run of sentences) copied EXACTLY from the paper text below that reports this finding. Start at the beginning of a sentence (never mid-sentence: a dropped head can invert the meaning). Prefer Results text; use the figure legend if Results has nothing. "N/A" only if no sentence reports it.
- summary: structured notation like (APOE3 -> APOE4) -> (lower endosomal pH in astrocytes). Use "no change in" for nulls. "N/A" if the form does not fit.
- system: the experimental system as precisely as the paper allows: species, cell type and its source (e.g. primary astrocytes from human APOE4 targeted-replacement mice, C57BL/6 background; or iPSC-derived astrocytes from line X, isogenic), treatment, age/time, assay.
- data_location: the panel (Fig 4C), table (Table 2), supplementary panel (Supplementary Fig 3B), or the exact sentence if only in text.
- effect_size: for THIS comparison, in exactly one of these shapes (the validator rejects anything else):
    "40%" (percent change, no sign: the direction goes in description), "2.5x" or "0.6x" (fold, ratio of the two groups),
    "d=3.7" / "r=0.58" / "dpH=0.6" (a named effect: ASCII letters, =, a number), "qualitative", or "N/A".
    Rules:
    * a number printed in the Results text, legend or a table -> copy it into the right shape; provenance printed_in_text (supplement_only if only in the supplement).
    * the paper prints only the two group values (e.g. pH 5.2 vs 5.8, or 120 vs 80 units): you may express them as a fold or difference, and the description MUST quote both printed values; provenance printed_in_text.
    * never convert one effect measure into another (no d -> %, no fold -> %).
    * direction visible only in the figure, no printed number -> "qualitative", provenance visual_only.
    * a printed bound or a value that fits no shape (">1 pH unit") -> "qualitative" with printed_in_text, and put the printed value in the description.
    * the paper reports no difference -> "N/A" with not_found_in_source unless it prints a number for the difference.
- effect_size_provenance: one of printed_in_text, visual_only, supplement_only, not_found_in_source, ambiguous_panel
- p_value: shape "0.03", "<0.001", ">0.05" or "N/A" only (no words, no "n.s."). Exactly as printed for THIS comparison. "not significant" with the paper's stated threshold (e.g. "P > 0.05" or legend "ns, P > 0.05") -> ">0.05". If only stars: the inequality the legend's own key gives (e.g. ** = p<0.01 -> "<0.01") with provenance visual_only. Stars with no key -> "N/A", ambiguous_panel. Never estimate a P value. Not reported -> "N/A", not_found_in_source.
- p_value_provenance: one of printed_in_text, visual_only, supplement_only, not_found_in_source, ambiguous_panel
- sample_size: shape "12" or "8-12" or "N/A" only: n for this panel as printed, or the range as printed. Say what n counts in the description if the paper says (cells, mice, wells, independent experiments). Not stated -> "N/A".
- sample_size_provenance: printed_in_text, supplement_only, not_found_in_source, ambiguous_panel
- directness_class: 1 direct (A itself perturbed or naturally varying, i.e. APOE4 vs APOE3, and B itself measured); 2 A perturbed through a surrogate A' (e.g. an NHE6 inhibitor stands in for APOE4), B measured; 3 A itself perturbed, B inferred from a surrogate B' (e.g. a pH-sensitive dye's colocalisation, or a downstream readout standing in for B); 4 surrogate at both ends; 5 other (say why in description).
- directness_strength: 1 very strong .. 5 very weak (1 = closest to the hypothesis). Class 1 is normally 1 or 2. Class 4 is rarely below 3.
- relevance: 0..1, how directly this finding bears on THIS hypothesis (both supporting and contrary findings can be highly relevant).
- direction: supports | against | null | mixed
- evidence_note: at most 25 words: where exactly you read the effect, P and n (e.g. "Results para 3 states P; n from legend Fig 2").

{supp_note}

Return a JSON array with one object per finding, in the same order, each with "item" (the finding's number) plus exactly those keys. No commentary.

PAPER TEXT:
{text}
