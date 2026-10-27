"""Pipeline cache and SQLite-backed reviewer state for the local API process."""
from __future__ import annotations
import os, sys
import pandas as pd

# Make the NLP modules importable
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from medthread.schemas import Note  # noqa: E402
from backend.storage import SQLiteStore


class AppState:
    """Keep derived pipeline results in memory while source data is persisted."""

    def __init__(self) -> None:
        self.notes: list[Note] = []
        self.mentions_df: pd.DataFrame = pd.DataFrame()
        self.comparison_df: pd.DataFrame = pd.DataFrame()
        self.pipeline_run: bool = False
        self.dataset_source: str = "empty"
        self.review_states: dict[str, dict[str, str]] = {}
        self.review_details: dict[str, dict[str, dict[str, str]]] = {}
        self.store = SQLiteStore()

    def clear_review_states(self) -> None:
        self.review_states.clear()
        self.review_details.clear()

    def get_review_states(self, session_id: str) -> dict[str, str]:
        if session_id not in self.review_states:
            decisions = self.store.get_review_decisions(session_id)
            self.review_states[session_id] = {
                key: value["state"] for key, value in decisions.items()
            }
            self.review_details[session_id] = decisions
        return self.review_states[session_id]

    def get_review_details(self, session_id: str) -> dict[str, dict[str, str]]:
        self.get_review_states(session_id)
        return self.review_details.setdefault(session_id, {})

    def save_review_decision(
        self,
        session_id: str,
        review_key: str,
        decision: str,
        rationale: str,
    ) -> dict[str, str]:
        details = self.store.save_review_decision(
            session_id, review_key, decision, rationale
        )
        self.review_states.setdefault(session_id, {})[review_key] = decision
        self.review_details.setdefault(session_id, {})[review_key] = details
        return details

    def reset(self) -> None:
        self.notes = []
        self.mentions_df = pd.DataFrame()
        self.comparison_df = pd.DataFrame()
        self.pipeline_run = False
        self.dataset_source = "empty"
        self.clear_review_states()


# Global singleton
state = AppState()
