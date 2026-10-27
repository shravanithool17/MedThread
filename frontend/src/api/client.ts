import type {
  AppState,
  Cooccurrence,
  ConceptExplorerResult,
  ComparisonResult,
  EvaluationResult,
  ImportNote,
  ImportPreview,
  ImportResult,
  Mention,
  Note,
  NoteDetail,
  ReviewState,
  Stats,
  TimelineResponse,
} from '../types';

const BASE = '/api';
const SESSION_STORAGE_KEY = 'medthread-review-session';

function getReviewSession(): string {
  if (typeof window === 'undefined') return 'server-render';
  let sessionId = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    window.sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  return sessionId;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  headers.set('X-MedThread-Session', getReviewSession());
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const body = JSON.parse(text) as { detail?: unknown };
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) {
        message = body.detail.map(issue => {
          if (typeof issue === 'object' && issue !== null) {
            const item = issue as { row?: number; field?: string; message?: string; msg?: string };
            const where = [item.row ? `Row ${item.row}` : '', item.field ?? ''].filter(Boolean).join(', ');
            return `${where ? `${where}: ` : ''}${item.message ?? item.msg ?? JSON.stringify(issue)}`;
          }
          return String(issue);
        }).join('\n');
      } else if (body.detail !== undefined) message = JSON.stringify(body.detail);
    } catch {
      // Keep plain-text API errors intact.
    }
    throw new Error(`${res.status}: ${message}`);
  }
  return res.json() as Promise<T>;
}

async function downloadCsv(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'X-MedThread-Session': getReviewSession() },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = path.endsWith('review.csv')
    ? 'medthread_review.csv'
    : 'medthread_mentions.csv';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function buildQuery(params?: Record<string, string | undefined>): string {
  if (!params) return '';
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) p.set(k, v);
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

export const api = {
  health: () =>
    request<{ status: string; pipeline_run: boolean; n_notes: number }>('/health'),

  getState: () => request<AppState>('/state'),

  loadDemo: () =>
    request<{ message: string; n_notes: number }>('/demo', { method: 'POST' }),

  reset: () => request<{ message: string }>('/reset', { method: 'POST' }),

  getStats: () => request<Stats>('/stats'),

  getNotes: (patient_id?: string) =>
    request<Note[]>(`/notes${buildQuery({ patient_id })}`),

  getNote: (note_id: string) => request<NoteDetail>(`/notes/${encodeURIComponent(note_id)}`),

  getPatients: () => request<string[]>('/patients'),

  getMentions: (params?: { patient_id?: string; note_id?: string; entity?: string; context?: string }) =>
    request<Mention[]>(`/mentions${buildQuery(params)}`),

  getCooccurrence: () => request<Cooccurrence[]>('/cooccurrence'),

  getConceptExplorer: (params?: {
    patient_id?: string;
    start_date?: string;
    end_date?: string;
    context?: string;
  }) => request<ConceptExplorerResult>(`/concepts${buildQuery(params)}`),

  getComparison: (params?: { patient_id?: string; status?: string }) =>
    request<ComparisonResult[]>(`/comparison${buildQuery(params)}`),

  getTimeline: (patient_id: string) =>
    request<TimelineResponse>(`/timeline/${encodeURIComponent(patient_id)}`),

  getReview: (params?: { patient_id?: string; show_all?: string }) =>
    request<ComparisonResult[]>(`/review${buildQuery(params)}`),

  updateReview: (key: string, state: ReviewState, rationale = '') =>
    request<{ key: string; state: ReviewState; rationale: string; updated_at: string }>(`/review/${encodeURIComponent(key)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state, rationale }),
    }),

  getEvaluation: () => request<EvaluationResult>('/evaluation/demo'),

  getLexicon: () => request<Record<string, string[]>>('/lexicon'),

  uploadNotes: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<{ message: string; n_notes: number; n_errors: number; errors: string[] }>(
      '/upload',
      { method: 'POST', body: form },
    );
  },

  previewNotes: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<ImportPreview>('/notes/preview', { method: 'POST', body: form });
  },

  importNotes: (notes: ImportNote[], mode: 'replace' | 'append') =>
    request<ImportResult>('/notes/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes, mode }),
    }),

  downloadMentions: () => downloadCsv('/export/mentions.csv'),

  downloadReview: () => downloadCsv('/export/review.csv'),
};
