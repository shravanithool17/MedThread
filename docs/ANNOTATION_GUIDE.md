# MedThread Annotation Guide

## Status and scope

`data/gold_annotations.csv` is the project-authored context-example set for the synthetic demo. Its annotation status is **not independently reviewed**. The file contains context-labeled examples, not exhaustive annotation of every target concept in every sentence. It is not a held-out test set. Do not call unmatched predictions false positives or report extraction precision/F1 from this file.

The corresponding machine-readable row schema is [../data/annotation_schema.json](../data/annotation_schema.json); benchmark provenance and coverage are in [../data/benchmark_metadata.json](../data/benchmark_metadata.json).

## Current CSV schema

| Field | Required | Definition |
|---|---:|---|
| `note_id` | yes | Unique synthetic source note ID |
| `sentence` | yes | Exact or punctuation-normalized source evidence sentence |
| `entity_normalized` | yes | Canonical concept from the configured lexicon |
| `context` | yes | One of the five context labels below |
| `notes` | no | Rationale for the current label |

One row means one concept/context judgment tied to one source sentence. A sentence may have multiple rows when multiple target concepts occur or context differs by concept. Note IDs resolve to patient and date through the source note dataset.

At load time, judgments are keyed by note ID, canonical entity, and a
punctuation/whitespace-normalized sentence. Repeated equivalent rows with the
same context are deduplicated and surfaced as a warning. If duplicate rows for
that key disagree on context, every row in that conflicting group is excluded
and reported; the evaluator does not select a label arbitrarily.

## Exact-span extraction evaluation

`entity_start` and `entity_end` are optional for the existing context-example
benchmark. When provided, both must be integer, zero-based, half-open Unicode
code-point offsets into the exact original note text. The substring must match
an alias of `entity_normalized` and fall within the annotated source sentence.
Offsets are not UTF-16 indices and must not be measured against normalized or
preprocessed text.

Exact-span precision, recall, and F1 are reported only when benchmark metadata
declares the complete set of exhaustively annotated `entity_exhaustive_note_ids`,
all those source notes are available, and every gold entity occurrence in that
scope has a valid canonical label and exact span. The declared scope must
include notes (or complete note text) with no target concepts, so predictions
inside the scope can validly count as false positives. Occurrences repeated in
one note are separate gold rows with distinct offsets. Same-span duplicate rows
are deduplicated with a warning; conflicting canonical concepts at one span
invalidate exact-span scoring. Missing offsets, invalid offsets, incomplete
scope, or unavailable notes make these metrics unavailable; do not infer spans
from system predictions.

The current benchmark declares an empty exhaustive scope and has no entity
offset columns. Therefore extraction precision, recall, and F1 are unavailable
for it. Its partial context rows support only the separately reported
source-aligned context/example analysis. Predictions not matched to those
partial rows remain unscorable, not false positives.

The CSV has 60 raw rows; evaluation skips one because `NOTE_013` labels
`cough` in “Patient denies all symptoms.” without a cough surface form in the
sentence. This is an annotation/evidence-alignment gap, not a prediction to
repair automatically. The gold row is unchanged; evaluation warns and scores
the other 59 eligible examples.

## Context definitions

| Label | Use when | Example |
|---|---|---|
| `affirmed` | Text asserts a current or ongoing symptom, including partial improvement that does not explicitly say it ended | “Patient has fever.” / “Fatigue is better.” |
| `negated` | Text explicitly denies a symptom in the stated time context | “Patient has no fever.” |
| `uncertain` | Text hedges, suspects, or cannot establish the finding | “Possible infection.” |
| `resolved` | Text explicitly states that a previously described symptom ended | “Fever has resolved.” / “No longer has a cough.” |
| `unclear` | Evidence is ambiguous, conflicting, or insufficient for the other labels | Use only with a rationale; do not infer from silence |

These are textual assertions, not diagnoses or claims about a patient's actual condition.

## Temporal and longitudinal distinctions

- **Historical** evidence describes an earlier period; it is not automatically current.
- **Newly documented** means a concept appears in this record at this point. It does not prove biological onset.
- **Explicit onset** requires onset language such as “started today”; first chart appearance alone is insufficient.
- **Explicit resolution** requires resolution language. Improvement (“better”, “improved”) is not by itself resolution.
- **Temporal change** records different dates or time intervals and is not automatically a contradiction.
- **Potential contradiction** requires incompatible affirmations for the same patient and comparable time context. It remains a review signal, not a conclusion.
- **Missing documentation** is distinct from negation and resolution.
- **Different patients** must never be compared. Patient identity is part of every longitudinal grouping key.

The current benchmark does not include gold temporal labels or longitudinal case labels; those metrics are unavailable.

## Annotation edge-case instructions

1. Annotate multiple concepts independently. For “Denies cough but reports fever”, label cough `negated` and fever `affirmed`.
2. Keep negation within its grammatical scope. In “No fever, but reports cough”, fever is `negated`, cough is `affirmed`.
3. Do not negate a later independent clause: “No fever; patient has cough.”
4. Do not turn uncertainty into affirmation: “Possible infection” is `uncertain`.
5. Explicit endings are `resolved`; partial improvement is not resolution.
6. Preserve relative date language and use a normalized ISO date only when the reference date and phrase resolve unambiguously.
7. Leave unresolved or ambiguous temporal interpretation null/ambiguous; never invent a date.
8. A sentence with no target concepts must be included only in an explicitly exhaustive benchmark with a documented annotation-coverage boundary. The current context-example CSV has no such coverage declaration.
9. Keep “not mentioned” distinct from “negated”, “resolved”, and “not applicable”.
10. Record rationale and annotation status. Mark an example `draft`, `reviewed`, or `adjudicated`; do not call it reviewed unless a second qualified annotator has checked it.

## Future exhaustive benchmark format

Before measuring entity false positives, annotate all target entity spans (including negative sentences and sentences with no targets) in a declared note/case scope. Add inclusive/exclusive offsets (`entity_start`, `entity_end`), exhaustive-coverage declaration, annotation status, rationale, and patient/case group IDs. Independently review and adjudicate labels. Split cases by patient/group before any learned model is trained or any holdout score is reported. The current demo annotations must not be silently relabeled or treated as exhaustive.

For temporal/longitudinal evaluation, add independently reviewed gold labels
for event-time interpretation and pair/case outcomes, including explicit
resolution, temporal change, missing documentation, potential contradiction,
uncertainty, and not-comparable cases. Retain the source note IDs, exact
evidence sentences/spans, reference date, normalized event date (or an explicit
unknown/ambiguous value), and annotation rationale. Visit dates are metadata
and cannot substitute for an event date.

## Provenance and limitations

The bundled source notes are synthetic and project-authored. No real patient records are included. Independent clinical annotation, inter-annotator agreement, and adjudication are not documented. The current set is small and intended for software regression and example-level development checks, not clinical performance estimation.
