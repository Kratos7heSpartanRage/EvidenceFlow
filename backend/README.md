# EvidenceFlow backend

Status: literature-source adapters for Europe PMC and PubMed (Member B). The API, database and
processing engines are added by other workstreams.

## Setup and tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest            # offline: unit + local-HTTP integration tests
EVIDENCEFLOW_LIVE=1 NCBI_EMAIL=you@example.org python -m pytest tests/live -v   # real APIs
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

- `QuerySpec.title_abstract_only` scopes the expression with `TITLE_ABS:(...)`, so
  terms must appear in the title or abstract. Without it, Europe PMC also
  searches open-access full text (e.g. 13,790 vs 788 PubMed hits for the same
  query). PubMed ignores the flag because it never searches full text.
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

### PubMed (`pubmed.py`)

- ESearch (JSON) returns PMIDs; EFetch (XML) is called **only for PMIDs not
  already stored**, in batches of 200. This is true incremental fetch.
- Every request sends `tool` and `email`. Configure with environment variables
  (see `.env.example`): `NCBI_EMAIL` (needed), `NCBI_TOOL` (default
  `evidenceflow`), `NCBI_API_KEY` (optional).
- Rate limit: 2.8 requests/s without a key, 9/s with one (NCBI allows 3 and 10).
- Date range uses publication date (`datetype=pdat`, `mindate`/`maxdate`).
- ESearch can only page through the first 10,000 results, so the cap is limited
  to 10,000.
- Parsing: structured abstracts are joined as `LABEL: text`; inline markup such
  as `<i>` or `<sub>` is flattened; year falls back to `MedlineDate`
  ("2019 Jan-Feb"); DOI comes from `ArticleIdList`, else `ELocationID`;
  `source_record_id` is the PMID; book records are skipped with a warning.
- A query PubMed rejects (HTTP 200 with an `ERROR` field) becomes `bad_query`.
- **Any screen showing PubMed content must show NCBI's disclaimer** and link to
  `NCBI_POLICY_URL`.

`get_adapter("europe_pmc" | "pubmed")` returns a configured adapter.
