# Member C: engines and service integration

This repository includes Member C's deterministic baseline from the original planning blueprint. See `INTEGRATION_ANALYSIS.md` for the merged A/B/C status. All
engine and service code uses the Python standard library. No API key, model
download, paid service, or network connection is needed to run its checks.

## Run locally

From the repository root, using Python 3.11 or newer:

```powershell
cd backend
python -m unittest discover -s tests -v
python -m examples.member_c_demo
```

The demo uses explicitly synthetic records. It prints duplicate suggestions,
groups, screening evidence, and PICO spans. It does not import real literature,
start an HTTP server, or write a database. The implementation was checked with
Python 3.13.5; Python 3.11 has not been run in this environment.

## Delivered scope

| Module | Responsibility |
| --- | --- |
| `backend/app/engines/types.py` | Immutable records, criteria, review terms, and output dataclasses |
| `backend/app/engines/normalize.py` | DOI, PMID, title, author, and journal normalization |
| `backend/app/engines/dedup.py` | Pair blocking/scoring, connected components, stable group keys, representatives |
| `backend/app/engines/screening.py` | Metadata-first eligibility suggestions with rule evidence |
| `backend/app/engines/pico.py` | P/I/C/O spans, original-text offsets, explicit unknowns |
| `backend/app/services/deduplication_service.py` | Human pair overrides, machine evaluations, snapshots, transitive rejection conflicts |
| `backend/app/services/screening_service.py` | Suggestion caching and decision staleness checks |
| `backend/app/services/pico_service.py` | Eligible representative processing and machine annotation caching |
| `backend/tests/` | Offline engine and service tests using a test repository |
| `docs/MEMBER_C_REPORT.md` | Methods, criteria, human review, limitations, and cost discussion |

The engines import only standard-library modules and other engine modules. They
do not import application services, ORM models, configuration, or HTTP clients.
All source-record strings and metadata must be mapped into these types by the
caller; source-specific parsing belongs to Member B.

## Contracts

```python
from app.engines import (
    CriterionSpec, PicoTerms, RecordLite, extract_pico, group, score_pairs, screen,
)

record = RecordLite(
    id=1,
    title="A study title",
    abstract="Patients with migraine received compound x.",
    year=2024,
    authors=("Smith J",),
    language="eng",
    mesh=("Humans",),
)
terms = PicoTerms(population=("migraine",), intervention=("compound x",))
criteria = [CriterionSpec(
    id=1,
    code="non_human",
    reason="This review evaluates human treatment.",
)]

pairs = score_pairs([record])
components = group([record.id], [])
suggestion = screen(record, criteria, terms)
spans = extract_pico(record.abstract, terms)
```

`RecordLite.id` is the internal database record ID (UUID strings in the current models), not a source PMID. Positive integer IDs remain supported for examples. Metadata fields
`authors`, `pub_types`, and `mesh` accept sequences of strings. Missing values use
`None` or empty tuples. Publication year must already be an integer or `None`.
`first_author` takes precedence over the first item in `authors`.

Each `CriterionSpec` requires a nonempty, review-specific `reason`. Supported
codes are `non_english`, `non_human`, `case_report`, `simulation`, and
`custom_keyword`. Detectors are `metadata`, `rule`, `metadata_then_rule`, and
`manual_only`. The default is `metadata_then_rule`. Criteria can be switched off
with `is_active=False`. Keyword parameters use `{"terms": ["phrase", ...]}`;
`keywords`, `include_terms`, and `exclude_terms` are also accepted. All keyword
matching is case-insensitive, accent-normalized, and bounded by words.

The `kind` field controls whether a detector match is inclusion or exclusion
evidence. For the supplied study-type codes, the intended use is `exclude`.
An unmatched inclusion criterion returns Maybe rather than exclusion. Unknown
codes, missing required metadata, and `manual_only` criteria require review.

PICO offsets count **Unicode code points** in the exact original abstract;
`end_char` is exclusive: `abstract[start_char:end_char] == span.text`. A JavaScript
UI must account for UTF-16 when supplementary characters occur. For example:

```typescript
const codePoints = Array.from(abstract);
const before = codePoints.slice(0, span.start_char).join("");
const highlighted = codePoints.slice(span.start_char, span.end_char).join("");
const after = codePoints.slice(span.end_char).join("");
```

Unknown annotations have `text`, `start_char`, and `end_char` set to `None`; do
not render them as text spans. Suggested spans include their cue and may overlap.
Render overlapping spans with an interval-aware highlighter or per-label view.

## Persistence handoff for Member A

The database foundations, review/query repositories, and routes are now present. The three engine services still accept typed repository interfaces that need real SQLAlchemy adapters. The engine-service repository implementation currently present is a test double. The `to_engine_record()` mapper connects the persisted record shape to C's input; database duplicate review is now implemented separately in `deduplication_db_service.py`, using the shared pure grouping routine. Screening/PICO repositories, versioned machine evaluation storage, and group screening-decision reconciliation remain pending.

1. Implement the `DeduplicationRepository`, `ScreeningRepository`, and
   `PicoRepository` Protocol methods against a repository scoped to one review.
   Do not mix records from different reviews in a service call.
2. Wrap **each service call in its own pipeline-step transaction**. Repository
   methods must not commit. Roll back the entire step on error; the services do
   not manage transactions or emit audit events.
