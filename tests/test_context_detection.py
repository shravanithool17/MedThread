"""Tests for context detection — negation, uncertainty, resolution, affirmed.

Covers the 16 required test cases from the specification.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from medthread.entity_extraction import find_entity_spans_regex
from medthread.context_detection import detect_context, annotate_mentions_with_context


def _get_context(sentence: str, entity_normalized: str) -> str:
    """Helper: find entity in sentence and return its detected context."""
    spans = find_entity_spans_regex(sentence)
    for span in spans:
        if span["entity_normalized"] == entity_normalized:
            context, _ = detect_context(
                sentence=sentence,
                entity=span["entity"],
                char_start=span["start"],
                char_end=span["end"],
            )
            return context
    return "not_found"


# Test 1: "Patient has fever." → fever affirmed
def test_fever_affirmed():
    ctx = _get_context("Patient has fever.", "fever")
    assert ctx == "affirmed", f"Expected affirmed, got {ctx}"


# Test 2: "Patient has no fever." → fever negated
def test_fever_negated_no():
    ctx = _get_context("Patient has no fever.", "fever")
    assert ctx == "negated", f"Expected negated, got {ctx}"


# Test 2 variant: "Denies cough" → negated
def test_cough_denied():
    ctx = _get_context("Patient denies cough.", "cough")
    assert ctx == "negated", f"Expected negated, got {ctx}"


# Test 3: "Denies cough but reports fever." → cough negated, fever affirmed
def test_cough_negated_fever_affirmed():
    sentence = "Denies cough but reports fever."
    ctx_cough = _get_context(sentence, "cough")
    ctx_fever = _get_context(sentence, "fever")
    assert ctx_cough == "negated", f"cough: Expected negated, got {ctx_cough}"
    assert ctx_fever == "affirmed", f"fever: Expected affirmed, got {ctx_fever}"


# Test 4: "Possible infection." → uncertain
def test_possible_infection_uncertain():
    ctx = _get_context("Possible infection.", "infection")
    assert ctx == "uncertain", f"Expected uncertain, got {ctx}"


# Test 4 variant: "suspected pneumonia"
def test_suspected_uncertain():
    ctx = _get_context("Suspected pneumonia.", "infection")
    assert ctx == "uncertain", f"Expected uncertain, got {ctx}"


# Test 4 variant: "may have fever"
def test_may_have_fever_uncertain():
    ctx = _get_context("Patient may have fever.", "fever")
    assert ctx == "uncertain", f"Expected uncertain, got {ctx}"


# Test 5: "Fever has resolved." → resolved
def test_fever_resolved():
    ctx = _get_context("Fever has resolved.", "fever")
    assert ctx == "resolved", f"Expected resolved, got {ctx}"


# Test 5 variant: "cough resolved"
def test_cough_resolved():
    ctx = _get_context("The cough resolved.", "cough")
    assert ctx == "resolved", f"Expected resolved, got {ctx}"


# Test 5 variant: "no longer has a cough"
def test_no_longer_has_cough():
    ctx = _get_context("No longer has a cough.", "cough")
    assert ctx == "resolved"


@pytest.mark.parametrize("sentence", [
    "Fatigue is better.",
    "Shortness of breath improved.",
    "Cough is resolving.",
])
def test_improvement_is_not_explicit_resolution(sentence):
    sentence_lower = sentence.casefold()
    entity = "shortness_of_breath" if "shortness" in sentence_lower else (
        "fatigue" if "fatigue" in sentence_lower else "cough"
    )
    assert _get_context(sentence, entity) == "affirmed"


def test_not_yet_resolved_is_not_mislabeled_as_resolved():
    assert _get_context("Fever has not resolved.", "fever") == "affirmed"


# Test 12: Negation scope — negation of fever should not affect cough in different clause
def test_negation_scope():
    sentence = "No fever; patient has cough."
    ctx_fever = _get_context(sentence, "fever")
    ctx_cough = _get_context(sentence, "cough")
    assert ctx_fever == "negated", f"fever: Expected negated, got {ctx_fever}"
    assert ctx_cough == "affirmed", f"cough: Expected affirmed (scope test), got {ctx_cough}"


# Test 12 variant: "without nausea" should not negate cough
def test_without_nausea_cough_unaffected():
    sentence = "Without nausea; patient has cough."
    ctx_nausea = _get_context(sentence, "nausea")
    ctx_cough = _get_context(sentence, "cough")
    assert ctx_nausea == "negated", f"nausea: Expected negated, got {ctx_nausea}"
    assert ctx_cough == "affirmed", f"cough scope: Expected affirmed, got {ctx_cough}"


def test_resolution_scope_does_not_cross_clauses():
    sentence = "Fever resolved; fever returned today."
    spans = find_entity_spans_regex(sentence)

    contexts = [
        detect_context(sentence, span["entity"], span["start"], span["end"])[0]
        for span in spans
    ]

    assert contexts == ["resolved", "affirmed"]


# Test: annotate_mentions_with_context returns proper dicts
def test_annotate_mentions_returns_context():
    raw = [
        {
            "patient_id": "P1",
            "note_id": "N1",
            "visit_date": None,
            "sentence_index": 0,
            "sentence": "Patient has no fever.",
            "entity": "fever",
            "entity_normalized": "fever",
            "char_start": 15,
            "char_end": 20,
            "extraction_method": "regex_lexicon",
        }
    ]
    annotated = annotate_mentions_with_context(raw)
    assert len(annotated) == 1
    assert annotated[0]["context"] == "negated"
    assert "reason" in annotated[0]


# Test: uncertainty does not count as confirmed positive
def test_uncertain_is_not_affirmed():
    ctx = _get_context("Possible fever.", "fever")
    assert ctx != "affirmed", f"Uncertain should not be affirmed, got {ctx}"
