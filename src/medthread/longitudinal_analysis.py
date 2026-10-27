"""Cross-visit longitudinal consistency analysis.

Groups mentions by (patient_id, entity_normalized), sorts by visit_date,
and applies conservative deterministic rules to produce a ComparisonResult.

Rules:
  1. Only one mention across all notes → newly_reported (if affirmed/uncertain)
     or explicitly_negated (if negated) or explicitly_resolved (if resolved).
  2. Consistently affirmed across visits → persistent_documented.
  3. Affirmed in early visit, then explicitly resolved/negated in later visit → explicitly_resolved/explicitly_negated.
  4. Earlier note says affirmed/certain; later note says negated, OR
     both notes reference the SAME day/time context with conflicting claims → possible_inconsistency.
  5. Temporal change (e.g., "no fever Monday" then "fever started Wednesday") is NOT a contradiction.
  6. Uncertain mentions → does not count as confirmed positive.
  7. Missing from a later note → not_documented (NOT resolved).
  8. Conflicting or ambiguous dates → unclear.
  9. Never compare across different patient_ids.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from .schemas import ComparisonResult


def _safe_date(val) -> Optional[date]:
    if isinstance(val, date):
        return val
    return None


def _can_compare_temporally(
    note_date_a: Optional[date],
    note_date_b: Optional[date],
    event_date_a: Optional[str],
    event_date_b: Optional[str],
) -> tuple[bool, str]:
    """
    Determine whether two mentions might refer to the same time frame.
    Returns (can_compare, reason).

    Two mentions can be compared if:
    - They have overlapping or same normalized event dates, OR
    - Neither has a normalized event date (so time context is unspecified).
    They SHOULD NOT be compared if they clearly refer to different days.
    """
    if event_date_a and event_date_b:
        if event_date_a == event_date_b:
            return True, f"Both mentions explicitly reference the same date ({event_date_a})."
        else:
            return False, (
                f"Different temporal contexts: '{event_date_a}' vs '{event_date_b}'. "
                "This is a temporal change, not necessarily a contradiction."
            )
    # One or both lack a normalized event date → cannot rule out overlap → compare cautiously
    return True, "No conflicting temporal context — mentions may refer to overlapping periods."


def analyze_patient_entity(
    patient_id: str,
    entity: str,
    mentions: list[dict],  # pre-sorted or to be sorted by visit_date
) -> ComparisonResult:
    """
    Produce a ComparisonResult for one (patient_id, entity) group.
    mentions: list of annotated mention dicts (already filtered to this patient+entity).
    """
    # Sort by visit_date (None dates go last)
    def sort_key(m):
        d = _safe_date(m.get("visit_date"))
        return (0, d) if d else (1, date.max)

    sorted_mentions = sorted(mentions, key=sort_key)

    note_ids = [m["note_id"] for m in sorted_mentions]
    sentences = [m["sentence"] for m in sorted_mentions]
    contexts = [m["context"] for m in sorted_mentions]
    event_dates = [m.get("normalized_event_date") for m in sorted_mentions]
    visit_dates = [_safe_date(m.get("visit_date")) for m in sorted_mentions]
    reasons = [m.get("reason", "") for m in sorted_mentions]

    n = len(sorted_mentions)

    # Single mention
    if n == 1:
        m = sorted_mentions[0]
        ctx = contexts[0]
        if ctx == "negated":
            return ComparisonResult(
                patient_id=patient_id,
                entity=entity,
                status="explicitly_negated",
                evidence_note_ids=note_ids,
                evidence_sentences=sentences,
                explanation=f"Single note documents '{entity}' as negated.",
                rule_trace=f"Rule: single_negated. Context reason: {reasons[0]}",
            )
        if ctx == "resolved":
            return ComparisonResult(
                patient_id=patient_id,
                entity=entity,
                status="explicitly_resolved",
                evidence_note_ids=note_ids,
                evidence_sentences=sentences,
                explanation=f"Single note documents '{entity}' as resolved.",
                rule_trace=f"Rule: single_resolved. Context reason: {reasons[0]}",
            )
        if ctx == "uncertain":
            return ComparisonResult(
                patient_id=patient_id,
                entity=entity,
                status="unclear",
                evidence_note_ids=note_ids,
                evidence_sentences=sentences,
                explanation=f"Single note mentions '{entity}' with uncertainty — no confirmed diagnosis.",
                rule_trace=f"Rule: single_uncertain. Context reason: {reasons[0]}",
            )
        # affirmed or unclear → newly_reported
        return ComparisonResult(
            patient_id=patient_id,
            entity=entity,
            status="newly_reported",
            evidence_note_ids=note_ids,
            evidence_sentences=sentences,
            explanation=f"'{entity}' first documented in note {note_ids[0]}. Newly reported in record (not necessarily true onset).",
            rule_trace=f"Rule: single_affirmed_newly_reported. Context reason: {reasons[0]}",
        )

    # Multiple mentions — build context summary
    affirmed_indices = [i for i, c in enumerate(contexts) if c in ("affirmed",)]
    negated_indices  = [i for i, c in enumerate(contexts) if c == "negated"]
    resolved_indices = [i for i, c in enumerate(contexts) if c == "resolved"]
    uncertain_indices = [i for i, c in enumerate(contexts) if c == "uncertain"]

    # Check for explicit resolution in later note
    if affirmed_indices and resolved_indices:
        later_resolved_indices = [
            resolved_index
            for resolved_index in resolved_indices
            if any(
                visit_dates[affirmed_index] is not None
                and visit_dates[resolved_index] is not None
                and visit_dates[resolved_index] > visit_dates[affirmed_index]
                for affirmed_index in affirmed_indices
            )
        ]
        if later_resolved_indices:
            last_resolved = max(later_resolved_indices)
            return ComparisonResult(
                patient_id=patient_id,
                entity=entity,
                status="explicitly_resolved",
                evidence_note_ids=note_ids,
                evidence_sentences=sentences,
                explanation=(
                    f"'{entity}' was affirmed in note(s) "
                    f"{[note_ids[i] for i in affirmed_indices]} "
                    f"and later resolved in note {note_ids[last_resolved]}."
                ),
                rule_trace="Rule: affirmed_then_resolved. Textual evidence of resolution found.",
            )

    # Check for possible inconsistency: affirmed in one note, negated in another
    if affirmed_indices and negated_indices:
        # Check temporal comparability for each pair
        inconsistencies = []
        temporal_changes = []
        for ai in affirmed_indices:
            for ni in negated_indices:
                can_compare, temp_reason = _can_compare_temporally(
                    visit_dates[ai], visit_dates[ni],
                    event_dates[ai], event_dates[ni],
                )
                if can_compare:
                    inconsistencies.append((ai, ni, temp_reason))
                else:
                    temporal_changes.append((ai, ni, temp_reason))

        if inconsistencies:
            idx_pairs = [(note_ids[ai], note_ids[ni]) for ai, ni, _ in inconsistencies]
            temp_reason = inconsistencies[0][2]
            return ComparisonResult(
                patient_id=patient_id,
                entity=entity,
                status="possible_inconsistency",
                evidence_note_ids=note_ids,
                evidence_sentences=sentences,
                explanation=(
                    f"'{entity}' is documented as affirmed in some notes and negated in others "
                    f"with possibly overlapping time context. Pairs: {idx_pairs}. "
                    "Requires human review."
                ),
                rule_trace=(
                    f"Rule: affirmed_vs_negated_same_context. Temporal analysis: {temp_reason}. "
                    f"Affirmed in: {[note_ids[i] for i in affirmed_indices]}. "
                    f"Negated in: {[note_ids[i] for i in negated_indices]}."
                ),
            )
        elif temporal_changes:
            # Only temporal changes — not a contradiction
            tc_reason = temporal_changes[0][2]
            return ComparisonResult(
                patient_id=patient_id,
                entity=entity,
                status="unclear",
                evidence_note_ids=note_ids,
                evidence_sentences=sentences,
                explanation=(
                    f"'{entity}' is documented as affirmed and negated in different notes, "
                    f"but temporal expressions suggest different time periods. {tc_reason}"
                ),
                rule_trace=(
                    f"Rule: temporal_change_not_contradiction. {tc_reason}"
                ),
            )

    # All affirmed (possibly across multiple notes) → persistent_documented
    if set(contexts) <= {"affirmed"} and n > 1:
        return ComparisonResult(
            patient_id=patient_id,
            entity=entity,
            status="persistent_documented",
            evidence_note_ids=note_ids,
            evidence_sentences=sentences,
            explanation=f"'{entity}' affirmed across {n} notes — persistently documented.",
            rule_trace=f"Rule: all_affirmed_persistent. Notes: {note_ids}.",
        )

    # All negated → explicitly_negated
    if set(contexts) <= {"negated"} and n > 1:
        return ComparisonResult(
            patient_id=patient_id,
            entity=entity,
            status="explicitly_negated",
            evidence_note_ids=note_ids,
            evidence_sentences=sentences,
            explanation=f"'{entity}' consistently negated across {n} notes.",
            rule_trace=f"Rule: all_negated. Notes: {note_ids}.",
        )

    # Uncertain mentions mixed with other contexts
    if uncertain_indices and not affirmed_indices and not negated_indices:
        return ComparisonResult(
            patient_id=patient_id,
            entity=entity,
            status="unclear",
            evidence_note_ids=note_ids,
            evidence_sentences=sentences,
            explanation=f"'{entity}' only mentioned with uncertainty — no confirmed status.",
            rule_trace=f"Rule: only_uncertain. Notes: {note_ids}.",
        )

    # Mixed contexts without clear contradiction
    context_summary = ", ".join(f"{note_ids[i]}:{contexts[i]}" for i in range(n))
    return ComparisonResult(
        patient_id=patient_id,
        entity=entity,
        status="unclear",
        evidence_note_ids=note_ids,
        evidence_sentences=sentences,
        explanation=f"'{entity}' has mixed or complex context across notes. Manual review recommended.",
        rule_trace=f"Rule: mixed_context_unclear. Context per note: {context_summary}.",
    )


def run_longitudinal_analysis(annotated_mentions: list[dict]) -> list[ComparisonResult]:
    """
    Group mentions by (patient_id, entity_normalized) and analyze each group.
    Patient IDs are NEVER mixed across groups.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for mention in annotated_mentions:
        key = (mention["patient_id"], mention["entity_normalized"])
        groups.setdefault(key, []).append(mention)

    results = []
    for (patient_id, entity), mentions in groups.items():
        result = analyze_patient_entity(patient_id, entity, mentions)
        results.append(result)

    return results
