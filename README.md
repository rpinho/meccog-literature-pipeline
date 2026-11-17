# Method

MecCog Step 1 submission: an open pipeline that finds the papers bearing on a mechanism hypothesis and extracts each experimental finding into the MecCog template.

- **Team:** rstack
- **Hypothesis:** H1-H5 of the [APOE4 endosome set](https://huggingface.co/spaces/MecCog/meccog-challenge) (one spreadsheet each)
- **Submission date:** DATE

Everything here is agent work: AI-written code, AI extraction, an AI referee, and an AI spot-check. Read the numbers with that in mind.

---

## 1. Who did the work

Several agents, plus one person who set the goal and runs the machine. No person read the findings against the papers.

| Step | Agent | What it does |
|---|---|---|
| Pipeline code, queries, prompts | Claude Code (claude-opus-5-5) | wrote `pipeline/`, `prompts/` and `config/queries/`; spot-checks the output (section 5) |
| Screening | gpt-6.1-sol via Codex CLI | title and abstract screen, batches of 20: yes / maybe / no |
| Finding inventory | gpt-6.1-sol via Codex CLI | one call per paper: every panel, table or text result that bears on the hypothesis, supporting, contrary or null |
| Extraction | gpt-6.1-sol via Codex CLI | one call per finding: the 17 fields of a finding row |
| Code checks | no model | quote found in the paper text, value shapes, provenance consistent with the value, no estimated P value |
| Referee | gpt-6.2-astra via Codex CLI | re-reads the paper and supplement and checks every field of every row: PASS, FIX (with corrections) or REJECT |

Work passes between steps as files under `data/`. Only rows the referee passed, or fixed with corrections that survive the code checks, go into a sheet.

## 2. Model and version

- gpt-6.1-sol (OpenAI), Codex CLI 0.167.0, reasoning effort low for screening and high for inventory and extraction
- gpt-6.2-astra (OpenAI), Codex CLI 0.167.0, reasoning effort high, referee
- claude-opus-5-5 (Anthropic), Claude Code, pipeline author and spot-check

All model calls are logged with the model id in `runs/llm_calls.jsonl` (not published; counts in section 6).

## 3. How papers were found

`pipeline/search.py`, per hypothesis:

1. PubMed E-utilities, five queries per hypothesis in `config/queries/H*.txt`. The queries name APOE4 and the B variable without a direction word, so null and contrary papers come back too.
2. Europe PMC search with the same queries (adds preprints, and searches full text).
3. Citation snowball from the starting reference: its reference list and every paper citing it (OpenAlex).

Hit counts for every query, including the ones that returned almost nothing, are in `data/H*/search_log.jsonl` and summarised in section 6.

Then `pipeline/screen.py`: a code filter keeps papers whose title or abstract names APOE4 (or that came from the snowball) and drops reviews; a model screens the rest by title and abstract and keeps yes and maybe.

## 4. How full text was obtained

`pipeline/fetch.py` and `pipeline/supplements.py`, in this order:

1. Europe PMC `fullTextXML` (open-access subset), plus its `supplementaryFiles` zip
2. PMC Cloud S3 bucket (`pmc-oa-opendata`): JATS XML, figures, PDF
3. The PMC article page (covers author manuscripts outside the open-access subset)
4. Europe PMC rendered PDF of the PMC copy
5. Open-access locations from OpenAlex (the Unpaywall data): publisher PDF or article HTML. A preprint copy is never used for a published paper: figures and numbers can differ between versions.
6. bioRxiv PDF for preprints

Supplement files (PDF, DOCX, XLSX, CSV) are converted to text and read with the paper. PMC puts a JavaScript page in front of supplement downloads; for those the pipeline uses a headless Chrome for Testing. No paywalled content was obtained by any other route, and nothing was obtained with a login.

Reach, per hypothesis: REACH. A paper we could not reach is not extracted, so it has no rows in the sheet.

## 5. What a human checked

No person checked the findings. Instead:

- The referee (a second model) checked every row against the paper: VERDICTS.
- Claude Code (claude-opus-5-5) checked a sample field by field against the full text: SPOTCHECK. Two papers per hypothesis were drawn by hash before extraction and kept out of all prompt changes, so the sample is not one the pipeline was tuned on.

## 6. Anything else

- **Contrary and null findings are kept.** The inventory step asks for them by name, and the referee checks the direction column.
- **Quotes are matched against the paper by code.** A naive substring test fails correct quotes on markup, the multiplication sign, Greek letters and inline figure references; the matcher in `pipeline/quotes.py` normalises those in tiers and writes the paper's own characters into the sheet. Quotes start at a sentence boundary, so a dropped negation cannot invert a finding.
- **No values read off figures yet.** Where a figure shows a difference with no printed number the row says qualitative and visual_only. Measuring bars is planned, and every such value will carry a ~ and estimated_from_figure.
- **Effect sizes are reported as printed.** Where a paper prints only the two group values (pH 5.38 vs 5.74), the sheet gives the difference or ratio and the description quotes both values.
- **Scope calls.** The hypotheses name non-aged human brain cells, and almost nothing in this literature meets every clause. We keep model-system findings and record the system precisely, as the challenge asks.
- **Known weaknesses.** Papers behind publisher bot walls without a PMC copy are missed. The referee is one model; it fixes and rejects, but it can also be wrong.
- Lessons from the organizers' earlier agent collab shaped several steps; see References.

---

## Code and prompts

| Path | What |
|---|---|
| `pipeline/search.py` | stage 1, candidate pool |
| `pipeline/screen.py`, `prompts/screen.md` | stage 2, screen |
| `pipeline/fetch.py`, `pipeline/supplements.py`, `pipeline/browser.py` | stage 3, full text and supplements |
| `pipeline/extract.py`, `prompts/inventory.md`, `prompts/extract.md`, `pipeline/quotes.py` | stage 4, inventory, extraction, code checks |
| `pipeline/referee.py`, `prompts/referee.md` | stage 5, referee |
| `pipeline/build_sheet.py` | stage 6, sheet and validation |
| `pipeline/validate_submission.py` | the organizers' validator, unchanged |
| `config/` | hypotheses (copied from the submission Space), variables A and B per hypothesis, queries, template |

Run, per hypothesis: `search.py H1`, `screen.py H1`, `fetch.py H1`, `supplements.py`, `extract.py H1`, `referee.py H1`, `build_sheet.py H1`. Python 3, `openpyxl`, `pymupdf`, `playwright`; model calls go through the Codex CLI (`pipeline/llm.py`).

MIT license.

## References

- MecCog challenge, rules and template: https://huggingface.co/spaces/MecCog/meccog-challenge
- MecCog Agentic Challenge (the organizers' earlier collab), final set and analyses: https://huggingface.co/datasets/MecCogAgenticChallenge/meccog-final-set. The quote-provenance sweep there (nakos-lipid-scout) and the pool check (k-dense) are where the layered quote matcher and the sentence-boundary rule come from.
- panel-audit, a review agent for that collab: https://huggingface.co/datasets/MecCogAgenticChallenge/meccog-panel-audit
- Kundu K, Darden L, Moult J. MecCog: a knowledge representation framework for genetic disease mechanism. Bioinformatics 2021;37(22):4180-4186.
- PaperQA2 (FutureHouse): https://github.com/Future-House/paper-qa
- Europe PMC REST API: https://europepmc.org/RestfulWebService ; PMC Cloud Service: https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/ ; OpenAlex: https://openalex.org
