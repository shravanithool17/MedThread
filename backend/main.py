"""MedThread FastAPI backend — exposes NLP pipeline results as REST endpoints."""
from __future__ import annotations

import math
import os
import re
import sys
import csv
import io
import json
from itertools import combinations
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, Literal, Optional

import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# ── NLP module path setup ────────────────────────────────────────────────────
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from medthread.config import SYMPTOM_LEXICON
from medthread.evaluation import (
    align_predictions_with_gold,
    compute_context_metrics,
    find_errors,
    load_gold_annotations,
    sentence_occurs_in_text,
    compute_entity_coverage_metrics,
    summarize_unmatched_predictions,
)
from medthread.pipeline import run_pipeline
from medthread.preprocessing import extract_sentences_from_note
from medthread.schemas import REVIEW_STATES, review_state_key
from medthread.text_mining import build_concept_explorer, compute_corpus_stats
from medthread.validation import load_notes_from_csv, parse_notes_import, validate_import_records

from backend.models import (
    ComparisonOut,
    CooccurrenceOut,
    ConceptExplorerResponse,
    EvidenceItem,
    EvaluationResponse,
    HealthResponse,
    ImportPreviewResponse,
    ImportResultResponse,
    ImportNotesRequest,
    MentionOut,
    NoteDetail,
    NoteOut,
    ReviewUpdateRequest,
    StatsResponse,
    StateResponse,
    TimelineResponse,
    TimelineVisit,
    UploadResponse,
)
from backend.state import state

# ── Helpers ───────────────────────────────────────────────────────────────────

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_DEMO_CSV = os.path.join(_DATA_DIR, "synthetic_notes.csv")
_GOLD_CSV = os.path.join(_DATA_DIR, "gold_annotations.csv")
_BENCHMARK_METADATA = os.path.join(_DATA_DIR, "benchmark_metadata.json")
_MAX_IMPORT_BYTES = 10 * 1024 * 1024


def _clean(val: Any) -> Any:
    """Convert NaN / NaT to None; preserve numeric types for JSON serialisation."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    if isinstance(val, (int, float, bool)):
        return val
    s = str(val).strip()
    if s.lower() in ("nan", "nat", "none", "<na>", ""):
        return None
    return s


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialise a DataFrame to a list of dicts with safe None values."""
    if df.empty:
        return []
    result = []
    for row in df.to_dict("records"):
        result.append({k: _clean(v) for k, v in row.items()})
    return result


def _offset_map(raw: str, normalized: str) -> list[int]:
    """Map normalized sentence character positions back to the original note."""
    positions: list[int] = []
    raw_index = 0
    for char in normalized:
        if char.isspace():
            while raw_index < len(raw) and raw[raw_index].isspace():
                raw_index += 1
            positions.append(max(raw_index - 1, 0))
            continue
        while raw_index < len(raw) and raw[raw_index].isspace():
            raw_index += 1
        positions.append(raw_index)
        raw_index += 1
    return positions


