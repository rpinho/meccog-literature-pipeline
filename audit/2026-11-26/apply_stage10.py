#!/usr/bin/env python3
"""Apply stage-10 corrections (2026-11-26):
1. Recover missing effect sizes, star-key P values, and dot-count sample sizes from
   2026 PMC WebP figures unlocked by adding WebP support to pipeline/figures.py
   (pmid42636814 H5 P3, pmid42539043 H5 P29, pmid42330346 H5 P37) and newly extracted
   or refreshed PDF figures (pmid32588544, pmid34453582, pmid16298992).
2. Fix 4 verified H3 P15 (pmid28684412) P values previously dropped by the validator
   because of the unicode '≤0.001' sign instead of ASCII '<=0.001'.
3. Resolve the remaining unsealed main-figure ambiguous_panel tags across H2-H5
   against cached figures and exact legends (pmid30375977, pmid34982109, pmid39880097,
   pmid23060451, pmid35969759, pmid32517777, pmid42274838, pmid41103078, pmid23132858,
   pmid40164781, pmid32709881).

42 rows updated across 16 non-sealed papers: H2 (2), H3 (9), H4 (3), H5 (28).
H1 unchanged. Zero sealed papers touched.

Idempotent: replaces any existing stage == 10 entries in config/corrections.json.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CORR_PATH = ROOT / "config" / "corrections.json"

STAGE10 = [
    # ==================== H2 (2 rows) ====================
    {
        "key": "pmid30375977",
        "hyp": "H2",
        "stage": 10,
        "quote_start": "As shown in Figure 4D and E, physiological concentrations of ApoE3",
        "summary_contains": "greater reduction of surface-to-total Apoer2 ratio",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 4E marks stars for E3 vs Con (*) and E4 vs Con (***), with no pairwise E4 vs E3 test shown; provenance is not_found_in_source rather than ambiguous_panel (matches sibling H4 P4.F5).",
        "source": "PMC6261251 figimg/4.png Panel E + Figure 4 legend",
    },
    {
        "key": "pmid30375977",
        "hyp": "H2",
        "stage": 10,
        "quote_start": "Increasing concentrations progressively restored normal surface recycl",
        "summary_contains": "restored Apoer2 surface recycling",
        "set": {
            "p_value": "<0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 4C shows explicit brackets from E4+0 uM EMD87580 to 0.3 uM (**), 1 uM (***), and 3 uM (****); Figure 4 legend defines *p<0.05, **p<0.01, ***p<0.001 (omitting a separate **** threshold), so <0.001 is strictly supported for the 3 uM vs 0 uM restoration.",
        "source": "PMC6261251 figimg/4.png Panel C + Figure 4 legend",
    },

    # ==================== H3 (9 rows) ====================
    {
        "key": "pmid34982109",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "Internalization levels were isoform-dependent, with the highest fluore",
        "summary_contains": "higher intracellular APOE-associated fluorescence during uptake",
        "set": {
            "effect_size": "~1.25x",
            "effect_size_provenance": "estimated_from_figure",
            "p_value": "<0.05",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 7B (St14A endocytosis time course) shows 24 h endpoint APOE4 ~2.25e-4 vs APOE3 ~1.80e-4 (~1.25x) with an explicit pink significance bar labelled 'APOE3 vs APOE4 FDR<0.05' printed in the panel key.",
        "source": "PMC8917355 figimg/7.png Panel B",
    },
    {
        "key": "pmid39880097",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "Notably, rAPOE4 exhibited a higher β-sheet content, both in isolation ",
        "summary_contains": "higher baseline ThT-inferred amyloid-like APOE aggregation",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 6C marks Dunnett comparisons only for +LPS concentrations against each isoform's own baseline, with no statistical test between baseline APOE3 and baseline APOE4; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC11879696 figimg/6.png Panel C + Figure 6 legend",
    },
    {
        "key": "pmid28684412",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "When comparing the interactions between corresponding combinations of ",
        "summary_contains": "higher intracellular C+C intermolecular FRET in mouse astrocytes",
        "set": {
            "p_value": "<=0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 3C (C+C terminus in astrocytes) shows an explicit short bracket connecting E3-RFP+E3-GFP and E4-RFP+E4-GFP marked '***' (legend: '*** ≤ 0.001'); replaces prior unicode '≤0.001' that the validator rejected.",
        "source": "PMC5592654 figimg/3.png Panel C + Figure 3 legend",
    },
    {
        "key": "pmid28684412",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "When comparing the interactions between corresponding combinations of ",
        "summary_contains": "higher intracellular N+C intermolecular FRET in mouse astrocytes",
        "set": {
            "p_value": "<=0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 3C (N+C terminus in astrocytes) shows an explicit short bracket connecting RFP-E3+E3-GFP and RFP-E4+E4-GFP marked '***' (legend: '*** ≤ 0.001'); replaces prior unicode '≤0.001' that the validator rejected.",
        "source": "PMC5592654 figimg/3.png Panel C + Figure 3 legend",
    },
    {
        "key": "pmid28684412",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "When comparing the interactions between corresponding combinations of ",
        "summary_contains": "higher intracellular C+C intermolecular FRET in HEK cells",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 3B (C+C terminus in HEK cells) shows only a single 3-group bracket spanning E2, E3, and E4 marked '*', with no pairwise E3 vs E4 bracket; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC5592654 figimg/3.png Panel B",
    },
    {
        "key": "pmid28684412",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "When comparing the interactions between corresponding combinations of ",
        "summary_contains": "higher intracellular N+C intermolecular FRET in HEK cells",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 3B (N+C terminus in HEK cells) shows only a single 3-group bracket spanning E2, E3, and E4 marked '*', with no pairwise E3 vs E4 bracket; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC5592654 figimg/3.png Panel B",
    },
    {
        "key": "pmid28684412",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "When comparing the interactions between corresponding combinations of ",
        "summary_contains": "higher C+C intermolecular FRET in astrocyte-secreted apoE",
        "set": {
            "p_value": "<=0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 3E (C+C terminus in astrocyte-secreted apoE) shows an explicit short bracket connecting E3-RFP+E3-GFP and E4-RFP+E4-GFP marked '***' (legend: '*** ≤ 0.001'); replaces prior unicode '≤0.001' that the validator rejected.",
        "source": "PMC5592654 figimg/3.png Panel E + Figure 3 legend",
    },
    {
        "key": "pmid28684412",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "When comparing the interactions between corresponding combinations of ",
        "summary_contains": "higher N+C intermolecular FRET in astrocyte-secreted apoE",
        "set": {
            "p_value": "<=0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 3E (N+C terminus in astrocyte-secreted apoE) shows an explicit short bracket connecting RFP-E3+E3-GFP and RFP-E4+E4-GFP marked '***' (legend: '*** ≤ 0.001'); replaces prior unicode '≤0.001' that the validator rejected.",
        "source": "PMC5592654 figimg/3.png Panel E + Figure 3 legend",
    },
    {
        "key": "pmid23060451",
        "hyp": "H3",
        "stage": 10,
        "quote_start": "However, the lower total apoE4 levels are reflected only in their sign",
        "summary_contains": "comparable levels of formic-acid-extracted hippocampal apoE",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 5A (FA panel) shows '*' (age vs 2/4 mo) only and no '#' (isoform vs apoE2/apoE3) across the 2-, 4-, and 6-month bars, with no single numeric P value reported across ages; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC3516726 figimg/5.png Panel A + Figure 5 legend",
    },

    # ==================== H4 (3 rows) ====================
    {
        "key": "pmid30375977",
        "hyp": "H4",
        "stage": 10,
        "quote_start": "Increasing concentrations progressively restored normal surface recycl",
        "summary_contains": "restored Apoer2 surface recycling",
        "set": {
            "p_value": "<0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 4C shows explicit brackets from E4+0 uM EMD87580 to 0.3 uM (**), 1 uM (***), and 3 uM (****); Figure 4 legend defines ***p<0.001 (harmonized with sibling H2 P3.F11).",
        "source": "PMC6261251 figimg/4.png Panel C + Figure 4 legend",
    },
    {
        "key": "pmid32588544",
        "hyp": "H4",
        "stage": 10,
        "quote_start": "Colocalization of receptor/ligand complexes in Tf-positive cell compar",
        "summary_contains": "higher Manders tM1 colocalization of sortilin",
        "set": {
            "effect_size": "~1.8x",
            "effect_size_provenance": "estimated_from_figure",
            "p_value": "<0.01",
            "p_value_provenance": "visual_only",
        },
        "reason": "PDF figure read 11-26: Fig 5C (Manders tM1: Transferrin to PLA) shows +apoE4 mean ~0.14 vs +apoE3 mean ~0.08 (~1.8x) with '**' directly above the comparison (legend: '*P < .05; **P < .01').",
        "source": "pmid32588544 figimg/5.png Panel C + Figure 5 legend",
    },
    {
        "key": "pmid35969759",
        "hyp": "H4",
        "stage": 10,
        "quote_start": "In contrast, APOE4 enhanced the trafficking of surface LRP1 levels (Fi",
        "summary_contains": "higher neuronal surface LRP1",
        "set": {
            "effect_size": "~3.8x",
            "effect_size_provenance": "estimated_from_figure",
            "p_value": "<0.01",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 6C (O.D. S.LRP1/T.LRP1 quantification of Fig 6A) shows APOE4 ~10000 vs Control ~2600 (~3.8x) with an explicit bracket marked '**' (legend: '** P < 0.01').",
        "source": "PMC9407658 figimg/6.png Panel C + Figure 6 legend",
    },

    # ==================== H5 (28 rows) ====================
    {
        "key": "pmid42636814",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "APOE4/4 astrocytes showed significantly reduced lysosomal DQ-BSA signa",
        "summary_contains": "lower lysosomal proteolytic activity in Donor 1 astrocytes",
        "set": {
            "effect_size": "~0.74x",
            "effect_size_provenance": "estimated_from_figure",
        },
        "reason": "PMC WebP figure read 11-26: Fig 4d (DQ-BSA Normalized MFI, Donor #1) shows APOE4/4 ~74 vs APOE3/3 ~100 (~0.74x; printed p=0.0032 and n=3-4 already present).",
        "source": "PMC13528747 figimg/4.png Panel d",
    },
    {
        "key": "pmid42636814",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Treatment with 2-hydroxypropyl-β-cyclodextrin (2HβCD) and methyl-β-cyc",
        "summary_contains": "higher lysosomal proteolytic activity",
        "set": {
            "effect_size": "~1.9x",
            "effect_size_provenance": "estimated_from_figure",
        },
        "reason": "PMC WebP figure read 11-26: Fig 5b bottom (DQ-BSA Integrated Intensity AUC) shows APOE4/4 + 2HβCD ~9.3e6 vs APOE4/4 Vehicle ~5.0e6 (~1.9x; printed p=0.0002 and n=4 already present).",
        "source": "PMC13528747 figimg/5.png Panel b",
    },
    {
        "key": "pmid42636814",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "To assess degradation, extracellular α-Syn was removed after 24 hours,",
        "summary_contains": "impaired intracellular clearance of exogenous α-Syn in astrocytes",
        "set": {
            "effect_size": "~1.4x",
            "effect_size_provenance": "estimated_from_figure",
            "p_value": "<0.0001",
            "p_value_provenance": "visual_only",
        },
        "reason": "PMC WebP figure read 11-26: Fig 4c (α-Synuclein HiLyte Intensity at 48 h, 24 h post-washout) shows higher retained intracellular signal in APOE4/4 (~2.4) vs APOE3/3 (~1.7) (~1.4x) with '****' directly between APOE4/4 and APOE3/3 at 48 h (legend: '****p < 0.0001').",
        "source": "PMC13528747 figimg/4.png Panel c + Figure 4 legend",
    },
    {
        "key": "pmid42636814",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Consistent with improved lysosomal capacity, MβCD increased LysoTracke",
        "summary_contains": "higher LysoTracker-positive lysosomal signal",
        "set": {
            "effect_size": "~1.27x",
            "effect_size_provenance": "estimated_from_figure",
        },
        "reason": "PMC WebP figure read 11-26: Fig 5d (LysoTracker Mean Intensity Normalized to Hoechst) shows APOE4/4 + MβCD ~0.94 vs APOE4/4 Vehicle ~0.74 (~1.27x; printed p=0.044 and n=5-6 already present).",
        "source": "PMC13528747 figimg/5.png Panel d",
    },
    {
        "key": "pmid32517777",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Surprisingly, measurement of Ca2+ stored inside acidic organelles usin",
        "summary_contains": "no significant increase detected in GPN-releasable acidic-store calcium",
        "set": {
            "p_value": ">0.05",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 7b (APOE3 FBS vs APOE3 KH GPN AUC, unpaired t-test) shows no asterisk above the two bars (legend: 'p < 0.05 (*)') matching the text's null result.",
        "source": "PMC7285605 figimg/7.png Panel b + Figure 7 legend",
    },
    {
        "key": "pmid42274838",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "The LC3-II/LC3-I ratio was significantly higher in APOE3 compared to A",
        "summary_contains": "lower LC3-II/LC3-I ratio",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 7B plots APOE3 and APOE4 on separate axes each normalized to its own control, with stars marking within-genotype vs control (*) and MPP+ vs Rapamycin+MPP+ (^) only; no direct APOE3 vs APOE4 test is shown on Fig 7B.",
        "source": "PMC13260029 figimg/7.png Panel B + Figure 7 legend",
    },
    {
        "key": "pmid42274838",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "As shown in Fig. 3A, the levels of p62 were significantly higher in AP",
        "summary_contains": "loss of the α-synuclein-associated increase in p62",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 3B (p62/Actin) marks APOE3 Control vs α-Synuclein (*) and baseline APOE3 vs APOE4 (**), with no star for APOE4 Control vs α-Synuclein and no genotype x treatment interaction P value; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC13260029 figimg/3.png Panel B + Figure 3 legend",
    },
    {
        "key": "pmid42274838",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "As shown in Fig. 3B, α-synuclein treatment significantly reduced the l",
        "summary_contains": "loss of the α-synuclein-associated decrease in LC3-II",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 3A (LC3-II/LC3-I) marks APOE3 Control vs α-Synuclein (*) and baseline APOE3 vs APOE4 (****), with no star for APOE4 Control vs α-Synuclein and no genotype x treatment interaction P value; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC13260029 figimg/3.png Panel A + Figure 3 legend",
    },
    {
        "key": "pmid34453582",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Western blotting showed that the addition of exogenous astrocytic medi",
        "summary_contains": "GCase protein abundance was similar with apoE4- and apoE3-conditioned media",
        "set": {
            "p_value": ">0.05",
            "p_value_provenance": "visual_only",
        },
        "reason": "Refreshed PDF figure read 11-26: Fig 4e (GCase/β-actin) shows an explicit horizontal bracket spanning all four groups (+KO, +E2, +E3, +E4) labelled 'n.s.' (legend: one-way ANOVA, n.s. = not significant).",
        "source": "PMC8500881 figimg/4.png Panel e + Figure 4 legend",
    },
    {
        "key": "pmid41103078",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "In concordance with our observations in Neuro-2a cells, we found that ",
        "summary_contains": "higher lysosomal TMED5 PLA signal",
        "set": {
            "effect_size": "~2.1x",
            "effect_size_provenance": "estimated_from_figure",
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 6G (quantification of neuronal lysosomal TMED5 PLA) shows APOE4 ~1160 vs APOE3 ~550 (~2.1x) with '***', but the Figure 6 XML legend's star key is corrupted ('*p < .05; ****p < .0005; *p < .0001' omits '***'), so P value remains N/A (not_found_in_source).",
        "source": "PMC12758178 figimg/6.png Panel G + Figure 6 legend",
    },
    {
        "key": "pmid16298992",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "ApoE3- and apoE4-transfected cells treated with A1–42 had a similar 4-",
        "summary_contains": "no change in reported Aβ-induced LAMP1-labeling response",
        "set": {
            "effect_size": "~0.96x",
            "effect_size_provenance": "estimated_from_figure",
        },
        "reason": "Refreshed PDF figure read 11-26: Fig 12C (LAMP1 Immunofluorescence Intensity/Cell, With Aβ at 16 h) shows E4 ~2550 vs E3 ~2650 (~0.96x; at 8 h E4 ~2380 vs E3 ~2480, also ~0.96x), consistent with a similar 4-fold increase.",
        "source": "pmid16298992 figimg/12.png Panel C",
    },
    {
        "key": "pmid23132858",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "When lysosomal degradation of Aβ42 was calculated by subtracting the c",
        "summary_contains": "lower inhibitor-derived lysosomal Aβ42 degradation",
        "set": {
            "p_value": "<0.05",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 5B (Degraded Aβ42) shows an explicit bracket connecting E3 and E4 marked '*' (legend: '*, p < 0.05; **, p < 0.01').",
        "source": "PMC3531774 figimg/5.png Panel B + Figure 5 legend",
    },
    {
        "key": "pmid23132858",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "In addition, confocal microscopy also revealed that internalized FAM-A",
        "summary_contains": "lower Aβ42 delivery to LysoTracker-positive compartments",
        "set": {
            "p_value": "<0.05",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 5D (quantification of Fig 5C FAM-Aβ42 in lysosomes) shows an explicit bracket connecting E3 and E4 marked '*' (legend: '*, p < 0.05; **, p < 0.01').",
        "source": "PMC3531774 figimg/5.png Panel D + Figure 5 legend",
    },
    {
        "key": "pmid23132858",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Upon quantification, we confirmed that the amounts of Aβ42 in lysosome",
        "summary_contains": "lower lysosome-associated Aβ42",
        "set": {
            "p_value": "<0.05",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 5D (Aβ42 in lysosomes) shows an explicit bracket connecting E3 and E4 marked '*' (legend: '*, p < 0.05; **, p < 0.01').",
        "source": "PMC3531774 figimg/5.png Panel D + Figure 5 legend",
    },
    {
        "key": "pmid23132858",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "The more efficient trafficking of apoE3 than apoE4 was confirmed by im",
        "summary_contains": "less efficient apoE trafficking to LAMP1-positive compartments",
        "set": {
            "effect_size": "~0.65x",
            "effect_size_provenance": "estimated_from_figure",
            "p_value": "<0.05",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 7D (ApoE in lysosomes, Ratio to E3) shows E4 ~0.65 vs E3 1.0 (~0.65x) with an explicit bracket connecting E3 and E4 marked '*' (legend: '*, p < 0.05').",
        "source": "PMC3531774 figimg/7.png Panel D + Figure 7 legend",
    },
    {
        "key": "pmid42539043",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "In contrast, simultaneous inhibition of proteasomal and lysosomal prot",
        "summary_contains": "less additional protein accumulation after combined lysosomal/proteasomal blockade",
        "set": {
            "sample_size_provenance": "not_found_in_source",
        },
        "reason": "PMC WebP figure read 11-26: Fig 4E plots counts of significantly altered proteins with no replicate dots, and the legend gives only a lower bound 'n ≥ 3 biological and technical replicates' (no exact integer or upper bound); provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC13419530 figimg/4.png Panel E + Figure 4 legend",
    },
    {
        "key": "pmid42539043",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Each treatment individually had a modest impact on the proteome with a",
        "summary_contains": "similar numbers of proteins responding to lysosomal inhibition",
        "set": {
            "sample_size_provenance": "not_found_in_source",
        },
        "reason": "PMC WebP figure read 11-26: Fig 4E (BafA1 bars) plots protein counts with no replicate dots, and the legend gives only 'n ≥ 3 biological and technical replicates'; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC13419530 figimg/4.png Panel E + Figure 4 legend",
    },
    {
        "key": "pmid42539043",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "By analyzing the clearance-sensitive proteome, we found that several o",
        "summary_contains": "higher baseline abundance of proteins sensitive to combined clearance blockade",
        "set": {
            "sample_size": "~3-4",
            "sample_size_provenance": "estimated_from_figure",
        },
        "reason": "PMC WebP figure read 11-26: Fig 4H dot plot shows 3-4 individual replicate points per condition per protein (matching Fig 4G and legend 'n ≥ 3 biological and technical replicates').",
        "source": "PMC13419530 figimg/4.png Panel H + Figure 4 legend",
    },
    {
        "key": "pmid40164781",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Thus, autophagosomes delivery to lysosomes is hampered in APOE4 microg",
        "summary_contains": "less autophagosome delivery to lysosomes",
        "set": {
            "p_value_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 6A shows representative confocal micrographs with no statistical test on the panel (quantification and P value are reported separately on Fig 6B / P32.F2); provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC11958439 figimg/6.png Panel A",
    },
    {
        "key": "pmid40164781",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "We found that following rapamycin treatment, 41.03% ± 3.268 of autopha",
        "summary_contains": "lower red-only LC3 fraction indicating reduced autolysosome formation",
        "set": {
            "sample_size_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 6B legend gives only a lower bound 'n ≥ 50 cells/treatment' with no exact n or upper bound (not representable as an exact integer/range); provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC11958439 Figure 6 legend",
    },
    {
        "key": "pmid40164781",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "However, the levels of p62 following chloroquine treatment were signif",
        "summary_contains": "lower p62 accumulation during lysosomal blockade",
        "set": {
            "p_value": "<0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 5B (EBSS+CQ condition) shows '***' directly above the APOE4 black bar vs APOE3 white bar; Figure 5 legend defines '* p < 0.05 ** p < 0.001, ApoE3 compared to APOE4 cells', so <0.001 is strictly supported.",
        "source": "PMC11958439 figimg/5.png Panel B + Figure 5 legend",
    },
    {
        "key": "pmid40164781",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Next, we measured the rate of Aβ degradation in APOE3 compared to APOE",
        "summary_contains": "lower apparent intracellular Aβ degradation",
        "set": {
            "sample_size_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 2B legend gives only a lower bound 'n ≥ 4' with no exact integer or upper bound; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC11958439 Figure 2 legend",
    },
    {
        "key": "pmid32709881",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Furthermore, using the tandem LC3-GFP-RFP reporter30, we found that fo",
        "summary_contains": "lower autophagosome maturation/fusion with lysosomes after CCCP",
        "set": {
            "p_value": "<0.01",
            "p_value_provenance": "visual_only",
            "sample_size_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 3c (tandem LC3 puncta under CCCP) shows '**' directly on the APOE4 bar (legend: '** p < 0.01, APOE3 compared with APOE4'); legend states only 'n ≥ 50 cells/treatment', so sample_size_provenance is not_found_in_source.",
        "source": "PMC7382473 figimg/3.png Panel C + Figure 3 legend",
    },
    {
        "key": "pmid32709881",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Accordingly, APOE3 astrocytes treated with CCCP combined with chloroqu",
        "summary_contains": "lower autophagic flux after mitochondrial damage",
        "set": {
            "p_value": "<0.01",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 3d right graph (ΔLC3-II ± CQ under CCCP) shows '**' directly above the APOE4 black bar (legend: '* p < 0.05 and **, APOE3 compared with APOE4', matching '** p < 0.01' across Fig 3a-c and Fig 4).",
        "source": "PMC7382473 figimg/3.png Panel D + Figure 3 legend",
    },
    {
        "key": "pmid32709881",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "As shown in Fig. 2a, increased accumulation (differences between CQ tr",
        "summary_contains": "lower chloroquine-sensitive mitochondrial p62 turnover",
        "set": {
            "sample_size_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 2a legend gives only a lower bound 'n ≥ 3' with no exact integer or upper bound; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC7382473 Figure 2 legend",
    },
    {
        "key": "pmid32709881",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Accordingly, APOE3 astrocytes treated with CCCP combined with chloroqu",
        "summary_contains": "lower LC3-II accumulation during combined CCCP and chloroquine treatment",
        "set": {
            "p_value": "<0.01",
            "p_value_provenance": "visual_only",
        },
        "reason": "Figure/legend audit 11-26: Fig 3d left graph (LC3-II under CCCP+CQ) shows '**' directly above the APOE4 black bar (legend: '* p < 0.05 and **, APOE3 compared with APOE4', matching '** p < 0.01' across Fig 3a-c and Fig 4).",
        "source": "PMC7382473 figimg/3.png Panel D + Figure 3 legend",
    },
    {
        "key": "pmid32709881",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "Additionally, treatment with chloroquine/MG-132 led to parkin accumula",
        "summary_contains": "lower chloroquine-sensitive parkin degradation",
        "set": {
            "sample_size_provenance": "not_found_in_source",
        },
        "reason": "Figure/legend audit 11-26: Fig 4e legend gives only a lower bound 'n ≥ 3' with no exact integer or upper bound; provenance is not_found_in_source rather than ambiguous_panel.",
        "source": "PMC7382473 Figure 4 legend",
    },
    {
        "key": "pmid42330346",
        "hyp": "H5",
        "stage": 10,
        "quote_start": "In both APOE3 and APOE4‐derived microglia, Lilrb4a knockdown enhanced ",
        "summary_contains": "loss of enhanced Aβ uptake and degradation",
        "set": {
            "effect_size": "qualitative",
            "effect_size_provenance": "printed_in_text",
            "p_value": "<0.001",
            "p_value_provenance": "visual_only",
        },
        "reason": "PMC WebP figure read 11-26: Fig 4M shows both APOE4 uptake (left, E4-ASO-L4a ~210 vs +GW9662 ~115, ~0.55x) and 24 h residual Aβ (right, ~370 vs ~870, ~2.4x higher residual = loss of degradation) with explicit '***' brackets on both comparisons (legend: '*** p < 0.001'); effect kept qualitative because row combines uptake and degradation.",
        "source": "PMC13336908 figimg/4.png Panel M + Figure 4 legend",
    },
]


def main():
    doc = json.loads(CORR_PATH.read_text())
    kept = [c for c in doc["corrections"] if c.get("stage") != 10]
    doc["corrections"] = kept + STAGE10
    CORR_PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {len(STAGE10)} stage-10 entries (total corrections: {len(doc['corrections'])})")


if __name__ == "__main__":
    main()
