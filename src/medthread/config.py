"""Configuration: symptom lexicon, cue patterns, and application settings."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Symptom / condition lexicon
# ---------------------------------------------------------------------------
# Each entry: canonical term -> list of surface forms (lowercase).
# Add new entries here to extend coverage.

SYMPTOM_LEXICON: dict[str, list[str]] = {
    "cough": ["cough", "coughing", "coughs"],
    "fever": ["fever", "febrile", "high temperature", "pyrexia"],
    "headache": ["headache", "head pain", "cephalgia"],
    "nausea": ["nausea", "nauseous", "nauseated"],
    "vomiting": ["vomiting", "vomit", "emesis"],
    "fatigue": ["fatigue", "tired", "tiredness", "exhaustion", "exhausted"],
    "shortness_of_breath": [
        "shortness of breath",
        "dyspnea",
        "dyspnoea",
        "difficulty breathing",
        "breathlessness",
        "short of breath",
        "sob",
    ],
    "chest_pain": ["chest pain", "chest tightness", "chest discomfort"],
    "sore_throat": ["sore throat", "pharyngitis", "throat pain"],
    "dizziness": ["dizziness", "dizzy", "lightheaded", "vertigo"],
    "rash": ["rash", "skin rash", "redness", "erythema"],
    "congestion": ["congestion", "nasal congestion", "stuffy nose"],
    "pain": ["pain", "ache", "aching", "hurting"],
    "infection": ["infection", "infectious", "pneumonia", "bacteremia", "sepsis"],
}

# All surface forms -> canonical name (built at module load time)
SURFACE_TO_CANONICAL: dict[str, str] = {}
for _canonical, _surfaces in SYMPTOM_LEXICON.items():
    for _surface in _surfaces:
        SURFACE_TO_CANONICAL[_surface.lower()] = _canonical

# ---------------------------------------------------------------------------
# Context cue patterns
# Categories: negation, uncertainty, resolution
# ---------------------------------------------------------------------------

NEGATION_CUES: list[str] = [
    "no ",
    "no evidence of",
    "denies",
    "deny",
    "denied",
    "without",
    "absence of",
    "absent",
    "not have",
    "does not have",
    "did not have",
    "never had",
    "not present",
    "negative for",
    "rules out",
    "ruled out",
    "free of",
    "no complaints of",
    "no history of",
    "not experiencing",
]

UNCERTAINTY_CUES: list[str] = [
    "possible",
    "possibly",
    "probable",
    "probably",
    "suspected",
    "suspect",
    "may have",
    "might have",
    "could have",
    "cannot rule out",
    "can't rule out",
    "rule out",
    "likely",
    "unlikely",
    "seems to have",
    "appears to have",
    "consistent with",
    "suggestive of",
]

RESOLUTION_CUES: list[str] = [
    "resolved",
    "has resolved",
    "have resolved",
    "no longer",
    "subsided",
    "cleared",
    "gone",
    "remission",
    "recovered",
    "recovery",
]

# ---------------------------------------------------------------------------
# Temporal patterns (simple regex fragments — see temporal.py for use)
# ---------------------------------------------------------------------------

# Days of the week
DAYS_OF_WEEK: list[str] = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Month names
MONTH_NAMES: list[str] = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
]

# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------

APP_TITLE = "MedThread"
APP_SUBTITLE = "Longitudinal Clinical Text Mining & Consistency Analysis"

SAFETY_NOTICE = (
    "⚠️ **Educational research prototype.** Not for diagnosis, treatment, or clinical decision-making. "
    "Use synthetic or authorized de-identified text only. All flags require human review. "
    "Results reflect text-mining patterns, NOT medical truth."
)

# Cross-visit comparison window (days): if two notes are within this window
# and give conflicting context, they may be compared. Set to None to skip window check.
COMPARISON_WINDOW_DAYS: int | None = None  # conservative: compare regardless of window
