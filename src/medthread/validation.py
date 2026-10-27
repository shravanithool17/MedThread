"""Input validation for notes loaded from CSV, JSON, or manual entry."""

from __future__ import annotations

import io
import csv
import json
from datetime import date, datetime
from typing import Any, Iterable

import pandas as pd

from .schemas import Note


REQUIRED_COLUMNS = {"patient_id", "note_id", "visit_date", "text"}


def parse_date(value: Any) -> date | None:
    """Try to parse a date value. Return None if unparseable."""
    if value is None or (pd.api.types.is_scalar(value) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s or s.lower() in ("", "nan", "none", "nat"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def validate_notes_dataframe(df: pd.DataFrame) -> tuple[list[Note], list[str]]:
    """
    Validate a DataFrame and return (valid_notes, error_messages).

    Rules:
    - Required columns must be present.
    - patient_id and note_id must be non-empty strings.
    - visit_date must be parseable or left as None (with a warning).
    - text must be a non-empty string.
    - Duplicate note_ids generate warnings.
    """
    errors: list[str] = []
    notes: list[Note] = []

    # Check required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        errors.append(f"Missing required columns: {sorted(missing)}")
        return notes, errors

    seen_note_ids: set[str] = set()

    for idx, row in df.iterrows():
        row_errors: list[str] = []

        def _clean(val) -> str:
            """Convert to string, treating NaN/None/nan as empty."""
            if val is None:
                return ""
            s = str(val).strip()
            return "" if s.lower() in ("nan", "none", "nat", "<na>") else s

        patient_id = _clean(row.get("patient_id", ""))
        note_id = _clean(row.get("note_id", ""))
        visit_date_raw = row.get("visit_date")
        text = _clean(row.get("text", ""))

        if not patient_id:
            row_errors.append(f"Row {idx}: patient_id is empty.")
        if not note_id:
            row_errors.append(f"Row {idx}: note_id is empty.")
        if not text:
            row_errors.append(f"Row {idx}: text is empty.")

        visit_date = parse_date(visit_date_raw)
        if visit_date is None and visit_date_raw is not None:
            raw_str = str(visit_date_raw).strip()
            if raw_str and raw_str.lower() not in ("nan", "none", "nat", ""):
                errors.append(f"Row {idx}: Could not parse visit_date '{visit_date_raw}' — treated as unknown.")

        if row_errors:
            errors.extend(row_errors)
            continue

        if note_id in seen_note_ids:
            errors.append(f"Row {idx}: Duplicate note_id '{note_id}' — keeping first occurrence.")
            continue

        seen_note_ids.add(note_id)

        notes.append(Note(
            patient_id=patient_id,
            note_id=note_id,
            visit_date=visit_date,
            text=text,
        ))

    return notes, errors


def load_notes_from_csv(content: str | bytes) -> tuple[list[Note], list[str]]:
    """Load notes from a CSV string or bytes. Returns (notes, errors)."""
    try:
        if isinstance(content, bytes):
            df = pd.read_csv(io.BytesIO(content), dtype=str)
        else:
            df = pd.read_csv(io.StringIO(content), dtype=str)
    except Exception as exc:
        return [], [f"Failed to parse CSV: {exc}"]
    return validate_notes_dataframe(df)


def load_notes_from_json(content: str | bytes) -> tuple[list[Note], list[str]]:
    """Load notes from a JSON array string or bytes. Returns (notes, errors)."""
    import json
    try:
        if isinstance(content, bytes):
            data = json.loads(content.decode())
        else:
            data = json.loads(content)
        if not isinstance(data, list):
            return [], ["JSON must be an array of objects."]
        df = pd.DataFrame(data, dtype=str)
    except Exception as exc:
        return [], [f"Failed to parse JSON: {exc}"]
    return validate_notes_dataframe(df)


def validate_import_records(
    records: Iterable[dict[str, Any]],
    columns: set[str],
    existing_note_ids: set[str] | None = None,
    first_row: int = 2,
) -> tuple[list[Note], list[dict[str, Any]], int]:
    """Strictly validate import rows and return accepted notes and safe field errors."""
    records = list(records)
    row_count = len(records)
    missing_columns = sorted(REQUIRED_COLUMNS - columns)
    if missing_columns:
        return [], [{
            "row": 1,
            "field": "columns",
            "message": f"Missing required columns: {', '.join(missing_columns)}.",
        }], row_count

    errors: list[dict[str, Any]] = []
    notes: list[Note] = []
    seen_note_ids = set(existing_note_ids or set())

    for row_number, row in enumerate(records, start=first_row):
        if not isinstance(row, dict):
            errors.append({
                "row": row_number,
                "field": "row",
                "message": "Each note must be an object with the required fields.",
            })
            continue

        values = {
            field: str(row.get(field) if row.get(field) is not None else "").strip()
            for field in REQUIRED_COLUMNS
        }
        row_errors: list[dict[str, Any]] = []
        for field in REQUIRED_COLUMNS:
            raw_value = row.get(field)
            if raw_value is not None and not isinstance(raw_value, str):
                row_errors.append({
                    "row": row_number,
                    "field": field,
                    "message": f"{field} must be a string.",
                })
        for field in ("patient_id", "note_id", "visit_date", "text"):
            if not values[field]:
                row_errors.append({
                    "row": row_number,
                    "field": field,
                    "message": f"{field} is required.",
                })
        if len(values["patient_id"]) > 256:
            row_errors.append({
                "row": row_number,
                "field": "patient_id",
                "message": "patient_id must be 256 characters or fewer.",
            })
        if len(values["note_id"]) > 256:
            row_errors.append({
                "row": row_number,
                "field": "note_id",
                "message": "note_id must be 256 characters or fewer.",
            })
        if len(values["text"]) > 250_000:
            row_errors.append({
                "row": row_number,
                "field": "text",
                "message": "text must be 250,000 characters or fewer.",
            })

        visit_date = parse_date(values["visit_date"])
        if values["visit_date"] and visit_date is None:
            row_errors.append({
                "row": row_number,
                "field": "visit_date",
                "message": "visit_date must be a valid date (YYYY-MM-DD recommended).",
            })

        note_id = values["note_id"]
        if note_id and note_id in seen_note_ids:
            row_errors.append({
                "row": row_number,
                "field": "note_id",
                "message": "note_id is duplicated in this import or already loaded.",
            })

        if row_errors:
            errors.extend(row_errors)
            continue

        seen_note_ids.add(note_id)
        notes.append(Note(
            patient_id=values["patient_id"],
            note_id=note_id,
            visit_date=visit_date,
            text=values["text"],
        ))

    return notes, errors, row_count


def parse_notes_import(
    content: bytes,
    filename: str,
    existing_note_ids: set[str] | None = None,
) -> tuple[list[Note], list[dict[str, Any]], int]:
    """Parse a CSV/JSON import without including clinical text in errors."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in {"csv", "json"}:
        return [], [{
            "row": 0,
            "field": "file",
            "message": "Upload a CSV or JSON file.",
        }], 0

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [{
            "row": 0,
            "field": "file",
            "message": "File must use UTF-8 encoding.",
        }], 0

    if suffix == "json":
        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return [], [{
                "row": 0,
                "field": "file",
                "message": "Could not parse JSON. Upload an array of note objects.",
            }], 0
        if not isinstance(payload, list):
            return [], [{
                "row": 0,
                "field": "file",
                "message": "JSON must be an array of note objects.",
            }], 0
        columns = set().union(*(item.keys() for item in payload if isinstance(item, dict)))
        return validate_import_records(
            payload,
            columns,
            existing_note_ids=existing_note_ids,
            first_row=1,
        )

    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        columns = set(reader.fieldnames or [])
        if not reader.fieldnames:
            return [], [{
                "row": 1,
                "field": "columns",
                "message": "CSV must include a header row.",
            }], 0
        records = list(reader)
    except csv.Error:
        return [], [{
            "row": 0,
            "field": "file",
            "message": "Could not parse CSV.",
        }], 0

    return validate_import_records(
        records,
        columns,
        existing_note_ids=existing_note_ids,
        first_row=2,
    )
