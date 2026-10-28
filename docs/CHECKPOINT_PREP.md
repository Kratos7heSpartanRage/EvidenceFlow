# Manas's checkpoint preparation

Read this first. The measured tables are in
[the evaluation report](evaluation/checkpoint/EVALUATION_REPORT.md). Give the
[PPT handoff](evaluation/checkpoint/PPT_HANDOFF.md) to the teammate making slides.
This packet does not edit the supplied PowerPoint.

## What is ready, and what remains

| Checkpoint item | Evidence/status | What the team must do next |
|---|---|---|
| Deployed and functional product | Pending. You said deployment is planned today; no hosted URL was supplied. | B: deploy, verify persistence and share the real URL. Test the hosted product from another device. |
| UI/backend/database integration | Connected in merged PR #14; local browser workflow and fresh automated checks are documented. | Repeat the complete workflow on the deployed environment. Local success does not prove hosting works. |
| Algorithms and testing | Dedup, screening and PICO rules exist; this packet adds measured external-data screening/PIO benchmarks. | Present the methods, denominators and quality gaps honestly. |
| PPT and presentation | Your teammate owns the supplied 12-slide deck. Several claims need evidence or corrected wording. | Share the PPT handoff; rehearse the actual current app. |
| End-to-end demo | Local fixture workflow passed earlier. A real deployed/live-source demo is still a separate check. | Use a small live query, a populated pair and a clearly labeled backup recording. |
| Submission form and LinkedIn | Required by the checkpoint notice; neither was submitted by this work. | Team: obtain actual Form/template links, publish the required post/tag and submit its URL. |

The notice names **28 October** but says “tomorrow.” Confirm the actual checkpoint
time with the organizer; do not assume there is another full day available.
The PS says scoring weights are in a separate Scoring Metrics document, which was
not supplied. These are engineering evaluation results, not an invented official score.

## Your role in one sentence

“I worked on the deduplication, screening and PICO algorithms, their integrity
checks, and connecting the algorithm outputs into the working application.”

The supplied deck assigns backend/database/loop to Shrinivas, sources/import/
deployment to Kartik, algorithms/integration to Manas, and frontend to Mayank.
Describe shared work accurately if someone asks who implemented a particular fix.

## Your 90-second technical explanation

“EvidenceFlow helps a reviewer change literature searches without losing earlier
decisions. My part is the algorithm layer and its integration.

“Deduplication first checks normalized DOI and PMID, then title, year and author.
Uncertain or contradictory matches go to a reviewer. A conference abstract and a
journal report are protected from automatic merging. Screening checks available
metadata before applying documented text rules. Weak or missing evidence can stay
Maybe. PICO uses cue phrases and the review's own terms, and every proposed span
must point back to the abstract. These functions produce suggestions. The reviewer
can override them, and earlier evidence remains in history.

“For evaluation, we used the datasets named in the problem statement: 1,865 records
from three SYNERGY reviews and 186 expert-labelled EBM-NLP test abstracts. The
current rules are a limited baseline: strict Include F1 is 18.54%, and cue-only PIO
token F1 is 14.66%. These identify real relevance and boundary errors that unit
tests alone would not show. We keep human decisions explicit and do not claim the
rules replace expert screening. The next algorithm improvement needs to be measured
against this baseline.”

Do not rush every percentage into the product pitch. Show the table when discussing
evaluation, then explain one failure and the planned improvement.

## The numbers you must understand

| Number | Correct interpretation |
|---|---|
| 1,865 / 141 | Screening records / included reference records across three complete SYNERGY subsets. Not the entire SYNERGY corpus. |
| 11.05% / 57.45% / 18.54% | Strict Include precision / recall / F1. Only an Include suggestion counts positive. Maybe does not. |
| 138 / 141 = 97.87% | Included reference studies kept if both Include and Maybe remain for human review. This is not 97.87% accuracy. |
| 1,650 / 1,865 = 88.47% | All records retained under that same hypothetical policy. High retention comes with substantial reviewer workload. |
| 3 | Included reference studies received Exclude suggestions. Human override remains necessary. |
| 917 = 49.17% | Records receiving Maybe. SYNERGY has no expert Maybe class. |
| 186 / 50,907 | Complete expert P/I/O test abstracts / official tokens in this benchmark. |
| 14.66% | PIO positive-token micro F1, with predicted I+C unioned into the corpus's Interventions label. Cue-only extraction, no review lexicon supplied. |
| 0.13% | Exact-span micro F1 on the same projected token runs. Boundary precision is a substantial limitation. |
| Comparator F1 | Not measured: EBM-NLP has no separate Comparator gold label. |
| Dedup precision/recall | Not measured: the selected corpora do not supply expert duplicate-pair labels. Regression tests check behavior separately. |

Use the generated report as the source of truth if any rerun changes a displayed
value. No manual reviewer-time study or reliable time-savings percentage was measured.

## Judge questions and answers

**Why did you use rules instead of an LLM?**

