# MedThread Project Report

**Title:** MedThread — Explainable Longitudinal Clinical Text Mining and Consistency Analysis  
**Project type:** Educational software prototype  
**Benchmark version:** 0.1.0  
**Data:** Synthetic only

## Abstract

MedThread is a local React/Vite/TypeScript application backed by FastAPI and a modular Python NLP pipeline. It accepts clinical-note text, extracts lexicon concepts, classifies mention context, associates limited temporal expressions, and compares evidence within each patient. Results are traceable to notes and sentences and are intended for human review, not clinical use. The bundled evaluation set contains a small, partial set of project-authored context examples over synthetic notes. It is not independently reviewed or exhaustive. Therefore context-label metrics are limited to source-aligned examples, entity recall is reported only over eligible annotations, extraction precision/F1 are unavailable, and temporal/longitudinal metrics are not reported. There is no fitted ML model or held-out test split.

## 1. Problem and objectives

Clinical notes are unstructured and can document symptoms at different times, with negation, uncertainty, resolution, and missing documentation. MedThread demonstrates a modular approach to:

1. Validate and import structured note records.
2. Detect configured symptom/condition terms and retain their original source evidence.
3. Assign conservative text-context labels.
4. Associate limited time expressions with note dates.
5. Compare notes only within the same patient and flag rule-based cases for review.
6. Expose concept counts, note-level co-occurrence, and evaluation evidence without implying clinical conclusions.

The application does not diagnose, recommend treatment, establish patient status, or establish that a chart entry is clinically wrong.

## 2. System architecture and method

The React/Vite frontend calls FastAPI endpoints. FastAPI validates imports and invokes the shared modules under `src/medthread/`. The pipeline sequence is preprocessing and sentence splitting, lexicon extraction, context rules, temporal phrase extraction, then longitudinal grouping by `(patient_id, entity_normalized)`. Patient Journey, consistency review, concept exploration, exports, and Evaluation Studio display actual active-dataset API results. Note text is rendered as React text rather than injected markup.

The FastAPI application persists the active source notes and dataset metadata in
SQLite at `.medthread/medthread.sqlite3` by default; `MEDTHREAD_DB_PATH` may
select another local database file. On restart, the application restores the
notes and recomputes NLP outputs rather than persisting stale derived results.
Reviewer decisions, optional rationale, UTC timestamps, and decision-event
history are also stored per browser-session identifier and review key. Replacing
or resetting the dataset clears review decisions. The legacy Streamlit entry
point remains available and retains its separate session-state behavior.
SQLite contains plaintext source note text. The prototype does not encrypt data,
provide multi-user database guarantees, or offer clinical security controls.
Do not upload real patient or protected health information.

Extraction currently uses configured aliases with word-boundary regex matching, or spaCy PhraseMatcher when available. Overlapping matches are filtered longest-first. Context rules are clause-scoped and return one of `affirmed`, `negated`, `uncertain`, `resolved`, or `unclear`. Improvement language is not treated as explicit resolution; explicit “no longer” language is. Temporal parsing is best effort. Longitudinal rules never compare different patient IDs. Undocumented symptoms are not treated as absent or resolved.

Mention spans are exposed as zero-based, half-open Unicode code-point offsets
into the original note. Backend validation confirms the exact source substring;
the React text renderer converts these offsets to JavaScript UTF-16 indices for
highlighting. If a span cannot be verified, it is not highlighted or linked as
an exact span.

These are deterministic rules, not a trained model. Their output is evidence for review, not verified medical truth.

Consistency records keep the automated rule status and reviewer conclusion as
separate fields. The evidence view presents the rule trace and source notes,
dates, exact source sentences, validated mention spans, contexts, and
normalized event-date comparison when available. It reports elapsed time only
when both comparable normalized event dates exist; note visit dates are not
used as substitutes. A date-less or unparseable event time is shown as
unavailable, not inferred. Review rationale and history are scoped by the
existing browser-session identifier and stored in SQLite; another browser
session does not inherit those decisions. These annotations do not modify
clinical records.

