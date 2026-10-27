# Backend Guide
- Layers: api → services → (engines | repositories | adapters). Engines are pure (no DB, no I/O, no app imports).
- Routes: thin. Validate with Pydantic, call ONE service method, map AppError → error envelope
  {error:{code,message,details}}. 404 for missing, 409 for version/state conflicts, 422 validation.
- Transactions: one per pipeline step; services take a Session; never commit inside engines/adapters.
  A failed step must leave earlier steps committed and consistent and the run marked failed.
- Immutability: query_version is frozen after preview; criteria_version and criterion are immutable;
  edits create new versions. Decision tables are append-only (supersede, never UPDATE values).
- Machine vs human: *_suggestion, duplicate_pair, pico_annotation(origin=machine) are machine.
  screening_decision, pair_decision, pico_annotation(origin=human), representative_pin are human.
  Machine reruns must not read-modify-write human rows.
- Idempotency keys: record (review, source, source_record_id); query_record PK;
  suggestion (record, criteria_version, content_hash, algo_version); conflict open fingerprint.
- Audit: every human mutation writes audit_event with before/after. System runs write one
  summary event per run. No events for no-op changes.
- External APIs: httpx with timeout (env HTTP_TIMEOUT, default 20s), token-bucket limiter
  (PubMed 3/s, or 10/s with key; Europe PMC ≤ 5/s), retry 3x with backoff on 429/5xx, send NCBI tool+email.
  Adapter returns RecordIn only. Tests must not hit the network (respx + fixtures); live tests are
  marked @pytest.mark.live and skipped by default.
- Migrations: Alembic only, by Member A, batch mode for SQLite.
- Tests: unit for engines/normalisers; integration with a temp SQLite DB for every service path and
  every loop scenario A–F.
