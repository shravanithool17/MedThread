"""Pydantic response models for the MedThread API."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Literal, Optional


class HealthResponse(BaseModel):
    status: str
    pipeline_run: bool
    n_notes: int


class StateResponse(BaseModel):
    pipeline_run: bool
    n_notes: int
    n_patients: int
    dataset_source: str = "empty"


class StatsResponse(BaseModel):
    n_patients: int
    n_notes: int
    n_mentions: int
    n_review_flags: int
    n_possible_inconsistency: int
    pipeline_run: bool


class NoteOut(BaseModel):
    patient_id: str
    note_id: str
    visit_date: Optional[str]
    text: str
    text_preview: str


class NoteDetail(NoteOut):
    mentions: list[dict[str, Any]]


class MentionOut(BaseModel):
    patient_id: str
    note_id: str
    visit_date: Optional[str]
    entity_normalized: str
    context: str
    sentence: str
    reason: Optional[str]
    time_expression: Optional[str]
    normalized_event_date: Optional[str]
    entity: Optional[str] = None
    char_start: Optional[int]
    char_end: Optional[int]
    offset_unit: Optional[str] = None
    offset_convention: Optional[str] = None
    offset_validated: bool = False
    extraction_method: Optional[str] = None
    journey_status: Optional[str] = None
    sentence_index: Optional[int] = None


class EvidenceItem(BaseModel):
    note_id: str
    visit_date: Optional[str]
    context: str
    sentence: str
    reason: Optional[str] = None
    time_expression: Optional[str] = None
    normalized_event_date: Optional[str] = None
    entity: Optional[str] = None
    entity_normalized: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    offset_unit: Optional[str] = None
    offset_convention: Optional[str] = None
    offset_validated: bool = False


class ComparisonOut(BaseModel):
    flag_id: str
    patient_id: str
    entity: str
    status: str
    explanation: str
    rule_trace: str
    evidence_note_ids: str
    evidence_sentences: str
    review_state: str
    review_key: str
    review_rationale: str = ""
    review_updated_at: Optional[str] = None
    review_history: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    temporal_comparisons: list[dict[str, Any]] = Field(default_factory=list)


class TimelineVisit(BaseModel):
    note_id: str
    visit_date: Optional[str]
    mentions: list[dict[str, Any]]
    note_text: str
    note_preview: str


class TimelineResponse(BaseModel):
    patient_id: str
    visits: list[TimelineVisit]


class ReviewUpdateRequest(BaseModel):
    state: str
    rationale: str = Field(default="", max_length=4000)


class EvaluationResponse(BaseModel):
    benchmark: dict[str, Any] = Field(default_factory=dict)
    entity_metrics: dict[str, Any] = Field(default_factory=dict)
    entity_span_metrics: dict[str, Any] = Field(default_factory=dict)
    overall: dict[str, Any]
    per_class: list[dict[str, Any]]
    confusion_matrix: Optional[list[list[int]]]
    confusion_labels: list[str]
    errors: list[dict[str, Any]]
    error_counts: dict[str, int] = Field(default_factory=dict)
    unscorable_predictions: dict[str, Any] = Field(default_factory=dict)
    exclusions: list[dict[str, Any]] = Field(default_factory=list)
    annotation_warnings: list[str] = Field(default_factory=list)
    temporal_metrics: dict[str, Any] = Field(default_factory=dict)
    longitudinal_metrics: dict[str, Any] = Field(default_factory=dict)
    n_context_samples: int = 0
    n_samples: int
    message: Optional[str] = None


class UploadResponse(BaseModel):
    message: str
    n_notes: int
    n_errors: int
    errors: list[str]


class ImportNote(BaseModel):
    patient_id: str
    note_id: str
    visit_date: str
    text: str


class ImportIssue(BaseModel):
    row: int
    field: str
    message: str


class ImportPreviewResponse(BaseModel):
    valid_notes: list[ImportNote]
    errors: list[ImportIssue]
    valid_count: int
    invalid_count: int
    row_count: int


class ImportNotesRequest(BaseModel):
    notes: list[dict[str, Any]] = Field(min_length=1, max_length=5000)
    mode: Literal["replace", "append"]


class ImportResultResponse(BaseModel):
    message: str
    imported_count: int
    total_notes: int
    mention_count: int


class CooccurrenceOut(BaseModel):
    entity_a: str
    entity_b: str
    note_count: int
    note_ids: list[str]


class ConceptMentionEvidence(BaseModel):
    patient_id: str
    note_id: str
    visit_date: Optional[str]
    entity_normalized: str
    context: str
    sentence: str


class ConceptOut(BaseModel):
    entity_normalized: str
    mention_count: int
    note_count: int
    context_counts: dict[str, int]
    evidence: list[ConceptMentionEvidence]


class ConceptCooccurrenceEvidence(BaseModel):
    patient_id: str
    note_id: str
    visit_date: Optional[str]
    mentions: list[ConceptMentionEvidence]


class ConceptCooccurrenceOut(BaseModel):
    entity_a: str
    entity_b: str
    note_count: int
    evidence: list[ConceptCooccurrenceEvidence]


class ConceptExplorerResponse(BaseModel):
    mentions: int
    concepts: list[ConceptOut]
    cooccurrences: list[ConceptCooccurrenceOut]
