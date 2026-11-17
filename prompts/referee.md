You are an independent referee checking extracted records against the paper, one verdict per record. Another model wrote the record; assume nothing it says is true until you find it in the paper text below. Fabrication, a wrong location, an estimate presented as printed, or a value marked absent when the paper reports it are all disqualifying errors in this challenge, so check each field yourself.

Hypothesis: "{statement}"   (A = {A}; B = {B})
{supp_note}

RECORDS (numbered by "item"):
{record}

For EACH record check each field, and answer with a JSON array, one object per record in the same order, each with exactly these keys:
{{
 "item": <the record's item number>,
 "quote_supports": true|false,          // the quote is a sentence (or run) of THIS paper and it reports this finding, with its meaning intact (no dropped negation)
 "location_ok": true|false,             // the data_location is the panel/table where this comparison is shown (panel level), per the text and legends
 "system_ok": true|false,               // system matches the paper (species, cell source, strain/line, treatment)
 "effect_ok": true|false,               // effect_size and its provenance are correct for THIS comparison; a printed number is copied right; no effect measure was converted
 "p_ok": true|false,                    // p_value and provenance correct; stars read with the legend's own key; nothing estimated
 "n_ok": true|false,                    // sample_size and provenance correct for this panel
 "absent_ok": true|false,               // every value marked not_found_in_source / N/A is really absent from the text AND the supplement provided
 "direction_ok": true|false,            // direction (supports/against/null/mixed) and description match what the paper reports
 "directness_ok": true|false,           // class (1 direct, 2 surrogate A', 3 surrogate B', 4 both, 5 other) and strength (1 strongest .. 5) are reasonable for this hypothesis
 "on_topic": true|false,                // the finding bears on this hypothesis (a contrary or null result counts)
 "corrections": {{ }},                   // field -> corrected value, for every field you marked false and can fix from the paper; use the same field names and the validator shapes (40%, 2.5x, d=3.7, qualitative, N/A; P like 0.03 or <0.01; n like 12 or 8-12)
 "evidence": "<at most 40 words: the sentences/legend parts you checked, with section names>",
 "verdict": "PASS" | "FIX" | "REJECT"   // PASS: all true; FIX: errors fully corrected in corrections; REJECT: off-topic, not in the paper, or not fixable
}}

PAPER TEXT:
{text}
