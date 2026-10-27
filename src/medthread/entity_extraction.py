"""Entity extraction: find symptom/condition mentions in sentences.

Uses spaCy PhraseMatcher if available, otherwise falls back to regex with
word boundaries against the configured SYMPTOM_LEXICON.
"""

from __future__ import annotations

import re
from typing import Any

from .config import SYMPTOM_LEXICON, SURFACE_TO_CANONICAL
from .schemas import Note, Mention
from .preprocessing import extract_sentences_from_note, _get_spacy_model


def _build_surface_pattern(surface: str) -> re.Pattern:
    """Build a case-insensitive word-boundary regex for a surface form."""
    escaped = re.escape(surface)
    # Use word boundaries; for multi-word phrases use \b only at start/end
    return re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)


# Build patterns once at import time
_SURFACE_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (_canonical, _surface, _build_surface_pattern(_surface))
    for _canonical, _surface in sorted(
        (
            (canonical, surface)
            for canonical, surfaces in SYMPTOM_LEXICON.items()
            for surface in surfaces
        ),
        key=lambda item: (-len(item[1]), item[1], item[0]),
    )
]


def find_entity_spans_regex(sentence: str) -> list[dict]:
    """
    Find all symptom mentions in a sentence using regex.
    Returns list of dicts: {entity, entity_normalized, start, end}
    Longest surface forms take priority; overlapping shorter matches are suppressed.
    """
    matches: list[dict] = []
    covered: set[tuple[int, int]] = set()

    for canonical, surface, pattern in _SURFACE_PATTERNS:
        for m in pattern.finditer(sentence):
            start, end = m.start(), m.end()
            # Check for overlap with already-covered spans
            overlap = any(
                not (end <= cs or start >= ce)
                for cs, ce in covered
            )
            if not overlap:
                covered.add((start, end))
                matches.append({
                    "entity": m.group(),
                    "entity_normalized": canonical,
                    "start": start,
                    "end": end,
                })

    return sorted(matches, key=lambda x: x["start"])


def find_entity_spans_spacy(sentence: str, nlp: Any) -> list[dict]:
    """
    Find symptom mentions using spaCy PhraseMatcher.
    Falls back to regex if PhraseMatcher setup fails.
    """
    try:
        from spacy.matcher import PhraseMatcher  # type: ignore
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        for canonical, surfaces in SYMPTOM_LEXICON.items():
            patterns = [nlp.make_doc(s) for s in surfaces]
            matcher.add(canonical, patterns)
        doc = nlp(sentence)
        results = []
        for match_id, start_token, end_token in matcher(doc):
            span = doc[start_token:end_token]
            canonical = nlp.vocab.strings[match_id]
            results.append({
                "entity": span.text,
                "entity_normalized": canonical,
                "start": span.start_char,
                "end": span.end_char,
            })
        selected: list[dict] = []
        for result in sorted(
            results,
            key=lambda item: (-(item["end"] - item["start"]), item["start"], item["end"]),
        ):
            if any(
                not (result["end"] <= current["start"] or result["start"] >= current["end"])
                for current in selected
            ):
                continue
            selected.append(result)
        return sorted(selected, key=lambda item: (item["start"], item["end"]))
    except Exception:
        return find_entity_spans_regex(sentence)


def extract_mentions_from_sentences(
    sentence_records: list[dict],
    extraction_method: str = "auto",
) -> list[dict]:
    """
    Given sentence records (from preprocessing), return raw mention dicts
    with: patient_id, note_id, visit_date, sentence, sentence_index,
           entity, entity_normalized, start, end.
    """
    nlp = _get_spacy_model()
    use_spacy = nlp is not None and extraction_method in ("auto", "spacy")

    results = []
    for rec in sentence_records:
        sentence = rec["sentence"]
        if use_spacy:
            spans = find_entity_spans_spacy(sentence, nlp)
            method = "spacy_phrase_matcher"
        else:
            spans = find_entity_spans_regex(sentence)
            method = "regex_lexicon"

        for span in spans:
            results.append({
                "patient_id": rec["patient_id"],
                "note_id": rec["note_id"],
                "visit_date": rec["visit_date"],
                "sentence_index": rec["sentence_index"],
                "sentence": sentence,
                "entity": span["entity"],
                "entity_normalized": span["entity_normalized"],
                "char_start": span["start"],
                "char_end": span["end"],
                "extraction_method": method,
            })

    return results


def extract_mentions_from_notes(notes: list[Note]) -> list[dict]:
    """Full pipeline: notes → sentence records → raw mention dicts."""
    all_sentences = []
    for note in notes:
        all_sentences.extend(extract_sentences_from_note(note))
    return extract_mentions_from_sentences(all_sentences)
