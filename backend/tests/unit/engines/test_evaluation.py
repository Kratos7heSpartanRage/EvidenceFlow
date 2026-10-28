"""Known-answer checks prevent attractive but incorrect benchmark numbers."""

import pytest

from app.engines.evaluation import (
    classification,
    contiguous_spans,
    latency_summary,
    prf,
    screening_metrics,
    set_prf,
    token_offsets,
    tokens_overlapping_spans,
)


def test_precision_recall_and_f1_use_counts_not_accuracy():
    row = prf(2, 1, 2)
    assert row["precision"] == pytest.approx(2 / 3)
    assert row["recall"] == 0.5
    assert row["f1"] == pytest.approx(4 / 7)
    assert row["gold_support"] == 4 and row["predicted_positive"] == 3


def test_undefined_scores_have_zero_and_explicit_denominators():
    row = prf(0, 0, 5)
    assert row["precision"] == row["recall"] == row["f1"] == 0
    assert row["predicted_positive"] == 0 and row["gold_support"] == 5
    with pytest.raises(ValueError):
        prf(-1, 0, 0)


def test_macro_f1_is_average_of_class_f1_for_imbalanced_reference():
    row = classification(("n", "n", "n", "p"), ["n", "n", "n", "n"], ["n", "p"])
    assert row["accuracy"] == 0.75
    assert row["macro_f1"] == pytest.approx((6 / 7) / 2)
    assert row["per_class"]["p"]["f1"] == 0


def test_maybe_is_not_a_gold_class_or_an_automatic_true_positive():
    row = screening_metrics([1, 1, 0, 0], ["include", "maybe", "exclude", "maybe"])
    assert row["per_class"]["included"]["recall"] == 0.5
    assert row["maybe_rate"] == 0.5
    assert row["eligible_retention_if_maybe_stays_for_review"] == 1
    assert row["fraction_records_retained_if_only_exclude_removed"] == 0.75
    assert row["eligible_records_suggested_exclude"] == 0
    assert row["three_way_confusion"]["excluded"]["maybe"] == 1


def test_eligible_exclusions_are_counted_and_empty_positive_support_is_explicit():
    assert (
        screening_metrics([1, 0], ["exclude", "exclude"])["eligible_records_suggested_exclude"] == 1
    )
    assert screening_metrics([0], ["maybe"])["eligible_retention_if_maybe_stays_for_review"] is None


def test_incompatible_inputs_fail_instead_of_silent_zip_truncation():
    for gold, predictions in [([], []), ([1, 0], ["maybe"]), ([2], ["maybe"]), ([1], ["invalid"])]:
        with pytest.raises(ValueError):
            screening_metrics(gold, predictions)
    with pytest.raises(ValueError):
        classification(["unknown"], ["p"], ["p"])


def test_exact_spans_penalize_wrong_boundaries_even_with_token_overlap():
    gold, guess = contiguous_spans([0, 1, 1, 0]), contiguous_spans([0, 1, 1, 1])
    assert gold == {(1, 3)} and guess == {(1, 4)}
    assert set_prf(gold, guess)["f1"] == 0
    assert set_prf({1, 2}, {1, 2, 3})["f1"] == 0.8


def test_spans_and_tokens_preserve_unicode_and_repeated_token_positions():
    text, offsets = token_offsets(["😀", "β-therapy", "placebo", "placebo"])
    assert text[offsets[1][0] : offsets[1][1]] == "β-therapy"
    assert tokens_overlapping_spans(offsets, [offsets[3]]) == {3}
    assert tokens_overlapping_spans(offsets, [offsets[2], offsets[3]]) == {2, 3}
    with pytest.raises(ValueError):
        tokens_overlapping_spans(offsets, [(3, 3)])
    with pytest.raises(ValueError):
        token_offsets(["valid", ""])


def test_duplicate_predictions_do_not_count_the_same_token_twice():
    _, offsets = token_offsets(["a", "b"])
    assert tokens_overlapping_spans(offsets, [(0, 3), (0, 3)]) == {0, 1}
    assert contiguous_spans([1, 1, 0, 1]) == {(0, 2), (3, 4)}


def test_latency_percentile_uses_documented_nearest_rank():
    row = latency_summary([0.001, 0.003, 0.002, 0.004])
    assert row["median_ms"] == 2.5 and row["p95_ms_nearest_rank"] == 4
    with pytest.raises(ValueError):
        latency_summary([])
