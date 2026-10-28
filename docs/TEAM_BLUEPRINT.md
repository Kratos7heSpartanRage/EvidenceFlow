# EvidenceFlow — next-work blueprint for Members A, B, C and D

Planning baseline: `main` at `686f341` after PR #14, 28 October 2026.
This is a work plan, not a claim that the tasks below are implemented or tested.

C1 update: an initial external-data baseline and metric-validation harness are now
available in [the checkpoint report](evaluation/checkpoint/EVALUATION_REPORT.md).
The results expose quality gaps; C2 improvements and hosted deployment checks are
still follow-up work. See [Manas's preparation](CHECKPOINT_PREP.md).

## 1. Where the project stands

The frontend is connected to FastAPI for review creation, queries, preview/import,
records, duplicate decisions, screening, PICO curation, conflicts, history, audit
and CSV. Internal IDs are UUIDs. Machine suggestions and human edits are separate.

Last verified baseline: 242 backend tests passed, 8 live tests skipped, 74 subtests
passed; 20 frontend tests passed; Ruff, ESLint, TypeScript and the production build
passed. Browser verification used synthetic literature responses and a disposable
database. These results establish integration, not clinical accuracy or deployment
readiness. See [the integration guide](LIVE_FRONTEND_INTEGRATION.md).

Known unfinished work:

- Saving criteria does not automatically schedule re-screening.
- Records and audit views currently fetch all pages for client-side filtering.
- Changed machine duplicate evidence needs versioned persistence; the current
  implementation rejects an incompatible pending re-evaluation to protect history.
- Current query snapshots restore a query's set/grouping, not arbitrary unions of
  active queries or a historical copy of every reviewer decision.
- Live literature behavior needs a fresh check through the connected application.
- Populated duplicate-pair interactions need browser coverage.
- The reviewer selector is attribution, not authentication. Some review/query audit
  actions still use a default actor.
- Packaging, clean-clone startup, deployment and measured method quality need proof.

## 2. Assignment at a glance

| Member | Own the next outcome | First task | Main handoff |
|---|---|---|---|
| A — backend/database | Close the criteria-change loop and protect versioned state | Agree the re-screen request/run contract with D, then implement it | Run response, schemas, migrations and API notes for B/C/D |
| B — sources/ingestion/delivery | Prove real retrieval and make startup repeatable | Run small approved searches through both sources in the connected app | Reproducible checks, source fixtures and launch instructions |
| C — engines/quality — you | Measure dedup, screening and PICO quality and fix observed failures | Build a labeled evaluation set and baseline report | Failure fixtures for A/B/D and measured methods/results |
| D — frontend/demo | Make the connected workflow usable and demonstrable | Add server-driven screening/audit pagination | Browser regression coverage, working demo and report assembly |

Priority meanings: **P0** = finish before calling the release/demo ready;
**P1** = the next loop improvements; **P2** = optional innovation after P0 passes.
No submission deadline or available hours have been confirmed. Treat the two work
sessions below as sequencing, not calendar promises.

## 3. Member A — backend, database and integration

### A1. P0 — make criteria changes actually re-screen

- Preserve immutable criteria versions and explicitly start a stored processing
  run for the selected version. Agree whether the criteria response includes an
  optional `run_id` or a separate explicit trigger; document the choice before D
  wires the button. Do not silently change the existing response contract.
- Recompute eligible machine suggestions against the selected criteria version.
  Preserve every human decision, reason, reviewer and PICO overlay. Use input
  fingerprints so repeating the same run does not duplicate outputs or audits.
- Surface queued/running/completed/failed state through the existing run contract.
  Failure must be visible and retryable without a source refetch when stored
  records are sufficient.
- Define how already-screened records show a changed machine assessment without
  replacing their human verdict.

**Done when:** a changed criterion changes the applicable machine suggestion;
the old human decision and earlier suggestions remain stored; a repeat run is a
no-op where inputs are unchanged; D can follow progress and retry a failure.

### A2. P0 — finish the integration audit

- Verify conflict lifecycle after a group merge/split and after another reviewer
  changes a verdict: open conflicts still quarantine the right records, resolved
  conflicts do not hide a new disagreement, and consensus remains explicit.
- Verify decision inheritance when an undecided record becomes the new canonical
  representative. Do not create an independent human verdict from machine code.
- Agree a consistent actor field for remaining human review/query actions; retain
  compatibility and explain that labels are not login identities.
- Reconcile `REQUIREMENTS.md`, `ARCHITECTURE.md`, `LOOP_DESIGN.md` and the release
  checklist with actual behavior: representative election, query states, criteria
  reruns and restore scope. Distinguish planned behavior from passing checks.

**Done when:** the relevant loop regressions pass, export and record detail agree,
and no documentation advertises an unimplemented guarantee as complete.

### A3. P1 — persist machine re-evaluation history

- With C, define immutable duplicate-evaluation identity: record inputs, algorithm
  version, evaluation/run and pair identity. A owns any migration.
- Select current machine evidence without editing earlier evidence or human pair
  decisions. Compare old/new outputs without interpreting model confidence as a
  calibrated probability.
- If full active-query workspace revisions are required by the judging rubric,
  design them separately from the existing query snapshot contract. Define which
  parts restore and which human history remains current before implementation.

**Done when:** changed inputs can create a new evaluation, identical inputs reuse
it, prior evaluations remain readable, and rejected human pairs stay respected.

**Files:** `backend/app/{api,schemas,models,repositories,core}`, relevant services,
`backend/alembic/`, API/design docs. Keep migrations with A.

## 4. Member B — adapters, ingestion, fixtures and delivery

### B1. P0 — verify live sources through the connected workflow

- Use a private environment with valid NCBI identification/configuration. Never
  commit credentials or personal contact settings.
- Pick two different review topics and use small import caps. For PubMed and
  Europe PMC, record the date, expression, search options, reported hits, imported
  count, warnings and truncation. Do not expect equal hit counts between sources.
- Verify titles/abstracts-only behavior, empty results, absent abstracts/DOIs,
  source-scoped IDs and incremental retrieval of known records.
- Repeat an approved import and confirm record/provenance counts remain correct.
  Exercise a source failure and recovery using deterministic fixtures as well.
- Turn observed parsing failures into minimal lawful fixtures; keep the default
  test suite offline and live tests explicitly opt-in.

**Done when:** both adapters work through the UI on fresh queries, repeat import
preserves identity/provenance, and a short live verification log distinguishes
observations from skipped cases.

### B2. P0 — make a stranger able to run the project

- Test installation from a fresh clone of `Manas-Jain-24/evidenceflow`, following
  only the written guide. Verify Python install, `npm ci`, migrations and the API
  proxy. Fix commands that assume missing tooling such as the current Makefile.
- Add a repeatable launcher/check script; document environment variables, working
  directories, ports and persistent database location. A reviews database setup.
- Add CI for offline backend tests/lint and frontend tests/lint/build, with A
  reviewing the workflow. Do not make live literature availability a normal CI gate.
- If a hosted demo is required, prepare packaging and verify persistence across
  restart. Choose hosting only after the team's requirements and access are known;
  a container build alone is not evidence of a working deployment.

**Done when:** another teammate starts a clean clone without verbal help, saves
data, restarts it and finds that data intact. CI runs the documented checks.

### B3. P1 — supply deterministic integration scenarios

Provide an opt-in fixture workflow for a populated duplicate pair, a conference
and journal report that must stay separate, a reviewer disagreement, an expanded
query and an empty query. Keep fixtures inside tests/examples; production must
continue to use real configured sources and never silently fall back to samples.

**Files:** `backend/app/adapters/`, ingestion/pipeline work coordinated with A,
`backend/tests/fixtures/`, `backend/scripts/`, delivery configuration.

## 5. Member C — your engines, evaluation and innovation

### C1. P0 — measure the existing methods first

- Start with a manageable labeled set, for example 40–60 abstracts and 25–40
  duplicate pairs. These are suggested initial sizes, not evidence of statistical
  sufficiency. Include familiar and unseen topics, missing metadata, conference
  reports, non-human studies and ambiguous comparators.
- Label dedup pairs, eligibility plus reason, and exact P/I/C/O spans. Have another
  teammate check ambiguous examples and record disagreement rather than inventing
  a single unquestionable label.
- Separate development and held-out examples by underlying study/duplicate group
  to avoid leakage. Keep a manifest with IDs, provenance, usage rights and split.
- Add a reproducible evaluation command and report dedup precision/recall,
  screening include/exclude/Maybe counts and errors, and PICO span metrics with a
  stated exact-match/overlap policy. Report comparator performance separately.
- Record missing-abstract coverage, abstentions, per-stage time and dataset size.
  Do not equate an ordinal evidence strength with a probability or claim clinical
  validation from a small set.

**Done when:** another teammate reproduces the measured baseline from the saved
manifest, and the report identifies actual errors and uncertainty.

### C2. P0 — fix the highest-value observed failures

- Prioritize false duplicate merges, unjustified exclusions, incorrect comparator
  spans and offsets that do not slice the original abstract exactly.
- Add a regression fixture for each fixed failure. Re-run the held-out evaluation
  and document any precision/recall tradeoff; do not tune on the held-out examples.
- Keep engine functions pure and deterministic. Preserve Maybe/unknown when
  evidence is insufficient. Pass failure fixtures to A/B/D where the issue crosses
  engine, ingestion, persistence or UI boundaries.

**Done when:** selected failures are fixed, regressions pass and the updated
evaluation shows what improved and what became worse or stayed unresolved.

### C3. P1 — provide engine contracts for safe reruns

Specify the input/version fingerprints needed by A's evaluation-history work,
including changed review terms and algorithm versions. Demonstrate that repeated
inputs produce the same output and that human overrides remain outside the engine.

### C4. P2 — one optional AI/ML differentiator

**Proposed experiment: query-change review prioritization.** After a query changes,
rank the new or changed records that deserve attention first, using review context
and available reviewer labels. Explain each priority with evidence and whether a
query/criteria change affected it. Ranking must not create a human decision,
auto-exclude a record or resolve a conflict.

- Begin with the current ordering as a baseline and a reproducible split/order.
  Add a learned ranker only if there are enough independent labels to evaluate it;
  otherwise report insufficient evidence and retain the baseline.
- Compare relevant-study recall at a fixed screening budget and reviewer work
  required at a stated recall target. Report the exact denominator and uncertainty.
- Keep the experiment off by default until A agrees persistence/API semantics and
  D labels it as an experimental priority, separate from eligibility suggestions.
- If it does not improve the measured baseline, report that result. Do not add an
  LLM dependency merely to describe the product as AI-powered.

**Files:** `backend/app/engines/`, engine service interfaces/tests, a proposed
`backend/examples/evaluate_engines.py`, and proposed `docs/ENGINE_EVALUATION.md`.
The two proposed evaluation artifacts do not exist merely because this plan names them.

**Your immediate task:** C1, then C2. You do not need to rebuild the adapters,
database models or the frontend connection.

## 6. Member D — frontend, browser coverage and submission

### D1. P0 — stop loading entire reviews into the browser

- Start with screening and audit: send explicit page/page-size/filter parameters,
  retain server totals and include these parameters in TanStack Query keys.
- Preserve the selected record and handle loading, empty, error/retry and last-page
  transitions. Review switches must never reuse another review's data.
- Paginate export previews without truncating the backend-generated CSV download.
- Coordinate with A on a group-scoped member lookup before changing conflict views;
  fetching one page of a review is not a correct substitute for all group members.
- Extend the same approach to PICO lists where needed. Do not display unsupported
  sorting or metrics as if the backend supplied them.

**Done when:** first-page use does not fetch the full review, filters/totals agree
with the API, and the CSV still contains the complete eligible result set.

### D2. P0 — complete browser regression coverage

- With B's fixtures and C's hard cases, exercise populated duplicate confirm/reject,
  exact abstract/PICO corrections, mandatory exclusion reasons, opposing reviewers,
  explicit consensus, quarantine, zero-hit imports, restart/retry and restore.
- Verify criteria-change progress using A1's agreed contract. Do not imply that
  saving a criterion has already re-screened records before the run completes.
- Check keyboard shortcuts, modal focus/escape, narrow layouts and connection
  recovery. Keep machine suggestions, human decisions and experimental priorities
  visually distinct.

**Done when:** one repeatable browser workflow covers the actual connected app,
including a populated pair, with no production mock fallback or invented counts.

### D3. P0 — make the demo and report truthful

- Rewrite `DEMO_SCRIPT.md`: the removed Reset Demo button, fixed record IDs/hit
  counts, seven-step mock run and unsupported highlights must not be presented as
  current functionality. Use the real run steps and observed counts.
- Rehearse a five-minute walkthrough: protocol → approved search/import → duplicate
  review → screening reason → PICO correction → changed query/conflict → restore
  and CSV. Prepare a clearly labeled recorded/fixture backup.
- Assemble the short report from A's integrity/architecture notes, B's source and
  reproducibility notes, and C's measured baseline/tradeoffs. Label estimates.
- Confirm the original brief's five-minute demo/three-page report limits against
  the actual organizer instructions before submission; the current rubric/deadline
  has not been supplied in this chat.

**Files:** `frontend/`, `docs/DEMO_SCRIPT.md`, proposed `docs/PROJECT_REPORT.md`.

## 7. Parallel work and handoffs

| Work session | A | B | C — you | D |
|---|---|---|---|---|
| First | Agree and build criteria re-screen contract; audit integrity gaps | Verify live source flow; cold-clone startup | Create labels/split and baseline evaluation | Implement screening/audit pagination and populated-pair browser tests |
| Integration checkpoint | Share exact request/response/run examples | Share source failures and deterministic fixtures | Share measured failures and regression cases | Verify A's run response and B/C's cases in the UI |
| Second | Finish P0 regressions/docs; begin versioned evidence if P0 is green | Finish repeatable launch/CI and live log | Fix top failures and repeat evaluation | Wire criteria progress; rehearse demo and assemble report |
| After P0 | Evaluation/workspace version contracts | Support reproducible experiment data | Optional priority-ranking experiment | Optional experimental priority display |

Dependencies:

1. A1 contract → D's criteria progress UI. D's pagination can proceed independently.
2. B fixtures + C failure cases → A/D integrity and browser regression coverage.
3. A's versioned-evidence design + C's fingerprints → safe new machine evaluations.
4. P0 checks + measured C baseline → decide whether C4 is worth adding.

## 8. Release gate and collaboration rules

- Each member starts from current `main` and uses a focused branch/PR. A owns
  migrations and coordinates integration. Preserve teammates' commits; never
  force-push shared main.
- Every contract change includes API docs, Pydantic schemas and TypeScript wire
  types in the same PR, with an example request/response and affected consumers.
- PRs state assumptions, blockers, checks actually run and behavior not tested.
  Passing tests are evidence for their covered cases, not proof of every invariant.
- Release only after a clean-clone run, both-source checks, populated duplicate
  review, criteria rerun preserving human work, conflict quarantine/consensus,
  repeat-import idempotency, empty/populated restore, CSV and restart persistence.
- Re-run the relevant automated checks after changes and record the actual results;
  the baseline test count above is not a permanent expected total.
- Do not add authentication, arbitrary workspace time travel, a new model stack or
  a hosted service to P0 without an actual requirement and a reviewed design.
- If time is tight, finish P0 and show the measured deterministic baseline. Keep
  P1/P2 listed as future work rather than presenting them as completed innovation.

**Next team checkpoint:** each member reports their task ID, branch/PR, evidence
produced and exact blocker. No teammate messages or assignments have been sent by
creating this blueprint; it is ready for you to share.