## 3. Dataset and annotation protocol

The bundled source file contains 15 synthetic notes grouped under five synthetic patient IDs. The context annotation CSV contains 60 project-authored examples. No real patient records are included. Benchmark identity, schema, provenance, coverage, and status are recorded in [../data/benchmark_metadata.json](../data/benchmark_metadata.json) and [../data/annotation_schema.json](../data/annotation_schema.json); label guidance is in [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md).

The annotation status is **author-annotated, not independently reviewed**. The labels are not exhaustive over the corpus and do not include entity offsets, complete negative/none-of-target spans, temporal gold labels, or longitudinal case labels. A current row is aligned by note ID, canonical entity, and punctuation-insensitive sentence tokens. Gold examples with an exact aligned prediction are used for context classification. Unmatched gold examples are tracked separately; prediction examples without matching gold are unscorable, not false positives. Source rows that do not match an active source note are listed as exclusions.

No values in this report should be interpreted as clinical performance or independently adjudicated gold quality.

Duplicate annotation judgments are checked during loading. Repeated equivalent
rows with the same label are deduplicated and reported as a warning; conflicting
labels for the same note/entity/source sentence are excluded and reported,
rather than selected arbitrarily.

## 4. Evaluation methodology

### Context classification

For matched mentions only, the five context labels use a fixed order: affirmed, negated, uncertain, resolved, unclear. Precision, recall, F1, accuracy, per-class support, macro/weighted aggregates, and the confusion matrix are computed with zero-division set to zero. Missing gold mentions are excluded from context-classification scores and reported as extraction misses. Punctuation differences are ignored for source-sentence alignment; entity canonical label and note ID must still match.

### Entity extraction coverage

Eligible annotated-example recall is matched gold examples divided by eligible gold examples (matched plus actual missed extraction). Precision and F1 are deliberately null: the annotations are not exhaustive, so unmatched model outputs cannot be treated as false positives. Predictions without a gold match are reported with reason codes such as `no_gold_for_note_entity` or `sentence_alignment_mismatch`.

Exact-span extraction metrics are a separate measure and require valid
zero-based half-open source-text offsets for every gold occurrence plus an
explicitly exhaustive set of source note IDs. Matching uses note ID, exact
start/end offsets, and canonical concept. Repeated mentions are counted by
their distinct spans. Invalid or conflicting offsets and missing notes are
reported as exclusions or make the span metrics unavailable; no predicted
offset is used to repair gold. The active metadata declares
`entity_exhaustive_note_ids: []`, and the annotation CSV contains no entity
offsets, so exact-span precision/recall/F1 remain unavailable.

### Temporal and longitudinal tasks

No temporal or longitudinal gold labels are present. Those metrics are not available. Rule traces and temporal outputs in the UI are not measured evaluation results.

### Splits and leakage

There is no training, validation, or test split because the system does not fit an ML model. The same small corpus is used only for development-time rule checks. Scores are not held-out estimates. Any future model experiment must split by patient/case group before fitting vectorizers or other preprocessing, keep the test set untouched during tuning, and report group counts and class supports.

## 5. Observed results

Recomputed from `GET /api/evaluation/demo` on 2026-10-28 using benchmark `medthread-synthetic-context-v1` v0.1.0:

