# EvidenceFlow

**An auditable workspace for systematic literature reviews.** EvidenceFlow is designed to help researchers move from a structured review question to a searchable, deduplicated, screened, and exportable evidence set while keeping reviewer decisions visible and traceable.

> **Project status:** Backend engine baseline implemented. Member C's deduplication, screening, PICO engines, repository interfaces, and offline tests are available. The application UI, HTTP API, source adapters, and database integration are still pending. The original planning blueprint is held locally as `Start.txt` and is not included in this repository.

## Member C implementation

See the [integration guide](docs/MEMBER_C.md) for contracts, persistence requirements, and handoff steps, and the [methods contribution](docs/MEMBER_C_REPORT.md) for report material.

With Python 3.11 or newer, run the offline checks and synthetic demo from the repository root:

```powershell
cd backend
python -m unittest discover -s tests -v
python -m examples.member_c_demo
```

These modules use the Python standard library; no API key or dependency installation is required. The services accept repository interfaces, with a test double used for verification. A real database adapter and end-to-end application still need to be connected.

## Why EvidenceFlow

Systematic review searches change as researchers refine their questions. Re-running a search can introduce new records, surface duplicates, or bring back a paper that was previously excluded. EvidenceFlow is planned around that iteration: query versions retain their provenance, reviewer decisions remain separate from machine suggestions, and changes to the evidence set can be inspected before conflicts are resolved.

**Project goal:** make search evolution auditable without losing human work.

## Planned workflow

1. **Define the review** — record the question in PICO form (Population, Intervention, Comparator, Outcome) and configure inclusion and exclusion criteria with reasons.
2. **Build and preview searches** — create versioned Boolean queries, set date ranges, choose a literature source, and inspect a result preview.
3. **Approve and import records** — fetch bibliographic metadata and available abstracts from supported sources, retaining the query version that found each record.
4. **Review duplicates** — identify likely duplicates using identifiers and bibliographic fields; confirm or reject uncertain pairs as a reviewer.
5. **Screen studies** — record Include, Exclude, or Maybe decisions. Exclusions require a reason, and machine suggestions remain distinguishable from reviewer decisions.
6. **Review PICO annotations** — inspect and correct suggested Population, Intervention, Comparator, and Outcome spans.
7. **Inspect changes and export** — compare query versions, review decision conflicts, inspect the audit history, and export included studies to CSV.

## Planned capabilities

- Search version history and provenance links from records to the queries that found them.
- Incremental imports with idempotent record storage.
- Duplicate suggestions based on DOI/PMID and, when identifiers are missing, documented bibliographic matching rules.
- Human confirmation or rejection of uncertain duplicate pairs.
- Three-way screening decisions with an explanation for exclusions.
- PICO span suggestions that reviewers can correct.
- Query-version diffs, decision preservation, conflict review, and exact workspace restoration from saved snapshots.
- Append-only audit history for reviewer actions and pipeline runs.
- CSV export of included representative studies.

These are planned capabilities from the project blueprint, not claims about the current codebase.

## Data sources

The blueprint proposes adapters for:

- [Europe PMC REST API](https://europepmc.org/RestfulWebService)
- [NCBI PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/)

Source integration, rate limiting, attribution, and any required notices must be implemented and verified before use. PubMed-derived data may have usage and copyright considerations; consult the applicable source guidance and display the required NCBI disclaimer in the product when PubMed content is shown.

## Planned architecture

The proposed stack is:

- **Frontend:** React, TypeScript, Vite, and Tailwind CSS
- **Backend:** Python 3.11, FastAPI, Pydantic, and SQLAlchemy
- **Storage:** SQLite for local development, with PostgreSQL as a possible deployment option
- **Processing:** separate, deterministic modules for deduplication, screening suggestions, and PICO extraction

The intended service layout keeps the UI, API, source adapters, processing logic, and persistence distinct. Processing suggestions and reviewer decisions are stored separately so reruns can refresh machine output without silently replacing human work.

## Repository status and roadmap

The project blueprint describes these milestones:

- Establish the review question, data model, API contracts, and end-to-end import flow.
- Implement the core workflow: source search, import, deduplication, screening, PICO review, and CSV export.
- Add query history, change comparison, decision reconciliation, and restoration from saved snapshots.
- Document installation, verify a clean setup, and prepare a reproducible demo.

The actual repository contents and completed milestones should be reflected here as implementation progresses.

## Running the project

The engine checks and offline demonstration can be run using the commands above. There is no application server or UI yet. The blueprint proposes a development setup based on `make` targets, but those targets have not been created. Application prerequisites, configuration, database setup, and startup commands will be documented as those components are implemented.

## Design principles

- **People make review decisions.** Automation provides suggestions and evidence; reviewers can override them.
- **Keep provenance.** Preserve which source and query version produced each record.
- **Preserve history.** Prefer hiding records and superseding decisions over destructive edits.
- **Make changes explainable.** Show why records were matched or suggested for exclusion, and surface disagreements for review.
- **Treat reruns as repeatable.** Reprocessing the same inputs should not create duplicate records or erase reviewer work.
- **Be conservative when uncertain.** Unclear screening evidence should be sent to human review.

## Limitations

The blueprint calls for a transparent, rules-based baseline. Such matching and screening methods can miss relevant studies or produce false positives; they are not a substitute for expert review. Abstracts and metadata may be incomplete, and the behavior of external APIs can change. EvidenceFlow is a research workflow aid, not an autonomous source of scientific conclusions.

## Contributing

Read the [Member C integration guide](docs/MEMBER_C.md) before changing engine contracts or connecting persistence. Each engine returns machine suggestions; reviewer decisions and annotations must remain separate. Keep tests offline and preserve versioned input keys when adding database adapters.

## License

No license has been selected yet. Until one is added, all rights remain with the copyright holder; do not assume the project is available for reuse or redistribution.
