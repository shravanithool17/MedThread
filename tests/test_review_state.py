"""Tests for review-state identity keys."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from medthread.schemas import review_state_key


def test_review_state_keys_do_not_collide_on_underscores():
    first = review_state_key("patient_a", "fever")
    second = review_state_key("patient", "a_fever")

    assert first != second


def test_review_state_key_is_stable_for_same_identity():
    assert review_state_key("patient-1", "fever") == review_state_key("patient-1", "fever")
