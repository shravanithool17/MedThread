"""Evaluation utilities for MedThread.

Computes precision, recall, F1 and confusion matrix against explicit gold annotations.
Gold annotations are authored by humans, NOT generated from model predictions.

Metrics are computed on synthetic test data only and do not establish clinical validity.
"""

from __future__ import annotations

import io
import re

import pandas as pd


GOLD_REQUIRED_COLUMNS = {"note_id", "sentence", "entity_normalized", "context"}
CONTEXT_LABEL_ORDER = ("affirmed", "negated", "uncertain", "resolved", "unclear")


def sentence_occurs_in_text(sentence: object, text: object) -> bool:
    """Compare source sentences while tolerating punctuation and whitespace variation."""
    sentence_tokens = re.findall(r"\w+", str(sentence).casefold(), flags=re.UNICODE)
    text_tokens = re.findall(r"\w+", str(text).casefold(), flags=re.UNICODE)
    if not sentence_tokens or len(sentence_tokens) > len(text_tokens):
        return False
    width = len(sentence_tokens)
    return any(
        text_tokens[index:index + width] == sentence_tokens
        for index in range(len(text_tokens) - width + 1)
    )


def load_gold_annotations(path_or_bytes) -> tuple[pd.DataFrame, list[str]]:
    """Load gold annotation CSV. Returns (df, errors)."""
    errors: list[str] = []
    try:
        if isinstance(path_or_bytes, (bytes, bytearray)):
            df = pd.read_csv(io.BytesIO(path_or_bytes), dtype=str)
        elif hasattr(path_or_bytes, "read"):
            df = pd.read_csv(path_or_bytes, dtype=str)
        else:
            df = pd.read_csv(path_or_bytes, dtype=str)
    except Exception as exc:
        return pd.DataFrame(), [f"Failed to read gold annotations: {exc}"]

    missing = GOLD_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        errors.append(f"Gold annotation file missing columns: {sorted(missing)}")
        return pd.DataFrame(), errors

    df = df.fillna("")
    for column in GOLD_REQUIRED_COLUMNS:
        df[column] = df[column].astype(str).str.strip()

    valid_contexts = {"affirmed", "negated", "uncertain", "resolved", "unclear"}
    missing_value_rows = pd.Series(False, index=df.index, dtype=bool)
    for column in sorted(GOLD_REQUIRED_COLUMNS):
        missing_value_rows |= df[column].str.strip().eq("")
    if missing_value_rows.any():
        errors.append(
            f"{int(missing_value_rows.sum())} gold rows have empty required values and were skipped."
        )

    invalid_context_rows = ~df["context"].isin(valid_contexts) & ~missing_value_rows
    if invalid_context_rows.any():
        errors.append(
            f"{int(invalid_context_rows.sum())} gold rows have unknown context labels and were skipped. "
            f"Valid: {sorted(valid_contexts)}. "
            f"Found: {sorted(df.loc[invalid_context_rows, 'context'].unique())}."
        )

    valid_rows = ~missing_value_rows & ~invalid_context_rows
    return df.loc[valid_rows].reset_index(drop=True), errors


def align_predictions_with_gold(
    gold_df: pd.DataFrame,
    pred_mentions: list[dict],
    allow_unique_fallback: bool = True,
) -> pd.DataFrame:
    """
    Align gold annotations with predicted mentions by (note_id, entity_normalized).
    Returns the source sentence alongside note/entity IDs and gold/predicted labels.

    Strategy: match on note_id + entity_normalized + normalized sentence when
    sentence text is available. If exactly one prediction exists for a key,
    it can be used as a fallback for older callers without sentence text.
    Ambiguous unmatched candidates are not arbitrarily selected.
    If a gold entry has no prediction, pred_context = "not_predicted".
    If a prediction has no gold, it is excluded from evaluation (unlabeled).
    """
    def normalize_sentence(sentence: object) -> str:
        return " ".join(re.findall(r"\w+", str(sentence).casefold(), flags=re.UNICODE))

    # Keep candidates so same-entity mentions in different sentences can align
    # independently instead of all inheriting the first prediction's context.
    pred_lookup: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    exact_lookup: dict[tuple[str, str, str], list[tuple[int, dict]]] = {}
    for index, m in enumerate(pred_mentions):
        key = (str(m.get("note_id", "")), str(m.get("entity_normalized", "")))
        candidate = (index, m)
        pred_lookup.setdefault(key, []).append(candidate)
        if m.get("sentence"):
            exact_key = (*key, normalize_sentence(m["sentence"]))
            exact_lookup.setdefault(exact_key, []).append(candidate)

    rows = []
    used_predictions: set[int] = set()
    for _, gold_row in gold_df.iterrows():
        key = (str(gold_row["note_id"]), str(gold_row["entity_normalized"]))
        candidates = [
            candidate
            for candidate in exact_lookup.get(
                (*key, normalize_sentence(gold_row["sentence"])),
                [],
            )
            if candidate[0] not in used_predictions
        ]

        if not candidates:
            unmatched_candidates = [
                candidate for candidate in pred_lookup.get(key, [])
                if candidate[0] not in used_predictions
            ]
            # Preserve compatibility for older callers without sentence text,
            # but avoid arbitrary alignment when several predictions compete.
            if allow_unique_fallback and len(unmatched_candidates) == 1:
                candidates = unmatched_candidates

        if candidates:
            prediction_index, prediction = candidates[0]
            used_predictions.add(prediction_index)
            pred_ctx = str(prediction.get("context", "unclear"))
            sentence = str(prediction.get("sentence") or gold_row["sentence"])
            alignment_status = "matched"
            match_method = (
                "unique_entity_fallback"
                if prediction.get("sentence")
                and normalize_sentence(prediction["sentence"]) != normalize_sentence(gold_row["sentence"])
                else "note_entity_sentence"
            )
        else:
            pred_ctx = "not_predicted"
            sentence = str(gold_row["sentence"])
            has_same_note_entity = bool(pred_lookup.get(key))
            alignment_status = (
                "unscorable_sentence_mismatch" if has_same_note_entity else "missed_extraction"
            )
            match_method = None
            prediction_index = None
        rows.append({
            "note_id": key[0],
            "entity_normalized": key[1],
            "sentence": sentence,
            "gold_context": gold_row["context"],
            "pred_context": pred_ctx,
            "alignment_status": alignment_status,
            "match_method": match_method,
            "prediction_index": prediction_index,
        })

    return pd.DataFrame(rows)


