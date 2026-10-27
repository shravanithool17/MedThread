"""Tests for corpus-level text mining statistics."""

import os
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from medthread.schemas import Note
from medthread.text_mining import build_concept_explorer, compute_corpus_stats


def test_stats_count_notes_without_extracted_mentions():
    mentions = pd.DataFrame([
        {"patient_id": "P1", "note_id": "N1", "entity_normalized": "fever", "context": "affirmed"},
    ])
    notes = [
        Note("P1", "N1", date(2024, 1, 1), "Patient has fever."),
        Note("P2", "N2", date(2024, 1, 2), "No matching lexicon terms."),
    ]

    stats = compute_corpus_stats(mentions, pd.DataFrame(), notes)

    assert stats["n_notes"] == 2
    assert stats["n_patients"] == 2
    assert stats["n_mentions"] == 1


def test_stats_count_loaded_notes_when_no_mentions_were_extracted():
    notes = [
        Note("P1", "N1", date(2024, 1, 1), "No matching lexicon terms."),
    ]

    stats = compute_corpus_stats(pd.DataFrame(), pd.DataFrame(), notes)

    assert stats["n_notes"] == 1
    assert stats["n_patients"] == 1
    assert stats["n_mentions"] == 0


def test_concept_explorer_aggregates_contexts_and_source_evidence():
    mentions = pd.DataFrame([
        {"patient_id": "P1", "note_id": "N1", "visit_date": "2024-01-01",
         "entity_normalized": "cough", "context": "affirmed", "sentence": "Reports cough."},
        {"patient_id": "P1", "note_id": "N1", "visit_date": "2024-01-01",
         "entity_normalized": "fever", "context": "negated", "sentence": "No fever."},
        {"patient_id": "P1", "note_id": "N2", "visit_date": "2024-01-03",
         "entity_normalized": "cough", "context": "uncertain", "sentence": "Possible cough."},
    ])

    result = build_concept_explorer(mentions)

    assert result["mentions"] == 3
    cough = next(concept for concept in result["concepts"] if concept["entity_normalized"] == "cough")
    assert cough["mention_count"] == 2
    assert cough["note_count"] == 2
    assert cough["context_counts"] == {"affirmed": 1, "uncertain": 1}
    assert cough["evidence"][0]["sentence"] == "Reports cough."
    pair = result["cooccurrences"][0]
    assert (pair["entity_a"], pair["entity_b"], pair["note_count"]) == ("cough", "fever", 1)
    assert pair["evidence"][0]["note_id"] == "N1"
    assert {row["sentence"] for row in pair["evidence"][0]["mentions"]} == {
        "Reports cough.", "No fever."
    }


def test_concept_explorer_filters_patient_date_and_context():
    mentions = pd.DataFrame([
        {"patient_id": "P1", "note_id": "N1", "visit_date": "2024-01-01",
         "entity_normalized": "cough", "context": "affirmed", "sentence": "Reports cough."},
        {"patient_id": "P1", "note_id": "N2", "visit_date": "2024-01-03",
         "entity_normalized": "fever", "context": "negated", "sentence": "No fever."},
        {"patient_id": "P2", "note_id": "N3", "visit_date": "2024-01-03",
         "entity_normalized": "cough", "context": "affirmed", "sentence": "Reports cough."},
    ])

    result = build_concept_explorer(
        mentions,
        patient_id="P1",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 4),
        context="negated",
    )

    assert result["mentions"] == 1
    assert [concept["entity_normalized"] for concept in result["concepts"]] == ["fever"]
    assert result["concepts"][0]["evidence"][0]["patient_id"] == "P1"
    assert result["cooccurrences"] == []


def test_concept_explorer_handles_empty_and_no_match_data():
    empty = build_concept_explorer(pd.DataFrame())
    no_match = build_concept_explorer(
        pd.DataFrame([{
            "patient_id": "P1", "note_id": "N1", "visit_date": "2024-01-01",
            "entity_normalized": "cough", "context": "affirmed", "sentence": "Reports cough.",
        }]),
        patient_id="P2",
    )

    assert empty == {"mentions": 0, "concepts": [], "cooccurrences": []}
    assert no_match == empty
