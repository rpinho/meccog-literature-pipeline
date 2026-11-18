# Method

MecCog Step 1 submission: an open pipeline that finds the papers bearing on a mechanism hypothesis and extracts each experimental finding into the MecCog template.

- **Team:** rstack
- **Hypothesis:** H1 (lower endosome pH), H2 (impaired receptor recycling) and H3 (APOE4 aggregation in the endo-lysosome) of the [APOE4 endosome set](https://huggingface.co/spaces/MecCog/meccog-challenge), one spreadsheet each. H4 and H5 follow with the same pipeline.
- **Submission date:** H1 and H2 2026-11-17, replaced 2026-11-18 after the figure read; H3 2026-11-18

Everything here is agent work: AI-written code, AI extraction, an AI referee, and an AI spot-check. Read the numbers with that in mind.

---

## 1. Who did the work

Several agents, plus one person who set the goal and runs the machine. No person read the findings against the papers.

| Step | Agent | What it does |
|---|---|---|
| Pipeline code, queries, prompts | Claude Code (claude-opus-5-5) | wrote `pipeline/`, `prompts/` and `config/queries/`; spot-checks the output (section 5) |
| Screening | gpt-6.1-sol via Codex CLI | title and abstract screen, batches of 20: yes / maybe / no |
| Inventory and extraction | gpt-6.1-sol via Codex CLI | one call per paper: list every figure panel and table, tag each as direct, contrary, path or not bearing on the hypothesis, then write the 17 fields of a row for every direct and contrary panel and for up to 5 path panels |
| Code checks | no model | quote found in the paper text, value shapes, provenance consistent with the value, no estimated P value, no result quoted from someone else's paper |
| Referee | gpt-6.2-astra via Codex CLI | one call per paper: re-reads the paper and supplement and checks every field of every row, including whether it is inside a written statement of what counts as B, its surrogates and its path for that hypothesis (`config/variables.json`): PASS, FIX (with corrections) or REJECT |
| Scope check | gpt-6.2-astra via Codex CLI | the same scope question as a separate short call, for rows refereed before the scope statement was added to the referee prompt |
| Figure read | gpt-6.1-sol via Codex CLI, with the figure image | one call per figure for rows whose number is only in the figure (section 6) |
| Sheet | no model | relevance floor 0.35, one row per panel (duplicates merged), a preprint dropped when its published version is in, papers ordered by their best finding, at most 50 |

Work passes between steps as files under `data/`. Only rows the referee passed, or fixed with corrections that survive the code checks, and that the scope check kept, go into a sheet.

## 2. Model and version

- gpt-6.1-sol (OpenAI), Codex CLI 0.167.0, reasoning effort low for screening and high for inventory and extraction
- gpt-6.2-astra (OpenAI), Codex CLI 0.167.0, reasoning effort high for the referee, medium for the scope check
- gpt-6.1-sol (OpenAI), Codex CLI 0.167.0, reasoning effort medium with the figure image attached, figure read
- claude-opus-5-5 (Anthropic), Claude Code, pipeline author and spot-check

All model calls are logged with the model id and token count in `runs/llm_calls.jsonl` (not published).

## 3. How papers were found

`pipeline/search.py`, per hypothesis:

1. PubMed E-utilities, five queries per hypothesis in `config/queries/H*.txt`. The queries name APOE4 and the B variable without a direction word, so null and contrary papers come back too.
2. Europe PMC search with the same queries (adds preprints, and searches full text).
3. Citation snowball from the starting reference: its reference list and every paper citing it (OpenAlex).

Hit counts per query, in the order of `config/queries/H*.txt` (Europe PMC searches full text; we keep the top 300 per query):

| | PubMed | Europe PMC | starting reference: cites / cited by |
|---|---|---|---|
| H1 | 67, 6, 2, 1, 66 (HDAC4 and v-ATPase queries returned almost nothing) | 1,255, 104, 241, 34, 1,389 | 73 / 203 |
| H2 | 1, 14, 8, 1, 24 (the ARF6 and Rab11 queries returned one paper each) | 73, 1,405, 734, 184, 1,319 | 41 / 153 |
| H3 | 24, 29, 154, 896, 91 | 3,436, 3,858, 8,425, 87, 3,054 | 81 / 118 |

The funnel per hypothesis is in the table in section 5.

Then `pipeline/screen.py`: a code filter keeps papers whose title or abstract names APOE4 (or that came from the snowball) and drops reviews; a model screens the rest by title and abstract and keeps yes and maybe.

## 4. How full text was obtained

`pipeline/fetch.py` and `pipeline/supplements.py`, in this order:

1. Europe PMC `fullTextXML` (open-access subset), plus its `supplementaryFiles` zip
2. PMC Cloud S3 bucket (`pmc-oa-opendata`): JATS XML, figures, PDF
3. The PMC article page (covers author manuscripts outside the open-access subset)
4. Europe PMC rendered PDF of the PMC copy
5. Open-access locations from OpenAlex (the Unpaywall data): publisher PDF or article HTML. A preprint copy is never used for a published paper: figures and numbers can differ between versions.
6. bioRxiv JATS XML (via the bioRxiv API) or PDF for preprints, one request per 10 seconds
7. For open-access papers whose publisher pages block scripts (Cloudflare), the publisher PDF downloaded by hand in a browser and placed in `data/manual_pdfs/` (route `manual_pdf` in each paper's record)

Supplement files (PDF, DOCX, XLSX, CSV) are converted to text and read with the paper. PMC puts a JavaScript page in front of supplement downloads; for those the pipeline uses a headless Chrome for Testing. No paywalled content was obtained by any other route, and nothing was obtained with a login.

Reach is in the table in section 5. Most papers we could not reach are closed access with no PMC copy, or bioRxiv preprints that were rate-limited on the day. A paper we could not reach is not extracted, so it has no rows in the sheet.

## 5. What a human checked

No person checked the findings. Instead:

- The referee (a second model) checked every row against the paper:

| | candidates | passed code filter | kept by screen | full text reached when extracted | rows extracted | referee PASS / FIX / REJECT | in the sheet |
|---|---|---|---|---|---|---|---|
| H1 | 983 | 403 | 73 | 58 (79%) | 221 | 51 / 68 / 98 (4 not refereed) | 8 papers, 20 rows |
| H2 | 960 | 302 | 95 | 79 (83%) | 680 | see note | 13 papers, 72 rows |
| H3 | 1,267 | 708 | 89 | 68 (76%); 62 extracted, 6 timed out | 262 | 40 / 59 / 163 | 21 papers, 61 rows |

  H2 note: 48 PASS / 64 FIX / 517 REJECT in the first round; the top-up added 5 papers. Rows in the sheet are referee PASS or FIX rows that the scope check kept, at relevance 0.35 or higher, with duplicates merged. The H2 REJECT count is high because 40 H2 papers were extracted with an earlier, more inclusive prompt; the referee removed what was outside the hypothesis.
- Claude Code (claude-opus-5-5) read all 21 rows of the first H1 sheet and checked the quote, location, effect size, P value and n of 5 rows against the full text (Prasad and Rao 2018 Fig 3B; Fig 5B; Lysosomal proteomics 2025 Fig 1E; JBC 2025 Fig 4J; Stem Cell Reports 2025 Fig 5F). All 5 matched. It found 2 defective rows: a row quoting a dissertation's literature review (someone else's result) and a duplicate of the same result under its representative-image panel. Both are now caught by code, and the sheet has 20 rows.
- Two papers per hypothesis were drawn by hash before extraction and kept out of all prompt changes, for a later check the pipeline was not tuned on. For H1 neither yielded a row in scope.

## 6. Anything else

- **Contrary and null findings are kept.** The inventory step asks for them by name, and the referee checks the direction column.
- **Quotes are matched against the paper by code.** A naive substring test fails correct quotes on markup, the multiplication sign, Greek letters and inline figure references; the matcher in `pipeline/quotes.py` normalises those in tiers and writes the paper's own characters into the sheet. Quotes start at a sentence boundary, so a dropped negation cannot invert a finding.
- **Values read off figures** (`pipeline/figures.py`, `pipeline/figread.py`, `prompts/figure_read.md`). For rows whose number is only in a figure, one call per figure gets the figure image (taken from the PDF where we have it, else the PMC or Europe PMC figure file) with its legend and that figure's rows, and no paper text. It fills only what is missing: an effect size measured off the bars is written with a leading ~ and estimated_from_figure; group values printed on the figure itself (numbers on the bars) are used as printed and marked printed_in_text, with both values quoted in the description; a P value comes only from significance marks read with that legend's own key (visual_only), never estimated; n from counted points carries a ~. A value already printed in the text is never replaced, and any value the validator would reject is dropped. H1: 15 rows read, 6 changed; H2: 30 rows read, 6 changed; the rest stayed as they were, mostly because the panel showed no number we could defend or the legend gave no key for its stars. Claude checked 3 of the changed values against the images (Prasad 2018 Fig 5D, ~1.1 pH units; Mol Neurobiol 2026 Fig 4D, ~73%; JAD 2024 Fig 6B, ~65%): all matched.
- **Effect sizes are reported as printed.** Where a paper prints only the two group values (pH 5.38 vs 5.74), the sheet gives the difference or ratio and the description quotes both values.
- **Scope calls.** The hypotheses name non-aged human brain cells, and almost nothing in this literature meets every clause. We keep model-system findings and record the system precisely, as the challenge asks.
- **Significance stars.** Where a legend gives one key for the whole figure ("*** p < 0.001") but the text does not say which panels carry the stars, the P value is N/A with ambiguous_panel until we read the figure images.
- **H3 starting reference.** Kaji et al. 2024 (Immunity) is open access but behind a publisher bot wall; it is not in this H3 version and will be added in a replacement.
- **Known weaknesses.** Papers behind publisher bot walls without a PMC copy are missed. Most effect sizes are "qualitative" because the number is only in a figure and we do not read figures yet. The referee is one model; it fixes and rejects, but it can also be wrong. The H1 sheet is small (8 papers) because rows outside the hypothesis are dropped; we think that is the right call for this challenge, but it means some related lysosome results are not in it.
- Lessons from the organizers' earlier agent collab shaped several steps; see References.

---

## Code and prompts

| Path | What |
|---|---|
| `pipeline/search.py` | stage 1, candidate pool |
| `pipeline/screen.py`, `prompts/screen.md` | stage 2, screen |
| `pipeline/fetch.py`, `pipeline/supplements.py`, `pipeline/browser.py` | stage 3, full text and supplements |
| `pipeline/extract.py`, `prompts/inventory.md`, `prompts/extract.md`, `pipeline/quotes.py` | stage 4, inventory, extraction, code checks (`prompts/inventory_v1.md` is the first inventory prompt, kept for the record: it returned nothing for 39 of 58 H1 papers) |
| `pipeline/referee.py`, `prompts/referee.md` | stage 5, referee |
| `pipeline/scope.py`, `prompts/scope.md` | stage 5b, scope check |
| `pipeline/figures.py`, `pipeline/figread.py`, `prompts/figure_read.md` | stage 5c, figure read |
| `pipeline/build_sheet.py`, `pipeline/check_ids.py` | stage 6, sheet, validation, and DOI/PMID check |
| `pipeline/validate_submission.py` | the organizers' validator, unchanged |
| `config/` | hypotheses (copied from the submission Space), variables A and B per hypothesis, queries, template |

Run, per hypothesis: `search.py H1`, `screen.py H1`, `fetch.py H1`, `supplements.py`, `extract.py H1`, `referee.py H1`, `scope.py H1`, `build_sheet.py H1`. Python 3, `openpyxl`, `pymupdf`, `playwright`; model calls go through the Codex CLI (`pipeline/llm.py`).

MIT license.

## References

- MecCog challenge, rules and template: https://huggingface.co/spaces/MecCog/meccog-challenge
- MecCog Agentic Challenge (the organizers' earlier collab), final set and analyses: https://huggingface.co/datasets/MecCogAgenticChallenge/meccog-final-set. The quote-provenance sweep there (nakos-lipid-scout) and the pool check (k-dense) are where the layered quote matcher and the sentence-boundary rule come from.
- panel-audit, a review agent for that collab: https://huggingface.co/datasets/MecCogAgenticChallenge/meccog-panel-audit
- Kundu K, Darden L, Moult J. MecCog: a knowledge representation framework for genetic disease mechanism. Bioinformatics 2021;37(22):4180-4186.
- Prior art we read but did not run: PaperQA2 (FutureHouse), https://github.com/Future-House/paper-qa
- Europe PMC REST API: https://europepmc.org/RestfulWebService ; PMC Cloud Service: https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/ ; OpenAlex: https://openalex.org
