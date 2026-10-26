"""Cue-based PICO span suggestions with exact original-text offsets."""

from __future__ import annotations

import re

from .types import PicoTerms, SpanSuggestion

ALGO_VERSION = "pico-cues-1"
_CUES = {
    "P": (
        r"patients? with", r"adults? with", r"children aged", r"\d+ participants?",
        r"women who", r"subjects? with",
    ),
    "I": (r"randomi[sz]ed to", r"received", r"treated with", r"administration of"),
    "C": (
        r"versus", r"vs\.?", r"compared (?:with|to)", r"placebo", r"usual care",
        r"standard care", r"control group", r"sham",
    ),
    "O": (
        r"primary outcome", r"secondary outcome", r"measured", r"change in",
        r"incidence of", r"mortality",
    ),
}


def _sentences(text: str) -> list[tuple[int, int]]:
    """A small splitter that keeps common abbreviations and decimal numbers intact."""
    bounds, start = [], 0
    for match in re.finditer(r"[.!?](?:\s+|$)", text):
        punctuation = match.start()
        token = re.search(r"([A-Za-z]+)\.$", text[:punctuation + 1])
        if token and token.group(1).casefold() in {"vs", "dr", "mr", "mrs", "prof", "al", "e", "g", "i"}:
            continue
        if punctuation > 0 and text[punctuation - 1].isdigit():
            following = text[punctuation + 1:match.end() + 1].lstrip()
            if following and following[0].isdigit():
                continue
        bounds.append((start, punctuation + 1))
        start = match.end()
    if start < len(text):
        bounds.append((start, len(text)))
    return bounds


def _term_pattern(term: str) -> str:
    return r"\s+".join(re.escape(part) for part in term.split())


def extract_pico(text: str | None, pico_terms: PicoTerms) -> list[SpanSuggestion]:
    """Return suggested spans and one explicit unknown row per missing label.

    Spans include their cue, stop at a clause/sentence/next cue, and contain at
    most 12 whitespace-delimited tokens. Scores are deliberately not provided.
    """
    text = text or ""
    terms = dict(zip("PICO", (
        pico_terms.population, pico_terms.intervention, pico_terms.comparator, pico_terms.outcome,
    )))
    found: list[SpanSuggestion] = []
    for sentence_start, sentence_end in _sentences(text):
        sentence = text[sentence_start:sentence_end]
        cues: list[tuple[int, int, str, str]] = []
        for label, patterns in _CUES.items():
            for pattern in patterns:
                for match in re.finditer(r"(?<!\w)(?:" + pattern + r")(?!\w)", sentence, re.I):
                    cues.append((match.start(), match.end(), label, f"cue: {match.group()}"))
            for term in terms[label]:
                for match in re.finditer(r"(?<!\w)" + _term_pattern(term) + r"(?!\w)", sentence, re.I):
                    cues.append((match.start(), match.end(), label, f"review term: {term}"))
        # Prefer the first/longest overlapping cue of the same label. Independent
        # labels may legitimately overlap (e.g. a review's intervention is placebo).
        selected: list[tuple[int, int, str, str]] = []
        for cue in sorted(set(cues), key=lambda value: (value[0], -(value[1] - value[0]), value[2], value[3])):
            if not any(cue[2] == other[2] and cue[0] < other[1] and cue[1] > other[0] for other in selected):
                selected.append(cue)
        valid_cues = []
        for cue in selected:
            start, cue_end, label, rule = cue
            prefix, suffix = sentence[:start], sentence[cue_end:]
            if label == "C" and re.search(r"\b(?:no|without|without a|no active)\s*$", prefix, re.I):
                continue
            if label in {"C", "O"} and re.match(
                r"\s+(?:(?:was|were|is|are)\s+)?(?:not (?:reported|specified|measured)|unknown|unavailable)\b",
                suffix, re.I,
            ):
                continue
            valid_cues.append(cue)
        for start, cue_end, label, rule in valid_cues:
            end = len(sentence)
            next_cues = [
                other[0] for other in valid_cues
                if other[2] != label and other[0] >= cue_end and other[0] > start
            ]
            if next_cues:
                end = min(end, min(next_cues))
            boundary = re.search(r";|\n|\band the\b|[.!?](?:\s|$)", sentence[cue_end:end], re.I)
            if boundary:
                end = min(end, cue_end + boundary.start())
            # Trim clause punctuation that immediately precedes another cue.
            while end > start and sentence[end - 1] in " \t\r\n,;:.!?":
                end -= 1
            tokens = list(re.finditer(r"\S+", sentence[start:end]))
            if len(tokens) > 12:
                end = start + tokens[11].end()
            if end <= start:
                continue
            if label in {"P", "I", "O"} and rule.startswith("cue:") and not sentence[cue_end:end].strip():
                continue
            absolute_start, absolute_end = sentence_start + start, sentence_start + end
            if any(
                span.label == label and span.start_char <= absolute_start
                and span.end_char >= absolute_end
                for span in found
            ):
                continue
            found.append(SpanSuggestion(label, text[absolute_start:absolute_end], absolute_start,
                                        absolute_end, "suggested", rule))
    result: list[SpanSuggestion] = []
    for label in "PICO":
        spans = sorted((span for span in found if span.label == label), key=lambda span: span.start_char)
        result.extend(spans or [SpanSuggestion(label, None, None, None, "unknown", "No cue or review term found.")])
    return result
