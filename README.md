# MedThread — Clinical Intelligence

> Longitudinal clinical text mining and consistency analysis over synthetic patient notes.

**All demo data is explicitly SYNTHETIC. No real patient data is included. This application is a prototype and provides no clinical data security guarantees.**

---

## Architecture

```
MedThread/
├── backend/          ← FastAPI REST API (Python)
│   ├── main.py       ← REST endpoints; starts the real NLP pipeline on loaded notes
│   ├── state.py      ← In-memory NLP cache and SQLite-backed review state
│   ├── storage.py    ← Local SQLite persistence for active notes and reviews
│   └── models.py     ← Pydantic response schemas
├── src/medthread/    ← Shared NLP pipeline and evaluation logic
│   ├── config.py     ← Symptom lexicon + context cues
│   ├── pipeline.py   ← Orchestrator: notes → mentions → comparisons
│   ├── entity_extraction.py
│   ├── context_detection.py
│   ├── temporal.py
│   ├── longitudinal_analysis.py
│   ├── text_mining.py
│   └── evaluation.py
├── frontend/         ← React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── api/      ← Typed API client with reviewer-session header
│       ├── pages/    ← Import, journey, note inspector, investigation, mining, evaluation
│       └── components/
├── data/
│   ├── synthetic_notes.csv     ← bundled synthetic demo notes
│   ├── gold_annotations.csv    ← context-labeled examples; not exhaustive
│   ├── benchmark_metadata.json ← version, provenance, coverage, limitations
│   └── annotation_schema.json  ← machine-readable current annotation schema
└── tests/
    └── test_*.py               ← NLP, API, and evaluation regression tests
```

The React application calls the FastAPI backend; the backend calls the shared Python NLP modules. The original Streamlit application remains available as a separate entry point. The FastAPI application persists active source notes and reviewer decisions in a local SQLite database, then recomputes derived NLP results at startup. In-memory DataFrames are only a process cache. This is a local, single-process prototype, not a multi-user or production clinical system.

---

## Quick Start

The commands below are for Windows PowerShell, run from the project root.

### 1. Backend (FastAPI)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt

# Optional: choose a different local database file before starting the API.
# The default is .medthread\medthread.sqlite3 under the repository root.
# $env:MEDTHREAD_DB_PATH = "C:\medthread-data\medthread.sqlite3"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

On the first start with a fresh database, the backend seeds and processes the bundled synthetic dataset. Later starts restore the last active notes from SQLite and recompute NLP results. Visit `http://127.0.0.1:8001/docs` for the interactive API explorer. Binding to `127.0.0.1` keeps the server local and avoids common Windows socket permission errors.

### 2. Frontend (React + Vite)

Open a second PowerShell terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open **http://localhost:5173** in your browser.

The Vite dev server proxies `/api/*` to the backend at `http://localhost:8001`.

### 3. Legacy Streamlit app (optional)

From a terminal at the project root with the Python environment activated:

```powershell
python -m pip install -r requirements.txt
streamlit run app.py --server.port 8502
```

---

## Running Tests

```powershell
# From the project root, with the backend dependencies installed:
python -m pytest tests -q

# Frontend TypeScript check and production build:
Set-Location frontend
npm run build
```

---

## Pages

| Page | URL | Description |
|---|---|---|
| Clinical Home | `/` | Stats dashboard, recent inconsistency signals |
| Clinical Notes | `/import` | Preview/import CSV or JSON, manually enter a note, filter loaded notes |
| Patient Journey | `/journey` | Chronological original notes, mention context/status, source links |
| Note Explorer | `/notes` | Original note text and clickable entity evidence |
| Consistency | `/consistency` | Dated source evidence, triggering rule, persisted session decisions/rationale |
| Text Intelligence | `/intelligence` | Filterable concept frequencies/context, source-linked note co-occurrence, CSV export |
| Evaluation | `/evaluation` | Source-aligned context metrics, coverage-limited entity recall, exclusions, error evidence |

Entity and review evidence are displayed from backend NLP results. A missing detected mention is not interpreted as symptom absence. Mention counts and same-note co-occurrence are descriptive only, not prevalence, diagnosis, causation, or a clinical relationship.

### Evaluation scope and limitations

The bundled `data/gold_annotations.csv` contains 60 project-authored context examples over 15 synthetic notes and five patient groups. Its status is not independently reviewed and it is **not exhaustive**. Context metrics are computed only for source-aligned examples with a predicted mention. The app reports recall on eligible annotated examples, but extraction precision/F1 are unavailable because predictions outside the partial annotations cannot be confirmed false positives. Such unmatched predictions are listed as unscorable, not false positives. Temporal and longitudinal scores are unavailable because there are no gold labels for those tasks. There is no train/test split or fitted ML model; reported scores are development checks on the bundled corpus, not held-out estimates. Synthetic results do not demonstrate clinical validity.

