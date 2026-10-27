# EvidenceFlow — Agent Guide
## Purpose
Mini-Rayyan systematic review tool: question → query versions → fetch (Europe PMC, PubMed)
→ store (nothing deleted) → dedup → screen (I/E/M + reason) → PICO → review/export,
with a query-change loop that preserves reviewer decisions. Authoritative spec:
docs/REQUIREMENTS.md, docs/ARCHITECTURE.md, docs/DATABASE_DESIGN.md, docs/LOOP_DESIGN.md,
docs/API_CONTRACTS.md. If code and docs disagree, stop and flag it.

## Non-negotiables
1. Never delete records, decisions, suggestions or audit rows. Hide via state.
2. Machine output and human decisions live in different tables. Machine code never writes human tables.
3. Every exclusion has a reason (criterion_id or reason_text). Enforced in schema, API and UI.
4. Conflicts are never resolved automatically.
5. No hardcoded topics, titles, IDs, counts or demo-only logic.
6. Reruns are idempotent: no duplicate records, pairs, suggestions, conflicts or audit events.
7. No secrets in git. Config via environment variables only.

## Run
make dev (backend :8000, frontend :5173) · make test · make seed · make build

## Ownership (do not edit outside your area without the owner's OK)
A: backend/app/{core,models,repositories,api}, services/{review,query,decision,loop,audit,export}, alembic, docs/*DESIGN*, API_CONTRACTS
B: backend/app/adapters, services/ingestion_service.py, tests/fixtures, scripts, Dockerfile
C: backend/app/engines, services/{deduplication,screening,pico}_service.py
D: frontend/**, docs/DEMO_SCRIPT.md
Only A creates migrations. Contract changes: update docs/API_CONTRACTS.md + schemas + TS types in ONE PR, notify all.

## Git
Branches: feat/<member>-<topic>. Small PRs into main; A merges at integration windows
(h6, h10, h14 … every 4h). Never force-push main. Rebase before PR.

## Definition of done
Tests added and passing (pytest / vitest); lint clean (ruff, eslint); behaviour verified
in the running app; docs updated if contracts changed; PR description lists what was
NOT tested. Never claim a test passed unless you ran it.

## Conventions
Python: snake_case, type hints, ruff format. TS: camelCase, strict mode.
API JSON is snake_case. Dates ISO-8601 UTC. Enums lowercase strings.
State assumptions and blockers explicitly in PRs (## Assumptions, ## Blockers).
