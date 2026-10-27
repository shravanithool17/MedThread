"""Integration tests for the MedThread FastAPI backend."""
import sys
import os

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.main import _activate_notes, _csv_response, app
from medthread.schemas import Note


@pytest.fixture(scope="session")
def client():
    """Session-scoped client — triggers lifespan so demo data auto-loads."""
    with TestClient(app) as c:
        yield c


# ── Health & state ────────────────────────────────────────────────────────────

def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert isinstance(body["pipeline_run"], bool)
    assert isinstance(body["n_notes"], int)


def test_state_ok(client):
    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.json()
    assert "pipeline_run" in body
    assert "n_notes" in body
    assert "n_patients" in body


def test_demo_auto_loaded(client):
    r = client.get("/api/health")
    assert r.json()["pipeline_run"] is True
    assert r.json()["n_notes"] == 15


def test_stats_returns_expected_counts(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["n_patients"] == 5
    assert body["n_notes"] == 15
    assert body["n_mentions"] > 0
    assert body["pipeline_run"] is True


# ── Notes ────────────────────────────────────────────────────────────────────

def test_notes_list(client):
    r = client.get("/api/notes")
    assert r.status_code == 200
    notes = r.json()
    assert len(notes) == 15
    for note in notes:
        assert "note_id" in note
        assert "patient_id" in note
        assert "text" in note


def test_notes_filter_by_patient(client):
    r = client.get("/api/notes?patient_id=DEMO_P001")
    assert r.status_code == 200
    notes = r.json()
    assert len(notes) == 3
    assert all(n["patient_id"] == "DEMO_P001" for n in notes)


def test_note_detail(client):
    r = client.get("/api/notes/NOTE_001")
    assert r.status_code == 200
    note = r.json()
    assert note["note_id"] == "NOTE_001"
    assert "text" in note
    assert "mentions" in note
    assert isinstance(note["mentions"], list)


def test_note_not_found(client):
    r = client.get("/api/notes/NONEXISTENT")
    assert r.status_code == 404


# ── Patients ──────────────────────────────────────────────────────────────────

def test_patients_list(client):
    r = client.get("/api/patients")
    assert r.status_code == 200
    patients = r.json()
    assert len(patients) == 5
    assert "DEMO_P001" in patients


# ── Mentions ──────────────────────────────────────────────────────────────────

def test_mentions_all(client):
    r = client.get("/api/mentions")
    assert r.status_code == 200
    mentions = r.json()
    assert len(mentions) > 0
    for m in mentions[:5]:
        assert "entity_normalized" in m
        assert "context" in m
        assert m["context"] in {"affirmed", "negated", "uncertain", "resolved", "unclear"}


def test_mentions_filter_by_patient(client):
    r = client.get("/api/mentions?patient_id=DEMO_P001")
    assert r.status_code == 200
    mentions = r.json()
    assert all(m["patient_id"] == "DEMO_P001" for m in mentions)


def test_mentions_filter_by_context(client):
    r = client.get("/api/mentions?context=negated")
    assert r.status_code == 200
    mentions = r.json()
    assert all(m["context"] == "negated" for m in mentions)


def test_mention_offsets_point_to_original_surface_text(client):
    for note in client.get("/api/notes").json():
        detail = client.get(f"/api/notes/{note['note_id']}").json()
        for mention in detail["mentions"]:
            start, end = mention["char_start"], mention["char_end"]
            assert detail["text"][start:end].casefold() == mention["entity"].casefold()


# ── Comparison ────────────────────────────────────────────────────────────────

def test_comparison_all(client):
    r = client.get("/api/comparison")
    assert r.status_code == 200
    comparisons = r.json()
    assert len(comparisons) > 0
    for c in comparisons[:5]:
        assert "entity" in c
        assert "status" in c
        assert "patient_id" in c


def test_comparison_filter_by_status(client):
    r = client.get("/api/comparison?status=possible_inconsistency")
    assert r.status_code == 200
    data = r.json()
    assert all(c["status"] == "possible_inconsistency" for c in data)


# ── Timeline ──────────────────────────────────────────────────────────────────

def test_timeline_patient(client):
    r = client.get("/api/timeline/DEMO_P001")
    assert r.status_code == 200
    body = r.json()
    assert body["patient_id"] == "DEMO_P001"
    assert "visits" in body
    assert len(body["visits"]) == 3
    for visit in body["visits"]:
        assert "note_id" in visit
        assert "mentions" in visit
        assert "note_text" in visit


def test_timeline_not_found(client):
    r = client.get("/api/timeline/FAKE_PATIENT")
    assert r.status_code == 404


def test_timeline_mentions_have_explicit_documentation_states(client):
    visits = client.get("/api/timeline/DEMO_P001").json()["visits"]
    statuses = {
        "newly_reported", "persistent_documented", "explicitly_resolved",
        "explicitly_negated", "unclear",
    }
    mentions = [mention for visit in visits for mention in visit["mentions"]]
    assert mentions
    assert all(
        mention["journey_status"] in statuses or (
            mention["context"] == "uncertain" and mention["journey_status"] is None
        )
        for mention in mentions
    )
    for visit in visits:
        for mention in visit["mentions"]:
            start, end = mention["char_start"], mention["char_end"]
            assert visit["note_text"][start:end].casefold() == mention["entity"].casefold()


# ── Review ────────────────────────────────────────────────────────────────────

def test_review_queue_returns_flags(client):
    r = client.get("/api/review")
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    for item in items:
        assert item["status"] in {"possible_inconsistency", "unclear"}


def test_review_update_state(client):
    items = client.get("/api/review").json()
    assert len(items) > 0
    key = items[0]["review_key"]

    r = client.put(f"/api/review/{key}", json={"state": "reviewed"})
    assert r.status_code == 200
    assert r.json()["state"] == "reviewed"

    items2 = client.get("/api/review").json()
    match = next((i for i in items2 if i["review_key"] == key), None)
    assert match is not None
    assert match["review_state"] == "reviewed"


def test_review_invalid_state(client):
    r = client.put("/api/review/some_key", json={"state": "invalid_state"})
    assert r.status_code == 400


@pytest.mark.parametrize("decision", [
    "confirmed_inconsistency",
    "not_a_contradiction",
    "needs_further_review",
])
def test_review_supports_investigation_actions(client, decision):
    headers = {"X-MedThread-Session": f"decision-{decision}"}
    item = client.get("/api/review", headers=headers).json()[0]
    saved = client.put(
        f"/api/review/{item['review_key']}",
        headers=headers,
        json={"state": decision},
    )
    assert saved.status_code == 200
    updated = client.get("/api/review", headers=headers).json()
    assert next(row for row in updated if row["review_key"] == item["review_key"])["review_state"] == decision


def test_review_evidence_has_dates_context_and_source_sentences(client):
    item = client.get("/api/review?show_all=true").json()[0]
    assert item["rule_trace"]
    assert item["evidence"]
    evidence_keys = {
        (
            evidence["note_id"],
            evidence["context"],
            evidence["sentence"],
            evidence["time_expression"],
            evidence["normalized_event_date"],
        )
        for evidence in item["evidence"]
    }
    assert len(evidence_keys) == len(item["evidence"])
    notes = {note["note_id"]: note for note in client.get("/api/notes").json()}
    for evidence in item["evidence"]:
        assert evidence["note_id"] in notes
        assert evidence["visit_date"] == notes[evidence["note_id"]]["visit_date"]
        assert evidence["sentence"] in notes[evidence["note_id"]]["text"]
        assert evidence["context"] in {"affirmed", "negated", "uncertain", "resolved", "unclear"}


def test_review_decisions_are_isolated_by_session(client):
    headers_a = {"X-MedThread-Session": "test-review-session-a"}
    headers_b = {"X-MedThread-Session": "test-review-session-b"}
    item = client.get("/api/review", headers=headers_a).json()[0]
    key = item["review_key"]

    updated = client.put(
        f"/api/review/{key}",
        headers=headers_a,
        json={"state": "needs_follow_up"},
    )
    assert updated.status_code == 200
    reviewed_a = client.get("/api/review", headers=headers_a).json()
    reviewed_b = client.get("/api/review", headers=headers_b).json()
    assert next(row for row in reviewed_a if row["review_key"] == key)["review_state"] == "needs_follow_up"
    assert next(row for row in reviewed_b if row["review_key"] == key)["review_state"] == "unreviewed"


def test_note_cooccurrence_counts_distinct_notes(client):
    response = client.get("/api/cooccurrence")
    assert response.status_code == 200
    pairs = response.json()
    assert pairs
    pair = pairs[0]
    assert pair["note_count"] == len(pair["note_ids"])
    assert pair["note_count"] > 0


def test_concept_explorer_filters_and_traces_source_evidence(client):
    response = client.get(
        "/api/concepts?patient_id=DEMO_P002&start_date=2024-02-10&end_date=2024-02-20&context=negated"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["mentions"] > 0
    notes = {note["note_id"]: note for note in client.get("/api/notes?patient_id=DEMO_P002").json()}
    for concept in result["concepts"]:
        assert concept["mention_count"] == len(concept["evidence"])
        assert sum(concept["context_counts"].values()) == concept["mention_count"]
        for evidence in concept["evidence"]:
            assert evidence["patient_id"] == "DEMO_P002"
            assert evidence["context"] == "negated"
            assert evidence["note_id"] in notes
            assert evidence["visit_date"] in {"2024-02-10", "2024-02-17"}
            assert evidence["sentence"] in notes[evidence["note_id"]]["text"]
    for pair in result["cooccurrences"]:
        assert pair["note_count"] == len(pair["evidence"])
        for source in pair["evidence"]:
            assert source["patient_id"] == "DEMO_P002"
            assert source["note_id"] in notes
            assert {mention["entity_normalized"] for mention in source["mentions"]} == {
                pair["entity_a"], pair["entity_b"],
            }
            assert all(mention["sentence"] in notes[source["note_id"]]["text"] for mention in source["mentions"])


def test_concept_explorer_rejects_invalid_filters(client):
    assert client.get("/api/concepts?start_date=2024-03-01&end_date=2024-02-01").status_code == 422
    assert client.get("/api/concepts?context=not-a-context").status_code == 422


def test_csv_exports_and_formula_safety(client):
    mentions = client.get("/api/export/mentions.csv")
    assert mentions.status_code == 200
    assert "text/csv" in mentions.headers["content-type"]
    assert "entity_normalized" in mentions.text

    review = client.get(
        "/api/export/review.csv",
        headers={"X-MedThread-Session": "test-export-session"},
    )
    assert review.status_code == 200
    assert "review_key" in review.text

    safe = _csv_response([{"sentence": "  =1+1"}], "test.csv")
    assert "'  =1+1" in safe.body.decode("utf-8")


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/upload",
        files={"file": ("notes.txt", b"clinical notes", "text/plain")},
    )
    assert response.status_code == 400


# ── Evaluation ────────────────────────────────────────────────────────────────

def test_evaluation_demo(client):
    r = client.get("/api/evaluation/demo")
    assert r.status_code == 200
    body = r.json()
    assert "overall" in body
    assert "per_class" in body
    assert "confusion_matrix" in body
    assert body["n_samples"] > 0
    assert body["n_context_samples"] == body["n_samples"]
    assert body["benchmark"]["benchmark_version"]
    assert body["benchmark"]["annotation_status"] == "author_annotated_not_independently_reviewed"
    assert body["entity_metrics"]["precision"] is None
    assert body["entity_metrics"]["f1"] is None
    assert body["unscorable_predictions"]["classification"].startswith("unscorable")
    assert body["temporal_metrics"]["available"] is False
    assert body["longitudinal_metrics"]["available"] is False
    assert "not_predicted" not in body["confusion_labels"]
    overall = body["overall"]
    assert 0.0 <= overall.get("accuracy", 0) <= 1.0
    assert 0.0 <= overall.get("macro_f1", 0) <= 1.0


def test_evaluation_per_class_types(client):
    r = client.get("/api/evaluation/demo")
    body = r.json()
    for row in body["per_class"]:
        if row.get("precision") is not None:
            assert isinstance(row["precision"], float)
        if row.get("recall") is not None:
            assert isinstance(row["recall"], float)
        if row.get("f1") is not None:
            assert isinstance(row["f1"], float)


def test_evaluation_reports_all_aggregate_metrics_and_error_sentences(client):
    body = client.get("/api/evaluation/demo").json()
    for metric in (
        "macro_precision", "macro_recall", "macro_f1",
        "weighted_precision", "weighted_recall", "weighted_f1",
    ):
        assert 0.0 <= body["overall"][metric] <= 1.0
    assert all("sentence" in error for error in body["errors"])
    assert all(
        error["error_category"] in {"missed_extraction", "context_confusion"}
        and "gold_context" in error
        and "pred_context" in error
        for error in body["errors"]
    )
    assert body["error_counts"]["false_positive_context"] == body["error_counts"]["context_confusion"]
    assert body["error_counts"]["false_negative_context"] <= len(body["errors"])
    assert body["entity_metrics"]["n_annotated_examples"] == (
        body["entity_metrics"]["n_matched_examples"]
        + body["entity_metrics"]["n_missed_extractions"]
        + body["entity_metrics"]["n_unscorable_examples"]
    )


# ── Lexicon ───────────────────────────────────────────────────────────────────

def test_lexicon(client):
    r = client.get("/api/lexicon")
    assert r.status_code == 200
    lexicon = r.json()
    assert isinstance(lexicon, dict)
    assert len(lexicon) > 0
    for entity, terms in list(lexicon.items())[:3]:
        assert isinstance(terms, list)


# ── Clinical note import ─────────────────────────────────────────────────────

def test_csv_preview_reports_valid_and_invalid_rows(client):
    content = (
        "patient_id,note_id,visit_date,text\n"
        "P_IMPORT,N_CSV_1,2026-02-01,Patient reports cough.\n"
        "P_IMPORT,N_CSV_2,not-a-date,Patient reports headache.\n"
        "P_IMPORT,N_CSV_3,2026-02-03,\n"
    )
    response = client.post(
        "/api/notes/preview",
        files={"file": ("notes.csv", content.encode(), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid_count"] == 1
    assert body["invalid_count"] == 2
    assert body["row_count"] == 3
    assert body["valid_notes"][0]["note_id"] == "N_CSV_1"
    assert {issue["field"] for issue in body["errors"]} == {"visit_date", "text"}


def test_json_preview_and_import_uses_nlp_pipeline(client):
    payload = (
        '[{"patient_id":"P_JSON","note_id":"N_JSON_1",'
        '"visit_date":"2026-02-02","text":"Patient reports headache."}]'
    )
    preview = client.post(
        "/api/notes/preview",
        files={"file": ("notes.json", payload.encode(), "application/json")},
    )
    assert preview.status_code == 200
    rows = preview.json()["valid_notes"]
    assert preview.json()["valid_count"] == 1

    try:
        imported = client.post(
            "/api/notes/import",
            json={"mode": "replace", "notes": rows},
        )
        assert imported.status_code == 200
        detail = client.get("/api/notes/N_JSON_1").json()
        assert detail["patient_id"] == "P_JSON"
        assert any(mention["entity_normalized"] == "headache" for mention in detail["mentions"])
        assert client.get("/api/state").json()["dataset_source"] == "imported"
    finally:
        client.post("/api/demo")


def test_import_preview_rejects_missing_columns_and_duplicate_ids(client):
    missing_columns = client.post(
        "/api/notes/preview",
        files={"file": ("missing.csv", b"patient_id,note_id,text\nP1,N1,Note.", "text/csv")},
    )
    assert missing_columns.status_code == 200
    assert missing_columns.json()["valid_count"] == 0
    assert missing_columns.json()["invalid_count"] == 1
    assert "visit_date" in missing_columns.json()["errors"][0]["message"]

    duplicates = client.post(
        "/api/notes/preview",
        files={
            "file": (
                "duplicates.csv",
                b"patient_id,note_id,visit_date,text\n"
                b"P1,N1,2026-01-01,Has cough.\n"
                b"P1,N1,2026-01-02,Has fever.\n",
                "text/csv",
            )
        },
    )
    body = duplicates.json()
    assert body["valid_count"] == 1
    assert body["invalid_count"] == 1
    assert any(issue["field"] == "note_id" and issue["row"] == 3 for issue in body["errors"])


def test_manual_entry_appends_and_rejects_duplicate_note_ids(client):
    note = {
        "patient_id": "P_MANUAL",
        "note_id": "N_MANUAL_1",
        "visit_date": "2026-02-03",
        "text": "Patient reports nausea.",
    }
    initial_count = len(client.get("/api/notes").json())
    invalid_manual = client.post(
        "/api/notes/import",
        json={
            "mode": "append",
            "notes": [{
                "patient_id": "P_MANUAL",
                "note_id": "N_MANUAL_INVALID",
                "visit_date": "not-a-date",
                "text": "   ",
            }],
        },
    )
    assert invalid_manual.status_code == 422
    invalid_fields = {issue["field"] for issue in invalid_manual.json()["detail"]}
    assert {"visit_date", "text"} <= invalid_fields

    added = client.post(
        "/api/notes/import",
        json={"mode": "append", "notes": [note]},
    )
    assert added.status_code == 200
    assert added.json()["total_notes"] == initial_count + 1
    assert client.get("/api/notes/N_MANUAL_1").json()["text"] == note["text"]
    assert any(row["note_id"] == "N_MANUAL_1" for row in client.get("/api/mentions").json())

    duplicate = client.post(
        "/api/notes/import",
        json={"mode": "append", "notes": [note]},
    )
    assert duplicate.status_code == 422
    assert "duplicated" in duplicate.json()["detail"][0]["message"]
    client.post("/api/demo")


def test_csv_import_end_to_end_and_demo_remains_available(client):
    content = (
        "patient_id,note_id,visit_date,text\n"
        "P_E2E,N_E2E_1,2026-02-04,Patient reports persistent cough.\n"
        "P_E2E,N_E2E_2,2026-02-10,Cough persists and headache is denied.\n"
    )
    preview = client.post(
        "/api/notes/preview",
        files={"file": ("e2e.csv", content.encode(), "text/csv")},
    ).json()
    assert preview["valid_count"] == 2

    imported = client.post(
        "/api/notes/import",
        json={"mode": "replace", "notes": preview["valid_notes"]},
    )
    assert imported.status_code == 200
    assert imported.json()["imported_count"] == 2
    assert imported.json()["mention_count"] > 0

    assert len(client.get("/api/notes").json()) == 2
    assert client.get("/api/timeline/P_E2E").json()["visits"][0]["note_id"] == "N_E2E_1"
    assert any(m["note_id"] == "N_E2E_1" for m in client.get("/api/mentions").json())
    assert client.get("/api/notes/N_E2E_2").json()["mentions"]
    assert client.get("/api/state").json()["dataset_source"] == "imported"
    assert client.get("/api/evaluation/demo").json()["n_samples"] == 0

    restored = client.post("/api/demo")
    assert restored.status_code == 200
    assert restored.json()["n_notes"] == 15
    assert client.get("/api/state").json()["dataset_source"] == "synthetic-demo"


def test_patient_journey_statuses_only_use_documented_evidence(client):
    rows = [
        {"patient_id": "P_JOURNEY", "note_id": "J1", "visit_date": "2026-03-01", "text": "Patient reports cough."},
        {"patient_id": "P_JOURNEY", "note_id": "J2", "visit_date": "2026-03-05", "text": "Possible cough, uncertain."},
        {"patient_id": "P_JOURNEY", "note_id": "J3", "visit_date": "2026-03-10", "text": "Cough persists."},
        {"patient_id": "P_JOURNEY", "note_id": "J4", "visit_date": "2026-03-12", "text": "Cough has resolved."},
        {"patient_id": "P_OTHER", "note_id": "J5", "visit_date": "2026-03-15", "text": "Patient denies cough."},
    ]
    try:
        imported = client.post("/api/notes/import", json={"mode": "replace", "notes": rows})
        assert imported.status_code == 200

        journey = client.get("/api/timeline/P_JOURNEY").json()
        assert [visit["note_id"] for visit in journey["visits"]] == ["J1", "J2", "J3", "J4"]
        cough_mentions = [
            next(mention for mention in visit["mentions"] if mention["entity_normalized"] == "cough")
            for visit in journey["visits"]
        ]
        assert cough_mentions[0]["journey_status"] == "newly_reported"
        assert cough_mentions[1]["context"] == "uncertain"
        assert cough_mentions[1]["journey_status"] is None
        assert cough_mentions[2]["journey_status"] == "persistent_documented"
        assert cough_mentions[3]["journey_status"] == "explicitly_resolved"
        assert client.get("/api/timeline/P_OTHER").json()["visits"][0]["note_id"] == "J5"
    finally:
        client.post("/api/demo")


def test_patient_journey_does_not_infer_chronology_for_undated_notes(client):
    notes = [
        Note(patient_id="P_UNDATED", note_id="U1", visit_date=None, text="Patient reports fatigue."),
        Note(patient_id="P_UNDATED", note_id="U2", visit_date=None, text="Fatigue continues."),
    ]
    try:
        _activate_notes(notes, "imported")
        visits = client.get("/api/timeline/P_UNDATED").json()["visits"]
        assert all(
            mention["journey_status"] is None
            for visit in visits
            for mention in visit["mentions"]
            if mention["context"] == "affirmed"
        )
    finally:
        client.post("/api/demo")
