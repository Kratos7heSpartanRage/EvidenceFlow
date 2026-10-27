"""Explainable screening suggestions; no function writes a reviewer decision."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import normalize_title
from .types import CriterionSpec, Evidence, PicoTerms, RecordLite, Suggestion, record_id_key

ALGO_VERSION = "screening-rules-1"

_ENGLISH = {"en", "eng", "english", "en us", "en gb"}
_OTHER_LANGUAGES = {
    "fr",
    "fre",
    "fra",
    "french",
    "de",
    "ger",
    "deu",
    "german",
    "es",
    "spa",
    "spanish",
    "pt",
    "por",
    "portuguese",
    "it",
    "ita",
    "italian",
    "nl",
    "dut",
    "nld",
    "dutch",
    "ru",
    "rus",
    "russian",
    "zh",
    "chi",
    "zho",
    "chinese",
    "ja",
    "jpn",
    "japanese",
    "ko",
    "kor",
    "korean",
    "ar",
    "ara",
    "arabic",
    "hi",
    "hin",
    "hindi",
    "pl",
    "pol",
    "polish",
    "sv",
    "swe",
    "swedish",
    "da",
    "dan",
    "danish",
    "no",
    "nor",
    "norwegian",
    "fi",
    "fin",
    "finnish",
    "tr",
    "tur",
    "turkish",
    "cs",
    "cze",
    "ces",
    "czech",
    "el",
    "gre",
    "ell",
    "greek",
    "he",
    "heb",
    "hebrew",
    "fa",
    "per",
    "fas",
    "persian",
    "uk",
    "ukr",
    "ukrainian",
    "ro",
    "rum",
    "ron",
    "romanian",
    "hu",
    "hun",
    "hungarian",
    "id",
    "ind",
    "indonesian",
    "th",
    "tha",
    "thai",
    "vi",
    "vie",
    "vietnamese",
    "ta",
    "tam",
    "tamil",
    "bn",
    "ben",
    "bengali",
}

# Small deterministic fallback, intentionally limited. These markers are not a
# general language model. Ambiguous/short/unsupported text stays Maybe.
_LANGUAGE_MARKERS = {
    "english": {
        "the",
        "and",
        "with",
        "were",
        "was",
        "patients",
        "participants",
        "this",
        "study",
        "received",
        "from",
    },
    "french": {
        "les",
        "des",
        "une",
        "dans",
        "pour",
        "avec",
        "chez",
        "cette",
        "etude",
        "patients",
        "ont",
        "ete",
    },
    "spanish": {
        "los",
        "las",
        "una",
        "para",
        "con",
        "del",
        "esta",
        "estudio",
        "pacientes",
        "fueron",
        "recibieron",
    },
    "german": {
        "der",
        "die",
        "das",
        "und",
        "mit",
        "eine",
        "einer",
        "wurden",
        "diese",
        "studie",
        "patienten",
    },
    "portuguese": {
        "os",
        "uma",
        "com",
        "dos",
        "das",
        "para",
        "este",
        "estudo",
        "pacientes",
        "foram",
        "receberam",
    },
    "italian": {
        "gli",
        "una",
        "con",
        "dei",
        "delle",
        "per",
        "questo",
        "studio",
        "pazienti",
        "sono",
        "stati",
    },
}

_ANIMALS = re.compile(
    r"\b(?:rats?|mice|mouse|murine|porcine|swine|pigs?|rabbits?|zebrafish|"
    r"rodents?|canine|dogs?|bovine|in vitro|cell lines?|animal models?)\b",
    re.IGNORECASE,
)
_HUMANS = re.compile(
    r"\b(?:patients?|participants?|adults?|children|women|men|volunteers?|"
    r"human subjects?|clinical trial)\b",
    re.IGNORECASE,
)
_CASE = re.compile(
    r"\b(?:case reports?|we report a case|an? \d{1,3}[ -]year[ -]old)\b", re.IGNORECASE
)
_SIMULATION = re.compile(
    r"\b(?:simulations?|in silico|monte carlo|modell?ing study|microsimulations?|markov model)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _Result:
    fired: bool
    uncertain: bool
    evidence: Evidence | None


def phrase_hits(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    normalized = f" {normalize_title(text)} "
    return tuple(
        term
        for term in terms
        if (normalize_title(term) and f" {normalize_title(term)} " in normalized)
    )


def _evidence(
    criterion: CriterionSpec, source: str, field: str, matches: tuple[str, ...], explanation: str
) -> Evidence:
    return Evidence(criterion.code, source, field, matches, explanation, criterion.id)


def _metadata(record: RecordLite, criterion: CriterionSpec) -> _Result | None:
    if criterion.code == "non_english" and record.language:
        languages = {normalize_title(value) for value in re.split(r"[,;/|]", record.language)}
        if languages & _ENGLISH:
            return _Result(False, False, None)
        if languages and languages <= _OTHER_LANGUAGES:
            return _Result(
                True,
                False,
                _evidence(
                    criterion,
                    "metadata",
                    "language",
                    (record.language,),
                    criterion.reason,
                ),
            )
        return None
    if criterion.code == "non_human" and record.mesh:
        headings = {normalize_title(value.split("/", 1)[0]) for value in record.mesh}
        animals = any(re.fullmatch(r"animals?(?: mesh)?", item) for item in headings)
        humans = any(re.fullmatch(r"humans?(?: mesh)?", item) for item in headings)
        if humans:
            return _Result(False, False, None)
        if animals:
            return _Result(
                True,
                False,
                _evidence(
                    criterion,
                    "metadata",
                    "mesh",
                    tuple(record.mesh),
                    criterion.reason,
                ),
            )
    if criterion.code == "case_report" and record.pub_types:
        matches = tuple(
            value
            for value in record.pub_types
            if (normalize_title(value) in {"case report", "case reports"})
        )
        return _Result(
            bool(matches),
            False,
            _evidence(
                criterion,
                "metadata",
                "pub_types",
                matches,
                criterion.reason,
            )
            if matches
            else None,
        )
    return None


def _language_rule(text: str, criterion: CriterionSpec) -> _Result:
    tokens = set(normalize_title(text).split())
    counts = sorted(
        ((len(tokens & markers), language) for language, markers in _LANGUAGE_MARKERS.items()),
        reverse=True,
    )
    best, language = counts[0]
    total = sum(count for count, _ in counts)
    threshold = float(criterion.params.get("language_threshold", 0.80))
    if not 0.5 <= threshold <= 1:
        raise ValueError("language_threshold must be between 0.5 and 1")
    # Marker share is a heuristic threshold, not a calibrated probability.
    reliable = len(tokens) >= 10 and best >= 4 and total > 0 and best / total >= threshold
    if not reliable:
        return _Result(
            False,
            True,
            _evidence(
                criterion,
                "rule",
                "title,abstract",
                (),
                "Language fallback has insufficient or ambiguous marker evidence; review manually.",
            ),
        )
    matches = tuple(sorted(tokens & _LANGUAGE_MARKERS[language]))
    return _Result(
        language != "english",
        False,
        _evidence(
            criterion,
            "rule",
            "title,abstract",
            matches,
            f"Language marker heuristic: {language}; {criterion.reason}",
        ),
    )


def _rule(record: RecordLite, criterion: CriterionSpec) -> _Result:
    text = f"{record.title}\n{record.abstract or ''}"
    if criterion.code == "non_english":
        return _language_rule(text, criterion)
    pattern = {
        "non_human": _ANIMALS,
        "case_report": _CASE,
        "simulation": _SIMULATION,
    }.get(criterion.code)
    if pattern is not None:
        # Rules on study type use the abstract, not a species in the title alone.
        abstract = record.abstract or ""
        matches = tuple(dict.fromkeys(match.group() for match in pattern.finditer(abstract)))
        if criterion.code == "non_human" and _HUMANS.search(abstract):
            return _Result(False, False, None)
        return _Result(
            bool(matches),
            False,
            _evidence(
                criterion,
                "rule",
                "abstract",
                matches,
                criterion.reason,
            )
            if matches
            else None,
        )
    if criterion.code == "custom_keyword":
        values = criterion.params.get("terms", criterion.params.get("keywords", ()))
        if not values:
            values = criterion.params.get(f"{criterion.kind}_terms", ())
        if isinstance(values, str):
            values = (values,)
        matches = phrase_hits(text, tuple(values))
        return _Result(
            bool(matches),
            not bool(values),
            _evidence(
                criterion,
                "rule",
                "title,abstract",
                matches,
                criterion.reason if values else "No keywords configured; review manually.",
            ),
        )
    return _Result(
        False,
        True,
        _evidence(
            criterion,
            "manual",
            "criterion",
            (),
            "No detector for this criterion; review manually.",
        ),
    )


def _evaluate(record: RecordLite, criterion: CriterionSpec) -> _Result:
    if criterion.detector == "manual_only":
        return _Result(
            False,
            True,
            _evidence(
                criterion,
                "manual",
                "criterion",
                (),
                "This criterion requires a reviewer.",
            ),
        )
    if criterion.detector in {"metadata", "metadata_then_rule"}:
        result = _metadata(record, criterion)
        if result is not None:
            return result
        if criterion.detector == "metadata":
            return _Result(
                False,
                True,
                _evidence(
                    criterion,
                    "metadata",
                    "metadata",
                    (),
                    "Required metadata is unavailable; review manually.",
                ),
            )
    return _rule(record, criterion)


def screen(record: RecordLite, criteria: list[CriterionSpec], pico_terms: PicoTerms) -> Suggestion:
    """Suggest Include/Exclude/Maybe; keyword absence never produces Exclude.

    No abstract always yields Maybe. Metadata-backed exclusion wins over weak
    exclusions, and every triggered exclusion remains in the evidence list.
    Unassessable active criteria block an automatic Include suggestion.
    """
    if len({criterion.id for criterion in criteria}) != len(criteria):
        raise ValueError("Criterion ids must be unique")
    if not (record.abstract or "").strip():
        return Suggestion(
            "maybe",
            "none",
            None,
            (
                Evidence(
                    "no_abstract",
                    "rule",
                    "abstract",
                    (),
                    "No abstract; review manually.",
                ),
            ),
            ALGO_VERSION,
        )
    evidence: list[Evidence] = []
    exclusions: list[tuple[CriterionSpec, _Result]] = []
    uncertain, missing_inclusion = False, False
    for criterion in sorted(criteria, key=lambda item: record_id_key(item.id)):
        if not criterion.is_active:
            continue
        result = _evaluate(record, criterion)
        if result.evidence is not None:
            evidence.append(result.evidence)
        uncertain |= result.uncertain
        if criterion.kind == "exclude" and result.fired:
            exclusions.append((criterion, result))
        if criterion.kind == "include" and not result.fired:
            missing_inclusion = True
    if exclusions:
        criterion, result = min(
            exclusions,
            key=lambda item: (
                item[1].evidence.source != "metadata",
                record_id_key(item[0].id),
            ),
        )
        strong = result.evidence.source == "metadata"
        return Suggestion(
            "exclude", "strong" if strong else "weak", criterion.id, tuple(evidence), ALGO_VERSION
        )
    text = f"{record.title}\n{record.abstract}"
    population = phrase_hits(text, pico_terms.population)
    intervention = phrase_hits(text, pico_terms.intervention)
    if population and intervention and not uncertain and not missing_inclusion:
        evidence.append(
            Evidence(
                "pico_terms",
                "rule",
                "title,abstract",
                population + intervention,
                "Both review population and intervention terms matched; reviewer confirmation required.",
            )
        )
        return Suggestion("include", "weak", None, tuple(evidence), ALGO_VERSION)
    evidence.append(
        Evidence(
            "insufficient_evidence",
            "rule",
            "title,abstract",
            (),
            "Insufficient evidence for inclusion; missing terms are not grounds for exclusion.",
        )
    )
    return Suggestion("maybe", "none", None, tuple(evidence), ALGO_VERSION)
