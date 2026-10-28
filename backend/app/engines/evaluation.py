"""Pure evaluation arithmetic. This module never changes engine predictions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Iterable, Sequence
from math import ceil


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def prf(tp: int, fp: int, fn: int) -> dict[str, int | float]:
    """Zero-division=0, with raw counts retained so undefined precision is visible."""
    if min(tp, fp, fn) < 0:
        raise ValueError("Confusion counts cannot be negative")
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": ratio(tp, tp + fp) or 0.0,
        "recall": ratio(tp, tp + fn) or 0.0,
        "f1": ratio(2 * tp, 2 * tp + fp + fn) or 0.0,
        "gold_support": tp + fn,
        "predicted_positive": tp + fp,
    }


def set_prf(gold: Iterable[Hashable], predicted: Iterable[Hashable]) -> dict:
    gold_set, predicted_set = set(gold), set(predicted)
    return prf(
        len(gold_set & predicted_set), len(predicted_set - gold_set), len(gold_set - predicted_set)
    )


def classification(gold: Sequence[str], predicted: Sequence[str], labels: Sequence[str]) -> dict:
    if len(gold) != len(predicted) or not gold:
        raise ValueError("Gold/predictions must have the same nonzero length")
    if len(set(labels)) != len(labels) or not labels:
        raise ValueError("Labels must be unique and nonempty")
    if not {*gold, *predicted} <= set(labels):
        raise ValueError("Encountered an unknown label")
    matrix = {truth: {guess: 0 for guess in labels} for truth in labels}
    for truth, guess in zip(gold, predicted, strict=True):
        matrix[truth][guess] += 1
    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in labels if other != label)
        fn = sum(matrix[label][other] for other in labels if other != label)
        per_class[label] = prf(tp, fp, fn)
    return {
        "n": len(gold),
        "accuracy": sum(a == b for a, b in zip(gold, predicted, strict=True)) / len(gold),
        "macro_f1": sum(row["f1"] for row in per_class.values()) / len(labels),
        "confusion_matrix_rows_gold_columns_prediction": matrix,
        "per_class": per_class,
        "gold_counts": dict(Counter(gold)),
        "prediction_counts": dict(Counter(predicted)),
    }


def screening_metrics(gold: Sequence[int], predicted: Sequence[str]) -> dict:
    """Binary reference labels with explicit Maybe rather than fabricated Maybe gold."""
    if len(gold) != len(predicted) or not gold:
        raise ValueError("Screening inputs must have the same nonzero length")
    if not set(gold) <= {0, 1} or not set(predicted) <= {"include", "exclude", "maybe"}:
        raise ValueError("Unexpected screening label")
    matrix = {
        "excluded": {p: 0 for p in ("include", "exclude", "maybe")},
        "included": {p: 0 for p in ("include", "exclude", "maybe")},
    }
    for truth, guess in zip(gold, predicted, strict=True):
        matrix["included" if truth else "excluded"][guess] += 1
    positive = matrix["included"]
    negative = matrix["excluded"]
    strict = classification(
        ["included" if x else "excluded" for x in gold],
        ["included" if x == "include" else "excluded" for x in predicted],
        ["excluded", "included"],
    )
    return {
        **strict,
        "strict_policy": "Only Include counts positive; Maybe is non-Include for this score.",
        "three_way_confusion": matrix,
        "maybe_count": predicted.count("maybe"),
        "maybe_rate": predicted.count("maybe") / len(gold),
        "non_maybe_suggestion_rate": 1 - predicted.count("maybe") / len(gold),
        "eligible_records_suggested_exclude": positive["exclude"],
        "eligible_retention_if_maybe_stays_for_review": ratio(
            positive["include"] + positive["maybe"], sum(positive.values())
        ),
        "fraction_records_retained_if_only_exclude_removed": ratio(
            sum(positive.values())
            + sum(negative.values())
            - positive["exclude"]
            - negative["exclude"],
            len(gold),
        ),
    }


def token_offsets(tokens: Sequence[str]) -> tuple[str, list[tuple[int, int]]]:
    """Canonical one-space reconstruction of a corpus's official tokenization."""
    if any(not token for token in tokens):
        raise ValueError("Empty corpus token")
    offsets, cursor = [], 0
    for token in tokens:
        offsets.append((cursor, cursor + len(token)))
        cursor += len(token) + 1
    return " ".join(tokens), offsets


def tokens_overlapping_spans(
    offsets: Sequence[tuple[int, int]], spans: Iterable[tuple[int, int]]
) -> set[int]:
    spans = list(spans)
    if any(start < 0 or end <= start for start, end in spans):
        raise ValueError("Invalid span bounds")
    return {
        index
        for index, (a, b) in enumerate(offsets)
        if any(a < end and b > start for start, end in spans)
    }


def contiguous_spans(labels: Sequence[int]) -> set[tuple[int, int]]:
    """Half-open token-index spans, for binary gold or projected predictions."""
    if not set(labels) <= {0, 1}:
        raise ValueError("Span labels must be binary")
    result, start = set(), None
    for index, value in enumerate([*labels, 0]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            result.add((start, index))
            start = None
    return result


def latency_summary(seconds: Sequence[float]) -> dict:
    if not seconds or min(seconds) < 0:
        raise ValueError("Need nonnegative measurements")
    values = sorted(seconds)
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
    return {
        "calls": len(values),
        "total_seconds": sum(values),
        "median_ms": 1000 * median,
        "p95_ms_nearest_rank": 1000 * values[ceil(0.95 * len(values)) - 1],
    }
