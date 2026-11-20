#!/usr/bin/env python3
"""Cross-sheet consistency pass for H5: group rows by readout x manipulation, one convention per group."""
import json, sys, collections, pathlib

D = pathlib.Path(sys.argv[1])
d = json.load(open(D / "verify_H5_0.json"))

def ids(s):
    return [x.strip() for x in s.split(",") if x.strip()]

# group: (class, strength, why, members)
G = {
 "DEG": (1, 1, "Lysosomal degradation assay (DQ-BSA/self-quenched substrate dequenching, lysosomal activity kit, or lysosome-inhibitor-sensitive cargo turnover) in APOE4 vs APOE3 cells measures B itself (degradation), so class 1 strength 1 under the class 1 rule, for every row of this assay.",
         ids("P15.F1,P15.F3,P15.F7,P15.F8,P15.F10,P15.F11,P15.F15,P3.F1,P3.F2,P1.F2,P7.F1,P2.F2,P22.F1,P22.F2,P12.F1,P29.F3,P29.F4")),
 "ENZ": (1, 1, "Live cathepsin activity (Magic Red substrate cleavage) in APOE4 vs APOE3 cells is lysosomal enzyme activity, B itself, so 1/1.",
         ids("P19.F1")),
 "PH": (1, 1, "Calibrated or ratiometric lysosomal / late-endosomal pH in APOE4 vs APOE3 cells is acidification, B itself, so 1/1 for every pH row (the class 1 rule overrides the 1/2 reference).",
        ids("P18.F1,P13.F2,P13.F4,P1.F1,P1.F3,P1.F4,P5.F1")),
 "FLUX": (1, 1, "Autophagic flux by lysosomal-inhibitor LC3-II turnover or the tandem mRFP-GFP-LC3 autolysosome readout in APOE4 vs APOE3 cells is autophagic flux, B itself, so 1/1 for every flux-assay row.",
          ids("P7.F3,P7.F4,P29.F1,P29.F2,P28.F1,P28.F2,P20.F2")),
 "LEAK": (3, 2, "Lysosomal membrane leakage (Lucifer Yellow release, cytosolic lysosomal enzyme by fractionation, galectin puncta) is not one of B's listed functions, so it is a surrogate B', but a permeabilized lysosome necessarily loses its acid gradient and hydrolases, so 3/2 for every leakage row.",
          ids("P17.F1,P17.F2,P17.F3,P17.F4,P17.F5,P21.F1,P7.F2,P8.F1,P9.F2")),
 "PHRODO_DECAY": (3, 2, "Pulse-chase decay half-life of internalized pHrodo-myelin normalizes uptake and is lost only by cargo degradation or loss of acidity, both B, so it is a tight surrogate (3/2) rather than B measured directly.",
                  ids("P13.F1")),
 "DQ_COUNT": (3, 2, "Number of DQ-BSA-positive (degradation-active) compartments is a surrogate for degradative capacity tied to the same dequenching assay, so 3/2 stays.",
              ids("P15.F12")),
 "CHOL": (3, 3, "Static cholesterol or neutral-lipid content in lysosomes/late endosomes (filipin, D4H*, Bodipy-cholesterol, BODIPY, EM lipid whorls) is a surrogate B' for cholesterol egress; greater delivery is a possible but unlikely-to-invalidate route, so 3/3 for every lysosomal-lipid row.",
          ids("P15.F2,P15.F5,P15.F16,P2.F1,P6.F1,P20.F1,P34.F2,P34.F3,P34.F4,P34.F5,P34.F6,P34.F9,P34.F12,P1.F5,P1.F6,P1.F8,P27.F1,P13.F3")),
 "LIPOF": (3, 4, "Lipofuscin autofluorescence is a lysosomal-storage surrogate that oxidative or lipid-peroxidation load raises without a lysosomal defect (a known route), so 3/4 for every lipofuscin row.",
           ids("P15.F9,P15.F19,P4.F2,P4.F4,P4.F12,P4.F13")),
 "CARGO": (3, 4, "Colocalization of a cargo, receptor or apoE itself with late-endosome/lysosome markers reports delivery set by upstream endosomal sorting, a known route that changes it without any change in lysosome function, so 3/4 for every cargo-colocalization row.",
           ids("P23.F3,P23.F5,P23.F6,P24.F3,P24.F4,P24.F5,P24.F6,P24.F7,P24.F8,P24.F9,P24.F10,P26.F1,P19.F2,P19.F5,P19.F6,P4.F11,P4.F15,P22.F3,P22.F4,P22.F5,P3.F6")),
 "LYSOIP": (3, 4, "LysoIP cargo composition reflects delivery to lysosomes (upstream mitophagy and trafficking) as much as lysosome function, a known alternative route, so 3/4 for every LysoIP row.",
            ids("P23.F7,P23.F9,P23.F10,P23.F11,P23.F12,P23.F13,P23.F14")),
 "PHRODO": (3, 4, "Accumulated pHrodo-cargo signal mixes uptake with acidification and persistence, a known non-lysosomal route (uptake), so 3/4 for every pHrodo accumulation row.",
            ids("P13.F6,P13.F11,P7.F11,P7.F14,P4.F8,P4.F16")),
 "AUTOMARK": (3, 3, "Static LC3-II, LC3-II/LC3-I, p62 or autophagic-vacuole staining without a turnover assay is a surrogate for autophagic flux; induction can move it but is unlikely to invalidate the link, so 3/3 for every static LC3/p62 row.",
              ids("P7.F7,P7.F8,P7.F9,P11.F2,P11.F3,P11.F4,P11.F5,P11.F6,P11.F7,P28.F3,P28.F4,P28.F5,P28.F6,P19.F9,P23.F1,P1.F11,P29.F5,P31.F1,P31.F2")),
 "INIT": (3, 4, "Beclin1/ATG7 abundance reports autophagy-initiation machinery upstream of the lysosome, which induction signalling changes independently of lysosome function, so 3/4.",
          ids("P23.F4")),
 "MITO": (3, 4, "TOM-20 mitochondrial mass is a loose mitophagy surrogate that mitochondrial biogenesis changes without any lysosomal change, so 3/4.",
          ids("P7.F12,P7.F13")),
 "MTKEIMA": (3, 3, "mtKeima reports mitochondrial delivery to acidic lysosomes, a surrogate for lysosome-dependent mitophagy flux with upstream damage signalling as a possible route, so 3/3.",
             ids("P19.F3,P19.F4,P19.F8")),
 "FUSION_QUAL": (3, 4, "Qualitative LAMP1-LC3 colocalization under bafilomycin, which itself perturbs fusion and acidity, is a surrogate for fusion with a known confounding route, so 3/4.",
                 ids("P19.F10")),
 "CLEAR_WC": (3, 3, "Whole-cell loss of internalized cargo after washout is not localized to the lysosome (proteasome or release could also lower it), a possible route, so 3/3.",
              ids("P3.F5,P28.F7")),
 "LYSOTRACKER": (3, 3, "LysoTracker intensity or spot count reflects lysosome number as well as acidity, a surrogate for acidification with a possible alternative route, so 3/3 for every LysoTracker row.",
                 ids("P15.F13,P15.F14,P13.F5,P19.F7,P11.F1")),
 "MARKER": (3, 3, "Late-endosome/lysosome marker abundance, compartment number, area, size or position (LAMP1/2, CD63, CD68, RAB7, cathepsin D immunostaining, NPC1/NPC2, V-ATPase subunit) is a structural surrogate B'; biogenesis is a possible but unlikely-to-invalidate route, so 3/3 for every marker row.",
            ids("P15.F17,P15.F18,P15.F21,P15.F22,P15.F23,P15.F24,P3.F9,P2.F3,P2.F4,P16.F1,P36.F1,P13.F7,P13.F8,P13.F9,P13.F10,P21.F4,P30.F1,P7.F5,P34.F1,P34.F7,P34.F8,P34.F10,P34.F11,P23.F2,P24.F1,P24.F2,P5.F2,P5.F6,P10.F1,P19.F11,P4.F14,P35.F1")),
 "PROT": (3, 3, "Whole-cell abundance of lysosomal proteins (hydrolases, V-ATPases, MFSD1) is a surrogate for lysosome function; lower abundance without a functional deficit is possible but unlikely to invalidate, so 3/3 for every lysosomal-proteomics row.",
          ids("P1.F7,P1.F9,P1.F10,P7.F6")),
 "CATD_LOC": (3, 3, "Cathepsin D retention in lysosomes by imaging or microsomal fraction is a surrogate for lysosomal integrity and enzyme content, with missorting a possible route, so 3/3.",
              ids("P8.F2,P8.F3,P8.F4")),
 "CA": (3, 3, "Lysosomal or acidic-store calcium content is a surrogate for lysosome state, not one of B's listed functions, with a possible alternative route, so 3/3.",
        ids("P5.F4,P19.F12")),
 "LYSOLIPID": (3, 4, "Isolated lysosomal-membrane lipid composition is weakly coupled to lysosome function (lipid supply alone changes it), so 3/4.",
               ids("P5.F8,P5.F10,P5.F11")),
 "PROTEO_CLEAR": (3, 3, "Proteomic response to lysosomal and/or proteasomal blockade is a surrogate for lysosome-dependent clearance that mixes in proteasomal turnover, so 3/3.",
                  ids("P25.F1,P25.F2,P25.F3,P25.F4")),
 "PROTEO_BASE": (3, 4, "Baseline abundance of clearance-sensitive proteins is changed by synthesis as well as clearance, a known route, so 3/4.",
                 ids("P25.F5")),
 "AEP": (3, 4, "Cleaved delta-secretase on lysosomal-fraction blots is a surrogate for lysosomal enzyme activity that rises with expression (the paper's own C/EBPb route), a known alternative, so 3/4.",
         ids("P9.F1,P9.F3")),
 "C5_B": (5, 4, "The manipulation does not act on APOE (class 5) and carries a known non-APOE route of its own; the readout is B itself or a tight surrogate, so strength 4 under the class 5 convention.",
          ids("P15.F6,P3.F3,P3.F4,P4.F5,P20.F3,P21.F2,P21.F3")),
 "C5_SURR": (5, 5, "The manipulation does not act on APOE (class 5) and the readout is itself a looser surrogate of B, so alternative routes sit at both ends and strength is 5 under the class 5 convention.",
             ids("P15.F4,P15.F20,P3.F7,P3.F8,P3.F10,P16.F2,P16.F3,P4.F1,P4.F3,P4.F6,P4.F7,P4.F9,P4.F10,P7.F10,P32.F1,P23.F8,P14.F1,P14.F2,P33.F1,P5.F3,P5.F5,P5.F7,P5.F9,P5.F12,P5.F13")),
}

