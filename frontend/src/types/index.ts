export type ContextType = 'affirmed' | 'negated' | 'uncertain' | 'resolved' | 'unclear';
export type ReviewState =
  | 'unreviewed'
  | 'confirmed_inconsistency'
  | 'not_a_contradiction'
  | 'needs_further_review'
  | 'reviewed'
  | 'needs_follow_up';
export type ComparisonStatus =
  | 'possible_inconsistency'
  | 'persistent_documented'
  | 'newly_reported'
  | 'explicitly_resolved'
  | 'explicitly_negated'
  | 'not_documented'
  | 'unclear';

export interface Note {
  patient_id: string;
  note_id: string;
  visit_date: string | null;
  text: string;
  text_preview: string;
}

export interface ImportNote {
  patient_id: string;
  note_id: string;
  visit_date: string;
  text: string;
}

export interface ImportIssue {
  row: number;
  field: string;
  message: string;
}

export interface ImportPreview {
  valid_notes: ImportNote[];
  errors: ImportIssue[];
  valid_count: number;
  invalid_count: number;
  row_count: number;
}

export interface ImportResult {
  message: string;
  imported_count: number;
  total_notes: number;
  mention_count: number;
}

export interface NoteDetail extends Note {
  mentions: Mention[];
}

export interface Mention {
  patient_id: string;
  note_id: string;
  visit_date: string | null;
  entity?: string;
  entity_normalized: string;
  context: ContextType;
  sentence: string;
  reason: string | null;
  time_expression: string | null;
  normalized_event_date: string | null;
  char_start: number | null;
  char_end: number | null;
  extraction_method?: string | null;
  journey_status?: ComparisonStatus | null;
  sentence_index?: number;
}

export interface EvidenceItem {
  note_id: string;
  visit_date: string | null;
  context: ContextType;
  sentence: string;
  reason: string | null;
  time_expression: string | null;
  normalized_event_date: string | null;
}

export interface ComparisonResult {
  patient_id: string;
  entity: string;
  status: ComparisonStatus;
  explanation: string;
  rule_trace: string;
  evidence_note_ids: string;
  evidence_sentences: string;
  review_state: ReviewState;
  review_key: string;
  evidence: EvidenceItem[];
}

export interface Stats {
  n_patients: number;
  n_notes: number;
  n_mentions: number;
  n_review_flags: number;
  n_possible_inconsistency: number;
  pipeline_run: boolean;
}

export interface AppState {
  pipeline_run: boolean;
  n_notes: number;
  n_patients: number;
  dataset_source?: 'synthetic-demo' | 'imported' | 'manual-entry' | 'empty' | string;
}

export interface TimelineVisit {
  note_id: string;
  visit_date: string | null;
  mentions: Mention[];
  note_text: string;
  note_preview: string;
}

export interface TimelineResponse {
  patient_id: string;
  visits: TimelineVisit[];
}

export interface EvaluationResult {
  benchmark: {
    benchmark_id?: string;
    benchmark_version?: string;
    schema_version?: string;
    annotation_status?: string;
    provenance?: string;
    note_count?: number;
    patient_group_count?: number;
    context_annotation_count?: number;
    entity_annotation_coverage?: string;
    split_method?: string;
    limitations?: string[];
    [key: string]: unknown;
  };
  entity_metrics: {
    precision: number | null;
    recall: number | null;
    f1: number | null;
    n_annotated_examples: number;
    n_matched_examples: number;
    n_missed_extractions: number;
    n_unscorable_examples: number;
    matching_method: string;
    limitation: string;
  };
  message?: string;
  overall: {
    accuracy?: number;
    macro_precision?: number;
    macro_recall?: number;
    macro_f1?: number;
    weighted_precision?: number;
    weighted_recall?: number;
    weighted_f1?: number;
    n_samples?: number;
    [key: string]: number | undefined;
  };
  per_class: Array<{
    context?: string;
    precision?: number;
    recall?: number;
    f1?: number;
    support?: number;
    [key: string]: string | number | undefined | null;
  }>;
  confusion_matrix: number[][] | null;
  confusion_labels: string[];
  errors: Array<{
    note_id?: string;
    entity_normalized?: string;
    gold_context?: string;
    pred_context?: string;
    sentence?: string;
    error_category?: 'missed_extraction' | 'context_confusion' | string;
    false_positive_label?: string | null;
    false_negative_label?: string | null;
    alignment_status?: string;
    error_type?: string;
    [key: string]: string | number | undefined | null;
  }>;
  error_counts: {
    false_positive_context: number;
    false_negative_context: number;
    missed_extraction: number;
    context_confusion: number;
  };
  unscorable_predictions: {
    total: number;
    counts_by_reason: Record<string, number>;
    examples: Array<{
      note_id: string;
      entity_normalized: string;
      reason: string;
    }>;
    classification: string;
  };
  exclusions: Array<{
    note_id: string;
    entity_normalized: string;
    reason: string;
  }>;
  annotation_warnings: string[];
  temporal_metrics: { available: boolean; reason?: string };
  longitudinal_metrics: { available: boolean; reason?: string };
  n_context_samples: number;
  n_samples: number;
}

export interface Cooccurrence {
  entity_a: string;
  entity_b: string;
  note_count: number;
  note_ids: string[];
}

export interface ConceptMentionEvidence {
  patient_id: string;
  note_id: string;
  visit_date: string | null;
  entity_normalized: string;
  context: ContextType;
  sentence: string;
}

export interface ExploredConcept {
  entity_normalized: string;
  mention_count: number;
  note_count: number;
  context_counts: Record<string, number>;
  evidence: ConceptMentionEvidence[];
}

export interface ConceptCooccurrenceEvidence {
  patient_id: string;
  note_id: string;
  visit_date: string | null;
  mentions: ConceptMentionEvidence[];
}

export interface ConceptCooccurrence {
  entity_a: string;
  entity_b: string;
  note_count: number;
  evidence: ConceptCooccurrenceEvidence[];
}

export interface ConceptExplorerResult {
  mentions: number;
  concepts: ExploredConcept[];
  cooccurrences: ConceptCooccurrence[];
}
