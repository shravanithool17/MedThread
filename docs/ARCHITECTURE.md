# MedThread Architecture

## Component Overview

```
MedThread/
├── app.py                          Home page, session state, demo data loader
├── pages/
│   ├── 1_Clinical_Notes.py         Upload/entry/view of notes
│   ├── 2_Patient_Timeline.py       Timeline visualization per patient
│   ├── 3_Review_Queue.py           Review flagged inconsistencies
│   ├── 4_Text_Mining.py            Corpus-level statistics
│   └── 5_Evaluation.py             Precision/recall/F1 evaluation
├── src/medthread/
│   ├── config.py                   Lexicon, cue lists, app settings
│   ├── schemas.py                  Dataclasses: Note, Mention, ComparisonResult
│   ├── validation.py               CSV/JSON input validation
│   ├── preprocessing.py            Text normalization + sentence splitting
│   ├── entity_extraction.py        Symptom mention detection
│   ├── context_detection.py        Negation/uncertainty/resolution rules
│   ├── temporal.py                 Time expression extraction/normalization
│   ├── longitudinal_analysis.py    Cross-visit consistency analysis
│   ├── pipeline.py                 Orchestrator: notes → results
│   ├── text_mining.py              Aggregation utilities
│   └── evaluation.py               Metrics computation
├── data/
│   ├── synthetic_notes.csv         15 synthetic notes, 5 patients
│   ├── gold_annotations.csv        60 partial context examples
│   ├── benchmark_metadata.json     Provenance, coverage, status, limitations
│   └── annotation_schema.json      Current row schema
├── backend/
│   ├── main.py                      FastAPI routes and pipeline integration
│   ├── state.py                     In-memory derived-results cache
│   ├── storage.py                   SQLite source-note and review persistence
│   └── models.py                    Pydantic response schemas
├── frontend/                        React/Vite/TypeScript user interface
└── tests/                          pytest test files
```

The React/FastAPI application is the primary workflow documented here;
`app.py` and `pages/` are retained as a separate legacy Streamlit entry point.

## Data Flow

```
CSV/JSON/manual note input
    │
    ▼
backend/main.py + validation.py ─ validates fields, dates, duplicates
    │
    ▼
preprocessing.py ───────────── normalize whitespace, split sentences
    │
    ▼
entity_extraction.py ────────── find symptom spans (regex or spaCy)
    │
    ▼
context_detection.py ─────────── classify each span: affirmed/negated/uncertain/resolved/unclear
    │
    ▼
temporal.py ──────────────────── extract time expressions, normalize to dates
    │
    ▼
longitudinal_analysis.py ─────── group by (patient, entity), apply comparison rules
    │
    ├── SQLite transaction ─ persists source notes after successful processing
    │
    ▼
text_mining.py ───────────────── aggregate stats for dashboard
evaluation.py ────────────────── align examples, score matched contexts, audit unscorable rows
```

On FastAPI startup, source notes are restored from SQLite and the pipeline is
recomputed. Derived DataFrames remain process-local. Review decisions/rationales
are persisted per browser-session ID and review key; an append-only event table
records changes. Dataset replacement/reset clears prior decisions.

## Key Algorithms

### Context Detection (context_detection.py)

1. **Clause isolation**: The sentence is split on `;`, ` but `, ` however `, ` although `, `\n`
   to obtain the clause containing the entity mention.
2. **Cue matching**: Cue lists are searched in text before the mention and a bounded
   look-ahead after it. Clause boundaries limit scope.
3. **Priority resolution**: Explicit negation of resolution is handled as ongoing/affirmed;
   explicit resolution takes precedence over ordinary negation, then negation, uncertainty,
   and default affirmed. The rules remain heuristic.

**Limitation**: This approach can fail when cues appear far from the entity, when phrasing
is complex, or when a clause contains implicit/ambiguous scope.

### Longitudinal Analysis (longitudinal_analysis.py)

Pseudocode:
```
for each (patient_id, entity) group:
    sort mentions by visit_date (None dates last)
    
    if only one mention:
        → newly_reported / explicitly_negated / explicitly_resolved / unclear
    
    if affirmed mentions AND resolved mentions:
        if last resolved > last affirmed:
            → explicitly_resolved
    
    if affirmed mentions AND negated mentions:
        for each (affirmed, negated) pair:
            check temporal comparability:
                if event dates are different → temporal change (not contradiction)
                if event dates are same or unknown → possible_inconsistency
        if any possible_inconsistency pairs found:
            → possible_inconsistency
        else (only temporal changes):
            → unclear (temporal change, not contradiction)
    
    if all affirmed:
        → persistent_documented
    
    if all negated:
        → explicitly_negated
    
    else:
        → unclear
```

### Temporal Comparability

Two mentions are "temporally comparable" (and thus can yield a possible inconsistency)
when both have the same normalized event date, or when at least one lacks a normalized
event date (ambiguous overlap).

Two mentions with provably different normalized event dates represent temporal change,
not contradiction (Test Case 6: "No fever Monday; fever started Wednesday").

## Design Choices

| Choice | Rationale |
|--------|-----------|
| Rule-based context detection | Explainable, auditable, no training data needed, deterministic |
| Clause-scoped negation | Prevents "no fever; patient has cough" from negating cough |
| spaCy as optional | Avoids hard dependency; regex fallback is production-viable |
| Temporal comparability check | Prevents temporal changes from being falsely flagged as contradictions |
| `not_documented` ≠ `resolved` | Absence of mention is not evidence of clinical absence |
| Local SQLite persistence | Restart-safe active source notes and review annotations; single-process prototype only |
| Code-point source offsets | Exact original-text spans; converted to UTF-16 indices only when rendered in React |

## Extension Points

- **Add symptoms**: Extend `SYMPTOM_LEXICON` in `config.py`
- **Add cue patterns**: Extend `NEGATION_CUES`, `UNCERTAINTY_CUES`, `RESOLUTION_CUES`
- **Use transformer NER**: Replace `find_entity_spans_regex` with a transformer model
- **Add ML context classifier**: future work only; current annotations are too small and partial
- **Evaluation constraints**: current gold examples are partial and not independently reviewed;
  unmatched predictions are unscorable, not false positives. Entity precision/F1, temporal scores,
  and longitudinal scores are unavailable.
- **Persistence**: SQLite is implemented for this local API; managed storage and security controls are required for multi-user/production use
- **PubMed integration**: Optional module; query PubMed API and display metadata alongside notes
