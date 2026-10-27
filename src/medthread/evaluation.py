"""Evaluation utilities for MedThread.

Computes precision, recall, F1 and confusion matrix against explicit gold annotations.
Gold annotations are authored by humans, NOT generated from model predictions.

Metrics are computed on synthetic test data only and do not establish clinical validity.
"""

from __future__ import annotations

import io
import re
from collections import Counter

import pandas as pd

from .config import SYMPTOM_LEXICON

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


def span_inside_source_sentence(sentence: object, text: object, start: int, end: int) -> bool:
    """Return whether an original-text character span falls within an aligned sentence."""
    sentence_tokens = [
        match.group().casefold()
        for match in re.finditer(r"\w+", str(sentence), flags=re.UNICODE)
    ]
    source_tokens = list(re.finditer(r"\w+", str(text), flags=re.UNICODE))
    if not sentence_tokens or not 0 <= start < end <= len(str(text)):
        return False
    source_words = [match.group().casefold() for match in source_tokens]
    width = len(sentence_tokens)
    for index in range(len(source_words) - width + 1):
        if source_words[index:index + width] != sentence_tokens:
            continue
        sentence_start = source_tokens[index].start()
        sentence_end = source_tokens[index + width - 1].end()
        if sentence_start <= start and end <= sentence_end:
            return True
    return False


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

    invalid_entity_rows = (
        ~df["entity_normalized"].isin(SYMPTOM_LEXICON)
        & ~missing_value_rows
    )
    if invalid_entity_rows.any():
        errors.append(
            f"{int(invalid_entity_rows.sum())} gold rows use unknown canonical concepts "
            f"and were skipped. Valid: {sorted(SYMPTOM_LEXICON)}."
        )

    entity_not_in_sentence = pd.Series(False, index=df.index, dtype=bool)
    for row_index, row in df.loc[
        ~missing_value_rows & ~invalid_entity_rows
    ].iterrows():
        aliases = SYMPTOM_LEXICON[row["entity_normalized"]]
        entity_not_in_sentence.loc[row_index] = not any(
            re.search(
                rf"(?<!\w){re.escape(alias)}(?!\w)",
                row["sentence"],
                flags=re.IGNORECASE,
            )
            for alias in aliases
        )
    if entity_not_in_sentence.any():
        errors.append(
            f"{int(entity_not_in_sentence.sum())} gold rows do not contain a source "
            "surface form for the canonical concept and were skipped."
        )

    valid_df = df.loc[
        ~missing_value_rows
        & ~invalid_context_rows
        & ~invalid_entity_rows
        & ~entity_not_in_sentence
    ].copy()
    if valid_df.empty:
        return valid_df.reset_index(drop=True), errors

    valid_df["_sentence_key"] = valid_df["sentence"].map(
        lambda value: " ".join(
            re.findall(r"\w+", value.casefold(), flags=re.UNICODE)
        )
    )
    judgment_keys = ["note_id", "entity_normalized", "_sentence_key"]
    if {"entity_start", "entity_end"} <= set(valid_df.columns):
        judgment_keys.extend(["entity_start", "entity_end"])
    duplicate_groups = valid_df.groupby(judgment_keys, sort=False, dropna=False)
    duplicate_group_keys = [
        key for key, group in duplicate_groups
        if len(group) > 1
    ]
    if duplicate_group_keys:
        conflicting_keys = {
            key for key, group in duplicate_groups
            if len(group["context"].unique()) > 1
        }
        conflicting_mask = valid_df.set_index(judgment_keys).index.isin(conflicting_keys)
        if conflicting_mask.any():
            errors.append(
                f"{int(conflicting_mask.sum())} gold rows in conflicting duplicate "
                "judgments were skipped."
            )
        valid_df = valid_df.loc[~conflicting_mask].copy()

        same_label_duplicates = valid_df.duplicated(judgment_keys, keep="first")
        if same_label_duplicates.any():
            errors.append(
                f"{int(same_label_duplicates.sum())} repeated gold rows with the same "
                "label were deduplicated."
            )
            valid_df = valid_df.loc[~same_label_duplicates].copy()

    valid_df = valid_df.drop(columns=["_sentence_key"])
    return valid_df.reset_index(drop=True), errors


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

        has_gold_span = (
            "entity_start" in gold_row
            and "entity_end" in gold_row
            and str(gold_row["entity_start"]).strip() != ""
            and str(gold_row["entity_end"]).strip() != ""
        )
        if has_gold_span:
            try:
                gold_start = int(gold_row["entity_start"])
                gold_end = int(gold_row["entity_end"])
            except (TypeError, ValueError):
                gold_start = gold_end = -1
            candidates = [
                candidate for candidate in candidates
                if candidate[1].get("char_start") == gold_start
                and candidate[1].get("char_end") == gold_end
            ]

        if not candidates and not has_gold_span:
            unmatched_candidates = [
                candidate for candidate in pred_lookup.get(key, [])
                if candidate[0] not in used_predictions
            ]
            # Preserve compatibility for older callers without sentence text,
            # but avoid arbitrary alignment when several predictions compete.
            if allow_unique_fallback and len(unmatched_candidates) == 1:
                candidates = unmatched_candidates

        if len(candidates) == 1:
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
                "unscorable_ambiguous_prediction"
                if len(candidates) > 1
                else "unscorable_sentence_mismatch"
                if has_same_note_entity
                else "missed_extraction"
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
    unscorable_count = int(status.astype(str).str.startswith("unscorable_").sum())
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