- 60 raw context annotation rows; one is excluded because `NOTE_013` labels `cough` in “Patient denies all symptoms.” without a cough surface form. The other 59 eligible examples align; there are no extraction misses or context-confusion errors. The source annotation remains unchanged.
- 59 context-classification samples. Computed accuracy was 1.000; macro precision/recall/F1 were 0.800/0.800/0.800 using all five fixed labels (the `unclear` class has zero support); weighted precision/recall/F1 were 1.000/1.000/1.000.
- Per-class results (precision / recall / F1 / support) were: affirmed 1.000 / 1.000 / 1.000 / 25; negated 1.000 / 1.000 / 1.000 / 23; uncertain 1.000 / 1.000 / 1.000 / 4; resolved 1.000 / 1.000 / 1.000 / 7; unclear 0.000 / 0.000 / 0.000 / 0.
- The fixed five-label macro average is 0.800 because `unclear` has no support and zero-division is set to zero; its per-class scores contribute zero to the unweighted mean. Weighted F1 is 1.000 because each of the 59 supported examples is in one of the four perfectly scored classes, while the zero-support class has zero weight. This difference is a label-support/evaluation-policy effect, not evidence that the benchmark is representative.
- The confusion matrix (rows = gold, columns = predicted; order: affirmed, negated, uncertain, resolved, unclear) was `[[25,0,0,0,0],[0,23,0,0,0],[0,0,4,0,0],[0,0,0,7,0],[0,0,0,0,0]]`. The implementation uses zero for undefined class precision/recall/F1.
- Annotated-example entity recall was 1.000 over 59 eligible examples. Entity precision and F1 were not computed because annotation coverage is partial.
- Eight predicted mentions had no matching note/entity gold row and were reported unscorable, not false positives. There were no sentence-alignment mismatches or ambiguous repeated-mention alignments among these predictions.
- No scored context errors were returned. Temporal and longitudinal metrics were unavailable because there are no gold labels for those tasks.
- Exact-span entity metrics were unavailable: the benchmark has no entity offsets and declares no exhaustively annotated note IDs. The evaluator does not convert the eight unmatched predictions into false positives.

These are descriptive results on a small synthetic development set with author annotations that are not independently reviewed. They are not held-out estimates, do not measure extraction precision, and do not establish clinical validity. A current run may be captured in [RESULTS_TEMPLATE.md](RESULTS_TEMPLATE.md).

No accuracy claim, clinical validity claim, or comparison against an ML baseline is made in this report. Unit fixtures use hand-calculated examples to verify metric arithmetic; they are not benchmark observations.

## 6. Error analysis and safeguards

Each scored error example includes note ID, canonical concept, expected context, predicted context, exact source sentence, and an error category. The UI links the note ID to Note Explorer. A missed extraction is distinct from a context confusion. Predictions not supported by exhaustive annotation coverage are displayed as unscorable rather than false positives.

Regression cases cover negation scope, separate contexts in one sentence, uncertainty, explicit resolution, partial improvement, unresolved symptoms, temporal change, punctuation-tolerant alignment, and patient isolation. Note-level concept co-occurrence is descriptive only and does not imply causation, diagnosis, prevalence, or clinical relationship.

## 7. Ethics, privacy, and limitations

- Synthetic results do not establish clinical validity or real-world performance.
- The synthetic gold set is small, partial, project-authored, and not independently reviewed.
- Entity extraction precision/F1, temporal scores, and longitudinal scores are unavailable.
- Exact-span entity precision/recall/F1 also require a nonempty, complete exhaustive-note scope with valid gold offsets; that requirement is not met by this benchmark.
- There is no patient-group held-out split or ML baseline.
- Rule-based extraction is limited by the configured lexicon; unseen aliases can be missed.
- Context scope and date normalization are heuristic and can fail on complex prose.
- “Unclear” and temporal ambiguity require human interpretation.
- The FastAPI local SQLite database is unencrypted and single-process; this prototype provides no clinical security guarantees. The legacy Streamlit entry point uses separate session state.
- Only synthetic or authorized, properly de-identified text should be used in a controlled local environment.

## 8. Conclusion and future work

MedThread provides an inspectable end-to-end software pipeline with note import, source-linked evidence, patient isolation, reviewer annotations, concept exploration, and explicitly bounded evaluation. The next credible research step is not score tuning: it is an exhaustive, independently reviewed, source-offset benchmark that includes negative/non-target spans, temporal labels, longitudinal cases, and patient-group splits. Only then should extraction precision/F1 or held-out temporal/longitudinal metrics be reported. A lightweight ML baseline is deferred because the current benchmark is too small, partial, and not group-split.

## References

See [RELATED_WORK.md](RELATED_WORK.md) for a scoped, verified bibliography and a statement of the literature-search limitations. No novelty or “first of its kind” claim is made.
