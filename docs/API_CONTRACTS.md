## PR #8 implementation update

The duplicate-pair GET and pair-decision POST routes are now implemented. Both
operate within the selected review. `RecordSummary.authors` is a list of display
name strings, including when stored authors are structured objects.

`PairDecisionIn` accepts exactly one target form: `duplicate_pair_id`, or both
`record_a_id` and `record_b_id`. Targets must exist in the review; self pairs and
incomplete/ambiguous targets return 422. Identical repeated verdicts are no-ops.
The latest verdict controls grouping, with earlier rows preserved. Database
verdict, regrouping, and audit writes form one transaction.

The direct-record import helper now runs real candidate scoring and deduplication,
records immutable first-import query snapshots, and pauses at 50% before
screening/PICO. A dedup failure marks the run failed while preserving committed
record/provenance rows for an idempotent retry. The background import route still
returns `501 PIPELINE_NOT_READY` until that runner is connected.

Machine pair evidence is immutable in the current schema. Changing an existing
pending evaluation returns `409 PAIR_EVALUATION_CHANGED` until versioned evaluation
storage is implemented. Historical group rows are retained and are not counted
as active studies when they have no visible members.

> **Implementation status (28 October 2026):** All core Role A backend modules are implemented and verified: Health, Reviews/Criteria, Query tree/preview/import/diff, Scenario E Zero-API Revert (`/api/queries/{id}/revert`), Duplicate-pairs review (`/api/reviews/{id}/duplicate-pairs`, `/api/reviews/{id}/pair-decisions`), Records listing & details (`/api/reviews/{id}/records`, `/api/records/{id}`), Screening decisions with mandatory exclusion reasons & conflict detection (`/api/records/{id}/screening`), PICO span curation (`/api/records/{id}/pico`), Conflict resolution by consensus (`/api/reviews/{id}/conflicts`, `/api/conflicts/{id}/resolve`), and RFC 4180 CSV Export & Audit Ledger (`/api/reviews/{id}/export.csv`, `/api/reviews/{id}/audit`). Direct supplied-record import returns `awaiting_processing` with downstream steps queued. All TypeScript types are synchronized in `frontend/src/types/api.ts`.

## Shared source and engine contract alignment

- Canonical `QuerySpec`: `source`, `expression`, validated `date_from`/`date_to`, `expand_synonyms` (default false), `title_abstract_only` (default false), and legacy `language`. The `synonyms` input alias remains accepted. Both search flags are persisted per query version; language is currently not applied by the adapters as a search filter.
- Canonical `RecordIn`: `source`, `source_record_id`, `title`, `abstract`, `doi`, `pmid`, `pmcid`, structured `authors` (`full_name`, `last_name`, `initials`), `year`, `publication_date`, `journal`, `volume`, `issue`, `pages`, `language`, `pub_types`, `mesh_terms`, `keywords`, `raw`. Missing metadata remains null/empty.
- Compatibility input aliases: `publication_year` -> `year`, `publication_types` -> `pub_types`, `mesh_headings` -> `mesh_terms`, `raw_payload` -> `raw`; author strings are converted to structured names. These old names remain read-only Python properties.
- Internal record IDs are UUID strings. Provider IDs such as `MED:12345` stay in `source_record_id`; uniqueness is `(review_id, source, source_record_id)`. C engines support UUID strings and integer fixture IDs.
- `to_engine_record()` maps persisted record fields and authors to the engine dataclass. Complete normalized metadata is retained under DB `raw_payload.normalized`, with original source data under `raw_payload.source_payload`.
- Preview responses now include `warnings`, preserve zero hit counts, and return an immutable saved response on repeated calls. Source errors produce `502 SOURCE_ERROR` without freezing the draft.
- Frontend boundary types are in `frontend/src/types/api.ts`. C's complete cache/batch keys remain defined in `MEMBER_C.md` and still require real persistence adapters.

# EvidenceFlow — API Contracts

This document is the authoritative contract between frontend and backend.
JSON payloads use `snake_case`. Enums are lowercase strings. Dates are ISO-8601 UTC.
All errors follow the `{ "error": { "code", "message", "details" } }` envelope.

---

## 1. System & Health
### `GET /api/health`
- **Response `200`**:
  ```json
  {
    "status": "ok",
    "database": "connected",
    "version": "0.1.0",
    "time": "2026-10-27T18:00:00Z"
  }
  ```

---

## 2. Reviews & Protocol
### `POST /api/reviews`
- **Request**:
  ```json
  {
    "title": "Efficacy of SGLT2 Inhibitors in Diabetic Kidney Disease",
    "question": "In adult patients with type 2 diabetes and CKD, do SGLT2 inhibitors reduce renal progression compared to standard care?",
    "pico": {
      "population": "Adults with T2D and CKD",
      "intervention": "SGLT2 inhibitors",
      "comparator": "Placebo or standard care",
      "outcome": "Doubling of serum creatinine, ESRD, mortality"
    }
  }
  ```
- **Response `201`**: Full Review object with generated UUID `id` and initial dashboard counts.

### `GET /api/reviews` / `GET /api/reviews/{id}`
- **Response `200`**: Review object with dynamic counts (`total_records`, `unique_studies`, `screened_included`, `screened_excluded`, `screened_maybe`, `open_conflicts`, etc.).

### `PATCH /api/reviews/{id}`
- **Request**: Partial `{ "question": ..., "pico": ... }`.
- **Response `200`**: Updated Review. Audited in `audit_event`.

