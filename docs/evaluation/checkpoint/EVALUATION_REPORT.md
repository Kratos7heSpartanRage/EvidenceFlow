# EvidenceFlow algorithm evaluation

Measured UTC: 2026-10-28T13:39:01.912543+00:00

These are measurements of the unchanged deterministic engines on external datasets named in the problem statement. They are not deployment verification, a clinical validation or the organizer's unpublished scoring rubric.

## Data and frozen setup

- SYNERGY release 1.0: three complete medical review subsets selected before evaluating predictions. Profiles in `backend/evaluation/datasets.json` approximate published criteria using existing abstract/metadata rules. No reference labels are passed to the engines. No model was trained or tuned on these records.
- Screening: 1865 records, 141 included reference labels and 75 missing abstracts. References are final review inclusion decisions; not all full-text criteria can be inferred from abstracts. This is a proxy benchmark, not an equivalent full-text review.
- EBM-NLP v2: 186 documents in the intersection of expert P/I/O test files, 50907 official tokens. Crowd/training labels were not used. The corpus was converted locally to Parquet without executing the Hugging Face loading script.
- PICO uses an empty review lexicon (cue-only baseline). Text is reconstructed with one space between official tokens. P maps to Participants; I and C predictions are unioned for the corpus's combined Interventions channel; O maps to Outcomes. I-only scores are also included in JSON. There is no separate comparator reference label.
- Raw abstracts, EBM token-level annotation sequences and converted Parquet remain in Git-ignored `.eval_data/`. Public artifacts contain aggregates, openly licensed SYNERGY reference decisions/error IDs, and per-document PIO error counts without source text or EBM annotation sequences.

## Screening results

Only Include counts positive for strict precision/recall/F1. Maybe counts as non-Include for that strict score. The separate retention metric counts Include + Maybe as remaining for human review. It must be read together with the fraction of all records retained.

| Review | N / included | Include precision | Include recall | Include F1 | Maybe | Eligible suggested Exclude |
|---|---:|---:|---:|---:|---:|---:|
| Donners_2021 | 258 / 15 | 8.70% | 80.00% | 15.69% | 44.96% | 0 |
| Meijboom_2021 | 882 / 37 | 6.11% | 83.78% | 11.40% | 37.64% | 3 |
| van_der_Valk_2021 | 725 / 89 | 43.18% | 42.70% | 42.94% | 64.69% | 0 |
| pooled | 1865 / 141 | 11.05% | 57.45% | 18.54% | 49.17% | 3 |

- Pooled strict accuracy: **61.82%**; all-excluded majority baseline: **92.44%**. High accuracy alone is weak evidence on this imbalanced set.
- Pooled strict macro F1 (Included/Excluded): **46.80%**. There is no gold Maybe class in SYNERGY.
- Eligible retention if Maybe remains for review: **97.87%**, while **88.47%** of all records remain. This is a hypothetical triage summary, not measured time saved or autonomous eligibility accuracy.
- Exclusion reason coverage: **215/215** suggestions have a criterion and explanatory evidence.

Pooled confusion matrix (rows: published reference; columns: engine suggestion):

| Reference | Include | Exclude | Maybe |
|---|---:|---:|---:|
| excluded | 652 | 212 | 860 |
| included | 81 | 3 | 57 |

## PIO extraction results

Positive-token micro precision/recall/F1 use official token positions, not matching strings. A token is predicted positive when its characters overlap a predicted span. Exact spans are contiguous positive-token runs after projection; boundaries must agree exactly. True-negative tokens are not rewarded in F1. Zero-division is 0 and TP/FP/FN counts are saved.

| Channel | Token precision | Token recall | Token F1 | Exact-span F1 |
|---|---:|---:|---:|---:|
| P  | 61.64% | 17.98% | 27.84% | 0.52% |
| I (I+C union) | 14.50% | 15.63% | 15.05% | 0.09% |
| O  | 35.06% | 2.70% | 5.01% | 0.00% |
| micro  | 27.36% | 10.01% | 14.66% | 0.13% |

- Valid original-string slices on the reconstructed benchmark text: **715/715**. Offset validity is a software-integrity check, not semantic correctness.
- Standalone Comparator precision/recall/F1: **not measured** because the selected corpus has no separate Comparator gold labels. Do not present the Interventions score as Comparator accuracy.

## Repeatability and timing

- Screening repeated identically without changing inputs: 1865/1865.
- PICO repeated identically: 186/186.
- screening: 1865 pure-function calls; median 0.948 ms, p95 4.140 ms, summed time 261.716 s. Excludes downloads, DB, API, frontend and metric calculation; not end-to-end latency.
- pico: 186 pure-function calls; median 3.188 ms, p95 7.396 ms, summed time 0.675 s. Excludes downloads, DB, API, frontend and metric calculation; not end-to-end latency.

## What these results do not establish

No expert deduplication pair labels were supplied by these corpora, so dedup precision/recall are not invented from record IDs. Existing unit/integration tests cover duplicate/grouping behavior separately. No manual reviewer time study was run. No confidence-calibration, deployment, live API or clinical-use claim follows from this benchmark. Subsets are a convenience selection, not a representative sample of all reviews. Read the per-review errors before generalizing.

## Reproduce

```powershell
python -m pip install -e "backend[evaluation]"
python backend/examples/prepare_evaluation_data.py --download
python backend/examples/evaluate_engines.py --output-dir docs/evaluation/checkpoint
```

Input revisions, checksums, algorithm versions, source-file hashes, environment and exact confusion counts are recorded in `metrics.json`. The first command may require installing the project's dev dependencies separately to run tests.

Sources: [SYNERGY](https://github.com/asreview/synergy-dataset), [pinned release](https://doi.org/10.34894/HE6NAQ), [EBM-NLP](https://github.com/bepnye/EBM-NLP), [BigBio dataset card](https://huggingface.co/datasets/bigbio/ebm_pico), [precision/recall/F1 conventions](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html).
