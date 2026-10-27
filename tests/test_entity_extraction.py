"""Tests for entity extraction."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from medthread.entity_extraction import find_entity_spans_regex


def _find_entities(sentence: str) -> dict[str, list[str]]:
    """Helper: return {canonical: [surface_forms]}."""
    spans = find_entity_spans_regex(sentence)
    result: dict[str, list[str]] = {}
    for s in spans:
        result.setdefault(s["entity_normalized"], []).append(s["entity"])
    return result


# Test 1: basic affirmed mentions
def test_fever_found():
    entities = _find_entities("Patient has fever.")
    assert "fever" in entities


def test_cough_found():
    entities = _find_entities("Patient reports cough.")
    assert "cough" in entities


# Test 4: infection is extractable
def test_infection_found():
    entities = _find_entities("Possible infection.")
    assert "infection" in entities


# Test 3: two symptoms in one sentence
def test_cough_and_fever():
    entities = _find_entities("Denies cough but reports fever.")
    assert "cough" in entities
    assert "fever" in entities


# Test 11: two symptoms with separate contexts in one sentence
def test_two_symptoms_same_sentence():
    entities = _find_entities("No fever but patient has sore throat.")
    assert "fever" in entities
    assert "sore_throat" in entities


# Test 14: empty input does not crash
def test_empty_sentence():
    spans = find_entity_spans_regex("")
    assert spans == []


# Test 14: unknown term does not crash
def test_unknown_term():
    spans = find_entity_spans_regex("Patient has an unknown condition.")
    assert isinstance(spans, list)


# Test for multi-word symptoms
def test_shortness_of_breath():
    entities = _find_entities("Patient has shortness of breath.")
    assert "shortness_of_breath" in entities


def test_chest_pain():
    entities = _find_entities("Reports chest pain and dizziness.")
    assert "chest_pain" in entities
    assert "dizziness" in entities


# No overlap: longer form wins
def test_no_overlap():
    entities = _find_entities("Patient has sore throat.")
    # should find sore_throat, not just pain
    assert "sore_throat" in entities


@pytest.mark.parametrize("text", [
    "feverish appearance",
    "painful movement",
    "coughdrop was mentioned",
])
def test_entity_boundaries_do_not_match_substrings(text):
    assert find_entity_spans_regex(text) == []


def test_longest_overlapping_concept_alias_wins():
    spans = find_entity_spans_regex("Patient reports chest pain.")
    assert [(span["entity_normalized"], span["entity"]) for span in spans] == [
        ("chest_pain", "chest pain"),
    ]
