# Checkpoint evaluation data and protocol

The problem statement's “Data and sources” page names SYNERGY for screening and
EBM-NLP for optional PICO training/test. This directory contains metadata and
evaluation configuration only. Raw text and annotations belong in Git-ignored
`.eval_data/` at the repository root, not in a PR, slide deck or release artifact.

## Reproduce

From the repository root, activate the project environment:

```powershell
python -m pip install -e "backend[evaluation]"
python backend/examples/prepare_evaluation_data.py --download
python backend/examples/evaluate_engines.py --output-dir docs/evaluation/checkpoint
```

The first preparation requires network access. Later runs omit `--download` to
use verified local inputs. Downloaded archives are checksum-verified, read as data
without extracting their paths, and converted to local Parquet with PyArrow.
No third-party Python loading script is executed. Ordinary app/tests do not need
PyArrow; it is an optional evaluation dependency.

## Frozen benchmark choices

`datasets.json` records exact URLs, upstream revisions, release/file checksums and
review profiles. Three complete small medical reviews were chosen before running
predictions: Donners_2021, Meijboom_2021 and van_der_Valk_2021. These form a
convenience subset, not a representative sample of all SYNERGY reviews.

Review keywords/exclusions approximate published eligibility criteria. They are
not learned from included-record titles or reference labels. Full-text inclusion
labels and abstract-only rules have a task mismatch, which remains visible in the
report. Missing language/publication metadata is not silently invented.

For EBM-NLP v2, use every document in the intersection of expert-labelled P/I/O
`starting_spans/*/test/gold` IDs. No training/crowd labels are included. Official
tokens are joined by a single space. Gold and predicted spans are scored against
those token positions. PICO uses `PicoTerms()` with no gold-driven review lexicon.
P maps to Participants; predicted I+C union maps to Interventions; O maps to
Outcomes. I-only results are included as a secondary variant. Comparator has no
independent gold label here.

## Metrics and safeguards

- Screening: strict Include precision/recall/F1, binary macro F1, confusion counts,
  Maybe rate and inclusion-reference Exclude counts. Separately report retention
  when Maybe stays for human review, alongside the fraction of all records retained.
- PIO: positive-token and exact-span precision/recall/F1 per label and micro totals.
  Exact spans are contiguous positive-token runs after projection. Any character
  overlap marks a predicted token positive. Repeated words at different offsets
  remain different tokens. No true-negative-token accuracy headline is used.
- Zero division is 0, with TP/FP/FN/support/prediction counts preserved. A precision
  denominator of zero is visible rather than advertised as a meaningful score.
- Repeatability and offset validity are integrity checks, separate from semantic
  quality. Timings are local pure-engine calls, excluding retrieval, DB and UI.
- No dedup quality percentage is inferred from IDs, and no Maybe ground-truth class
  is manufactured from binary SYNERGY labels.

Generated public outputs contain aggregate metrics and per-document error counts
or IDs. They exclude abstracts, token strings and annotation sequences. The EBM-NLP
card lists an unknown licence, and the event brief allows local training/testing
while prohibiting redistribution. Keep raw and converted corpus files local.

After reviewing a test result, do not tune against the same test labels and call a
rerun independent validation. Use training/development data or a new held-out set
for method changes, and retain this unchanged-rule baseline.

See [results](../../docs/evaluation/checkpoint/EVALUATION_REPORT.md) and
[Manas's preparation](../../docs/CHECKPOINT_PREP.md).
