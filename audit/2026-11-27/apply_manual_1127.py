#!/usr/bin/env python3
"""Stage 11 (2026-11-27, Claude, checked by hand against the figure images, no model call):
1. H3 Kaji-era Cell 2024 paper (pmid39532095): Fig 5Q quantifies the pH 4.5 aggregation that the H3 Fig 5P row
   kept as qualitative. Normalized pelletable ApoE ~1.07 (ApoE4) vs ~0.74 (ApoE3), ** between them (Methods key
   **p < 0.01), one-way ANOVA with Holm-Sidak comparisons, 3 experiments x 2 preparation batches = 6 points.
2. H3 pmid34982109 Fig 3A/3B: harmonized with the H5 rows on the same panels (checked 11-20 and again today):
   colocalization ~0.037 vs ~0.011 = ~3.3x (H3 had ~3.1x); green/red ratio ~0.8 vs ~2.15 = ~63% decrease (H3 had ~61%).
Idempotent: replaces any stage == 11 entries in config/corrections.json."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
P = ROOT / "config/corrections.json"
STAGE11 = [
    {"key": "pmid39532095", "hyp": "H3", "stage": 11,
     "quote_start": "Interestingly, CE(20:4)-ApoE3 demonstrated the lowest aggregation at both pH 7.4",
     "summary_contains": "higher pelletable ApoE at lysosomal pH across preparation batches",
     "description_start": "Quantification across two PUFA-CE",
     "set": {"data_location": "Fig 5P-Q, pH 4.5 (Fig 5Q: normalized pelletable ApoE)",
             "description": "Quantification across two PUFA-CE-ApoE preparation batches showed greater acidic-pH ApoE aggregation for ApoE4 than ApoE3, with variable absolute aggregation between batches. Normalized pelletable ApoE at pH 4.5 (Fig 5Q) was about 1.07 for ApoE4 versus 0.74 for ApoE3 (3 independent experiments for 2 batches; one-way ANOVA with Holm-Sidak comparisons).",
             "effect_size": "~1.4x", "effect_size_provenance": "estimated_from_figure",
             "p_value": "<0.01", "p_value_provenance": "visual_only",
             "sample_size": "6", "sample_size_provenance": "printed_in_text"},
     "reason": "Manual check 11-27: Fig 5Q bars ApoE4 ~1.07 vs ApoE3 ~0.74 (~1.4x), ** bracket ApoE3-ApoE4, Methods key **p < 0.01; legend: 3 independent experiments for 2 batches (6 points visible).",
     "source": "figimg/5.png Panel Q, Fig 5 legend (Q), Methods statistics key"},
    {"key": "pmid34982109", "hyp": "H3", "stage": 11,
     "quote_start": "Imaris analysis revealed that APOE4", "summary_contains": "greater APOE–lysosome colocalization",
     "description_start": "APOE4–mCh showed significantly greater colocalization",
     "set": {"effect_size": "~3.3x", "effect_size_provenance": "estimated_from_figure"},
     "reason": "Cross-sheet harmonization 11-27 (matches H5 P27.F5): Fig 3A colocalization ~0.037 (APOE4) vs ~0.011 (APOE3).",
     "source": "figimg/3.png Panel A"},
    {"key": "pmid34982109", "hyp": "H3", "stage": 11,
     "quote_start": "APOE4–mCh–SepH cells had a significantly lower ratio", "summary_contains": "lower green-to-red reporter ratio",
     "description_start": "Dual-tagged APOE4 produced",
     "set": {"effect_size": "~63%", "effect_size_provenance": "estimated_from_figure"},
     "reason": "Cross-sheet harmonization 11-27 (matches H5 P27.F6 ~0.37x): Fig 3B green/red ~0.8 (APOE4) vs ~2.15 (APOE3).",
     "source": "figimg/3.png Panel B"},
]
C = json.load(open(P))
items = C if isinstance(C, list) else C["corrections"]
items[:] = [c for c in items if c.get("stage") != 11] + STAGE11
json.dump(C, open(P, "w"), indent=1, ensure_ascii=False)
print("stage 11 entries:", len(STAGE11))
