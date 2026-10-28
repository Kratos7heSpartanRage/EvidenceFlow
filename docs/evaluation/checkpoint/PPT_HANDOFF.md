# Content handoff for the teammate making the PPT

This is a factual review of the supplied 12-slide
`EvidenceFlow — Hackathon Presentation_updated.pptx`. The deck itself was not edited.

## Corrections or evidence needed

| Slide | Current content | Action |
|---|---|---|
| 4 and 9 | “Highlighted spans” / visual PICO sentence | The sentence is explicitly illustrative. Current UI shows a plain abstract and extracted span cards; use “extracted spans” unless actual inline highlighting is added and tested. |
| 5 | One Docker container and persistent volume already packaged | No Dockerfile was present in the inspected main baseline. B may be building it separately. Keep this as verified deployment architecture only after a real image/start/restart check; otherwise label it planned. |
| 5 | “Costs nothing to run” | Prefer “No paid model API calls in the core rules pipeline.” Compute and hosting still have requirements. |
| 6 | 13,790 / 757 / 788 live counts from 27 Oct | These may be B's observations. Retain only with the exact query, dates, flags, source, access date and a saved log. Counts change and were not reproduced by the algorithm benchmark. |
| 7 | Similar titles imply a fuzzy review suggestion | Fuzzy matching is opt-in and disabled in the production scorer's current default call. Say “matching title with incomplete/conflicting metadata” for the default path. Exact identifiers also defer to review on conflicts/report-type guards. |
| 10 | Only what changed is reprocessed | Known source records are reused; screening/PICO use cached input/version fingerprints. Grouping may still be rebuilt on the active set. Avoid implying every stage is strictly incremental. |
| 10 | Exact restore | Current guarantee is saved query record set/grouping with zero source calls; it is not arbitrary workspace time travel or rollback of every human edit. |
| 11 | 242 backend tests | The original production baseline was 242. This work adds 13 evaluation/preparation tests, making 255 backend tests in the new full run. Keep “242 existing + 13 evaluation tests” if that distinction is useful. |
| 11 | 8/8 live tests passed | The fresh default suite reports 8 live tests skipped. B may have separate passing live logs. Show those logs with date/command, or replace with “8 live tests available, not rerun in this evaluation.” |
| 11 | 174 papers in about 7.5 seconds | Not established by the supplied files or this benchmark. Ask B for the run/query/cap/cache/environment/timing log. Do not replace it with pure-function timing and call that end-to-end. |
| 11 | Criteria-change tests imply automatic re-screening | Unit/service behavior is tested, but saving criteria does not yet schedule the complete re-screening run in the UI/backend workflow. State the scope. |
| 12 | Live demo | Use the real hosted URL and a rehearsed small live query. Clearly label any recorded/fixture backup. |

## Copy-ready evaluation content

**Title: Algorithm evaluation on the PS datasets**

| Task | Data used | Current unchanged-rule baseline |
|---|---|---|
| Relevance screening | 1,865 records / 141 included references across 3 SYNERGY reviews | Strict Include P/R/F1: **11.05% / 57.45% / 18.54%** |
| PIO tagging | 186 complete expert EBM-NLP test abstracts | Positive-token micro F1: **14.66%**; exact-span micro F1: **0.13%** |

**Visible qualification:** SYNERGY reference labels can depend on full text. The
profiles are abstract/metadata approximations. PIO is cue-only without a review
lexicon; predicted I+C are combined for the corpus's Interventions channel.
There is no standalone Comparator gold label in this benchmark.

**Speaker note:** Keeping Maybe for human review retains 138/141 included studies
(97.87%), but also retains 1,650/1,865 records (88.47%). Three included references
receive Exclude suggestions. This is not 97.87% accuracy or measured reviewer time
saved. Current rule quality needs improvement.

**Software checks:** 255 backend tests passed, 8 live tests skipped, 74 subtests
passed; 20 frontend tests, lint, TypeScript and production build passed. Unit-test
success is separate from agreement with external expert labels.

Sources for notes: [full measured report](EVALUATION_REPORT.md),
[exact counts/configuration](metrics.json), [table CSV](metrics.csv),
[SYNERGY](https://github.com/asreview/synergy-dataset),
[EBM-NLP](https://github.com/bepnye/EBM-NLP),
[BigBio card](https://huggingface.co/datasets/bigbio/ebm_pico).

## What to leave out

- A single “overall accuracy” that combines these different tasks or software tests.
- A Comparator percentage, dedup precision or work-savings percentage without labels
  or a measured time study.
- A learned model, active-learning feature or clinical-validation claim that is not
  implemented and measured.
- A deployment-ready badge before the team verifies the actual hosted environment.
