# Implementation Plan — Persistence, Evidence and Evaluation

## Baseline audit (2026-10-27)

MedThread is a React/Vite/TypeScript frontend, FastAPI backend, and shared
`src/medthread/` Python NLP package. The legacy Streamlit entry point remains in
`app.py` and `pages/`. Note input is validated in the backend, passed through
preprocessing, entity extraction, context detection, temporal annotation, and
longitudinal analysis, then serialized by FastAPI for the React pages.

The current note corpus and derived DataFrames are held in a process-global
`AppState`. Startup unconditionally reloads the synthetic demo; imported notes
are lost after process restart. Review decisions are an in-memory mapping keyed
by browser-session ID and patient/concept. Mentions and review evidence are
derived from source notes. Context evaluation uses partial project-authored
synthetic labels; extraction precision/F1 and temporal/longitudinal metrics are
not available.

Baseline checks before these changes:

- `python -m pytest tests -q` — 141 passed.
- `Set-Location frontend; npm run build` — succeeded.

## Existing functionality to preserve

- React routes: Import Notes, Patient Journey, Note Explorer, Consistency,
  Medical Concept Explorer, and Evaluation.
- FastAPI CSV/JSON preview and import, existing NLP processing and exports.
- Shared Python pipeline and legacy Streamlit app.
- Session-keyed review decisions and patient-scoped comparisons.
- Synthetic data remains available through the restore-demo action.

## Identified gaps

1. Active notes and reviewer decisions disappear on backend restart.
2. Startup always replaces the active dataset with demo data.
3. Review decisions have no rationale, timestamp, or audit trail.
4. Evidence offsets are Python Unicode code-point offsets, but JavaScript
   string slices use UTF-16 code units; an astral Unicode character before a
   mention can therefore misalign a highlight.
5. Timeline and review links select source notes, but do not yet identify a
   precise mention span or preserve a direct return to the selected patient.
6. Gold annotations are partial, with no exhaustive entity coverage or offsets;
   no extraction precision/F1 or temporal/longitudinal scores are justified.

## Proposed implementation

### Persistence

- Add a small standard-library SQLite store; no ORM or second NLP/storage stack.
- Default database path is repository-local `.medthread/medthread.sqlite3`;
  `MEDTHREAD_DB_PATH` overrides it.
- Store source notes and dataset metadata separately from derived NLP output.
  Recompute mentions/comparisons on startup from the saved note text.
- Store current reviewer decision, rationale, timestamp, and append-only
  decision events, scoped by existing browser-session ID and review key.
- Use an idempotent schema initialization/version table, transactions, SQLite
  foreign-key checking, and ignore local database files in Git.
- Seed the synthetic corpus only on a fresh database. Explicit demo restore
  replaces the active corpus. Explicit reset persists an empty state.
- Isolate tests with a unique temporary database path.

### Evidence and review

- Define spans as zero-based, half-open Unicode code-point offsets into the
  exact original note text. Convert to UTF-16 indices only at the JavaScript
  rendering boundary.
- Validate spans before rendering; expose unavailable/invalid reference
  fallbacks rather than fabricating a span.
- Add direct links from journey events/review evidence to the exact note and
  mention; allow returning to the same patient's timeline.
- Add optional reviewer rationale and saved timestamp; keep automated flag
  state separate from human review state.

### Evaluation

- Detect duplicate gold judgments and report them explicitly.
- Verify source-note alignment and preserve partial coverage semantics.
- Keep unmatched predictions unscorable outside exhaustive annotation.
- Do not add made-up gold labels, extraction metrics, or unavailable temporal
  and longitudinal metrics.

## Implementation sequence

1. Audit repository and capture passing baseline (complete).
2. Implement SQLite schema/store, restart-safe loading, and persistence tests.
3. Add Unicode-safe offset conversion and exact evidence navigation.
4. Persist reviewer rationale/timestamp/audit events and update UI/API types.
5. Harden gold annotation validation and retain honest metric availability.
6. Update README, architecture/project/reproducibility/annotation/demo docs.
7. Run focused tests, full backend suite, frontend production build, and a
   restart/import/evidence/review workflow check.

## Risks and compatibility

- SQLite is for a single-user/local prototype; it is not a multi-user database
  or a substitute for clinical security controls.
- Existing API fields remain; added response fields are additive. Review update
  accepts the existing state plus an optional rationale.
- Replacing the active dataset clears review decisions as the current
  application already does. Normal backend restart must not clear them.
