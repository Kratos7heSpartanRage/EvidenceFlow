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
