# PR #8 integration notes

## Implemented

- Candidate duplicate storage, scoped to the review with canonical endpoint order.
- `GET /api/reviews/{id}/duplicate-pairs` and
  `POST /api/reviews/{id}/pair-decisions`, including structured-author display.
- Automatic candidate scoring from C's actual engine during direct-record import.
- Deterministic grouping and representative selection using shared pure functions.
- Current human rejections act as cannot-link constraints. Bridges are held back
  and create unresolved `pair_override_bypassed` conflicts. Conflicts are not
  automatically marked resolved when the graph changes.
- Stable group identities based on review and membership. Historical groups are
  retained; orphaned historical groups do not inflate dashboard study counts.
- First-import group snapshots remain unchanged after later regrouping.
- Direct import completes storage and deduplication, then pauses at 50% before
  screening/PICO. Deduplication failures preserve the earlier committed import
  step and mark the run failed; retry does not duplicate imported records.

## Conflicts and correctness fixes

The incoming branch was based on the older A-only backend and conflicted with the
merged main branch. Its database implementation is now
`DatabaseDeduplicationService` in `deduplication_db_service.py`. C's
`DeduplicationService` and repository interfaces remain available in their
existing module. Imports consistently use `app.*`.

Both services use `group_with_rejections()` from the pure dedup engine. Human
confirmations are considered first, followed by automatic edges in stable
record-ID order. Edges crossing a rejection are held back and explicitly flagged
for review. The grouping policy change bumps the algorithm version to
`dedup-rules-2`. The database representative uses the existing engine preference:
abstract, valid DOI, PubMed source, then lowest internal ID.

The latest human verdict controls grouping, so a reviewer can correct an earlier
rejection. Repeating an identical verdict does not append duplicate decisions or
audits. Verdict, regrouping, and audit changes commit together, and roll back if
the audit fails.

The original split logic could reuse one group for both new components. The
membership-based identities prevent this. The incoming snapshot code also
overwrote historical assignments and deleted orphaned groups; both behaviors
have been removed.

Pair endpoints are validated before writes. Self pairs, incomplete or ambiguous
targets, and records from another review are rejected. Repeated candidates in
one batch are stored once. Structured authors remain JSON-safe in storage and
are converted to names in duplicate-review summaries.

## Remaining limitations

- The current duplicate-pair table has no revision/evaluation key. Existing
  pending evidence is immutable; a changed score/tier/reason payload returns
  `409 PAIR_EVALUATION_CHANGED` instead of overwriting history. A schema extension
  is still required for re-evaluation after content/algorithm changes.
- DB snapshots are first-import query snapshots, not full run/workspace revision
  history. Their presence does not implement exact revert or historical metadata
  restoration. Empty snapshots still have no separate completion marker.
- Grouping currently considers visible records in the whole review. Active
  query-version workspaces are still pending.
- Screening/PICO repositories and pipeline stages, group screening-decision
  reconciliation, conflict resolution, background source ingestion, export,
  exact-revert endpoints, and the frontend remain incomplete.
- Database import uses one query per source. The new tests use separate PubMed
  and Europe PMC versions rather than mixing sources under one query version.

## Validation

The combined Python 3.13.5 suite passed **216 tests**, with **8 live tests skipped**
and **74 subtests passed**. Focused checks cover changed verdicts, actual group
splitting, immutable snapshots, deterministic rejection guards, conflict
idempotency, retained-history counts, cross-review inputs, atomic audit failure,
immutable machine evidence, duplicate batches, malformed API targets, failed-step
retry, and consistency between pure and database grouping.

Ruff lint and formatting passed. A local Uvicorn server on a newly migrated disposable DB passed duplicate-list, confirm, and subsequent reject HTTP checks, with the rejected records ending in separate groups. Existing schema tables are reused; no database
migration was added. Live literature calls, PostgreSQL concurrency, deployment,
and clinical accuracy were not tested in this integration.
