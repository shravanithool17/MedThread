"""Text mining utilities: aggregate statistics for the dashboard.

All counts describe the loaded corpus only.
They do not represent disease prevalence, patient risk, or population statistics.
"""

from __future__ import annotations

from datetime import date
from itertools import combinations
from typing import Any, Optional

import pandas as pd

from .schemas import Note


def mentions_to_dataframe(annotated_mentions: list[dict]) -> pd.DataFrame:
    """Convert list of annotated mention dicts to a DataFrame."""
    if not annotated_mentions:
        return pd.DataFrame(columns=[
            "patient_id", "note_id", "visit_date", "sentence_index",
            "sentence", "entity", "entity_normalized", "context",
            "time_expression", "normalized_event_date",
            "extraction_method", "reason", "char_start", "char_end",
        ])
    return pd.DataFrame(annotated_mentions)


def comparison_results_to_dataframe(results: list) -> pd.DataFrame:
    """Convert ComparisonResult objects to a DataFrame."""
    rows = []
    for r in results:
        rows.append({
            "patient_id": r.patient_id,
            "entity": r.entity,
            "status": r.status,
            "evidence_note_ids": "; ".join(r.evidence_note_ids),
            "evidence_sentences": " | ".join(r.evidence_sentences[:2]),  # truncate for display
            "explanation": r.explanation,
            "rule_trace": r.rule_trace,
            "review_state": r.review_state,
        })
    return pd.DataFrame(rows)


def compute_corpus_stats(
    mentions_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    notes: list[Note] | None = None,
) -> dict:
    """Return summary statistics for the loaded corpus."""
    stats = {
        "n_patients": 0,
        "n_notes": 0,
        "n_mentions": 0,
        "n_review_flags": 0,
        "n_possible_inconsistency": 0,
        "n_unclear": 0,
    }

    if notes is not None:
        stats["n_patients"] = len({note.patient_id for note in notes})
        stats["n_notes"] = len(notes)
    elif not mentions_df.empty:
        stats["n_patients"] = int(mentions_df["patient_id"].nunique())
        stats["n_notes"] = int(mentions_df["note_id"].nunique())

    if not mentions_df.empty:
        stats["n_mentions"] = len(mentions_df)

    if not comparison_df.empty:
        stats["n_possible_inconsistency"] = int(
            (comparison_df["status"] == "possible_inconsistency").sum()
        )
        stats["n_unclear"] = int(
            (comparison_df["status"] == "unclear").sum()
        )
        stats["n_review_flags"] = stats["n_possible_inconsistency"] + stats["n_unclear"]

    return stats


def entity_frequency(mentions_df: pd.DataFrame) -> pd.DataFrame:
    """Return entity frequency counts (corpus only — not disease prevalence)."""
    if mentions_df.empty:
        return pd.DataFrame(columns=["entity_normalized", "count"])
    counts = mentions_df["entity_normalized"].value_counts().reset_index()
    counts.columns = ["entity_normalized", "count"]
    return counts


def context_distribution(mentions_df: pd.DataFrame) -> pd.DataFrame:
    """Return context label distribution."""
    if mentions_df.empty:
        return pd.DataFrame(columns=["context", "count"])
    counts = mentions_df["context"].value_counts().reset_index()
    counts.columns = ["context", "count"]
    return counts


def build_concept_explorer(
    mentions_df: pd.DataFrame,
    patient_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    context: str | None = None,
) -> dict:
    """Aggregate actual mention evidence and note-level concept co-occurrence."""
    empty_result = {"mentions": 0, "concepts": [], "cooccurrences": []}
    if mentions_df.empty:
        return empty_result

    df = mentions_df.copy()
    if patient_id:
        df = df[df["patient_id"] == patient_id]
    if context:
        df = df[df["context"] == context]
    if start_date or end_date:
        visit_dates = pd.to_datetime(df["visit_date"], errors="coerce").dt.date
        if start_date:
            df = df[visit_dates.notna() & (visit_dates >= start_date)]
            visit_dates = visit_dates.loc[df.index]
        if end_date:
            df = df[visit_dates.notna() & (visit_dates <= end_date)]
    df = df[df["entity_normalized"].notna()]
    df = df[df["entity_normalized"].astype(str).str.strip() != ""]
    if df.empty:
        return empty_result

    def evidence_row(row: pd.Series) -> dict:
        return {
            "patient_id": str(row["patient_id"]),
            "note_id": str(row["note_id"]),
            "visit_date": _optional_string(row.get("visit_date")),
            "entity_normalized": str(row["entity_normalized"]),
            "context": str(row["context"]),
            "sentence": str(row["sentence"]),
        }

    concepts: dict[str, dict] = {}
    for entity, group in df.groupby("entity_normalized", sort=True):
        context_counts = group["context"].value_counts().to_dict()
        concepts[str(entity)] = {
            "entity_normalized": str(entity),
            "mention_count": int(len(group)),
            "note_count": int(group[["patient_id", "note_id"]].drop_duplicates().shape[0]),
            "context_counts": {str(key): int(value) for key, value in context_counts.items()},
            "evidence": [evidence_row(row) for _, row in group.iterrows()],
        }

    pair_notes: dict[tuple[str, str], list[dict]] = {}
    for (patient, note_id), group in df.groupby(["patient_id", "note_id"], sort=False):
        entities = sorted(set(group["entity_normalized"].astype(str)))
        for entity_a, entity_b in combinations(entities, 2):
            pair_notes.setdefault((entity_a, entity_b), []).append({
                "patient_id": str(patient),
                "note_id": str(note_id),
                "visit_date": _optional_string(group.iloc[0].get("visit_date")),
                "mentions": [
                    evidence_row(row)
                    for _, row in group[group["entity_normalized"].isin([entity_a, entity_b])].iterrows()
                ],
            })

    cooccurrences = [
        {
            "entity_a": entity_a,
            "entity_b": entity_b,
            "note_count": len(evidence),
            "evidence": evidence,
        }
        for (entity_a, entity_b), evidence in sorted(
            pair_notes.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]
    return {
        "mentions": int(len(df)),
        "concepts": list(concepts.values()),
        "cooccurrences": cooccurrences,
    }


def _optional_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def status_distribution(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """Return comparison status distribution."""
    if comparison_df.empty:
        return pd.DataFrame(columns=["status", "count"])
    counts = comparison_df["status"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    return counts


def build_patient_timeline(
    mentions_df: pd.DataFrame,
    patient_id: Optional[str] = None,
    entity_filter: Optional[str] = None,
    status_filter: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Build a per-patient timeline DataFrame filtered as requested.
    Returns columns: patient_id, visit_date, entity_normalized, context, sentence.
    """
    df = mentions_df.copy()

    if patient_id:
        df = df[df["patient_id"] == patient_id]
    if entity_filter:
        df = df[df["entity_normalized"] == entity_filter]
    if status_filter:
        df = df[df["context"].isin(status_filter)]

    if df.empty:
        return df

    # Sort by patient, then date
    df = df.sort_values(["patient_id", "visit_date", "entity_normalized"])
    return df[[
        "patient_id", "note_id", "visit_date",
        "entity_normalized", "context", "sentence",
        "time_expression", "normalized_event_date",
    ]].reset_index(drop=True)