### `POST /api/reviews/{id}/criteria`
- **Request**: Full array of criteria for new version.
  ```json
  {
    "criteria": [
      { "type": "inclusion", "label": "RCT in adults", "description": "Adults >=18" },
      { "type": "exclusion", "label": "Animal study", "description": "Rodent models", "detector_rule": "rats|mice" }
    ]
  }
  ```
- **Response `201`**: `{ "criteria_version_id": "...", "status": "criteria_updated", "run_id": "..." }`. Triggers background criteria re-evaluation.

---

## 3. Query Strategy & Ingestion
### `POST /api/reviews/{id}/queries`
- **Request**:
  ```json
  {
    "label": "v1.0 — Initial targeted search",
    "parent_id": null,
    "spec": {
      "expression": "(TITLE:\"SGLT2\") AND (TITLE:\"kidney\")",
      "source": "europe_pmc",
      "synonyms": true,
      "date_from": "2019-01-01",
      "date_to": "2026-10-01"
    }
  }
  ```
- **Response `201`**: New `QueryVersion` in `draft` status.

### `POST /api/queries/{id}/preview`
- **Request**: Empty body `{}`.
- **Behavior**: Calls source adapter for count + top 20 sample. Freezes query version into `previewed`.
- **Response `200`**: `{ "query_id": "...", "estimated_hits": 84, "sample_records": [...], "is_frozen": true }`.

### `POST /api/queries/{id}/import`
- **Behavior**: Approves query, creates background `PipelineRun`, fetches records, dedups, screens, and extracts PICO. Idempotent: returns existing run if already running/imported.
- **Response `202`**: `{ "run_id": "...", "status": "queued" }`.

### `GET /api/runs/{id}`
- **Response `200`**: Pipeline run details with progress percent and step logs.

### `GET /api/queries/{id}/diff?against={parent_id}`
- **Response `200`**: Mathematical set difference:
  ```json
  {
    "query_v1_id": "qry-1",
    "query_v2_id": "qry-2",
    "new_records_count": 44,
    "retained_records_count": 84,
    "dropped_records_count": 0,
    "already_screened_retained_count": 62,
    "potential_conflicts_count": 1
  }
  ```

### `POST /api/queries/{id}/revert`
- **Behavior**: Restores workspace snapshot to query `id`. Makes **0 external API calls**.
- **Response `200`**: `{ "status": "reverted", "restored_version_id": "..." }`.

---

## 4. Records & Deduplication
### `GET /api/reviews/{id}/records`
- **Query Params**: `status`, `decision`, `q`, `version`, `page`, `page_size`, `representatives_only=true`.
- **Response `200`**: `{ "items": [ RecordItem, ... ], "total": 128, "page": 1 }`.

### `GET /api/records/{id}`
- **Response `200`**: Full Record with group provenance, suggestion, decision history, and PICO spans.

### `GET /api/reviews/{id}/duplicate-pairs`
- **Query Params**: `tier`, `decided=false`.
- **Response `200`**: Array of `DuplicatePair` (with similarity score, match reasons, and side-by-side records).

### `POST /api/reviews/{id}/pair-decisions`
- **Request**:
  ```json
  {
    "record_a_id": "rec-1",
    "record_b_id": "rec-2",
    "decision": "confirm",
    "note": "Same paper published in two indexes"
  }
  ```
- **Behavior**: Updates pair decision, triggers regrouping, preserves group snapshots.
- **Response `200`**: `{ "status": "recorded" }`.

---

## 5. Screening & Decisions
### `POST /api/records/{id}/screening`
- **Request**:
  ```json
  {
    "decision": "exclude",
    "criterion_id": "crit-exc-animal",
    "reason_text": "Animal model (Sprague-Dawley rats)",
    "reviewer_name": "Dr. Sarah Lin",
    "note": "Murine model only"
  }
  ```
- **Invariants**:
  - `decision == 'exclude'` **STRICTLY REQUIRES** `criterion_id` or `reason_text`. Missing reason returns **422 Unprocessable Entity**.
  - Decision supersedes prior decisions append-only.
  - Applies to the entire cluster group.
- **Response `201`**: Created `ScreeningDecision`.

---

## 6. PICO Annotations
### `PATCH /api/records/{id}/pico`
- **Request**:
  ```json
  {
    "ops": [
      { "op": "confirm", "span_id": "pico-1" },
      { "op": "correct", "span_id": "pico-2", "text": "dapagliflozin 10mg" },
      { "op": "reject", "span_id": "pico-3" }
    ]
  }
  ```
- **Response `200`**: `{ "status": "updated" }`.

---

## 7. Conflicts & Consensus
### `GET /api/reviews/{id}/conflicts`
- **Response `200`**: Array of open conflicts with opposing reviewer decisions.

### `POST /api/conflicts/{id}/resolve`
- **Request**:
  ```json
  {
    "decision": "include",
    "note": "Consensus panel confirmed primary endpoints match protocol",
    "reviewer": "Consensus Review Panel"
  }
  ```
- **Behavior**: Writes consensus decision to all cluster members with `origin='conflict_resolution'`. Marks conflict resolved.
- **Response `200`**: `{ "status": "resolved" }`.

---

## 8. Audit & Export
### `GET /api/reviews/{id}/audit`
- **Response `200`**: Paginated array of append-only `AuditEvent` with `before_state` and `after_state`.

### `GET /api/reviews/{id}/export.csv`
- **Behavior**: Generates RFC 4180 CSV of included canonical representatives.
- **Header Alert**: If open conflicts exist in the review, row count or header row includes quarantine warning.
- **Response `200`**: `text/csv; charset=utf-8`.
