# EvidenceFlow backend

Status: literature-source adapters only (Member B). The API, database and
processing engines are added by other workstreams.

## Setup and tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest            # offline: unit + local-HTTP integration tests
EVIDENCEFLOW_LIVE=1 python -m pytest tests/live -v   # hits the real Europe PMC API
ruff check . && ruff format --check .
```

Default tests never touch the internet. Live tests are marked `live` and skipped
unless `EVIDENCEFLOW_LIVE=1`.

## Literature-source adapters (`app/adapters/`)

Every adapter takes a `QuerySpec` and returns plain `RecordIn` models
(`app/schemas/contracts.py`). Adapters never touch the database.

| Method | Use |
|---|---|
| `count(spec)` | Hit count only (one cheap request) |
| `preview(spec, n=20)` | Hit count plus the top `n` records, so the researcher can judge a search before approving it |
| `search(spec, cap, known_ids)` | Up to `cap` records in rank order for import; records already stored (`known_ids`) are listed in `ids` but not returned again |

Shared behaviour (`app/adapters/base.py`):
- Standard-library HTTP; respects `HTTPS_PROXY` / `NO_PROXY`
- Per-source rate limit (Europe PMC: 5 requests/s)
- 20 s timeout; up to 3 retries with exponential backoff on timeouts, network
  errors, 429 (honouring `Retry-After`) and 5xx
- Failures raise `SourceError` with `kind` in `timeout`, `rate_limited`,
  `bad_query`, `upstream_error`, `network`, `malformed_response`, so the API layer
  can show a clear message and mark the pipeline step failed
- A failure part-way through paging raises rather than returning a partial set
- A single malformed record is skipped and reported in `warnings`

### Europe PMC (`europe_pmc.py`)

- Date range is applied as `FIRST_PDATE:[from TO to]`; an open end uses
  1800-01-01 or 2999-12-31.
- MeSH synonym expansion is controlled by `QuerySpec.expand_synonyms` (default
  off) and always sent explicitly.
- Cursor paging with up to 1000 records per page.
- `source_record_id` is `"<SRC>:<id>"`, e.g. `MED:31415926`, because Europe PMC
  ids are only unique within a source.
- Europe PMC returns full records in search pages, so incremental import skips
  records already stored but still downloads the pages.
- Titles and abstracts are stripped of HTML tags and entities; language codes are
  lowercased; nothing missing is invented (fields stay `None`).

To record real responses for comparison:
`python scripts/record_fixtures.py "metformin AND placebo" --from 2015-01-01 --to 2025-12-31`
