# MedThread Five-Minute Demonstration

## Preparation

From the project directory, start FastAPI in one terminal:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

In another terminal:

```powershell
Set-Location frontend
npm run dev
```

Open the Vite URL. The backend loads the labeled synthetic demo on startup. If needed, use the app's **Restore synthetic demo** action from Import Notes. Never upload real patient data for this demonstration.

## Demo flow (about five minutes)

### 1. Workspace and import (45 seconds)

Open **Import Notes**. Point out CSV/JSON preview and manual entry. Explain that imports are validated and processed through the same shared Python pipeline, then stored in the local SQLite database. A backend restart restores the active dataset and recomputes NLP results.

**Say:** “The bundled notes are synthetic. Imported note text is stored in plaintext in local SQLite; this prototype is not encrypted or certified for protected health information. Do not upload real patient records.”

### 2. Patient Journey (60 seconds)

Choose a synthetic patient such as `DEMO_P001`. Open a visit and inspect the original note, highlighted mentions, source sentences, and context. Compare an explicit resolution phrase with a mention that is merely absent in a later note.

**Say:** “A missing mention is not treated as absence or resolution. ‘Newly documented’ is a record observation, not proof of symptom onset.”

### 3. Consistency review (60 seconds)

Open **Consistency**, expand a flag, and show both source notes, exact source spans, dates, context, temporal details, rule trace, review decisions, rationale, and saved timestamp.

**Say:** “This is a rule-based review signal, not a confirmed clinical contradiction. Event-date intervals appear only when both normalized event dates are known; visit dates are not substitutes. Reviewer choices and rationale are prototype annotations scoped to this browser session; they do not update clinical records.”

### 4. Medical Concept Explorer (60 seconds)

Open **Text Intelligence** (Medical Concept Explorer). Filter by patient/date/context; select a concept and then a co-occurring pair. Show the note IDs and exact evidence sentences. Explain the dashboard's co-occurrence disclaimer.

**Say:** “These are counts of text mentions in the selected notes. Same-note co-occurrence does not establish causation, diagnosis, prevalence, or a clinical relationship.”

### 5. Evaluation Studio (75 seconds)

Open **Evaluation**. Show benchmark identity/status, context sample size, fixed-label confusion matrix, per-class support, and source-linked errors if present. Show unscorable predictions and unavailable exact-span extraction metrics.

**Say:** “The current synthetic annotations are partial and not independently reviewed. Context scores are computed on aligned labeled examples. Exact-span extraction metrics require valid offsets and a declared exhaustive note scope; neither is present here. Unmatched predictions are unscorable—not false positives. There is no held-out split and no clinical validity claim.”

## Closing

MedThread demonstrates an inspectable pipeline and evidence-traceable interface. It is an educational prototype; every output requires appropriate expert review and it must not be used for diagnosis or treatment.
