# Live frontend integration — 28 October 2026

## What is connected

- Create reviews in an empty database, select stored reviews by UUID, and remember the selected review.
- Save review question/PICO and create immutable criteria versions. Automatic detector rules are named codes or literal `|`-separated keywords; a blank detector requires manual assessment. Removing a criterion leaves its earlier versions in history. Criteria changes do not automatically schedule a new screening run.
- Create correctly nested query specs with synonym and titles/abstracts options, validate date order, preview hit counts (including zero), show warnings, approve import, and poll queued/running jobs every 1.5 seconds. Import caps are configured on the backend, not invented in the UI.
- Read duplicate candidates and detail abstracts, record confirm/reject verdicts, screen records with required exclusion reasons, and retain UUIDs in all requests.
- Read effective PICO spans from record detail and submit batch confirm/correct/reject operations. PICO curation now accepts reviewer attribution and keeps machine evidence intact. Creating arbitrary spans or changing their P/I/C/O label is not exposed because those operations are not implemented by the backend.
- Show active opposing reviewer decisions using `superseded_by_id`, submit explicit consensus with reasons for exclusion, and quarantine affected groups from CSV. Structural conflicts direct reviewers to duplicate-pair decisions.
- Compare any two stored query versions using the metrics actually returned by the API. Restore a chosen imported snapshot, including empty results; show real restored/hidden counts. No invented group-change metrics are displayed.
- Read paginated records/audit responses and download backend-generated CSV. The export preview uses stored decisions and effective PICO spans.

## Startup

From the repository root, with Python dependencies installed in `.venv`:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open Vite's URL. Create a review and enter its PICO/criteria, then use Search & Fetch. PubMed requires appropriate NCBI settings in the backend environment. `frontend/.env.example` documents API URL overrides. Production hosting needs a reverse proxy or a configured API base URL; it is not deployed by this change.

## Data and errors

There is no runtime mock fallback. Failed connections and backend validation errors appear with retry or an error banner. Every server read uses TanStack Query; query caches include the review UUID. Successful mutations invalidate relevant workspace data. Dashboard counts come from backend responses; empty databases show zero counts and an explicit create-review prompt.

The active reviewer is an attribution label, not authentication or authorization. Screening, consensus and PICO use it; some existing review/query operations still use the backend's default actor. Historical fixtures remain test-only.

## Verification

- 242 backend tests passed; 8 live literature tests skipped; 74 subtests passed.
- 20 frontend tests passed: empty-DB creation, review switching, zero counts, connection retry, error envelopes, wire payloads, paginated records, PICO operations, selected history comparisons/restores and queued-job polling.
- Frontend ESLint, backend Ruff lint/format, TypeScript compilation and Vite production build passed.
- Browser against local Vite + FastAPI + a migrated disposable SQLite database: created a review; saved PICO; created/previewed/imported a query; observed step completion; included one record and excluded another with a reason; confirmed/corrected PICO; created a reviewer disagreement; resolved consensus; downloaded CSV; compared a zero-hit query; restored empty and populated snapshots; inspected audit history.
- Browser source responses used synthetic fixtures. No production data or live literature requests were used in that smoke check.

## Remaining scope

Live literature availability, PubMed credentials, PostgreSQL, deployment, multi-worker concurrency, clinical accuracy and large-review performance are not established by this verification. Query restore remains query-specific grouping history rather than arbitrary multi-query workspace revisions. Versioned machine duplicate-pair re-evaluation remains backend follow-up work. Record/audit lists currently fetch every page for client filtering; large reviews will need server-driven pagination in the UI. Duplicate pair buttons use tested API contracts; populated pair interactions were not part of the browser fixture run.
