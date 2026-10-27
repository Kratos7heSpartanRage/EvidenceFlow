# PubMed fixtures

**Synthetic** responses shaped like NCBI E-utilities output. Identifiers, titles
and authors are invented.

| File | What it exercises |
|---|---|
| `esearch_page.json` | ESearch JSON with 4 PMIDs |
| `esearch_empty.json` | Zero hits with `phrasesnotfound` |
| `esearch_error.json` | ESearch `ERROR` returned with HTTP 200 (must become `bad_query`) |
| `efetch.xml` | Structured abstract with labels; inline `<i>`/`<sub>` markup; collective author; DOI in `ArticleIdList` and `ELocationID`; electronic `ArticleDate`; `MedlineDate` ("2019 Jan-Feb"); non-English record with no abstract; an article with an empty title (skipped with a warning); a book record (skipped); PMID 90000004 requested but absent (warning) |
