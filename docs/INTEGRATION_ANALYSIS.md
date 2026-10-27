# Combined backend analysis — 27 October 2026

## Integrated changes

This integration preserves the histories of Member C's engines (PR #1), Member
B's Europe PMC/PubMed adapters (PR #4, including the earlier #2/#3 commits), the
optional title/abstract search scope from closed PR #5, and Member A's backend
foundations and review/query services (PR #6). PR #5 was included after the user
delegated the choice: it is additive, optional, and directly useful for comparing
search scope. Closed PRs were not reopened.

## Compatibility fixes

- Standardized backend imports on `app.*`. Mixing `backend.app` and `app` could
  otherwise load duplicate SQLAlchemy metadata and incompatible model classes.
- Kept B's canonical `QuerySpec`, `Author`, and `RecordIn` fields, with validation
  aliases and read-only compatibility properties for A's initial names. Dates
  are validated as dates and converted to ISO strings for storage.
- Preserved the source enum under both `SourceName` and `LiteratureSource`.
- Mapped structured authors into JSON for persistence and added
  `to_engine_record()` to map DB fields, authors, and MeSH headings to C's input.
- C's engine/service IDs now accept A's UUID strings as well as the integer IDs
  used in existing examples, with deterministic ordering.
- Added migration `0002_query_options` to persist `title_abstract_only` and a
  frozen preview payload. Synonym expansion uses the existing DB `synonyms`
  field. Query responses expose both `synonyms` and `expand_synonyms`.
- Replaced fabricated preview counts/sample papers with calls to the selected
  source adapter. Zero-hit results remain zero; repeated previews use the saved
  payload. Source failures return a 502 error envelope without freezing a draft.
- Removed false completion reporting from the preliminary import helper. Direct
  supplied-record imports now stop at `awaiting_processing`, 25%, with later
  steps queued. The unwired background import route returns
  `501 PIPELINE_NOT_READY` before creating a run.
- Fixed validation-error JSON serialization and validated criterion types at the
  input boundary, before review/version writes.
- Isolated tests in a temporary SQLite database, retained offline source
  fixtures, reconciled dependency configuration, and formatted/linted the code.

## What is usable now

| Area | Current behavior |
| --- | --- |
| Database foundations | Initial schema plus search-option migration; SQLite foreign keys and WAL configuration |
| Reviews | Create/list/read/update reviews and version criteria; audit entries and dashboard counts |
| Query versions | Create/list/read versions, validate dates, save source/options, freeze real previews |
| Source adapters | Europe PMC and PubMed count/preview/search interfaces, rate limiting, retry handling, offline fixtures |
| Preliminary persistence | Direct `RecordIn` imports save unique source records and query provenance links |
| Version diff | Record-set differences between two query versions in the same review |
| Engines | Deterministic duplicate suggestions/groups, screening evidence, and PICO spans/unknowns |
| Engine services | Repository interfaces, caching semantics, staleness reporting, pair overrides and bypass conflicts |
| Server | FastAPI health/review/query/run routes and OpenAPI document |

## Work that remains

### 1. Complete the ingestion and processing runner — A + B + C

B's adapter `SearchResult.ids` includes already-known records while `records`
contains only newly fetched records. Ingestion must link **all** retrieved IDs to
the new query version, including known rows; accepting `records` alone would
lose provenance. Persist fetch warnings, source counts, skipped-known counts, and
truncation information. Handle empty results and failures in step transactions.
The helper currently counts newly stored records; the product must distinguish
new rows from the total records linked to a query version.

Connect a real background runner to fetch, persist, deduplicate, reconcile
decisions, screen, and tag. A successful run must mean every required step
succeeded. Preserve earlier committed steps on a later failure and support an
idempotent retry.

### 2. Align machine-result storage with engine contracts — A + C

The existing schema is not yet sufficient for the repository interfaces:

- Duplicate pairs need evaluation/algorithm lineage and immutable evidence.
  Historical edges must not silently become the current active edges.
- Group snapshots are currently keyed by query version; C's interface snapshots
  each pipeline run/workspace. A query version can participate in multiple runs.
- Screening needs the full context fingerprint and categorical evidence
  strength. The DB's required numeric `confidence` is not a calibrated engine
  probability and must not be fabricated to satisfy the column.
- PICO needs complete versioned batches, input/term fingerprints, nullable values
  for unknown labels, and a human correction/supersession model. Current required
  text/offset columns cannot directly store an unknown annotation.
- Stored criteria currently expose labels/descriptions/regex. C also needs
  explicit detector code, reason, parameters, kind, and active state. Agree on a
  mapping or extend the schema; do not infer detector codes from display labels.

`docs/MEMBER_C.md` describes the repository contracts and idempotency keys. A new
schema migration and real repository adapters are still needed. Passing the
cross-branch record-mapping tests does not mean these persistence adapters exist.

### 3. Finish human review and the query-change loop — A + C + D

Manual screening, pair decisions, PICO correction, group-decision reconciliation,
conflict resolution, active workspace selection, exact revert, audit-list and
CSV-export endpoints are still unimplemented. The loop document describes target
behavior. The current diff is a record-set diff; group merges/splits, inherited
decisions, and conflicts are not fully computed by the running application.
Dashboard counts and partial service tests do not establish the whole loop.

### 4. Build the UI — D

The frontend contains directory placeholders and an agent guide, with no runnable
React project. Build the forms/queues, highlights, provenance/history, conflict
review, export flow, and source notices. Shared API payload types are now in
`frontend/src/types/api.ts`; regenerate from OpenAPI as the API grows.

### 5. Tighten persistence guarantees and validate real workflows — team

Review service/audit methods still commit independently. Move toward step-level
transactions so a review/criteria write and its audit event cannot diverge on
failure. Add concurrency/version-number checks, content refresh handling, and
machine/human preservation tests against the actual repository adapters.

Legacy `QuerySpec.language` is retained as metadata for compatibility. Source
adapters do not currently apply it as a search filter. Apply explicit source
syntax or document a UI-level screening criterion before offering it as a working
search filter. Expanded record metadata is retained under
`Record.raw_payload.normalized`; not every field has a dedicated DB column.

Live API regressions, a real end-to-end demo, clinical relevance/PICO evaluation,
and reviewer-time measurements remain separate work. No model accuracy or time
saving has been demonstrated by synthetic software tests.

## Validation

The combined suite passed 202 tests plus 74 parametrized subtests, with 8 live API
tests skipped. New regression checks cover A/B field aliases, structured authors,
UUID-based engine processing, source option/date persistence, real/cached zero-hit
previews, source errors, invalid date envelopes, and truthful import status.

Alembic was checked on a disposable SQLite DB: upgrade from the initial schema,
preservation of an existing review/query, no metadata drift, downgrade to the
initial revision, and re-upgrade. Ruff lint and format checks passed. A local Uvicorn server started against a migrated disposable DB; health, OpenAPI, review/query requests, persisted options, and the unwired-import guard passed. The synthetic engine demo also completed.

The environment uses Python 3.13.5. Python 3.11, PostgreSQL, deployment, concurrent
imports, and live API calls were not validated in this integration. The installed
Starlette version emits deprecation warnings about its HTTPX test client and
the older 422 status constant; those did not fail the suite.
