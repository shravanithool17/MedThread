"""Data schemas for MedThread.

All dataclasses are plain Python with no external dependencies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Note:
    """A single clinical note."""
    patient_id: str
    note_id: str
    visit_date: Optional[date]
    text: str


@dataclass
class Mention:
    """A single symptom/condition mention extracted from a note."""
    patient_id: str
    note_id: str
    visit_date: Optional[date]
    sentence: str                   # original sentence text
    entity: str                     # surface form found in text
    entity_normalized: str          # canonical term from SYMPTOM_LEXICON
    context: str                    # affirmed | negated | uncertain | resolved | unclear
    time_expression: Optional[str]  # raw time expression string, if found
    normalized_event_date: Optional[str]  # best-effort normalized date or None
    extraction_method: str          # e.g. "regex_lexicon" or "spacy_phrase_matcher"
    reason: str                     # human-readable explanation of context label


@dataclass
class ComparisonResult:
    """Cross-visit consistency analysis result for one patient+entity."""
    patient_id: str
    entity: str                         # canonical entity name
    status: str                         # see COMPARISON_STATUSES
    evidence_note_ids: list[str]
    evidence_sentences: list[str]
    explanation: str                    # human-readable summary
    rule_trace: str                     # which rule(s) produced this status
    review_state: str = "unreviewed"    # unreviewed | reviewed | not_a_contradiction | needs_follow_up


# Valid context labels
CONTEXT_LABELS = frozenset({
    "affirmed",
    "negated",
    "uncertain",
    "resolved",
    "unclear",
})

# Valid comparison status labels
COMPARISON_STATUSES = frozenset({
    "persistent_documented",
    "newly_reported",
    "explicitly_resolved",
    "explicitly_negated",
    "possible_inconsistency",
    "unclear",
    "not_documented",
})

# Valid review states
REVIEW_STATES = frozenset({
    "unreviewed",
    "confirmed_inconsistency",
    "reviewed",
    "not_a_contradiction",
    "needs_further_review",
    "needs_follow_up",
})


def review_state_key(patient_id: object, entity: object) -> str:
    """Create an unambiguous string key for a patient/entity review state."""
    return json.dumps(
        [str(patient_id), str(entity)],
        ensure_ascii=True,
        separators=(",", ":"),
    )