def compute_context_metrics(aligned_df: pd.DataFrame) -> dict:
    """
    Compute precision, recall, F1 per context class and overall.
    Returns a dict with keys: per_class (DataFrame), overall (dict), confusion_matrix.

    Returns partial results on zero-division or edge cases.
    """
    if aligned_df.empty:
        return {"per_class": pd.DataFrame(), "overall": {}, "confusion_matrix": None}

    scored = aligned_df[aligned_df["pred_context"] != "not_predicted"].copy()
    if "alignment_status" in scored:
        scored = scored[scored["alignment_status"] == "matched"]
    if scored.empty:
        return {"per_class": pd.DataFrame(), "overall": {}, "confusion_matrix": None}

    labels = list(CONTEXT_LABEL_ORDER)
    y_true = scored["gold_context"].tolist()
    y_pred = scored["pred_context"].tolist()
    label_indices = {label: index for index, label in enumerate(labels)}
    unknown_labels = (set(y_true) | set(y_pred)) - set(labels)
    if unknown_labels:
        raise ValueError(f"Unknown context labels in evaluation data: {sorted(unknown_labels)}")

    confusion_counts = [[0 for _ in labels] for _ in labels]
    for expected, predicted in zip(y_true, y_pred):
        confusion_counts[label_indices[expected]][label_indices[predicted]] += 1

    support_values = [sum(row) for row in confusion_counts]
    predicted_counts = [
        sum(confusion_counts[row][column] for row in range(len(labels)))
        for column in range(len(labels))
    ]
    precision_values: list[float] = []
    recall_values: list[float] = []
    f1_values: list[float] = []
    for index in range(len(labels)):
        true_positives = confusion_counts[index][index]
        precision_value = (
            true_positives / predicted_counts[index] if predicted_counts[index] else 0.0
        )
        recall_value = (
            true_positives / support_values[index] if support_values[index] else 0.0
        )
        f1_value = (
            2 * precision_value * recall_value / (precision_value + recall_value)
            if precision_value + recall_value
            else 0.0
        )
        precision_values.append(precision_value)
        recall_values.append(recall_value)
        f1_values.append(f1_value)
    support_total = sum(support_values)

    def macro_average(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def weighted_average(values: list[float]) -> float:
        if support_total == 0:
            return 0.0
        return sum(value * count for value, count in zip(values, support_values)) / support_total

    unmatched_gold = aligned_df["pred_context"] == "not_predicted"
    if "alignment_status" in aligned_df:
        unmatched_gold &= aligned_df["alignment_status"] == "missed_extraction"

    # Per-class metrics
    per_class_df = pd.DataFrame([
        {
            "label": label,
            "precision": round(precision_values[index], 3),
            "recall": round(recall_values[index], 3),
            "f1": round(f1_values[index], 3),
            "support": support_values[index],
        }
        for index, label in enumerate(labels)
    ])
    overall = {
        "accuracy": round(
            sum(confusion_counts[index][index] for index in range(len(labels))) / len(scored),
            3,
        ),
        "macro_precision": round(macro_average(precision_values), 3),
        "macro_recall": round(macro_average(recall_values), 3),
        "macro_f1": round(macro_average(f1_values), 3),
        "weighted_precision": round(weighted_average(precision_values), 3),
        "weighted_recall": round(weighted_average(recall_values), 3),
        "weighted_f1": round(weighted_average(f1_values), 3),
        "n_samples": int(len(scored)),
        "n_unmatched_gold_extractions": int(unmatched_gold.sum()),
    }

    # Confusion matrix
    cm_df = pd.DataFrame(confusion_counts, index=labels, columns=labels)

    return {
        "per_class": per_class_df,
        "overall": overall,
        "confusion_matrix": cm_df,
    }


def find_errors(aligned_df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Return matched context errors and extractive misses; omit unscorable rows."""
    if aligned_df.empty:
        return pd.DataFrame()
    if "alignment_status" in aligned_df:
        scorable = aligned_df[
            aligned_df["alignment_status"].isin({"matched", "missed_extraction"})
        ]
    else:
        scorable = aligned_df
    errors = scorable[scorable["gold_context"] != scorable["pred_context"]].copy()
    errors["error_type"] = errors.apply(
        lambda r: f"gold={r['gold_context']} / pred={r['pred_context']}", axis=1
    )
    errors["error_category"] = errors["pred_context"].map(
        lambda predicted: "missed_extraction" if predicted == "not_predicted" else "context_confusion"
    )
    errors["false_positive_label"] = errors.apply(
        lambda row: (
            row["pred_context"]
            if row["pred_context"] not in {"not_predicted", row["gold_context"]}
            else None
        ),
        axis=1,
    )
    errors["false_negative_label"] = errors["gold_context"]
    return errors.head(n).reset_index(drop=True)


def compute_entity_coverage_metrics(aligned_df: pd.DataFrame) -> dict:
    """Report annotated-example recall; precision/F1 require exhaustive span labels."""
    if aligned_df.empty:
        return {
            "precision": None,
            "recall": None,
            "f1": None,
            "n_annotated_examples": 0,
            "n_matched_examples": 0,
            "n_missed_extractions": 0,
            "n_unscorable_examples": 0,
            "matching_method": "note_id + canonical entity + punctuation-insensitive sentence tokens",
            "limitation": "No metrics: there are no active source-aligned gold examples.",
        }
    status = aligned_df.get("alignment_status", pd.Series("matched", index=aligned_df.index))
    eligible = aligned_df[status.isin({"matched", "missed_extraction"})]
    matched_count = int((eligible["alignment_status"] == "matched").sum()) if "alignment_status" in eligible else int((eligible["pred_context"] != "not_predicted").sum())
    missed_count = int((eligible["alignment_status"] == "missed_extraction").sum()) if "alignment_status" in eligible else int((eligible["pred_context"] == "not_predicted").sum())
    unscorable_count = int((status == "unscorable_sentence_mismatch").sum())
    denominator = matched_count + missed_count
    return {
        "precision": None,
        "recall": round(matched_count / denominator, 3) if denominator else None,
        "f1": None,
        "n_annotated_examples": int(len(aligned_df)),
        "n_matched_examples": matched_count,
        "n_missed_extractions": missed_count,
        "n_unscorable_examples": unscorable_count,
        "matching_method": "note_id + canonical entity + punctuation-insensitive sentence tokens",
        "limitation": (
            "Precision and F1 are unavailable because the annotation set is not exhaustive "
            "and does not annotate all predicted spans. Recall covers only eligible annotated examples."
        ),
    }


def summarize_unmatched_predictions(
    gold_df: pd.DataFrame,
    pred_mentions: list[dict],
    aligned_df: pd.DataFrame,
    limit: int = 50,
) -> dict:
    """Audit predictions without an exact gold match without mislabeling them FP."""
    matched_indices = {
        int(index)
        for index in aligned_df.get("prediction_index", pd.Series(dtype="object")).dropna()
    }
    gold_keys = {
        (str(row["note_id"]), str(row["entity_normalized"]))
        for _, row in gold_df.iterrows()
    }
    examples = []
    counts = {"no_gold_for_note_entity": 0, "sentence_alignment_mismatch": 0}
    for index, prediction in enumerate(pred_mentions):
        if index in matched_indices:
            continue
        key = (
            str(prediction.get("note_id", "")),
            str(prediction.get("entity_normalized", "")),
        )
        reason = (
            "sentence_alignment_mismatch"
            if key in gold_keys
            else "no_gold_for_note_entity"
        )
        counts[reason] += 1
        if len(examples) < limit:
            examples.append({
                "note_id": key[0],
                "entity_normalized": key[1],
                "reason": reason,
            })
    return {
        "total": sum(counts.values()),
        "counts_by_reason": counts,
        "examples": examples,
        "classification": "unscorable, not false positive; annotation coverage is not exhaustive",
    }
