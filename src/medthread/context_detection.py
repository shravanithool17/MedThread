"""Context detection: negation, uncertainty, resolution, and affirmed.

Rules are conservative, explainable, and scoped to each mention.

Key design decisions:
- Context scope is limited to the clause containing the entity mention
  (clauses split on ';', 'but', 'however', 'although', newline).
- Cue search operates on the raw clause substring (not joined tokens)
  to avoid trailing-space mismatches with cue strings like "no ".
- A negation cue must appear in the text BEFORE the entity (or
  immediately after for "has resolved" type patterns).
- Priority when cues conflict: negated > resolved > uncertain > affirmed.
"""

from __future__ import annotations

import re
from typing import Optional

from .config import NEGATION_CUES, UNCERTAINTY_CUES, RESOLUTION_CUES


_NOT_RESOLVED = re.compile(
    r"\b(?:not|never|hasn't|haven't|has\s+not|have\s+not)\s+"
    r"(?:yet\s+)?(?:fully\s+)?(?:resolved|subsided|cleared|gone)\b",
    re.IGNORECASE,
)


def _clause_containing(sentence: str, char_start: int, char_end: int) -> tuple[str, int]:
    """
    Return (clause_text, clause_offset) where clause_text is the clause that
    contains the entity span and clause_offset is where that clause starts
    within the sentence.
    """
    boundary_pattern = re.compile(r';| but | however | although |\n', re.IGNORECASE)
    boundaries = [(-1, -1)] + [(m.start(), m.end()) for m in boundary_pattern.finditer(sentence)]
    # Build clause intervals
    clause_starts = [0] + [b[1] for b in boundaries[1:]]
    clause_ends = [b[0] for b in boundaries[1:]] + [len(sentence)]

    for cs, ce in zip(clause_starts, clause_ends):
        if cs <= char_start < ce:
            return sentence[cs:ce], cs

    return sentence, 0  # fallback: whole sentence


def _text_before_entity(clause: str, entity: str) -> str:
    """Raw text in the clause before the first occurrence of entity."""
    idx = clause.lower().find(entity.lower())
    if idx == -1:
        return clause
    return clause[:idx]


def _text_after_entity(clause: str, entity: str) -> str:
    """Raw text in the clause after the entity."""
    idx = clause.lower().find(entity.lower())
    if idx == -1:
        return ""
    return clause[idx + len(entity):]


def _find_cue(text: str, cues: list[str]) -> Optional[str]:
    """
    Return the first matching cue found in text (case-insensitive).
    Longer cues are checked first to avoid partial matches.
    """
    text_lower = text.lower()
    for cue in sorted(cues, key=len, reverse=True):
        # Use word-boundary-aware search for single words; substring for phrases
        cue_lower = cue.lower().strip()
        if " " in cue_lower:
            if cue_lower in text_lower:
                return cue
        else:
            # Word boundary check
            if re.search(r'\b' + re.escape(cue_lower) + r'\b', text_lower):
                return cue
    return None


def detect_context(
    sentence: str,
    entity: str,
    char_start: int,
    char_end: int,
) -> tuple[str, str]:
    """
    Determine context for an entity mention.

    Returns (context_label, reason_string).
    context_label in: affirmed | negated | uncertain | resolved | unclear
    """
    clause, clause_offset = _clause_containing(sentence, char_start, char_end)

    # Convert global char positions to clause-local positions
    local_start = char_start - clause_offset
    local_end = char_end - clause_offset

    # Guard against offset errors
    if local_start < 0 or local_start >= len(clause):
        # Fall back to whole clause
        before_text = _text_before_entity(clause, entity)
        after_text = _text_after_entity(clause, entity)
    else:
        before_text = clause[:local_start]
        after_text = clause[local_end:]

    # --- Check cues in text BEFORE entity (within clause) ---
    negation_before = _find_cue(before_text, NEGATION_CUES)
    uncertainty_before = _find_cue(before_text, UNCERTAINTY_CUES)
    resolution_before = _find_cue(before_text, RESOLUTION_CUES)

    # --- Check cues in text AFTER entity (shorter window — resolution only) ---
    after_window = after_text[:80]  # limit look-ahead
    resolution_after = _find_cue(after_window, RESOLUTION_CUES)
    uncertainty_after = _find_cue(after_window, UNCERTAINTY_CUES)

    if _NOT_RESOLVED.search(after_window):
        return "affirmed", f"Explicit negation of resolution near '{entity}' indicates an ongoing mention."

    # "No longer has X" is an explicit resolution, not a current-state negation.
    if resolution_before or resolution_after:
        cue = resolution_before or resolution_after
        return "resolved", f"Resolution cue '{cue}' found near '{entity}' in clause."

    if negation_before:
        return "negated", f"Negation cue '{negation_before}' found before '{entity}' in clause."

    if uncertainty_before or uncertainty_after:
        cue = uncertainty_before or uncertainty_after
        return "uncertain", f"Uncertainty cue '{cue}' found near '{entity}' in clause."

    return "affirmed", f"No negation/uncertainty/resolution cue found near '{entity}' — affirmed."


def annotate_mentions_with_context(raw_mentions: list[dict]) -> list[dict]:
    """
    Add 'context' and 'reason' fields to each raw mention dict.
    Returns an updated list (new dicts, original untouched).
    """
    annotated = []
    for mention in raw_mentions:
        context, reason = detect_context(
            sentence=mention["sentence"],
            entity=mention["entity"],
            char_start=mention.get("char_start", 0),
            char_end=mention.get("char_end", len(mention["entity"])),
        )
        updated = dict(mention)
        updated["context"] = context
        updated["reason"] = reason
        annotated.append(updated)
    return annotated
