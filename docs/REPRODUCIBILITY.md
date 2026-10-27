# Reproducibility Notes

## Code and benchmark identity

- Project: MedThread React/Vite/TypeScript + FastAPI + shared Python NLP.
- Benchmark ID/version: `medthread-synthetic-context-v1`, `0.1.0`.
- Schema version: `1.0.0`.
- Data files: `data/synthetic_notes.csv`, `data/gold_annotations.csv`.
- Benchmark metadata: `data/benchmark_metadata.json`.
- No real patient records are included.

## Runtime and dependency management

The backend requirements file expresses minimum compatible package versions rather than a fully pinned Python lock. The exact versions in a run depend on the resolved environment. Capture them before reporting a run:

```powershell
python --version
python -c "import fastapi, pandas, pydantic, sklearn; print('fastapi', fastapi.__version__); print('pandas', pandas.__version__); print('pydantic', pydantic.__version__); print('scikit-learn', sklearn.__version__)"
node --version
npm --version
```

The frontend dependency graph is locked by `frontend/package-lock.json`; use `npm ci` rather than `npm install` for a lockfile-based install. Python dependency ranges are listed in `backend/requirements.txt`; pytest is listed in the root `requirements.txt`.

## Setup and execution (Windows PowerShell)

From the project root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pip install pytest
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

The Vite development server proxies API requests to the local FastAPI server. A
fresh database is seeded with synthetic demo notes at first startup; subsequent
starts restore the active dataset.

The FastAPI application uses `.medthread\medthread.sqlite3` under the project
root by default. To use a different local file, set the variable in the same
PowerShell process before starting Uvicorn:

```powershell
$env:MEDTHREAD_DB_PATH = "C:\medthread-data\medthread.sqlite3"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Only a fresh database is seeded with demo notes. Later starts restore the last
active notes and recompute NLP output. Stop the backend before copying the
database for backup. It contains plaintext note text; do not use real patient
data. The React/FastAPI workflow persists via SQLite; the legacy Streamlit
application retains separate session-state behavior.

## Test and evaluation commands

From the root:

```powershell
python -m pytest tests -q
Set-Location frontend
npm test
npm run build
```

The active benchmark metrics are computed by the application and exposed at `GET /api/evaluation/demo`; the Evaluation Studio renders the same API results. Record the date, version, runtime versions, sample counts, metrics, and limitations in `RESULTS_TEMPLATE.md`. Do not transcribe expected values from test fixtures as experimental results.

## Determinism, seeds, and split policy

The application uses a deterministic rule-based pipeline and no pseudo-random sampling or model fitting; there is no random seed to set. No train/validation/test split exists. The bundled corpus is used only for development-time evaluation, not as held-out test data. Any future learned baseline must split by patient/case group before fitting text preprocessing or model parameters, and must reserve test groups from tuning.

## Data and annotation constraints

The current 60-row annotation CSV is partial, project-authored, and not independently reviewed. One row (`NOTE_013`, `cough`, “Patient denies all symptoms.”) is skipped because the labeled canonical concept has no source surface form in the sentence; do not silently repair it from model output. The file has no entity span offsets, exhaustive negative coverage, or temporal/longitudinal gold labels. `entity_exhaustive_note_ids` is empty. Unmatched predictions are reported as unscorable rather than false positives. Annotated-example recall is distinct from exact-span extraction metrics; exact-span precision/recall/F1 are unavailable until a complete scope, valid source offsets, and exhaustive coverage are independently established. Temporal/longitudinal metrics are unavailable.

The review API stores decisions and history in SQLite under the existing
browser-session identifier. The frontend keeps that identifier in
`sessionStorage`; decisions are therefore not shared with a different browser
session/tab, even though a given identifier's records survive backend restarts.
Changing or restoring the active dataset clears review annotations. Do not
interpret a persisted prototype decision as a clinical record update.

Temporal evidence may show the note visit dates as source metadata, but a day
difference is calculated only from two valid normalized event dates. Missing
or invalid event dates remain unavailable; visit dates are never substituted.

Equivalent duplicate gold judgments are deduplicated with a warning; conflicting
labels for the same note/entity/source sentence are excluded with a warning.
Neither policy changes the annotation file itself.

## Tested environment record

| Component | Observed version |
|---|---|
| Python | 3.15.0 |
| FastAPI | 0.162.0 |
| pandas | 3.0.6 |
| Pydantic | 2.14.1 |
| scikit-learn | 1.9.1 |
| pytest | 9.1.1 |
| Node.js | v24.22.0 |
| npm | 11.19.1 |
| React | 18.3.1 |
| Vite | 5.4.21 |
| TypeScript | 5.9.3 |
| Backend tests | `python -m pytest tests -q` — 161 passed on 2026-10-28 |
| Frontend unit tests | `npm test` — 4 passed on 2026-10-28 |
| Frontend build | `npm run build` — succeeded on 2026-10-28 |
| Diff whitespace check | `git diff --check` — clean on 2026-10-28 (Git emitted only LF-to-CRLF notices) |

These are observed versions for this validation run, not pinned project-wide versions. The manifests specify compatible ranges for Python, and the frontend lockfile fixes the JavaScript dependency graph.

The 2026-10-28 `npm audit --omit=dev` check reported two moderate advisories
through the existing `react-router` / `react-router-dom` 6.x dependency.
`npm audit` recommends a breaking React Router 7 upgrade; it was not applied
as part of this evaluation/explainability change.