The brief permits rules and explicitly prioritizes a working end-to-end system.
Rules give reproducible suggestions and visible evidence without paid model API
calls. The measured baseline is weak on broader relevance and PIO boundaries.
That is a reason to improve the methods, not a reason to advertise high accuracy.

**Does passing hundreds of tests prove the algorithm is accurate?**

No. Unit/integration tests check intended behavior, API contracts and data integrity.
Dataset evaluation checks agreement with external reference labels. We report both.

**Why are your screening scores low?**

The present method uses limited metadata and keyword rules. The profiles only
approximate each review's eligibility criteria, while SYNERGY labels represent
final review decisions that can depend on full text. There are 75 missing abstracts.
These limitations explain the task, but they do not erase the observed errors. The three included-reference exclusions matched the literal report-type keywords “editorial,” “meta-analysis” or “systematic review.” A word mention is insufficient proof of publication type, so this is a concrete rule limitation to explain.

**Why is the PIO score low?**

The baseline recognizes a limited set of cue phrases and emits broad spans, while
the expert corpus marks finer token spans. We supplied no review lexicon or gold
terms. The score measures that cue-only setting. Better entity detection and
boundary handling need validation on untouched expert test data after development
on the corpus's training/development portions.

**Can you say “98% recall”?**

Only with the exact policy: 138 of 141 included references remain if Maybe stays
for review, and 88.47% of all records also remain. Strict Include recall is 57.45%.
We cannot call retention accuracy or claim it demonstrates large work savings.

**What is your Comparator accuracy?**

There is no independent Comparator label in this EBM-NLP benchmark. Its
Interventions annotations combine treatment/control information. We report the
PIO mapping explicitly and keep Comparator accuracy unmeasured. Comparator rules
have regression coverage; an independently annotated comparator set is future work.

**What is innovative about the project?**

The concrete implemented distinction is the query-change workflow: immutable
query versions, record provenance, preserved human decisions, explicit conflicts
and query-snapshot restore without fetching sources again. A learned priority
ranker is only a proposed experiment, not a feature already present.

**What if an excluded paper appears in a later query?**

The same source-scoped record is linked to the new query version. Its human
decision remains stored. Machine output does not overwrite the human verdict.

**What if differently screened records become duplicates?**

The conflict must be shown to a reviewer and affected records stay quarantined
from export until explicit consensus. Earlier decisions remain in history.

**Does restore rewind every reviewer action?**

Current restore returns a query's saved record set/grouping without source calls.
It does not implement arbitrary historical workspace time travel or erase later
human decision history. Describe this scope exactly.

**Do criteria changes automatically re-screen everything?**

Currently a criteria update creates a new version; automatic scheduling of a
complete re-screen run is still planned. Processing uses the selected criteria
when it next runs. Do not present the planned trigger as already implemented.

**Is this multi-user authentication?**

No. The current reviewer name is an attribution label. Real authentication and
access control are separate work.

**How fast is it?**

The report measures pure engine calls locally and excludes retrieval, database,
network and UI time. Any full-pipeline claim needs a separate logged run with
query, cap, source, cache state, timing boundaries and environment. The deck's
174-papers/7.5-seconds figure needs Kartik's evidence before you repeat it.

## Your two-minute live-demo contribution

1. Show one actual duplicate candidate. Explain the identifier/field evidence and
   distinguish a suggestion from a human confirm/reject decision.
2. Open a record, press Exclude and show that a reason is required. Submit a real
   reason on a disposable demo record. Show the reviewer attribution.
3. Show PICO span cards, correct wording copied exactly from the abstract and show
   the effective human overlay. Do not promise inline highlighting that the current
   screen does not render.
4. If the prepared scenario contains a query expansion/conflict, explain preserved
   decisions and consensus. Show restore only after its import/snapshot completed.
5. Hand off to the presenter for audit and CSV. Keep a known working example; do
   not depend on discovering an uncertain pair during the presentation.

Practice these actions before the checkpoint. The original PS asks for live APIs
in the demo; a fixture backup must be labeled as a backup, not presented as a live
literature retrieval.

## After the team deploys today

- Open the public URL from a second device and verify `/api/health` reports the
  database connected. A status page alone is insufficient.
- Create a small demo review, save criteria/PICO, preview an approved live query,
  import with a small cap, and watch queued/running/completed or failure states.
- Verify an actual duplicate decision, exclusion reason, PICO correction, audit
  entry and downloadable CSV through that URL.
- Refresh/reopen the browser, then restart the deployed process and verify the
  saved review and decisions remain. Check the persistent storage/migration setup.
- Exercise the prepared changed-query/restore case and the empty-result case.
- Confirm the PPT is the required template copy, replace unsupported numbers, and
  have the team record a short backup while the known working scenario is ready.
- Complete the required LinkedIn post/tag and Form submission using the actual
  organizer links. This task did not publish a post, message anyone or submit a form.

## Final rehearsal

You should be able to answer, without reading code: what triggers an automatic
duplicate suggestion, why a record becomes Maybe, how an exclusion gets its
reason, what an offset proves, which metric comes from which dataset, and what
the team has verified on the hosted URL. If a feature is planned, say “planned.”
