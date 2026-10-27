"""Tests for evaluation metrics computation.

Test 15: metrics computed correctly for a known tiny test fixture.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import pandas as pd
from medthread.evaluation import (
    align_predictions_with_gold,
    compute_context_metrics,
    compute_entity_coverage_metrics,
    find_errors,
    load_gold_annotations,
)


def _make_aligned(gold_labels: list[str], pred_labels: list[str]) -> pd.DataFrame:
    rows = [
        {"note_id": f"N{i}", "entity_normalized": "fever",
         "gold_context": g, "pred_context": p}
        for i, (g, p) in enumerate(zip(gold_labels, pred_labels))
    ]
    return pd.DataFrame(rows)


# Test 15a: perfect predictions → f1 = 1.0
def test_perfect_metrics():
    labels = ["affirmed", "negated", "uncertain", "affirmed", "negated"]
    aligned = _make_aligned(labels, labels)
    result = compute_context_metrics(aligned)
    assert result["overall"]["weighted_f1"] == 1.0


# Test 15b: all wrong → low f1
def test_all_wrong_metrics():
    gold   = ["affirmed", "affirmed", "affirmed"]
    pred   = ["negated",  "negated",  "negated"]
    aligned = _make_aligned(gold, pred)
    result = compute_context_metrics(aligned)
    # affirmed recall should be 0
    per_class = result["per_class"]
    if not per_class.empty:
        affirmed_row = per_class[per_class["label"] == "affirmed"]
        if not affirmed_row.empty:
            assert affirmed_row.iloc[0]["recall"] == 0.0


# Test 15c: zero division handled without crash
def test_zero_division_no_crash():
    aligned = _make_aligned(["affirmed"], ["negated"])
    result = compute_context_metrics(aligned)
    assert "overall" in result


# Test 15d: empty aligned df
def test_empty_aligned():
    result = compute_context_metrics(pd.DataFrame())
    assert result["per_class"].empty
    assert result["overall"] == {}


# Test 15e: confusion matrix is square
def test_confusion_matrix_shape():
    labels = ["affirmed", "negated", "affirmed", "negated"]
    aligned = _make_aligned(labels, labels)
    result = compute_context_metrics(aligned)
    cm = result["confusion_matrix"]
    assert cm is not None
    assert cm.shape[0] == cm.shape[1]


def test_hand_calculated_context_metrics_and_prediction_sensitivity():
    aligned = _make_aligned(
        ["affirmed", "affirmed", "negated"],
        ["affirmed", "negated", "negated"],
    )
    first = compute_context_metrics(aligned)
    aligned.loc[1, "pred_context"] = "affirmed"
    corrected = compute_context_metrics(aligned)

    assert first["overall"]["accuracy"] == pytest.approx(2 / 3, abs=0.001)
    assert first["confusion_matrix"].loc["affirmed", "affirmed"] == 1
    assert first["confusion_matrix"].loc["affirmed", "negated"] == 1
    assert first["confusion_matrix"].loc["negated", "negated"] == 1
    assert first["overall"]["weighted_f1"] < corrected["overall"]["weighted_f1"]
    assert corrected["overall"]["accuracy"] == 1.0


# Test: align_predictions_with_gold works correctly
def test_align_predictions():
    gold_df = pd.DataFrame([
        {"note_id": "N1", "sentence": "s", "entity_normalized": "fever", "context": "affirmed"},
        {"note_id": "N2", "sentence": "s", "entity_normalized": "fever", "context": "negated"},
    ])
    pred_mentions = [
        {"note_id": "N1", "entity_normalized": "fever", "context": "affirmed"},
        {"note_id": "N2", "entity_normalized": "fever", "context": "negated"},
    ]
    aligned = align_predictions_with_gold(gold_df, pred_mentions)
    assert len(aligned) == 2
    assert all(aligned["gold_context"] == aligned["pred_context"])


# Test: missing prediction → not_predicted label
def test_missing_prediction():
    gold_df = pd.DataFrame([
        {"note_id": "N1", "sentence": "s", "entity_normalized": "fever", "context": "affirmed"},
    ])
    pred_mentions = []
    aligned = align_predictions_with_gold(gold_df, pred_mentions)
    assert aligned.iloc[0]["pred_context"] == "not_predicted"


def test_missing_prediction_is_excluded_from_context_confusion_matrix():
    aligned = _make_aligned(["affirmed"], ["not_predicted"])
    result = compute_context_metrics(aligned)
    assert result["overall"] == {}
    errors = find_errors(aligned, n=10)
    assert errors.iloc[0]["error_category"] == "missed_extraction"
    assert errors.iloc[0]["pred_context"] == "not_predicted"


def test_context_metrics_exclude_missing_extractions_and_use_fixed_labels():
    aligned = pd.DataFrame([
        {"note_id": "N1", "entity_normalized": "fever", "sentence": "Has fever.",
         "gold_context": "affirmed", "pred_context": "affirmed", "alignment_status": "matched"},
        {"note_id": "N2", "entity_normalized": "cough", "sentence": "No cough.",
         "gold_context": "negated", "pred_context": "not_predicted", "alignment_status": "missed_extraction"},
    ])

    result = compute_context_metrics(aligned)

    assert result["overall"]["n_samples"] == 1
    assert result["overall"]["accuracy"] == 1.0
    assert result["overall"]["n_unmatched_gold_extractions"] == 1
    assert result["confusion_matrix"].index.tolist() == [
        "affirmed", "negated", "uncertain", "resolved", "unclear",
    ]
    assert result["confusion_matrix"].values.sum() == 1


def test_unscorable_alignment_is_not_counted_as_missed_extraction():
    aligned = pd.DataFrame([
        {"note_id": "N1", "entity_normalized": "fever", "sentence": "Has fever.",
         "gold_context": "affirmed", "pred_context": "affirmed", "alignment_status": "matched"},
        {"note_id": "N2", "entity_normalized": "cough", "sentence": "Cough worsened.",
         "gold_context": "affirmed", "pred_context": "not_predicted",
         "alignment_status": "unscorable_sentence_mismatch"},
    ])

    result = compute_context_metrics(aligned)

    assert result["overall"]["n_samples"] == 1
    assert result["overall"]["n_unmatched_gold_extractions"] == 0


def test_sentence_alignment_tolerates_punctuation_without_unique_fallback():
    gold_df = pd.DataFrame([
        {"note_id": "N1", "sentence": "No fever no cough.", "entity_normalized": "fever", "context": "negated"},
    ])
    pred_mentions = [{
        "note_id": "N1", "sentence": "No fever, no cough.", "entity_normalized": "fever", "context": "negated",
    }]

    aligned = align_predictions_with_gold(gold_df, pred_mentions, allow_unique_fallback=False)

    assert aligned.iloc[0]["alignment_status"] == "matched"
    assert aligned.iloc[0]["match_method"] == "note_entity_sentence"


def test_entity_coverage_does_not_invent_precision_without_exhaustive_labels():
    aligned = pd.DataFrame([
        {"note_id": "N1", "entity_normalized": "fever", "sentence": "No fever.",
         "gold_context": "negated", "pred_context": "negated", "alignment_status": "matched"},
    ])

    metrics = compute_entity_coverage_metrics(aligned)

    assert metrics["precision"] is None
    assert metrics["f1"] is None
    assert metrics["recall"] == 1.0


def test_aligns_repeated_entity_by_sentence():
    gold_df = pd.DataFrame([
        {"note_id": "N1", "sentence": "Dizziness persists.", "entity_normalized": "dizziness", "context": "affirmed"},
        {"note_id": "N1", "sentence": "Possible vertigo.", "entity_normalized": "dizziness", "context": "uncertain"},
    ])
    pred_mentions = [
        {"note_id": "N1", "sentence": "Dizziness persists.", "entity_normalized": "dizziness", "context": "affirmed"},
        {"note_id": "N1", "sentence": "Possible vertigo.", "entity_normalized": "dizziness", "context": "uncertain"},
    ]

    aligned = align_predictions_with_gold(gold_df, pred_mentions)

    assert aligned["gold_context"].tolist() == ["affirmed", "uncertain"]
    assert aligned["pred_context"].tolist() == ["affirmed", "uncertain"]
    assert aligned["sentence"].tolist() == ["Dizziness persists.", "Possible vertigo."]


def test_evaluation_can_disable_ambiguous_sentence_fallback():
    gold_df = pd.DataFrame([
        {"note_id": "N1", "sentence": "Cough worsened.", "entity_normalized": "cough", "context": "affirmed"},
    ])
    pred_mentions = [
        {"note_id": "N1", "sentence": "Cough resolved.", "entity_normalized": "cough", "context": "resolved"},
    ]

    aligned = align_predictions_with_gold(
        gold_df,
        pred_mentions,
        allow_unique_fallback=False,
    )

    assert aligned.iloc[0]["pred_context"] == "not_predicted"


def test_aggregate_metrics_include_precision_recall_and_f1():
    aligned = _make_aligned(["affirmed", "negated"], ["affirmed", "affirmed"])
    result = compute_context_metrics(aligned)
    for metric in (
        "macro_precision", "macro_recall", "macro_f1",
        "weighted_precision", "weighted_recall", "weighted_f1",
    ):
        assert 0.0 <= result["overall"][metric] <= 1.0


def test_invalid_gold_rows_are_reported_and_excluded():
    content = (
        "note_id,sentence,entity_normalized,context\n"
        "N1,Has fever,fever,affirmed\n"
        "N2,Has cough,cough,unexpected\n"
        "N3,,nausea,negated\n"
    )

    gold_df, errors = load_gold_annotations(content.encode())

    assert len(gold_df) == 1
    assert gold_df.iloc[0]["note_id"] == "N1"
    assert any("unknown context labels" in error for error in errors)
    assert any("empty required values" in error for error in errors)


def test_error_analysis_distinguishes_context_confusion_and_missed_extraction():
    aligned = pd.DataFrame([
        {"note_id": "N1", "entity_normalized": "fever", "sentence": "No fever.",
         "gold_context": "negated", "pred_context": "affirmed"},
        {"note_id": "N2", "entity_normalized": "cough", "sentence": "Reports cough.",
         "gold_context": "affirmed", "pred_context": "not_predicted"},
    ])

    errors = find_errors(aligned, n=len(aligned))
    confusion = errors.iloc[0]
    missed = errors.iloc[1]

    assert confusion["error_category"] == "context_confusion"
    assert confusion["false_positive_label"] == "affirmed"
    assert confusion["false_negative_label"] == "negated"
    assert confusion["sentence"] == "No fever."
    assert missed["error_category"] == "missed_extraction"
    assert pd.isna(missed["false_positive_label"])
    assert missed["false_negative_label"] == "affirmed"
    assert missed["sentence"] == "Reports cough."
