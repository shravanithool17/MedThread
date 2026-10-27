"""Tests for longitudinal cross-visit consistency analysis.

Key requirements:
- Test 6: Temporal change is NOT a contradiction.
- Test 7: Same-time conflicting claims = possible_inconsistency.
- Test 8: Not mentioned in later note = not_documented, not resolved.
- Test 9: Different patient IDs are never compared.
- Test 10: Missing/invalid dates → graceful or unclear status.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import date
import pytest
from medthread.longitudinal_analysis import analyze_patient_entity, run_longitudinal_analysis


def _make_mention(
    patient_id="P1",
    note_id="N1",
    visit_date=None,
    sentence="",
    entity="fever",
    entity_normalized="fever",
    context="affirmed",
    normalized_event_date=None,
    reason="test",
):
    return {
        "patient_id": patient_id,
        "note_id": note_id,
        "visit_date": visit_date,
        "sentence_index": 0,
        "sentence": sentence or f"Patient has {entity}.",
        "entity": entity,
        "entity_normalized": entity_normalized,
        "context": context,
        "time_expression": None,
        "normalized_event_date": normalized_event_date,
        "extraction_method": "test",
        "reason": reason,
        "char_start": 0,
        "char_end": len(entity),
    }


# Test 1: Single affirmed → newly_reported
def test_single_affirmed_newly_reported():
    mentions = [_make_mention(context="affirmed")]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert result.status == "newly_reported"


# Test 2: Two affirmed notes → persistent_documented
def test_two_affirmed_persistent():
    mentions = [
        _make_mention(note_id="N1", visit_date=date(2024, 1, 1), context="affirmed"),
        _make_mention(note_id="N2", visit_date=date(2024, 1, 8), context="affirmed"),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert result.status == "persistent_documented"


# Test: affirmed then resolved → explicitly_resolved
def test_affirmed_then_resolved():
    mentions = [
        _make_mention(note_id="N1", visit_date=date(2024, 1, 1), context="affirmed"),
        _make_mention(note_id="N2", visit_date=date(2024, 1, 8), context="resolved"),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert result.status == "explicitly_resolved"


def test_missing_dates_do_not_establish_resolution_order():
    mentions = [
        _make_mention(note_id="N1", context="affirmed"),
        _make_mention(note_id="N2", context="resolved"),
    ]

    result = analyze_patient_entity("P1", "fever", mentions)

    assert result.status == "unclear"


def test_same_visit_date_does_not_establish_resolution_order():
    same_date = date(2024, 1, 1)
    mentions = [
        _make_mention(note_id="N1", visit_date=same_date, context="affirmed"),
        _make_mention(note_id="N2", visit_date=same_date, context="resolved"),
    ]

    result = analyze_patient_entity("P1", "fever", mentions)

    assert result.status == "unclear"


# Test 5 / single resolved → explicitly_resolved
def test_single_resolved():
    mentions = [_make_mention(context="resolved")]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert result.status == "explicitly_resolved"


# Test: single negated → explicitly_negated
def test_single_negated():
    mentions = [_make_mention(context="negated")]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert result.status == "explicitly_negated"


# Test 4: single uncertain → unclear
def test_single_uncertain():
    mentions = [_make_mention(context="uncertain")]
    result = analyze_patient_entity("P1", "infection", mentions)
    assert result.status == "unclear"


# Test 7: Fever affirmed in note A, negated in note B with no conflicting temporal context
# → possible_inconsistency
def test_affirmed_vs_negated_same_context():
    mentions = [
        _make_mention(note_id="N1", visit_date=date(2024, 1, 1), context="affirmed",
                      normalized_event_date=None),
        _make_mention(note_id="N2", visit_date=date(2024, 1, 1), context="negated",
                      normalized_event_date=None),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert result.status == "possible_inconsistency"


# Test 6: "No fever Monday; fever started Wednesday" — temporal change, NOT contradiction
def test_temporal_change_not_contradiction():
    mentions = [
        _make_mention(note_id="N1", visit_date=date(2024, 1, 8), context="negated",
                      normalized_event_date="2024-01-08",  # Monday
                      sentence="No fever Monday."),
        _make_mention(note_id="N2", visit_date=date(2024, 1, 10), context="affirmed",
                      normalized_event_date="2024-01-10",  # Wednesday
                      sentence="Fever started Wednesday."),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    # Different dates → not a contradiction → should NOT be possible_inconsistency
    assert result.status != "possible_inconsistency", (
        f"Temporal change was incorrectly flagged as possible_inconsistency. "
        f"Status: {result.status}, rule: {result.rule_trace}"
    )


# Test 7 (exact same day context): Both reference same date → possible_inconsistency
def test_same_day_contradiction():
    mentions = [
        _make_mention(note_id="N1", visit_date=date(2024, 1, 8), context="affirmed",
                      normalized_event_date="2024-01-08"),
        _make_mention(note_id="N2", visit_date=date(2024, 1, 8), context="negated",
                      normalized_event_date="2024-01-08"),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert result.status == "possible_inconsistency"


# Test 8: Symptom not mentioned in later note → not tracked, not resolved
def test_absence_is_not_resolved():
    """
    The longitudinal module only processes mentions that exist.
    A symptom absent from a note simply doesn't appear in the mentions list.
    The comparison result for an entity that only has one note should be
    newly_reported (not resolved).
    """
    # Only one mention — the later note has no mention, so it's not in the list
    mentions = [
        _make_mention(note_id="N1", visit_date=date(2024, 1, 1), context="affirmed"),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    # Should be newly_reported, NOT resolved
    assert result.status != "explicitly_resolved", (
        "Absence of mention was incorrectly treated as resolved."
    )
    assert result.status != "explicitly_negated"


# Test 9: Different patient IDs are NEVER compared
def test_different_patients_not_compared():
    all_mentions = [
        _make_mention(patient_id="P1", note_id="N1", visit_date=date(2024, 1, 1),
                      context="affirmed"),
        _make_mention(patient_id="P2", note_id="N2", visit_date=date(2024, 1, 1),
                      context="negated"),
    ]
    results = run_longitudinal_analysis(all_mentions)
    # Should produce two separate results, one per patient
    patient_ids = {r.patient_id for r in results}
    assert "P1" in patient_ids
    assert "P2" in patient_ids
    for r in results:
        if r.patient_id == "P1":
            assert r.status == "newly_reported"
        if r.patient_id == "P2":
            assert r.status == "explicitly_negated"


# Test 10: Missing or invalid dates → graceful handling
def test_missing_dates():
    mentions = [
        _make_mention(note_id="N1", visit_date=None, context="affirmed"),
        _make_mention(note_id="N2", visit_date=None, context="negated"),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    # Should not crash; status could be possible_inconsistency or unclear
    assert result.status in (
        "possible_inconsistency", "unclear", "not_documented",
        "newly_reported", "persistent_documented"
    )


# Test: run_longitudinal_analysis with empty list
def test_empty_mentions():
    results = run_longitudinal_analysis([])
    assert results == []


# Test 16: exported output contains evidence and correct labels
def test_result_has_evidence():
    mentions = [
        _make_mention(note_id="N1", context="affirmed", sentence="Patient has fever."),
    ]
    result = analyze_patient_entity("P1", "fever", mentions)
    assert len(result.evidence_sentences) > 0
    assert len(result.evidence_note_ids) > 0
    assert result.explanation
    assert result.rule_trace
