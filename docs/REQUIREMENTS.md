# EvidenceFlow — System Requirements Specification

## 1. Overview & Purpose
EvidenceFlow is a high-velocity, deterministic systematic review platform designed for clinical and evidence-based medicine researchers (Mini-Rayyan). It structures and automates the literature synthesis lifecycle:
$$\text{Research Question} \longrightarrow \text{Query Strategy Versions} \longrightarrow \text{Multi-Source Ingestion} \longrightarrow \text{Deduplication} \longrightarrow \text{Screening (I/E/M)} \longrightarrow \text{PICO Extraction} \longrightarrow \text{Conflict Resolution} \longrightarrow \text{RFC 4180 CSV Export}$$

The central challenge EvidenceFlow solves is the **Literature Search Evolution Loop**: Allowing reviewers to iteratively broaden, narrow, or pivot literature search queries across PubMed and Europe PMC without losing previously recorded human screening verdicts, duplicate pair decisions, or audit history.

---

## 2. Non-Negotiable Invariants

1. **Zero Data Deletion**:
   - Bibliographic records, screening verdicts, deduplication pairs, machine suggestions, and audit events are **never deleted**.
   - De-selection or rollbacks hide records via state (`is_hidden = True`).

2. **Strict Separation of Machine Output & Sovereign Human Decisions**:
   - Machine predictions live in `screening_suggestions` and `duplicate_pairs`.
   - Human reviewer verdicts live in `screening_decisions` and `pair_decisions`.
   - Machine pipeline runs **never** overwrite, mutate, or erase human decisions.

3. **Mandatory Exclusion Reasons**:
   - Every exclusion verdict (`decision == 'exclude'`) strictly requires an explicit reason (either a linked `criterion_id` or non-empty `reason_text`).
   - Enforced simultaneously in database check constraints, Pydantic schemas, and API validation (HTTP 422 Unprocessable Entity).

4. **No Automatic Conflict Resolution**:
   - Contradictory reviewer decisions (`include` vs `exclude`) or transitive duplicate bypasses are flagged as open `Conflict` items.
   - Conflicts are only resolved through explicit human consensus.

5. **Deterministic Idempotency**:
   - Rerunning query ingestion, candidate pair scoring, graph clustering, or screening suggestions produces identical states without creating duplicate database rows.
   - Enforced by unique composite constraints:
     - Record identity: `(review_id, source, source_record_id)`
     - Candidate pair: `(review_id, record_a_id, record_b_id)`
     - Suggestion idempotency: `(record_id, criteria_version_id, content_hash, algo_version)`
     - Group snapshot: `(query_version_id, record_id)`

6. **No Demo-Only Logic & No Hardcoded Data**:
   - Dynamic parameters only; production data structures used uniformly across test suites.

7. **Zero Secrets in Git**:
   - Configuration strictly driven by environment variables (`.env`).

---

## 3. Systematic Review Lifecycle (PRISMA 2020 Compliant)

### Phase 1: Problem Definition & Protocol Registration
- Protocol capture: Review title, PICO question framing (Population, Intervention, Comparator, Outcome).
- Eligibility criteria initialization: Inclusion and exclusion criteria with field targets (title, abstract, MeSH).

### Phase 2: Literature Search Strategy & Versioning
- Versioned query tree (`QueryVersion`) tracking parent-child evolutionary lineage.
- Offline and online query preview estimating search hits and returning sample records.
- Set-theoretic query diffing calculating $\Delta_{\text{new}}$, $\Delta_{\text{retained}}$, $\Delta_{\text{dropped}}$, and screened study retention.

### Phase 3: Deduplication & Canonical Election
- Two-tier hybrid deduplication:
  - Exact bibliographic matching (DOI, PMID, normalized title/year).
  - High-confidence / review-needed fuzzy scoring.
- Deterministic canonical study election within connected clusters:
  $$\text{Presence of DOI} > \text{Presence of PMID} > \text{Abstract Length} > \text{Earliest Publication Year}$$
- Scenario D Guard: Human pair rejection prevents transitive bridging across disconnected studies.

### Phase 4: High-Velocity Screening & Decision Propagation
- Sovereign decisions: Include, Exclude (with reason), Maybe.
- Intra-cluster propagation: Marking one study updates all sibling duplicates in the canonical cluster with `origin='inherited'`.
- Reviewer conflict engine: Divergent human verdicts trigger open conflict flags and block export.

### Phase 5: Clinical PICO Entity Span Extraction
- Spans extracted per clinical dimension ($P, I, C, O$) with text offsets and confidence ratings.
- Human curation operations: `confirm`, `correct` (updating entity text), `reject`.

### Phase 6: Synthesis, Quarantine & RFC 4180 CSV Export
- Generates compliant CSV exports containing only included canonical representatives.
- Quarantine engine: Records with open conflicts are excluded from export, triggering warning header `X-Conflict-Warning: QUARANTINE_OPEN_CONFLICTS`.
