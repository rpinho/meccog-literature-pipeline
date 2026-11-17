You are screening papers for a literature challenge. Hypothesis:

"{statement}"

The hypothesis has the form: a change in A causes a change in B.
A = {A}
B = {B}

A paper is RELEVANT if it reports at least one primary experiment (its own data, not a review) that bears on this hypothesis in either direction: it compares APOE4 with APOE3 (or E4 carriers with E3 carriers, or manipulates apoE4) and measures B or a close surrogate of B, or it tests a step of the A -> B link in an APOE context. Model systems count (mouse, iPSC, cell lines, in vitro protein work). Findings AGAINST the hypothesis and null results are just as relevant as supporting ones. General Alzheimer's or APOE papers that never measure B are NOT relevant.

For each paper below return one JSON object per line, nothing else:
{{"id": "<id>", "decision": "yes" | "maybe" | "no", "relevance": <0..1>, "primary_data": true|false, "why": "<at most 20 words>"}}
Use "maybe" when the abstract is not enough to tell but the full text could contain such an experiment.

Papers:
{papers}