See [docs/ANNOTATION_GUIDE.md](docs/ANNOTATION_GUIDE.md), [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md), and [docs/RESULTS_TEMPLATE.md](docs/RESULTS_TEMPLATE.md) before reporting results. Do not copy illustrative or example values as measured results.

Latest observed validation (2026-10-28): `python -m pytest tests -q` — 161 passed; `Set-Location frontend; npm test` — 4 passed; `npm run build` — succeeded. These are software validation results, not clinical performance results.

### Importing notes

Open **Import Notes** from the navigation. Upload a CSV with the header `patient_id,note_id,visit_date,text` or a JSON array with those same fields. Dates must be valid; empty required values, duplicate IDs, malformed files, and rows with missing values are reported before import. The CSV/JSON preview displays valid and invalid row counts, and only the valid rows are imported. File imports replace the active dataset; manual entry appends a note. FastAPI validates inputs and runs the shared NLP pipeline before activating a dataset. Notes are persisted in local SQLite; a fresh database is seeded with the synthetic demo, while later restarts restore the last active dataset. **Restore synthetic demo** replaces that dataset. **Reset** persists an empty dataset and does not reseed demo on restart.

### Local persistence, backup, and privacy

- The default SQLite file is `.medthread\medthread.sqlite3` (ignored by Git). Set `MEDTHREAD_DB_PATH` in the backend process environment to use another file.
- Source note text is stored in plaintext SQLite on the local machine. This prototype does not encrypt data or provide clinical security controls; do not upload real patient or protected health information.
- Reviewer decisions are scoped by the browser-session identifier and review key; rationale, latest decision, UTC timestamp, and append-only decision events are persisted. They are annotations, not clinical record updates.
- Replacing the dataset (including restoring demo) clears saved review decisions. Restarting FastAPI does not. Reset writes an empty dataset and clears decisions; it is an application-level deletion, not a secure-erasure guarantee.
- To back up, stop the backend and copy the configured SQLite database file to a protected location. Treat the backup as containing the full source note text.
- The legacy Streamlit entry point is retained; the SQLite lifecycle described here is implemented by the FastAPI application.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Corpus statistics |
| POST | `/api/demo` | Reload demo dataset |
| GET | `/api/patients` | List patient IDs |
| GET | `/api/notes` | List notes (optional `?patient_id=`) |
| GET | `/api/notes/{note_id}` | Note detail with mentions |
| POST | `/api/notes/preview` | Validate CSV/JSON and preview accepted rows |
| POST | `/api/notes/import` | Validate and process notes (`mode: replace` or `append`) |
| GET | `/api/mentions` | All mentions (filter by patient/entity/context) |
| GET | `/api/cooccurrence` | Note-level co-occurrence counts and source note IDs |
| GET | `/api/concepts` | Filterable concept/context aggregation with source-linked co-occurrence evidence |
| GET | `/api/comparison` | Longitudinal comparison results |
| GET | `/api/timeline/{patient_id}` | Patient visit timeline |
| GET | `/api/review` | Review queue (inconsistencies + unclear) |
| PUT | `/api/review/{key}` | Save review state and optional rationale; responses include timestamp and decision history |
| POST | `/api/reset` | Persist an empty active dataset and clear reviewer decisions |
| GET | `/api/export/mentions.csv` | Export extracted mentions |
| GET | `/api/export/review.csv` | Export review flags and session decisions |
| POST | `/api/upload` | Upload CSV/JSON notes file and run the NLP pipeline |
| GET | `/api/evaluation/demo` | Source-audited context evaluation and annotation coverage report |
| GET | `/api/lexicon` | Entity lexicon |

---

## Context Labels

| Label | Meaning |
|---|---|
| `affirmed` | Entity explicitly present |
| `negated` | Entity explicitly denied |
| `uncertain` | Possible or hedged mention |
| `resolved` | Previously mentioned, now resolved |
| `unclear` | Cannot determine from context |

---

## Security & Privacy

- No API key required for core use.
- No real patient data or fabricated clinical claims.
- No external service calls for clinical text processing.
- User-supplied note text is rendered as React text (not injected HTML).
- CSV formula-like values are escaped before export.
- No fake results, fake citations, or unsupported novelty claims.

---

## Tech Stack

**Backend:** Python 3.10+ · FastAPI · Uvicorn · Pydantic v2 · pandas · scikit-learn  
**Frontend:** React 18 · Vite · TypeScript · Tailwind CSS · Framer Motion · Recharts · TanStack Query · React Router
