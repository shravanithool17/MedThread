"""Tests for temporal expression extraction and normalization."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import date
import pytest
from medthread.temporal import (
    annotate_mentions_with_temporal,
    extract_time_expressions,
    normalize_time_expression,
)


def test_today_extracted():
    exprs = extract_time_expressions("Fever started today.")
    assert any(e["pattern_type"] == "relative_today" for e in exprs)


def test_yesterday_extracted():
    exprs = extract_time_expressions("Nausea started yesterday.")
    assert any(e["pattern_type"] == "relative_yesterday" for e in exprs)


def test_days_ago_extracted():
    exprs = extract_time_expressions("Cough started two days ago.")
    assert any(e["pattern_type"] == "relative_days_ago" for e in exprs)


def test_since_monday_extracted():
    exprs = extract_time_expressions("Fatigue since last Monday.")
    types = [e["pattern_type"] for e in exprs]
    assert any("relative_last_week" in t or "since_dow" in t or "on_dow" in t for t in types)


def test_day_of_week_extracted():
    exprs = extract_time_expressions("No fever Monday; fever started Wednesday.")
    raw_exprs = [e["raw_expression"].lower() for e in exprs]
    assert any("monday" in r for r in raw_exprs)
    assert any("wednesday" in r for r in raw_exprs)


def test_today_normalization():
    ref = date(2024, 1, 22)
    result = normalize_time_expression("today", "relative_today", ref)
    assert result == "2024-01-22"


def test_yesterday_normalization():
    ref = date(2024, 1, 22)
    result = normalize_time_expression("yesterday", "relative_yesterday", ref)
    assert result == "2024-01-21"


def test_two_days_ago_normalization():
    ref = date(2024, 1, 22)
    result = normalize_time_expression("two days ago", "relative_days_ago", ref)
    assert result == "2024-01-20"


def test_no_crash_on_empty():
    exprs = extract_time_expressions("")
    assert exprs == []


def test_no_crash_unknown_expression():
    result = normalize_time_expression("some weird expression", "unknown_type", date(2024, 1, 1))
    assert result is None


def test_no_normalization_without_visit_date():
    result = normalize_time_expression("yesterday", "relative_yesterday", None)
    assert result is None


def test_iso_date_extracted():
    exprs = extract_time_expressions("Patient seen on 2024-03-15.")
    assert any(e["pattern_type"] == "iso_date" for e in exprs)


def test_iso_date_normalized():
    result = normalize_time_expression("2024-03-15", "iso_date", date(2024, 3, 20))
    assert result == "2024-03-15"


def test_invalid_iso_date_is_not_normalized():
    result = normalize_time_expression("2024-99-99", "iso_date", date(2024, 3, 20))
    assert result is None


def test_mentions_use_time_expression_from_their_own_clause():
    sentence = "No fever Monday; fever started Wednesday."
    mentions = [
        {
            "sentence": sentence,
            "visit_date": date(2024, 1, 10),
            "char_start": 3,
        },
        {
            "sentence": sentence,
            "visit_date": date(2024, 1, 10),
            "char_start": 17,
        },
    ]

    annotated = annotate_mentions_with_temporal(mentions)

    assert [mention["time_expression"] for mention in annotated] == [
        "Monday",
        "Wednesday",
    ]
    assert [mention["normalized_event_date"] for mention in annotated] == [
        "2024-01-08",
        "2024-01-10",
    ]
