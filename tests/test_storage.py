from datetime import date
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.storage import SQLiteStore
from medthread.schemas import Note


def _note(note_id: str, text: str = "Patient reports cough.") -> Note:
    return Note(
        patient_id="PERSISTED_PATIENT",
        note_id=note_id,
        visit_date=date(2026, 10, 27),
        text=text,
    )


def test_store_initialization_and_dataset_survive_reopen(tmp_path):
    database_path = tmp_path / "medthread.sqlite3"
    first_store = SQLiteStore(database_path)
    first_store.initialize()
    first_store.initialize()
    assert first_store.load_dataset() is None

    first_store.save_dataset([_note("NOTE_1")], "imported")
    reopened_store = SQLiteStore(database_path)
    reopened_store.initialize()

    notes, source = reopened_store.load_dataset()
    assert [(note.note_id, note.text) for note in notes] == [
        ("NOTE_1", "Patient reports cough.")
    ]
    assert source == "imported"


def test_dataset_replacement_rolls_back_on_duplicate_note_ids(tmp_path):
    store = SQLiteStore(tmp_path / "rollback.sqlite3")
    store.initialize()
    store.save_dataset([_note("KEEP")], "imported")

    with pytest.raises(sqlite3.IntegrityError):
        store.save_dataset([_note("DUPLICATE"), _note("DUPLICATE")], "manual-entry")

    notes, source = store.load_dataset()
    assert [note.note_id for note in notes] == ["KEEP"]
    assert source == "imported"


def test_review_rationale_and_audit_history_survive_reopen(tmp_path):
    database_path = tmp_path / "reviews.sqlite3"
    store = SQLiteStore(database_path)
    store.initialize()
    store.save_review_decision(
        "browser-session", '["PERSISTED_PATIENT","cough"]',
        "confirmed_inconsistency", "Evidence conflicts on the same date.",
    )
    store.save_review_decision(
        "browser-session", '["PERSISTED_PATIENT","cough"]',
        "needs_further_review", "Second review requested.",
    )

    reopened_store = SQLiteStore(database_path)
    reopened_store.initialize()
    key = '["PERSISTED_PATIENT","cough"]'
    decision = reopened_store.get_review_decisions("browser-session")[key]

    assert decision["state"] == "needs_further_review"
    assert decision["rationale"] == "Second review requested."
    assert decision["updated_at"]
    history = reopened_store.get_review_event_history("browser-session", key)
    assert [event["state"] for event in history] == [
        "confirmed_inconsistency", "needs_further_review"
    ]


def test_empty_dataset_remains_empty_after_reopen(tmp_path):
    database_path = tmp_path / "reset.sqlite3"
    store = SQLiteStore(database_path)
    store.initialize()
    store.save_dataset([], "empty")

    notes, source = SQLiteStore(database_path).load_dataset()
    assert notes == []
    assert source == "empty"
