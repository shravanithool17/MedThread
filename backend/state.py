"""In-memory application state for the MedThread backend (single-process demo)."""
from __future__ import annotations
import os, sys
import pandas as pd

# Make the NLP modules importable
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from medthread.schemas import Note  # noqa: E402


class AppState:
    """Single-process demo corpus and per-browser review decisions."""

    def __init__(self) -> None:
        self.notes: list[Note] = []
        self.mentions_df: pd.DataFrame = pd.DataFrame()
        self.comparison_df: pd.DataFrame = pd.DataFrame()
        self.pipeline_run: bool = False
        self.dataset_source: str = "empty"
        self.review_states: dict[str, dict[str, str]] = {}

    def clear_review_states(self) -> None:
        self.review_states.clear()

    def get_review_states(self, session_id: str) -> dict[str, str]:
        return self.review_states.setdefault(session_id, {})

    def reset(self) -> None:
        self.notes = []
        self.mentions_df = pd.DataFrame()
        self.comparison_df = pd.DataFrame()
        self.pipeline_run = False
        self.dataset_source = "empty"
        self.clear_review_states()


# Global singleton
state = AppState()
