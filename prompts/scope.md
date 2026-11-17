You decide whether each extracted finding is in scope for a literature submission on ONE hypothesis. Padding a submission with findings that do not bear on the hypothesis is penalised; dropping a finding that does bear on it (including contrary and null results) is also penalised. Judge the SUBJECT of each finding, never its direction.

Hypothesis: "{statement}"
A = {A}
B = {B}
Scope for this hypothesis: {scope}

Findings (from paper "{title}"):
{findings}

Return a JSON array, one object per finding id, nothing else:
[{{"id": "<id>", "keep": true|false, "why": "<at most 15 words>"}}]
