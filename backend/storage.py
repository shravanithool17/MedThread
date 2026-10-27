"""SQLite persistence for source notes and reviewer decisions.

Derived NLP results are intentionally rebuilt from stored source notes.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from medthread.schemas import Note


SCHEMA_VERSION = 1


class SQLiteStore:
    """Persist active source notes and reviewer decisions for the local API."""

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        configured_path = path or os.environ.get(
            "MEDTHREAD_DB_PATH",
            str(Path(__file__).resolve().parents[1] / ".medthread" / "medthread.sqlite3"),
        )
        self.path = Path(configured_path).expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        """Create or safely re-open the current schema; never clear existing data."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            applied = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
            ).fetchone()["version"]
            if applied > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {applied} is newer than supported "
                    f"version {SCHEMA_VERSION}."
                )
            if applied < SCHEMA_VERSION and applied != 0:
                raise RuntimeError(
                    f"No migration path from database schema {applied} "
                    f"to {SCHEMA_VERSION} is defined."
                )

            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    note_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    visit_date TEXT,
                    source_text TEXT NOT NULL,
                    dataset_source TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_notes_patient_date
                    ON notes(patient_id, visit_date, note_id);
                CREATE TABLE IF NOT EXISTS dataset_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_decisions (
                    session_id TEXT NOT NULL,
                    review_key TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    rationale TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(session_id, review_key)
                );
                CREATE TABLE IF NOT EXISTS review_decision_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    review_key TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    rationale TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_review_events_key
                    ON review_decision_events(session_id, review_key, event_id);
                """
            )
            if applied == 0:
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, self._now()),
                )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    def has_initialized_dataset(self) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM dataset_metadata WHERE key = 'initialized'"
            ).fetchone()
            return row is not None and row["value"] == "1"

    def save_dataset(self, notes: list[Note], dataset_source: str) -> None:
        """Atomically replace source notes and invalidate decisions for the old dataset."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM notes")
            connection.executemany(
                """
                INSERT INTO notes(note_id, patient_id, visit_date, source_text, dataset_source)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        note.note_id,
                        note.patient_id,
                        note.visit_date.isoformat() if note.visit_date else None,
                        note.text,
                        dataset_source,
                    )
                    for note in notes
                ],
            )
            connection.execute(
                """
                INSERT INTO dataset_metadata(key, value) VALUES ('initialized', '1')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
            connection.execute(
                """
                INSERT INTO dataset_metadata(key, value) VALUES ('dataset_source', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (dataset_source,),
            )
            connection.execute("DELETE FROM review_decisions")
            connection.execute("DELETE FROM review_decision_events")

    def load_dataset(self) -> tuple[list[Note], str] | None:
        """Return persisted source notes, or None when this database is uninitialized."""
        with self._connect() as connection:
            metadata = {
                row["key"]: row["value"]
                for row in connection.execute(
                    "SELECT key, value FROM dataset_metadata"
                ).fetchall()
            }
            if metadata.get("initialized") != "1":
                return None
            rows = connection.execute(
                """
                SELECT patient_id, note_id, visit_date, source_text
                FROM notes ORDER BY visit_date IS NULL, visit_date, note_id
                """
            ).fetchall()
        notes = [
            Note(
                patient_id=row["patient_id"],
                note_id=row["note_id"],
                visit_date=date.fromisoformat(row["visit_date"]) if row["visit_date"] else None,
                text=row["source_text"],
            )
            for row in rows
        ]
        return notes, metadata.get("dataset_source", "imported")

    def get_review_decisions(self, session_id: str) -> dict[str, dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT review_key, decision, rationale, updated_at
                FROM review_decisions WHERE session_id = ?
                """,
                (session_id,),
            ).fetchall()
        return {
            row["review_key"]: {
                "state": row["decision"],
                "rationale": row["rationale"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        }

    def save_review_decision(
        self,
        session_id: str,
        review_key: str,
        decision: str,
        rationale: str,
    ) -> dict[str, str]:
        updated_at = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO review_decisions(session_id, review_key, decision, rationale, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id, review_key) DO UPDATE SET
                    decision = excluded.decision,
                    rationale = excluded.rationale,
                    updated_at = excluded.updated_at
                """,
                (session_id, review_key, decision, rationale, updated_at),
            )
            connection.execute(
                """
                INSERT INTO review_decision_events(
                    session_id, review_key, decision, rationale, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, review_key, decision, rationale, updated_at),
            )
        return {"state": decision, "rationale": rationale, "updated_at": updated_at}

    def get_review_event_history(
        self, session_id: str, review_key: str
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT decision, rationale, created_at
                FROM review_decision_events
                WHERE session_id = ? AND review_key = ?
                ORDER BY event_id
                """,
                (session_id, review_key),
            ).fetchall()
        return [
            {
                "state": row["decision"],
                "rationale": row["rationale"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