def compute_exact_span_metrics(
    gold_annotations: pd.DataFrame,
    predicted_mentions: list[dict],
    source_notes: dict[str, str],
    exhaustive_note_ids: list[str],
) -> dict:
    """Score exact entity spans only inside an explicitly exhaustive note scope."""
    unavailable = {
        "available": False,
        "precision": None,
        "recall": None,
        "f1": None,
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "n_gold_spans": 0,
        "n_predicted_spans": 0,
        "scope_note_count": len(exhaustive_note_ids),
        "invalid_gold_spans": [],
        "warnings": [],
    }
    if not exhaustive_note_ids:
        unavailable["warnings"] = [
            "No note IDs are declared as exhaustively entity-annotated."
        ]
        return unavailable
    missing_notes = sorted(set(exhaustive_note_ids) - set(source_notes))
    if missing_notes:
        unavailable["warnings"] = [
            f"Exhaustive scope notes are missing from the active dataset: {missing_notes}."
        ]
        return unavailable
    required = {"note_id", "entity_normalized", "entity_start", "entity_end"}
    if not required.issubset(gold_annotations.columns):
        unavailable["warnings"] = [
            "Gold annotations do not contain exact entity_start/entity_end offsets."
        ]
        return unavailable

    scope = set(exhaustive_note_ids)
    gold_counts: Counter[tuple[str, int, int, str]] = Counter()
    invalid_rows: list[dict[str, Any]] = []
    seen_span_entities: dict[tuple[str, int, int], str] = {}
    warnings: list[str] = []
    for row_index, row in gold_annotations.iterrows():
        note_id = str(row.get("note_id", ""))
        if note_id not in scope:
            continue
        canonical = str(row.get("entity_normalized", ""))
        text = source_notes[note_id]
        try:
            start_value, end_value = row["entity_start"], row["entity_end"]
            if isinstance(start_value, bool) or isinstance(end_value, bool):
                raise ValueError
            start, end = int(start_value), int(end_value)
            if str(start_value).strip() != str(start) or str(end_value).strip() != str(end):
                raise ValueError
        except (TypeError, ValueError):
            invalid_rows.append({"row": int(row_index) + 1, "reason": "invalid_integer_offsets"})
            continue

        if canonical not in SYMPTOM_LEXICON:
            invalid_rows.append({"row": int(row_index) + 1, "reason": "unknown_canonical_concept"})
            continue
        if not 0 <= start < end <= len(text):
            invalid_rows.append({"row": int(row_index) + 1, "reason": "span_out_of_bounds"})
            continue
        surface = text[start:end]
        if surface.casefold() not in {
            alias.casefold() for alias in SYMPTOM_LEXICON[canonical]
        }:
            invalid_rows.append({"row": int(row_index) + 1, "reason": "span_surface_concept_mismatch"})
            continue
        sentence = row.get("sentence")
        if sentence and not span_inside_source_sentence(sentence, text, start, end):
            invalid_rows.append({"row": int(row_index) + 1, "reason": "span_outside_annotated_sentence"})
            continue

        span_key = (note_id, start, end)
        prior_entity = seen_span_entities.get(span_key)
        if prior_entity is not None and prior_entity != canonical:
            invalid_rows.append({"row": int(row_index) + 1, "reason": "conflicting_duplicate_span"})
            continue
        if prior_entity == canonical:
            warnings.append(f"Duplicate gold span on note {note_id} at [{start}, {end}) was deduplicated.")
            continue
        seen_span_entities[span_key] = canonical
        gold_counts[(note_id, start, end, canonical)] += 1

    if invalid_rows:
        unavailable["invalid_gold_spans"] = invalid_rows
        unavailable["warnings"] = [
            "Exact-span metrics are unavailable because one or more gold spans failed validation."
        ]
        return unavailable

    predicted_counts: Counter[tuple[str, int, int, str]] = Counter()
    invalid_prediction_count = 0
    for mention in predicted_mentions:
        note_id = str(mention.get("note_id", ""))
        if note_id not in scope:
            continue
        start, end = mention.get("char_start"), mention.get("char_end")
        canonical = str(mention.get("entity_normalized", ""))
        text = source_notes[note_id]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start < end <= len(text)
            or canonical not in SYMPTOM_LEXICON
        ):
            invalid_prediction_count += 1
            continue
        predicted_counts[(note_id, start, end, canonical)] += 1

    true_positives = sum(
        min(count, gold_counts.get(key, 0))
        for key, count in predicted_counts.items()
    )
    false_positives = (
        sum(predicted_counts.values())
        - true_positives
        + invalid_prediction_count
    )
    false_negatives = sum(gold_counts.values()) - true_positives
    n_gold = sum(gold_counts.values())
    n_predicted = sum(predicted_counts.values()) + invalid_prediction_count
    precision = true_positives / n_predicted if n_predicted else None
    recall = true_positives / n_gold if n_gold else None
    f1_denominator = 2 * true_positives + false_positives + false_negatives
    f1 = 2 * true_positives / f1_denominator if f1_denominator else None
    return {
        "available": True,
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "n_gold_spans": n_gold,
        "n_predicted_spans": n_predicted,
        "scope_note_count": len(exhaustive_note_ids),
        "invalid_gold_spans": [],
        "warnings": warnings,
        "matching_method": "exact note ID + zero-based half-open code-point span + canonical concept",
        "coverage": "Only predictions within declared exhaustively annotated notes are scored.",
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
    ambiguous_keys = {
        (str(row["note_id"]), str(row["entity_normalized"]))
        for _, row in aligned_df.iterrows()
        if row.get("alignment_status") == "unscorable_ambiguous_prediction"
    }
    examples = []
    counts = {
        "no_gold_for_note_entity": 0,
        "sentence_alignment_mismatch": 0,
        "ambiguous_repeated_mention_alignment": 0,
    }
    for index, prediction in enumerate(pred_mentions):
        if index in matched_indices:
            continue
        key = (
            str(prediction.get("note_id", "")),
            str(prediction.get("entity_normalized", "")),
        )
        if key not in gold_keys:
            reason = "no_gold_for_note_entity"
        elif key in ambiguous_keys:
            reason = "ambiguous_repeated_mention_alignment"
        else:
            reason = "sentence_alignment_mismatch"
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