3. Store machine data append-only. Enforce unique keys atomically in the
   database. An identical repeated write is a no-op; different payloads under
   an immutable key raise. An algorithm change requires a new `ALGO_VERSION`.
4. After import/workspace changes, pass the **complete active record set**,
   current pair decisions (one per pair), and any representative pins to
   `DeduplicationService.run`. Persist the returned evaluation and immutable
   run snapshot using the Protocol methods.
5. Pass returned `pair_override_bypassed` conflicts to A's conflict service.
   Their stable fingerprint and explicit path support idempotent conflict
   storage. Detect Include/Exclude group conflicts and decision inheritance in
   A's decision service. These services never apply human screening decisions.
6. Pass only current group representatives to screening and PICO. The screening
   service reports suggestions and staleness; the caller records flags/audits.
7. Resolve effective status with human decisions taking precedence over machine
   suggestions. Run PICO for Include/Maybe representatives, omitting open
   conflicting groups. Human PICO corrections are selected by the annotation
   layer and must never be superseded by machine output.
8. Snapshot restoration and query provenance remain A/B responsibilities. Saved
   group membership enables restoration; these services do not implement the
   query-version revert endpoint or fetch records.

### Cache keys and schema requirements

- Pair evaluations: unique `input_fingerprint`, incorporating sorted active
  record inputs, algorithm version, and fuzzy option. Each complete evaluation
  defines the current machine edges. Keep older evaluations for history but do
  **not** union their stale edges into a new run.
- Group snapshots: immutable by `run_id`, with membership keys formed from
  SHA-1 of comma-separated sorted member IDs.
- Screening: the complete `SuggestionKey` is `(record_id, criteria_version_id,
  content_hash, algo_version, context_hash)`. `context_hash` includes the PICO
  terms and exact criteria parameters. This extends the blueprint's key because
  changing review terms can change a suggestion without changing the abstract.
- PICO: the complete `PicoKey` is `(record_id, content_hash, algo_version,
  terms_hash)`. Store completion of an entire batch, including unknown rows.
  Changing review terms must not return stale spans.
- Service `content_hash` values use `RecordLite.input_hash`, which fingerprints
  all supplied record fields. Do not substitute a source's hash without mapping
  the complete key consistently.

The proposed schema needs to preserve the context/terms fingerprints, pair
evaluation membership, and PICO batch completion. Add columns/relations or fold
context into a documented composite fingerprint through an adapter; do not
silently discard key components.

When recording a human screening decision, capture its `criteria_version_id`,
the service `content_hash`, and `context_hash` in the decision's evaluation
context. Supply them through `HumanDecision` on subsequent runs. Changed
criteria, content, or review terms can flag a disagreement as stale. An override
of the current suggestion is not automatically stale. If the optional hashes
are missing, same-version content/term change detection is unavailable. A removed
or disabled reason criterion is flagged separately.

### Deduplication behavior

Exact DOI or PMID normally yields an automatic edge. Exact normalized title,
same year, and matching first author yield a score of 0.95. Missing author,
adjacent/missing year, conflicting identifiers, or conference/journal evidence
yield uncertain suggestions. Uncertain pairs never become edges without a human
confirmation. Journal normalization is provided but journal agreement alone
does not establish duplication. Different valid DOIs or PMIDs downgrade an
otherwise exact match to uncertain. Malformed identifiers are treated as absent.

Author normalization supports surname-plus-initials and surname-comma-given-name
formats. Other full-name formats are compared conservatively without guessing a
surname. Title normalization preserves non-Latin letters.

Optional fuzzy mode uses title-token Jaccard similarity >= 0.90, at least three
shared tokens, and equal known years; it always requires review. The score is a
matching heuristic, not a probability. Blocking uses identifiers or the first
30 normalized title characters with adjacent/missing years; fuzzy mode adds
token/year blocks. Large blocks can be quadratic. Keep the planned import cap.

The service currently re-evaluates the full active set, preventing stale edges
after metadata changes. `score_pairs(..., changed_ids=...)` is available for a
future incremental adapter; such an adapter must invalidate old evaluations for
changed records and preserve valid results for untouched records. The service
does not yet implement incremental pair persistence.

Rejected direct edges are removed. Both the pure service and database workflow use
`group_with_rejections()` (dedup-rules-2): human-confirmed edges are considered
first, then automatic edges in stable ID order. An edge that would transitively
bridge a current rejection is held back; the records remain in different groups
and an unresolved conflict is surfaced. The pure service also returns a path in
the proposed graph for inspection. Reviewers may change earlier decisions; the
database workflow uses the latest verdict, preserving the complete history.


Representative preference is a supplied pin, then a nonempty abstract, valid DOI,
PubMed source, and lowest record ID. Multiple pins are resolved by the remaining
deterministic priorities; the UI should normally enforce one pin per group.

## Validation and remaining work

The offline suite covers identifier variants, missing data, cross-source matches,
publication guards, human pair overrides, transitive rejection conflicts,
screening detectors, PICO offsets/unknowns, cache invalidation, and preservation
of human state. See the final execution result for the current test count.

Still required for an end-to-end application: real machine-result repository adapters and
step transactions, background source imports, D's UI, shared persistence schema agreement, full API-level
checks, database concurrency tests, and clinical relevance evaluation on a
labeled dataset. Passing synthetic tests does not establish screening or PICO
accuracy on real literature.
