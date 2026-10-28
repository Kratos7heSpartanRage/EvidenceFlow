# PR reconciliation — 28 October 2026

## Scope

- PR #10 and PR #11 share the same head commit and contain the same review APIs.
  Their history is included once through PR #13.
- PR #12 makes the unreachable-local-port adapter test accept either network or
  timeout failure, including Windows behavior.
- PR #13 connects approved searches to the background import pipeline and
  includes the new records, screening, PICO, conflict, revert, audit and export
  routes.
- The existing frontend from main is retained. Backend wire types have moved to
  `frontend/src/types/backend.ts`, exported as `BackendApi` from `api.ts`.
  This avoids TypeScript interface merging with the UI's numeric-ID view models.

## Corrections made before merging

1. PICO confirmation/correction/rejection now appends human overlay rows rather
   than changing machine origin or provenance. `supersedes_id`, status and
   reviewer preserve the edit chain. Record detail returns effective
   `pico_spans` plus complete `pico_history`. Rejected annotations disappear from
   the effective view while their history remains available. Corrected offsets
   must slice the original abstract text exactly; invalid batches roll back.
2. Machine PICO batches include record/term fingerprints and algorithm version.
   Changed review terms can produce a new batch without erasing earlier
   suggestions or human overlays. Repeated identical curation is a no-op.
3. Opposing reviewers remain active until explicit consensus rather than being
   silently superseded by a different reviewer. Group merges with differing
   active verdicts create an open conflict and are quarantined from export.
   Consensus supersedes all applicable active verdicts and frees the open-conflict
   fingerprint so a later disagreement can be recorded.
4. Screening and consensus criteria must belong to the record's review. Manual
   criteria remain unassessed by automation and block an unearned Include
   suggestion. `detector_rule` accepts named engine codes or literal keyword
   alternatives separated by `|`; it is not a general-purpose regex runner.
5. Background workers atomically claim a queued run. Re-executing an already
   claimed/completed run does not repeat source requests or completion audits.
   Startup marks both queued and running interrupted jobs failed for retry.
6. Known records found after a revert are reactivated and linked to the approved
   query. Records returned by the wrong source adapter fail the fetch transaction.
7. Explicit snapshot-completion markers support restoring empty result sets.
   Query snapshots elect a representative from within that query's record set,
   including when the current global representative belongs to another source.
   Repeating an already identical restore does not append a no-op audit.
8. CSV export handles ungrouped representatives in the presence of unrelated
   conflicts and emits each representative once.
9. Earlier C methods and integration drafts are retained under `docs/archive/`.

## Database update

Migration `0003_review_integrity` adds PICO overlay/version fields, an explicit
query snapshot marker, and the four performance indexes added by the incoming
model changes. Existing records and annotations are preserved. Snapshot markers
are backfilled for earlier captured queries. Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

## Validation

- Python 3.13.5: 242 tests passed, 8 live tests skipped, 74 subtests passed.
- Backend Ruff lint and formatting passed.
- Frontend TypeScript compilation, production Vite build, and all 7 Vitest tests
  passed. The tests use the frontend's mock mode; they do not establish complete
  live UI-to-backend integration.
- Frontend ESLint reports 94 errors and 6 warnings. The same check against the
  previous main commit `99fa0cd` reports exactly 94 errors and 6 warnings.
  Existing unused bindings and explicit `any` types were not hidden by changing
  lint rules.
- Alembic upgrade, metadata drift check, downgrade/re-upgrade and legacy
  review/query/PICO preservation passed against disposable SQLite storage.
- A real local Uvicorn server on a migrated DB passed approved background import,
  record listing, append-only PICO curation, human screening, CSV export,
  repeated-import reuse, and empty-query restore with synthetic source fixtures.

## Remaining limits

- The frontend view models and live wire models still need deliberate mapping
  across all screens; successful compilation is not proof of live UI parity.
- Criteria version creation does not itself schedule a complete re-screening run;
  the new criteria take effect when processing next runs.
- Group snapshots represent a query's record set, not an arbitrary union of
  active query versions. Full workspace/run revision history remains unfinished.
- General structural-conflict resolution requires duplicate-pair decisions;
  screening consensus alone cannot change a rejected duplicate relationship.
- Machine duplicate-pair re-evaluation still needs versioned storage; changing
  pending evidence is rejected instead of overwriting history.
- Completed unknown-only PICO batches have no separate batch marker, so an
  unchanged untaggable abstract may be scanned again without creating rows.
- Multi-worker concurrency, PostgreSQL, deployment, live literature services,
  clinical accuracy and reviewer time savings were not validated here.
