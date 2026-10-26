# Member C report contribution: methods and limitations

This is a methods contribution for the team's final report, not a completed
evaluation report. The implementation has offline synthetic tests; relevance,
PICO accuracy, and reviewer time saved have not been measured.

## Simplest approach implemented

The baseline normalizes DOI and PMID, matches exact identifiers, and supplements
them with normalized title, year, and first-author comparisons. Identifier-free
matches are automatic only when all three bibliographic fields agree. Missing
or contradictory evidence goes to human review. Conference-versus-journal
evidence or conflicting valid identifiers prevents an automatic merge. An
optional title-token comparison is available as an uncertain suggestion only.
Groups are connected components, with a saved representative and membership
snapshot per run. A rejected pair that remains transitively connected produces
a conflict with a path showing the connection.

This baseline was chosen for reproducibility, explainable outputs, and low
setup cost. It has not been compared with a learned model or benchmarked for
recall. It was retained as the initial implementation; no claim is made that it
outperforms another method. The current service recomputes pairs for the capped
active set rather than persisting incremental edges, which reduces stale-edge
risks during integration.

Screening reads authoritative metadata before applying configured fallback
rules. Every output is a suggestion. Metadata-based exclusions are labeled
strong, rule-based exclusions weak. A missing abstract yields Maybe. If no
exclusion fires, both population and intervention terms must match before an
Include suggestion is made, and unresolved criteria keep the record at Maybe.
Missing keywords never cause an exclusion.

PICO extraction searches each sentence for explicit cues and review-provided
phrases. It emits original-text spans of at most twelve tokens and records the
rule that produced each span. Missing labels are explicitly unknown. No model
confidence is presented as a probability. Services store machine outputs using
versioned input keys and never mutate reviewer decisions or annotations.

## Available criteria and detection methods

The team must select the review topic and give each active criterion its own
reason. The following are supported detectors, not a mandate to exclude these
study categories in every review.

| Code | Metadata | Fallback | Human review / limitation |
| --- | --- | --- | --- |
| `non_english` | Recognized language field; English in a multilingual field prevents exclusion | Small lexical marker sets for English, French, Spanish, German, Portuguese, Italian | Short, ambiguous, or unsupported text stays Maybe; marker evidence is not a language probability |
| `non_human` | Animals MeSH heading without Humans | Animal/species/in-vitro/cell-line phrases in the abstract, suppressed by human-participant cues | Mixed human/animal work needs inspection; this is a heuristic |
| `case_report` | Case Reports publication type | Case-report phrases or a numbered year-old patient pattern | A positive rule is weak evidence; age wording can occur in other designs |
| `simulation` | No supplied metadata detector | Simulation, in silico, Monte Carlo, modelling study, microsimulation, Markov-model cues | Mentioning a simulation does not establish the entire study design |
| `custom_keyword` | No supplied metadata detector | Reviewer-defined, word-bounded terms | Term presence supports only the configured rule; absence never excludes |

The language fallback requires at least ten distinct normalized tokens, four
distinct markers for the winning language, and a winning share of at least 0.80
of all marker hits by default. Shared markers contribute to multiple languages
and can make the result ambiguous. This is deliberately a limited fallback;
source metadata and reviewer judgment remain preferable. Rules do not fully
interpret negation, multilingual abstracts, or complex study designs.

## Where humans decide

Reviewers choose the PICO question, terms, criteria, reasons, and active toggles;
confirm or reject uncertain duplicate pairs; accept or override suggestions;
give a reason for exclusions; and correct PICO spans. Bulk acceptance, if added
by the UI/API team, must be an explicit audited human action. Merged groups with
conflicting decisions and transitively bypassed pair rejections require the
decision/conflict layer; the engine never resolves them. Exact query-version
restoration belongs to the workspace layer.

An intentional override stays valid in the current evaluation context. Later
input changes can flag it for review without replacing it. Criteria-version and
input fingerprints must be captured with human decisions for that comparison.

## Effort, compute, and reviewer-time discussion

| Addition | Intended benefit | Cost and present evidence |
| --- | --- | --- |
| Exact identifier matching | Surface obvious duplicates before repeated review | Small normalization/index cost; synthetic behavior tested, real precision unmeasured |
| Bibliographic matching and guards | Handle missing identifiers while exposing uncertain reports | More candidates and reviewer inspection; no measured time saving |
| Metadata-first screening | Give the reviewer explicit eligibility evidence | Small per-record checks; source metadata can be missing or incorrect |
| Rule fallback | Suggest a disposition when structured metadata is absent | Additional false positives are possible; no measured accuracy |
| PICO cues and review terms | Give reviewers an editable starting point | Linear scans for each configured cue/term; clinical span quality unmeasured |
| Input-keyed reuse | Avoid recomputing unchanged machine outputs | Storage and schema complexity; repeated offline calls reuse cached screening/PICO batches |

No team effort or compute benchmark has been collected. A prospective time
estimate can be written as `eligible_records × acceptance_fraction × seconds_saved
per_accepted_suggestion − correction_time`. All inputs would be assumptions
until measured in a reviewer exercise; no numerical saving is claimed here.

## Validation and limitations

Offline engine and repository-contract tests exercise missing identifiers and
abstracts, DOI normalization, cross-source PMID matches, conference guards,
human pair overrides, transitive conflicts, each supported criterion, Maybe
defaults, PICO unknown comparators and offsets, stale-input caching, and human
state preservation. These are software behavior checks on synthetic inputs.

Real database and pipeline integration is pending Member A's schema and
repository adapters. Live APIs, UI behavior, labeled screening performance,
PICO span precision/recall, clinical usefulness, concurrent writes, and actual
reviewer time savings remain unmeasured. Title blocking can miss spelling
variants; optional fuzzy mode can add false candidates. Author normalization,
language markers, sentence splitting, negation handling, and cue extraction are
limited. Partial snapshots must be rolled back by the caller's transaction.
