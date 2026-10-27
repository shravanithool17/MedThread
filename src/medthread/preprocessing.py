"""Text preprocessing: normalization and sentence splitting.

spaCy is used if available; otherwise a regex-based fallback is used.
The fallback is not medically validated — it is a reasonable baseline for
splitting English prose into sentences.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Protocol

from .schemas import Note


class _Sentence(Protocol):
    text: str


class _Document(Protocol):
    sents: Iterable[_Sentence]


class _SpacyPipeline(Protocol):
    def __call__(self, text: str) -> _Document: ...


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

def _regex_sentence_split(text: str) -> list[str]:
    """Simple regex sentence splitter as fallback when spaCy is unavailable."""
    # Split on period/exclamation/question followed by whitespace + uppercase,
    # or on newlines that look like sentence boundaries.
    # Preserve punctuation at end of sentence.
    pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\s*(?=[A-Z])'
    parts = re.split(pattern, text)
    sentences = []
    for part in parts:
        part = part.strip()
        if part:
            sentences.append(part)
    return sentences if sentences else [text.strip()]


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences. Uses spaCy if available, regex otherwise."""
    try:
        import spacy  # type: ignore
        _nlp = _get_spacy_model()
        if _nlp is not None:
            doc = _nlp(text)
            return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    except ImportError:
        pass
    return _regex_sentence_split(text)


_SPACY_MODEL: _SpacyPipeline | None = None
_SPACY_LOADED: bool = False


def _get_spacy_model() -> _SpacyPipeline | None:
    """Load and cache a small spaCy model. Returns None if unavailable."""
    global _SPACY_MODEL, _SPACY_LOADED
    if _SPACY_LOADED:
        return _SPACY_MODEL
    _SPACY_LOADED = True
    try:
        import spacy  # type: ignore
        _SPACY_MODEL = spacy.load("en_core_web_sm")
    except Exception:
        try:
            import spacy  # type: ignore
            # Try blank model as sentence splitter with sentencizer
            nlp = spacy.blank("en")
            nlp.add_pipe("sentencizer")
            _SPACY_MODEL = nlp
        except Exception:
            _SPACY_MODEL = None
    return _SPACY_MODEL


def is_spacy_available() -> bool:
    """Return True if spaCy is importable and a model is loaded."""
    return _get_spacy_model() is not None


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize whitespace and formatting noise while preserving content.
    Does NOT remove stopwords, stem, or lowercase (to preserve negation cues).
    """
    # Collapse runs of whitespace (but not newlines) into a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Collapse 3+ newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()


# ---------------------------------------------------------------------------
# Note → sentences
# ---------------------------------------------------------------------------

def extract_sentences_from_note(note: Note) -> list[dict]:
    """
    Return a list of sentence records from a note, each being a dict with:
      patient_id, note_id, visit_date, sentence_index, sentence
    """
    normalized = normalize_text(note.text)
    sentences = split_into_sentences(normalized)
    records = []
    for i, sent in enumerate(sentences):
        records.append({
            "patient_id": note.patient_id,
            "note_id": note.note_id,
            "visit_date": note.visit_date,
            "sentence_index": i,
            "sentence": sent,
        })
    return records
