# Europe PMC fixtures

These files are **synthetic**. They follow the structure of Europe PMC search
responses (`format=json`, `resultType=core`) but every identifier, title and
author is invented, so tests never depend on live data.

| File | What it exercises |
|---|---|
| `search_page1.json` | Full record; collective author; HTML and entities in the abstract; uppercase language code; single pubType given as a string; preprint (PPR) with no PMID or abstract |
| `search_page2.json` | Record repeated from page 1; result with no `id` (must be skipped with a warning); non-English record with no `pubYear` (year comes from `firstPublicationDate`) |
| `search_page3_end.json` | Empty page whose `nextCursorMark` equals the previous one (end of results) |
| `empty.json` | Zero hits |

To capture **real** responses for comparison, run `scripts/record_fixtures.py`
on a machine with internet access. Recorded files go to `recorded/` and are not
used by the default test run.
