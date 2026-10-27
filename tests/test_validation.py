"""Tests for input validation."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import pandas as pd
from medthread.validation import validate_notes_dataframe, load_notes_from_csv, parse_date
from datetime import date, datetime


# Test: valid CSV loads correctly
def test_valid_csv():
    csv_content = """patient_id,note_id,visit_date,text
P1,N1,2024-01-01,Patient has fever.
P2,N2,2024-02-01,No cough.
"""
    notes, errors = load_notes_from_csv(csv_content)
    assert len(notes) == 2
    assert not errors
    assert notes[0].patient_id == "P1"
    assert notes[0].note_id == "N1"


# Test 13: duplicate note IDs generate warning
def test_duplicate_note_ids():
    csv_content = """patient_id,note_id,visit_date,text
P1,N1,2024-01-01,Patient has fever.
P1,N1,2024-01-08,Fever persists.
"""
    notes, errors = load_notes_from_csv(csv_content)
    assert len(notes) == 1  # second duplicate skipped
    assert any("Duplicate" in e for e in errors)


# Test 13: malformed row (empty text) is handled
def test_empty_text_row():
    csv_content = """patient_id,note_id,visit_date,text
P1,N1,2024-01-01,
P1,N2,2024-01-08,Valid note.
"""
    notes, errors = load_notes_from_csv(csv_content)
    # N1 should be skipped (empty text)
    note_ids = [n.note_id for n in notes]
    assert "N1" not in note_ids
    assert any("empty" in e.lower() for e in errors)


# Test: missing columns
def test_missing_columns():
    csv_content = """patient_id,note_id,text
P1,N1,Some text.
"""
    notes, errors = load_notes_from_csv(csv_content)
    assert len(notes) == 0
    assert any("Missing required" in e for e in errors)


# Test 10: invalid date is gracefully handled
def test_invalid_date():
    csv_content = """patient_id,note_id,visit_date,text
P1,N1,not-a-date,Patient has fever.
"""
    notes, errors = load_notes_from_csv(csv_content)
    # Note should still be created but with visit_date=None
    assert len(notes) == 1
    assert notes[0].visit_date is None
    assert any("Could not parse" in e for e in errors)


# Test: parse_date handles various formats
def test_parse_date_formats():
    assert parse_date("2024-01-15") == date(2024, 1, 15)
    assert parse_date("15/01/2024") == date(2024, 1, 15)
    assert parse_date("01/15/2024") == date(2024, 1, 15)
    assert parse_date(datetime(2024, 1, 15, 13, 30)) == date(2024, 1, 15)
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("nan") is None
    assert parse_date(pd.NaT) is None


# Test 14: completely empty CSV content
def test_empty_csv():
    notes, errors = load_notes_from_csv("patient_id,note_id,visit_date,text\n")
    assert len(notes) == 0


# Test: empty patient_id is rejected
def test_empty_patient_id():
    df = pd.DataFrame([{
        "patient_id": "",
        "note_id": "N1",
        "visit_date": "2024-01-01",
        "text": "Some text.",
    }])
    notes, errors = validate_notes_dataframe(df)
    assert len(notes) == 0
    assert any("patient_id is empty" in e for e in errors)


def test_invalid_row_does_not_reserve_duplicate_note_id():
    csv_content = """patient_id,note_id,visit_date,text
P1,N1,2024-01-01,
P1,N1,2024-01-02,Valid note.
"""
    notes, errors = load_notes_from_csv(csv_content)
    assert len(notes) == 1
    assert notes[0].note_id == "N1"
    assert any("text is empty" in error for error in errors)
    assert not any("Duplicate" in error for error in errors)


def test_missing_pandas_datetime_is_unknown_date():
    df = pd.DataFrame([{
        "patient_id": "P1",
        "note_id": "N1",
        "visit_date": pd.NaT,
        "text": "A valid note.",
    }])

    notes, errors = validate_notes_dataframe(df)

    assert not errors
    assert len(notes) == 1
    assert notes[0].visit_date is None