- Unicode offset conversion must be verified for ASCII, BMP Unicode, and
  supplementary-plane characters.
- Gold annotation edits must never be driven by system predictions.

## Final status

- SQLite persistence and startup restore are implemented. Dataset replacement
  and reset are transactional; a persisted empty dataset does not reseed demo.
- Review decisions, rationale, timestamps, and append-only history are
  persisted per browser-session ID. The API/UI expose the history, and CSV
  exports include the saved review fields.
- Mention offsets are validated against original source text using Unicode
  code points; the React renderer maps only requested spans to UTF-16 indices.
  Timeline and review links open exact validated spans where available and
  retain the patient/visit return path.
- Duplicate gold judgments are checked during loading: same-label repeats are
  deduplicated and warned about; conflicting labels are excluded and warned
  about. Gold data itself was not changed.
- Added restart, transactional rollback, empty-reset, rationale/history,
  Unicode source-offset, and duplicate-annotation tests.
- Validation on 2026-10-27: `python -m pytest tests -q` — 150 passed;
  `Set-Location frontend; npm run build` — succeeded; `git diff --check` —
  clean (Git only reported its normal LF-to-CRLF notices).

Remaining limitations: SQLite is local plaintext storage intended for this
single-process prototype, not a secure or multi-user clinical database.
Reviewer identity is the existing browser-tab session ID. Source-note text is
persisted, but derived NLP results are recomputed. Gold annotations remain
partial and synthetic; extraction precision/F1 and temporal/longitudinal
metrics remain unavailable. No clinical validation is implied.

## Explainability and reliable gold-evaluation phase

### Audit findings

- Candidate flags already carried rule traces, explanations, source sentences,
  dates, contexts, temporal phrases, and mention offsets where available. The
  missing explanation was a pairwise statement of whether normalized event
  dates were comparable and, only when they were, their elapsed days.
- Reviewer decisions are not part of the automated status. They remain keyed
  by the supplied browser-session identifier and review key; SQLite durability
  does not make one session's choices visible to another session.
- The gold CSV is a partial context-example set with no entity offsets. Its
  metadata declares an empty exhaustive-note scope. The eight unmatched
  predictions are unscorable rather than false positives.
- Of the 60 raw gold rows, the loader skips one invalid source alignment:
  `NOTE_013` assigns `cough` to “Patient denies all symptoms.”, which contains
  no canonical cough surface form. The gold file remains unchanged.
- No temporal or longitudinal gold labels exist, so those evaluation metrics
  cannot be calculated.

### Implemented

- Added pairwise temporal evidence to review responses and the investigator
  view. Event-date equality/difference and day intervals are shown only when
  both event dates are valid; visit metadata is not substituted.
- Kept reviewer conclusions/rationale separate from automated rules and
  documented session scope and prototype-only annotation semantics.
- Hardened gold validation for valid canonical concepts, source surface forms,
  exact offsets, sentence membership, duplicate spans, and conflicting spans.
- Added exact-span precision/recall/F1 calculation, gated by explicit
  exhaustive-note metadata and exact source text. The current benchmark reports
  these metrics as unavailable; no gold labels or offsets were fabricated.
- Recomputed demo results: 59 eligible aligned context examples; all four
  supported classes score 1.000, while zero-support `unclear` scores 0.000
  under zero-division handling. Macro F1 is 0.800 and weighted F1 is 1.000.
  Eight predictions have no note/entity gold row and remain unscorable.
- Kept partial-example context metrics separate from extraction metrics and
  reported invalid/missing scope or offsets rather than success-shaped scores.
- Added API and unit coverage for temporal changes, unknown event/visit dates,
  explicit resolution versus silence, patient isolation, exact and invalid
  spans, repeated mentions, and canonical-label validation.

### Remaining requirements

The benchmark still needs independent exhaustive entity-span annotation over
complete note scopes (including zero-mention notes), adjudication, and
independently reviewed temporal/longitudinal case labels before those metrics
can be reported. Added a focused Vitest suite for the temporal evidence formatter used by the
Consistency view. It checks valid event-date intervals, unavailable event
dates despite known visit dates, missing interval values, and same-event dates.
This is a focused display-logic unit test rather than a full browser or
component interaction test; broader UI workflow coverage remains future work.

Validation on 2026-10-28: `python -m pytest tests -q` — 161 passed;
`Set-Location frontend; npm test` — 4 passed; `npm run build` — succeeded;
`git diff --check` — clean (Git emitted only LF-to-CRLF notices). No commit or
push was made.
