"""Temporal expression extraction and normalization.

Extracts common time expressions from clinical text:
- Absolute: "Monday", "January 5th", "2024-01-01"
- Relative: "yesterday", "today", "two days ago", "last week"
- Duration: "since Monday", "for three days"
- Event-anchored: "fever started Wednesday", "resolved yesterday"

Normalization is best-effort against the note's visit_date.
Unresolvable expressions are kept as raw strings with normalized_event_date=None.

This module does NOT claim clinical accuracy.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Number words for relative expressions
_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}

# Days of week
_DOW = r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
# Months
_MONTH = r'(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)'

_TEMPORAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("relative_today",     re.compile(r'\btoday\b', re.I)),
    ("relative_yesterday", re.compile(r'\byesterday\b', re.I)),
    ("relative_days_ago",  re.compile(r'\b(?:(\w+)|(\d+))\s+days?\s+ago\b', re.I)),
    ("relative_weeks_ago", re.compile(r'\b(?:(\w+)|(\d+))\s+weeks?\s+ago\b', re.I)),
    ("relative_last_week", re.compile(r'\blast\s+week\b', re.I)),
    ("relative_this_week", re.compile(r'\bthis\s+week\b', re.I)),
    ("since_dow",          re.compile(r'\bsince\s+(' + _DOW + r')\b', re.I)),
    ("on_dow",             re.compile(r'\bon\s+(' + _DOW + r')\b|\b(' + _DOW + r')\b', re.I)),
    ("started_dow",        re.compile(r'\bstarted\s+(?:on\s+)?(' + _DOW + r')\b', re.I)),
    ("iso_date",           re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')),
    ("month_day",          re.compile(r'\b(' + _MONTH + r')\s+(\d{1,2})(?:st|nd|rd|th)?\b', re.I)),
]


def extract_time_expressions(sentence: str) -> list[dict]:
    """
    Return list of dicts: {pattern_type, raw_expression, start, end}
    for each time expression found in the sentence.
    """
    results = []
    covered: set[tuple[int, int]] = set()

    for pattern_type, pattern in _TEMPORAL_PATTERNS:
        for m in pattern.finditer(sentence):
            start, end = m.start(), m.end()
            # Avoid overlapping spans
            if any(not (end <= cs or start >= ce) for cs, ce in covered):
                continue
            covered.add((start, end))
            results.append({
                "pattern_type": pattern_type,
                "raw_expression": m.group().strip(),
                "start": start,
                "end": end,
            })

    return sorted(results, key=lambda x: x["start"])


def _day_of_week_offset(day_name: str, reference_date: date) -> Optional[date]:
    """Return the most recent occurrence of the named day on or before reference_date."""
    target = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
               "friday": 4, "saturday": 5, "sunday": 6}.get(day_name.lower())
    if target is None:
        return None
    offset = (reference_date.weekday() - target) % 7
    return reference_date - timedelta(days=offset)


def normalize_time_expression(
    raw_expression: str,
    pattern_type: str,
    visit_date: Optional[date],
) -> Optional[str]:
    """
    Attempt to normalize a raw time expression to an ISO date string.
    Returns ISO string or None if normalization is not possible.
    """
    if visit_date is None:
        return None

    ptype = pattern_type.lower()

    if ptype == "relative_today":
        return visit_date.isoformat()

    if ptype == "relative_yesterday":
        return (visit_date - timedelta(days=1)).isoformat()

    if ptype == "relative_days_ago":
        m = re.search(r'(?:(\w+)|(\d+))\s+days?\s+ago', raw_expression, re.I)
        if m:
            word = (m.group(1) or m.group(2) or "").lower()
            n = _NUM_WORDS.get(word) or (int(word) if word.isdigit() else None)
            if n is not None:
                return (visit_date - timedelta(days=n)).isoformat()
        return None

    if ptype == "relative_weeks_ago":
        m = re.search(r'(?:(\w+)|(\d+))\s+weeks?\s+ago', raw_expression, re.I)
        if m:
            word = (m.group(1) or m.group(2) or "").lower()
            n = _NUM_WORDS.get(word) or (int(word) if word.isdigit() else None)
            if n is not None:
                return (visit_date - timedelta(weeks=n)).isoformat()
        return None

    if ptype == "relative_last_week":
        return (visit_date - timedelta(weeks=1)).isoformat()

    if ptype == "relative_this_week":
        return (visit_date - timedelta(days=visit_date.weekday())).isoformat()

    if ptype in ("since_dow", "on_dow", "started_dow"):
        m = re.search(_DOW, raw_expression, re.I)
        if m:
            result = _day_of_week_offset(m.group(), visit_date)
            if result:
                return result.isoformat()
        return None

    if ptype == "iso_date":
        try:
            return date.fromisoformat(raw_expression.strip()).isoformat()
        except ValueError:
            return None

    if ptype == "month_day":
        # Best effort: assume current year
        try:
            import datetime as _dt
            cleaned = re.sub(r'(?<=\d)(st|nd|rd|th)', '', raw_expression, flags=re.I).strip()
            for fmt in ("%B %d", "%b %d"):
                try:
                    parsed = _dt.datetime.strptime(cleaned, fmt)
                    return parsed.replace(year=visit_date.year).date().isoformat()
                except ValueError:
                    pass
        except Exception:
            pass
        return None

    return None


def annotate_mentions_with_temporal(mentions: list[dict]) -> list[dict]:
    """
    For each mention dict, find the best time expression in its sentence
    and add 'time_expression' and 'normalized_event_date' fields.
    """
    result = []
    for mention in mentions:
        sentence = mention.get("sentence", "")
        visit_date = mention.get("visit_date")

        time_exprs = extract_time_expressions(sentence)

        char_start = mention.get("char_start", 0)
        boundaries = [
            (match.start(), match.end())
            for match in re.finditer(r';| but | however | although |\n', sentence, re.IGNORECASE)
        ]
        clause_start = 0
        clause_end = len(sentence)
        for start, end in boundaries:
            if char_start < start:
                clause_end = start
                break
            clause_start = end

        clause_time_exprs = [
            expr for expr in time_exprs
            if clause_start <= expr["start"] and expr["end"] <= clause_end
        ]

        # A time expression only applies within the mention's clause.
        best_expr = None
        best_dist = float("inf")
        for te in clause_time_exprs:
            dist = abs(te["start"] - char_start)
            if dist < best_dist:
                best_dist = dist
                best_expr = te

        updated = dict(mention)
        if best_expr:
            raw = best_expr["raw_expression"]
            normalized = normalize_time_expression(raw, best_expr["pattern_type"], visit_date)
            updated["time_expression"] = raw
            updated["normalized_event_date"] = normalized
        else:
            updated["time_expression"] = None
            updated["normalized_event_date"] = None

        result.append(updated)
    return result