NEW_REASON = {
 "P4.F5": "The reported contrast is CE(20:4)-loaded apoE3/apoE4 particles against low-lipofuscin treatments such as CE(18:1) particles, a lipid-cargo manipulation with no APOE4-versus-APOE3 difference reported, so APOE genotype is not the varied factor.",
 "P4.F9": "The reported contrast is CE(20:4)-loaded apoE3/apoE4 particles against other lipidated-apoE treatments, a lipid-cargo manipulation with no APOE4-versus-APOE3 difference established, so APOE genotype is not the varied factor.",
}

assign = {}
for g, (c, s, why, mem) in G.items():
    for m in mem:
        assert m not in assign, ("dup", m, g, assign.get(m))
        assign[m] = g
items = d["items"]
fids = {i["finding_id"] for i in items}
missing = fids - set(assign); extra = set(assign) - fids
assert not missing and not extra, (sorted(missing), sorted(extra))

out = []
for it in sorted(items, key=lambda x: x["item"]):
    f = it["finding_id"]; g = assign[f]; c, s, why, _ = G[g]
    old = (int(it["row"]["Directness class"]), int(str(it["row"]["Directness strength"])[0]))
    p = it["proposed"]; prop = (int(p["class"]), int(str(p["strength"])[0]))
    fin = (c, s)
    dec = "ACCEPT" if fin == prop else ("REJECT" if fin == old else "ADJUST")
    w = why
    if f == "P18.F1":
        w = "Reference row: ratiometric lysosomal pH in APOE4 vs APOE3 astrocytes is acidification, B itself, so the class 1 rule makes it 1/1 and the 11-19 value 1/2 does not stand."
    o = {"item": it["item"], "decision": dec, "class": c, "strength": s}
    if c == 5:
        o["reason_for_description"] = NEW_REASON.get(f) or p.get("reason_for_description")
        assert o["reason_for_description"], f
    o["why"] = w
    o["_finding_id"] = f; o["_group"] = g
    out.append(o)

final = [{k: v for k, v in o.items() if not k.startswith("_")} for o in out]
json.dump(final, open(D / "verified_H5_0.json", "w"), indent=1, ensure_ascii=False)
print(len(final))
print(collections.Counter(o["decision"] for o in final))
print(sorted(collections.Counter(o["class"] for o in final).items()))
print(sorted(collections.Counter((o["class"], o["strength"]) for o in final).items()))
json.dump(out, open(pathlib.Path(sys.argv[2]) / "decisions_annotated.json", "w"), indent=1, ensure_ascii=False)