def _mentions_for_note(note, mentions_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize a note's mentions with offsets into its original text."""
    if mentions_df.empty:
        return []
    rows = mentions_df[mentions_df["note_id"] == note.note_id]
    if rows.empty:
        return []

    sentence_offsets: dict[int, tuple[int, list[int]]] = {}
    cursor = 0
    for sentence_record in extract_sentences_from_note(note):
        sentence = sentence_record["sentence"]
        pattern = re.compile(r"\s+".join(re.escape(part) for part in sentence.split()))
        match = pattern.search(note.text, cursor)
        if match is None:
            continue
        sentence_index = int(sentence_record["sentence_index"])
        sentence_offsets[sentence_index] = (
            match.start(),
            _offset_map(match.group(), sentence),
        )
        cursor = match.end()

    result = _df_to_records(rows)
    for mention in result:
        sentence_index = mention.get("sentence_index")
        offset_data = sentence_offsets.get(int(sentence_index)) if sentence_index is not None else None
        local_start = mention.get("char_start")
        local_end = mention.get("char_end")
        if offset_data and local_start is not None and local_end is not None:
            sentence_start, offsets = offset_data
            if 0 <= local_start < len(offsets) and 0 < local_end <= len(offsets):
                mention["char_start"] = sentence_start + offsets[local_start]
                mention["char_end"] = sentence_start + offsets[local_end - 1] + 1
        mention["extraction_method"] = mention.get("extraction_method")
    return result


def _comparison_records(df: pd.DataFrame, session_id: str) -> list[dict[str, Any]]:
    """Add reviewer state and source-linked evidence to comparison results."""
    records = _df_to_records(df)
    review_states = state.get_review_states(session_id)
    notes_by_id = {note.note_id: note for note in state.notes}

    for record in records:
        key = review_state_key(record.get("patient_id", ""), record.get("entity", ""))
        record["review_key"] = key
        record["review_state"] = review_states.get(key, record.get("review_state", "unreviewed"))
        note_ids = list(dict.fromkeys(
            note_id.strip()
            for note_id in str(record.get("evidence_note_ids") or "").split(";")
            if note_id.strip()
        ))
        evidence: list[dict[str, Any]] = []
        patient_mentions = state.mentions_df[
            (state.mentions_df["patient_id"] == record["patient_id"])
            & (state.mentions_df["entity_normalized"] == record["entity"])
        ] if not state.mentions_df.empty else pd.DataFrame()
        for note_id in note_ids:
            note = notes_by_id.get(note_id)
            if note is None:
                continue
            mention_rows = patient_mentions[patient_mentions["note_id"] == note_id]
            for mention in _mentions_for_note(note, mention_rows):
                evidence.append({
                    "note_id": note_id,
                    "visit_date": str(note.visit_date) if note.visit_date else None,
                    "context": mention.get("context", "unclear"),
                    "sentence": mention.get("sentence", ""),
                    "reason": mention.get("reason"),
                    "time_expression": mention.get("time_expression"),
                    "normalized_event_date": mention.get("normalized_event_date"),
                })
        record["evidence"] = evidence
    return records


def _csv_response(
    rows: list[dict[str, Any]],
    filename: str,
    fieldnames: list[str] | None = None,
) -> Response:
    """Return spreadsheet-safe UTF-8 CSV without interpreting user text as formulas."""
    buffer = io.StringIO(newline="")
    columns = list(rows[0]) if rows else (fieldnames or [])
    if columns:
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            safe_row = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    value = str(value)
                text = "" if value is None else str(value)
                if text.lstrip().startswith(("=", "+", "-", "@")):
                    text = "'" + text
                safe_row[key] = text
            writer.writerow(safe_row)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _activate_notes(notes, dataset_source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run NLP before replacing active session data."""
    mentions_df, comparison_df = run_pipeline(notes)
    if not comparison_df.empty and "review_state" not in comparison_df.columns:
        comparison_df["review_state"] = "unreviewed"
    state.notes = notes
    state.mentions_df = mentions_df
    state.comparison_df = comparison_df
    state.pipeline_run = True
    state.dataset_source = dataset_source
    state.clear_review_states()
    return mentions_df, comparison_df


def _note_for_import(note) -> dict[str, Any]:
    return {
        "patient_id": note.patient_id,
        "note_id": note.note_id,
        "visit_date": note.visit_date.isoformat() if note.visit_date else "",
        "text": note.text,
    }


def _run_demo() -> None:
    """Load and pipeline the bundled synthetic dataset."""
    with open(_DEMO_CSV, "r", encoding="utf-8") as f:
        csv_content = f.read()
    notes, _ = load_notes_from_csv(csv_content)
    _activate_notes(notes, "synthetic-demo")


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_demo()
    yield


app = FastAPI(
    title="MedThread API",
    version="1.0.0",
    description="Longitudinal Clinical Text Mining & Consistency Analysis — REST API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        pipeline_run=state.pipeline_run,
        n_notes=len(state.notes),
    )


@app.get("/api/state", response_model=StateResponse)
def get_state():
    patients = len({note.patient_id for note in state.notes})
    return StateResponse(
        pipeline_run=state.pipeline_run,
        n_notes=len(state.notes),
        n_patients=patients,
        dataset_source=state.dataset_source,
    )


@app.post("/api/demo", summary="Load and process the bundled synthetic dataset")
def load_demo():
    _run_demo()
    return {"message": "Demo data loaded", "n_notes": len(state.notes)}


@app.post("/api/reset")
def reset_state():
    state.reset()
    return {"message": "State reset"}


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    if not state.pipeline_run:
        raise HTTPException(404, "Pipeline not run — POST /api/demo first")
    s = compute_corpus_stats(state.mentions_df, state.comparison_df, notes=state.notes)
    return StatsResponse(
        pipeline_run=True,
        n_patients=s["n_patients"],
        n_notes=s["n_notes"],
        n_mentions=s["n_mentions"],
        n_review_flags=s["n_review_flags"],
        n_possible_inconsistency=s["n_possible_inconsistency"],
    )


# ── Notes ─────────────────────────────────────────────────────────────────────

@app.get("/api/notes", response_model=list[NoteOut])
def get_notes(patient_id: Optional[str] = Query(None)):
    if not state.pipeline_run:
        raise HTTPException(404, "Pipeline not run")
    notes = state.notes
    if patient_id:
        notes = [n for n in notes if n.patient_id == patient_id]
    return [
        NoteOut(
            patient_id=n.patient_id,
            note_id=n.note_id,
            visit_date=str(n.visit_date) if n.visit_date else None,
            text=n.text,
            text_preview=(n.text[:150] + "…") if len(n.text) > 150 else n.text,
        )
        for n in notes
    ]


@app.get("/api/notes/{note_id}", response_model=NoteDetail)
def get_note(note_id: str):
    if not state.pipeline_run:
        raise HTTPException(404, "Pipeline not run")
    note = next((n for n in state.notes if n.note_id == note_id), None)
    if not note:
        raise HTTPException(404, f"Note {note_id!r} not found")
    mentions = _mentions_for_note(note, state.mentions_df)
    return NoteDetail(
        patient_id=note.patient_id,
        note_id=note.note_id,
        visit_date=str(note.visit_date) if note.visit_date else None,
        text=note.text,
        text_preview=(note.text[:150] + "…") if len(note.text) > 150 else note.text,
        mentions=mentions,
    )


# ── Patients ──────────────────────────────────────────────────────────────────

@app.get("/api/patients", response_model=list[str])
def get_patients():
    if not state.pipeline_run:
        return []
    return sorted({note.patient_id for note in state.notes})


# ── Mentions ──────────────────────────────────────────────────────────────────

@app.get("/api/mentions")
def get_mentions(
    patient_id: Optional[str] = Query(None),
    note_id: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    context: Optional[str] = Query(None),
):
    if not state.pipeline_run or state.mentions_df.empty:
        return []
    df = state.mentions_df.copy()
    if patient_id:
        df = df[df["patient_id"] == patient_id]
    if note_id:
        df = df[df["note_id"] == note_id]
    if entity:
        df = df[df["entity_normalized"] == entity]
    if context:
        df = df[df["context"] == context]
    notes_by_id = {note.note_id: note for note in state.notes}
    records: list[dict[str, Any]] = []
    for note_id, group in df.groupby("note_id", sort=False):
        note = notes_by_id.get(note_id)
        if note is not None:
            records.extend(_mentions_for_note(note, group))
    return records


# ── Comparison ────────────────────────────────────────────────────────────────

@app.get("/api/comparison", response_model=list[ComparisonOut])
def get_comparison(
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    x_medthread_session: str = Header(default="default", alias="X-MedThread-Session"),
):
    if not state.pipeline_run:
        return []
    if state.comparison_df.empty:
        return []
    df = state.comparison_df.copy()
    if patient_id:
        df = df[df["patient_id"] == patient_id]
    if status:
        df = df[df["status"] == status]
    return _comparison_records(df, x_medthread_session)


# ── Timeline ──────────────────────────────────────────────────────────────────

@app.get("/api/timeline/{patient_id}", response_model=TimelineResponse)
def get_timeline(patient_id: str):
    if not state.pipeline_run:
        raise HTTPException(404, "Pipeline not run")
    notes = [n for n in state.notes if n.patient_id == patient_id]
    if not notes:
        raise HTTPException(404, f"Patient {patient_id!r} not found")
    notes_sorted = sorted(
        notes,
        key=lambda note: (
            note.visit_date is None,
            note.visit_date or date.max,
        ),
    )
    visits: list[TimelineVisit] = []
    affirmed_dates: dict[str, list[date]] = {}
    for note in notes_sorted:
        mentions = _mentions_for_note(note, state.mentions_df)
        for mention in mentions:
            entity = str(mention.get("entity_normalized", ""))
            context = mention.get("context")
            if context == "resolved":
                mention["journey_status"] = "explicitly_resolved"
            elif context == "negated":
                mention["journey_status"] = "explicitly_negated"
            elif context == "unclear":
                mention["journey_status"] = "unclear"
            elif context == "affirmed":
                previous_dates = affirmed_dates.get(entity, [])
                if note.visit_date is None:
                    mention["journey_status"] = None
                elif any(previous_date < note.visit_date for previous_date in previous_dates):
                    mention["journey_status"] = "persistent_documented"
                else:
                    mention["journey_status"] = "newly_reported"
                if note.visit_date is not None:
                    affirmed_dates.setdefault(entity, []).append(note.visit_date)
            else:
                # Uncertain context is evidence of uncertainty, not a basis for a
                # longitudinal unclear or absence status.
                mention["journey_status"] = None
        visits.append(
            TimelineVisit(
                note_id=note.note_id,
                visit_date=str(note.visit_date) if note.visit_date else None,
                mentions=mentions,
                note_text=note.text,
                note_preview=(note.text[:200] + "…") if len(note.text) > 200 else note.text,
            )
        )
    return TimelineResponse(patient_id=patient_id, visits=visits)


# ── Review ────────────────────────────────────────────────────────────────────

@app.get("/api/review", response_model=list[ComparisonOut])
def get_review(
    patient_id: Optional[str] = Query(None),
    show_all: bool = Query(False),
    x_medthread_session: str = Header(default="default", alias="X-MedThread-Session"),
):
    if not state.pipeline_run or state.comparison_df.empty:
        return []
    df = state.comparison_df.copy()
    if not show_all:
        df = df[df["status"].isin(["possible_inconsistency", "unclear"])]
    if patient_id:
        df = df[df["patient_id"] == patient_id]
    return _comparison_records(df, x_medthread_session)


@app.put("/api/review/{review_key}")
def update_review(
    review_key: str,
    body: ReviewUpdateRequest,
    x_medthread_session: str = Header(default="default", alias="X-MedThread-Session"),
):
    if body.state not in REVIEW_STATES:
        raise HTTPException(400, f"Invalid state {body.state!r}. Must be one of: {list(REVIEW_STATES)}")
    state.get_review_states(x_medthread_session)[review_key] = body.state
    return {"key": review_key, "state": body.state}


# ── Upload ────────────────────────────────────────────────────────────────────

@app.post("/api/upload", response_model=UploadResponse)
async def upload_notes(file: UploadFile = File(...)):
    content = await file.read(_MAX_IMPORT_BYTES + 1)
    if len(content) > _MAX_IMPORT_BYTES:
        raise HTTPException(413, "File exceeds the 10 MB import limit.")
    notes, errors, _ = parse_notes_import(content, file.filename or "")
    if errors:
        raise HTTPException(400, detail=errors)
    if not notes:
        raise HTTPException(400, "No valid notes found in the file.")
    _activate_notes(notes, "imported")
    return UploadResponse(
        message=f"Pipeline run on {len(notes)} notes",
        n_notes=len(notes),
        n_errors=0,
        errors=[],
    )


@app.post("/api/notes/preview", response_model=ImportPreviewResponse)
async def preview_notes(file: UploadFile = File(...)):
    """Validate an uploaded CSV/JSON and return valid rows for user confirmation."""
    content = await file.read(_MAX_IMPORT_BYTES + 1)
    if len(content) > _MAX_IMPORT_BYTES:
        raise HTTPException(413, "File exceeds the 10 MB import limit.")
    notes, errors, row_count = parse_notes_import(content, file.filename or "")
    return ImportPreviewResponse(
        valid_notes=[_note_for_import(note) for note in notes],
        errors=errors,
        valid_count=len(notes),
        invalid_count=max(row_count - len(notes), 1 if errors and row_count == 0 else 0),
        row_count=row_count,
    )


@app.post("/api/notes/import", response_model=ImportResultResponse)
def import_notes(body: ImportNotesRequest):
    """Validate and process accepted notes using the existing NLP pipeline."""
    existing_note_ids = (
        {note.note_id for note in state.notes}
        if body.mode == "append" and state.pipeline_run
        else set()
    )
    notes, errors, _ = validate_import_records(
        body.notes,
        {"patient_id", "note_id", "visit_date", "text"},
        existing_note_ids=existing_note_ids,
        first_row=1,
    )
    if errors:
        raise HTTPException(422, detail=errors)
    if not notes:
        raise HTTPException(422, "No valid notes to import.")

    active_notes = [*state.notes, *notes] if body.mode == "append" and state.pipeline_run else notes
    source = "manual-entry" if body.mode == "append" else "imported"
    mentions_df, _ = _activate_notes(active_notes, source)
    return ImportResultResponse(
        message=f"Imported and processed {len(notes)} note(s).",
        imported_count=len(notes),
        total_notes=len(active_notes),
        mention_count=len(mentions_df),
    )


@app.get("/api/cooccurrence", response_model=list[CooccurrenceOut])
def get_cooccurrence():
    """Count note-level concept co-occurrences; this is descriptive, not causal."""
    if not state.pipeline_run or state.mentions_df.empty:
        return []

    note_ids_by_pair: dict[tuple[str, str], list[str]] = {}
    for note_id, group in state.mentions_df.groupby("note_id", sort=False):
        entities = sorted(set(group["entity_normalized"].dropna().astype(str)))
        for entity_a, entity_b in combinations(entities, 2):
            note_ids_by_pair.setdefault((entity_a, entity_b), []).append(str(note_id))

    return [
        CooccurrenceOut(
            entity_a=entity_a,
            entity_b=entity_b,
            note_count=len(note_ids),
            note_ids=note_ids,
        )
        for (entity_a, entity_b), note_ids in sorted(
            note_ids_by_pair.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]


@app.get("/api/concepts", response_model=ConceptExplorerResponse)
def get_concept_explorer(
    patient_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    context: Optional[Literal["affirmed", "negated", "uncertain", "resolved", "unclear"]] = Query(None),
):
    """Return filtered concept counts and source-linked, note-level co-occurrence."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must be on or before end_date.")
    if not state.pipeline_run or state.mentions_df.empty:
        return {"mentions": 0, "concepts": [], "cooccurrences": []}
    return build_concept_explorer(
        state.mentions_df,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        context=context,
    )


@app.get("/api/export/mentions.csv")
def export_mentions():
    if not state.pipeline_run:
        raise HTTPException(404, "Pipeline not run")
    rows = []
    notes_by_id = {note.note_id: note for note in state.notes}
    for note_id, group in state.mentions_df.groupby("note_id", sort=False):
        note = notes_by_id.get(note_id)
        if note is not None:
            rows.extend(_mentions_for_note(note, group))
    return _csv_response(
        rows,
        "medthread_mentions.csv",
        fieldnames=[
            "patient_id", "note_id", "visit_date", "sentence_index", "sentence",
            "entity", "entity_normalized", "char_start", "char_end",
            "extraction_method", "context", "reason", "time_expression",
            "normalized_event_date",
        ],
    )


@app.get("/api/export/review.csv")
def export_review(
    x_medthread_session: str = Header(default="default", alias="X-MedThread-Session"),
):
    if not state.pipeline_run:
        raise HTTPException(404, "Pipeline not run")
    if state.comparison_df.empty:
        return _csv_response(
            [],
            "medthread_review.csv",
            fieldnames=[
                "patient_id", "entity", "status", "explanation", "rule_trace",
                "evidence_note_ids", "evidence_sentences", "review_state",
                "review_key", "evidence",
            ],
        )
    review_df = state.comparison_df[
        state.comparison_df["status"].isin(["possible_inconsistency", "unclear"])
    ]
    rows = _comparison_records(review_df, x_medthread_session)
    return _csv_response(
        rows,
        "medthread_review.csv",
        fieldnames=[
            "patient_id", "entity", "status", "explanation", "rule_trace",
            "evidence_note_ids", "evidence_sentences", "review_state",
            "review_key", "evidence",
        ],
    )


# ── Evaluation ────────────────────────────────────────────────────────────────

@app.get("/api/evaluation/demo", response_model=EvaluationResponse)
def run_evaluation_demo():
    gold_df, gold_errors = load_gold_annotations(_GOLD_CSV)
    if gold_df.empty:
        raise HTTPException(500, f"Failed to load gold annotations: {gold_errors}")
    try:
        with open(_BENCHMARK_METADATA, encoding="utf-8") as metadata_file:
            benchmark = json.load(metadata_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, f"Failed to load benchmark metadata: {exc}") from exc

    active_notes = {note.note_id: note for note in state.notes}
    eligible_gold_rows = []
    exclusions: list[dict[str, Any]] = []
    for row_index, row in gold_df.iterrows():
        note = active_notes.get(str(row["note_id"]))
        if note is None:
            exclusions.append({
                "note_id": str(row["note_id"]),
                "entity_normalized": str(row["entity_normalized"]),
                "reason": "gold_note_not_in_active_dataset",
            })
        elif not sentence_occurs_in_text(row["sentence"], note.text):
            exclusions.append({
                "note_id": str(row["note_id"]),
                "entity_normalized": str(row["entity_normalized"]),
                "reason": "gold_sentence_not_found_in_source_note",
            })
        else:
            eligible_gold_rows.append(row_index)
    gold_df = gold_df.loc[eligible_gold_rows].reset_index(drop=True)
    if gold_df.empty:
        return EvaluationResponse(
            benchmark=benchmark,
            entity_metrics=compute_entity_coverage_metrics(pd.DataFrame()),
            overall={},
            per_class=[],
            confusion_matrix=None,
            confusion_labels=[],
            errors=[],
            error_counts={},
            unscorable_predictions=summarize_unmatched_predictions(
                gold_df, state.mentions_df.to_dict("records") if state.pipeline_run else [],
                pd.DataFrame(),
            ),
            exclusions=exclusions,
            annotation_warnings=gold_errors,
            temporal_metrics={
                "available": False,
                "reason": "The benchmark contains no gold temporal-expression labels.",
            },
            longitudinal_metrics={
                "available": False,
                "reason": "The benchmark contains no gold longitudinal-case labels.",
            },
            n_context_samples=0,
            n_samples=0,
            message="No bundled gold-labeled examples match the active notes; metrics were not calculated.",
        )
    aligned = align_predictions_with_gold(
        gold_df,
        state.mentions_df.to_dict("records") if state.pipeline_run else [],
        allow_unique_fallback=False,
    )
    result = compute_context_metrics(aligned)
    errors_df = find_errors(aligned, n=len(aligned))
    errors = _df_to_records(errors_df) if not errors_df.empty else []
    matched = aligned["alignment_status"] == "matched"
    mismatches = matched & (aligned["gold_context"] != aligned["pred_context"])
    missed = aligned["alignment_status"] == "missed_extraction"
    error_counts = {
        "false_positive_context": int((mismatches & ~missed).sum()),
        "false_negative_context": int(mismatches.sum()),
        "missed_extraction": int(missed.sum()),
        "context_confusion": int((mismatches & ~missed).sum()),
    }
    entity_metrics = compute_entity_coverage_metrics(aligned)
    unscorable_predictions = summarize_unmatched_predictions(
        gold_df,
        state.mentions_df.to_dict("records") if state.pipeline_run else [],
        aligned,
    )
    cm = result.get("confusion_matrix")
    if cm is not None and hasattr(cm, "values"):
        # cm is a pd.DataFrame with index = labels
        cm_list = cm.values.tolist()
        cm_labels_raw: list[str] = list(cm.index)
    else:
        cm_list = None
        cm_labels_raw = []
    per_class_df = result.get("per_class", pd.DataFrame())
    per_class = _df_to_records(per_class_df) if not per_class_df.empty else []
    return EvaluationResponse(
        benchmark=benchmark,
        entity_metrics=entity_metrics,
        overall=result.get("overall", {}),
        per_class=per_class,
        confusion_matrix=cm_list,
        confusion_labels=cm_labels_raw,
        errors=errors,
        error_counts=error_counts,
        unscorable_predictions=unscorable_predictions,
        exclusions=exclusions,
        annotation_warnings=gold_errors,
        temporal_metrics={
            "available": False,
            "reason": "The benchmark contains no gold temporal-expression labels.",
        },
        longitudinal_metrics={
            "available": False,
            "reason": "The benchmark contains no gold longitudinal-case labels.",
        },
        n_context_samples=int(result.get("overall", {}).get("n_samples", 0)),
        n_samples=int(result.get("overall", {}).get("n_samples", 0)),
        message=f"Evaluated {len(gold_df)} source-aligned examples with bundled gold labels.",
    )


# ── Lexicon ───────────────────────────────────────────────────────────────────

@app.get("/api/lexicon")
def get_lexicon():
    """Return the entity lexicon for frontend term highlighting."""
    return SYMPTOM_LEXICON
