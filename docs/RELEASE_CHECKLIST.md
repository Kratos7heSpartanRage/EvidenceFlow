# EvidenceFlow — Release & Verification Checklist (Hours 60–72)

## 1. Clean-Clone & Verification Instructions

### Step 1: Clone and Environment Setup
```bash
git clone https://github.com/SHRINIVAS-BHONG/evidenceflow.git
cd evidenceflow
cp .env.example .env
```

### Step 2: Database Migration Verification
Run migrations to head and assert zero schema drift:
```bash
cd backend
python -m alembic upgrade head
python -m alembic check
```
*Expected Result*: `No new upgrade operations detected.`

### Step 3: Linting & Code Standards Check
```bash
python -m ruff check backend/
python -m ruff format --check backend/
```
*Expected Result*: `All checks passed!`

### Step 4: Full Automated Test Suite Execution
```bash
python -m pytest backend/tests/ -v
```
*Expected Result*: **223 passed**, 0 failures.

---

## 2. Invariant & Contract Audit Checklist

- [x] **Zero Records Deleted**: Soft-hiding implemented via `is_hidden` column. Zero `DELETE` statements on bibliographic or decision tables.
- [x] **Machine vs. Human Separation**: Machine output stored in `screening_suggestions` and `duplicate_pairs`; human verdicts in `screening_decisions` and `pair_decisions`.
- [x] **Exclusion Reason Invariant**: Schema `CheckConstraint` and Pydantic validator enforce that `decision == 'exclude'` requires non-empty `criterion_id` or `reason_text`.
- [x] **Zero Auto Conflict Resolution**: Conflicts remain `open` until human consensus resolution.
- [x] **Idempotent Reruns**: Composite unique constraints prevent duplicate records, pairs, or suggestions on repeated imports.
- [x] **Transitive Bypass Guard (Scenario D)**: Negative human cannot-links prevent false transitive merges; BFS shortest path logs the explanatory chain.
- [x] **Zero-API Revert (Scenario E)**: Workspace rolled back exactly to `GroupSnapshot` with 0 external HTTP calls.
- [x] **Criteria Evolution Loop (Scenario F)**: Updating criteria creates versioned models and recalculates machine suggestions while keeping human decisions 100% intact.
- [x] **Quarantine CSV Export**: Open reviewer conflicts trigger `X-Conflict-Warning: QUARANTINE_OPEN_CONFLICTS` and isolate conflicting clusters.
