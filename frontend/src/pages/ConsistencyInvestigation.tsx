import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, ChevronDown, ChevronRight, Download, Scale, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import ContextBadge from '../components/ContextBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import EmptyState from '../components/EmptyState'
import PageWrapper from '../components/PageWrapper'
import type { ComparisonResult, EvidenceItem, ReviewState } from '../types'
import { formatTemporalComparison } from '../utils/temporalEvidence'

const REVIEW_OPTIONS: ReviewState[] = [
  'confirmed_inconsistency',
  'not_a_contradiction',
  'needs_further_review',
]
const REVIEW_LABELS: Record<ReviewState, string> = {
  unreviewed:           'Unreviewed',
  confirmed_inconsistency: 'Confirmed inconsistency',
  not_a_contradiction:  'Not a contradiction',
  needs_further_review: 'Needs further review',
  reviewed:             'Reviewed — no action (legacy)',
  needs_follow_up:      'Needs follow-up (legacy)',
}

function evidenceNoteUrl(patientId: string, evidence: EvidenceItem): string {
  const params = new URLSearchParams({
    note_id: evidence.note_id,
    patient_id: patientId,
    timeline_note_id: evidence.note_id,
    from_timeline: '1',
  })
  if (evidence.offset_validated && evidence.char_start != null && evidence.char_end != null) {
    params.set('mention_start', String(evidence.char_start))
    params.set('mention_end', String(evidence.char_end))
  }
  return `/notes?${params.toString()}`
}

function ReviewCard({
  item,
  onUpdate,
  isSaving,
  savedState,
}: {
  item: ComparisonResult
  onUpdate: (key: string, state: ReviewState, rationale: string) => void
  isSaving: boolean
  savedState: ReviewState | undefined
}) {
  const [open, setOpen] = useState(false)
  const [rationale, setRationale] = useState(item.review_rationale ?? '')
  useEffect(() => setRationale(item.review_rationale ?? ''), [item.review_rationale, item.review_updated_at])
  const evidence: EvidenceItem[] = item.evidence ?? []
  const evidenceByNote = evidence.reduce<Record<string, EvidenceItem[]>>((groups, source) => {
    groups[source.note_id] = [...(groups[source.note_id] ?? []), source]
    return groups
  }, {})
  const evidenceNoteIds = Object.keys(evidenceByNote)
  return (
    <div className="card">
      {/* Header row */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={`review-evidence-${encodeURIComponent(item.review_key)}`}
        className="w-full flex items-center gap-3 text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-800 capitalize">{item.entity}</span>
            <StatusBadge status={item.status} />
            <span className="text-xs text-gray-400">{item.patient_id}</span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5 truncate">{item.explanation}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {item.review_state !== 'unreviewed' && (
            <CheckCircle size={14} className="text-teal-600" />
          )}
          {open ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
        </div>
      </button>

      {/* Expanded evidence */}
      <AnimatePresence>
        {open && (
          <motion.div
            id={`review-evidence-${encodeURIComponent(item.review_key)}`}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-4 grid grid-cols-1 gap-4 border-t border-ivory-200 pt-4 lg:grid-cols-2">
              {/* Evidence sentences */}
              <div>
                <p className="section-label mb-2">Source Evidence</p>
                <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
                  {evidenceNoteIds.map(noteId => {
                    const sources = evidenceByNote[noteId]
                    const source = sources[0]
                    return (
                    <div key={noteId} className="rounded-lg border border-ivory-200 bg-ivory-50 px-3 py-3 text-xs text-gray-700">
                      <div className="mb-1 flex flex-wrap items-center gap-2">
                        <Link
                          className="font-semibold text-teal-800 underline"
                          to={evidenceNoteUrl(item.patient_id, source)}
                        >
                          {noteId}
                        </Link>
                        <span className="text-gray-500">{source.visit_date ?? 'Date not recorded'}</span>
                      </div>
                      <div className="mt-2 flex flex-col gap-3">
                        {sources.map((mention, index) => (
                          <div key={`${mention.context}-${index}`} className="border-t border-ivory-200 pt-2 first:border-0 first:pt-0">
                            <div className="mb-1 flex flex-wrap items-center gap-2">
                              <ContextBadge context={mention.context} />
                              {(mention.time_expression || mention.normalized_event_date) && (
                                <span className="text-[11px] text-teal-800">
                                  {mention.time_expression ? `Time: ${mention.time_expression}` : ''}
                                  {mention.time_expression && mention.normalized_event_date ? ' · ' : ''}
                                  {mention.normalized_event_date ? `Interpreted date: ${mention.normalized_event_date}` : ''}
                                </span>
                              )}
                            </div>
                            <p>{mention.sentence}</p>
                            {mention.offset_validated && mention.char_start != null && mention.char_end != null && (
                              <p className="mt-1 text-[10px] text-gray-500">
                                Mention span: [{mention.char_start}, {mention.char_end}) Unicode code points
                              </p>
                            )}
                            {mention.reason && <p className="mt-1 text-[11px] text-gray-500">{mention.reason}</p>}
                            <Link
                              className="mt-1 inline-flex text-[11px] font-semibold text-teal-800 underline"
                              to={evidenceNoteUrl(item.patient_id, mention)}
                            >
                              {mention.offset_validated ? 'Open exact source span' : 'Open source note'}
                            </Link>
                          </div>
                        ))}
                      </div>
                    </div>
                    )
                  })}
                  {evidence.length === 0 && <p className="text-xs text-gray-400">No structured evidence was returned.</p>}
                </div>
                <p className="mt-2 text-[11px] text-gray-500">
                  A missing mention is not treated as an absent symptom. Compare only documented evidence.
                </p>
              </div>

              {/* Rule trace + review */}
              <div className="flex flex-col gap-4">
                <div>
                  <p className="section-label mb-2">Exact Triggering Rule</p>
                  <p className="text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2 font-mono">
                    {item.rule_trace || '—'}
                  </p>
                  <p className="mt-2 text-xs text-gray-500">{item.explanation}</p>
                  <p className="mt-2 text-xs text-gray-600">
                    Automated flag: <span className="font-semibold">{item.status.replace(/_/g, ' ')}</span>
                    {' · '}Reviewer conclusion: <span className="font-semibold">{REVIEW_LABELS[item.review_state]}</span>
                  </p>
                  {['newly_reported', 'explicitly_resolved', 'explicitly_negated', 'persistent_documented', 'not_documented'].includes(item.status) && (
                    <p className="mt-2 rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-900">
                      This label describes a documented temporal change or charting pattern; it is not, by itself, a contradiction.
                    </p>
                  )}
                  {item.status === 'possible_inconsistency' && (
                    <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
                      This is a rule-based review flag, not a confirmed contradiction. Use the dated source sentences and clinical context for review.
                    </p>
                  )}
                  {item.temporal_comparisons?.length > 0 && (
                    <div className="mt-3 rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-900">
                      <p className="font-semibold">Pairwise temporal evidence</p>
                      <ul className="mt-1 flex flex-col gap-1">
                        {item.temporal_comparisons.map((pair, index) => (
                          <li key={`${pair.first_note_id}-${pair.second_note_id}-${index}`}>
                            {pair.first_note_id} ({pair.first_context}, visit {pair.first_visit_date ?? 'date unknown'})
                            {' vs '}
                            {pair.second_note_id} ({pair.second_context}, visit {pair.second_visit_date ?? 'date unknown'}):
                            {' '}
                            {formatTemporalComparison(pair)}
                          </li>
                        ))}
                      </ul>
                      <p className="mt-1">Visit dates are shown as note metadata; a visit-date difference alone is not treated as an event-date difference.</p>
                    </div>
                  )}
                </div>

                <div>
                  <p className="section-label mb-2">Review Decision</p>
                  <p className="mb-2 text-xs text-gray-500">
                    These are session-level prototype annotations; they do not update a clinical record.
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {REVIEW_OPTIONS.map(opt => (
                      <label
                        key={opt}
                        className="flex items-center gap-2 text-xs cursor-pointer group"
                      >
                        <input
                          type="radio"
                          name={`review-${item.review_key}`}
                          value={opt}
                          checked={item.review_state === opt}
                          disabled={isSaving}
                          onChange={() => onUpdate(item.review_key, opt, rationale)}
                          className="accent-teal-700"
                        />
                        <span className={`group-hover:text-gray-800 transition-colors ${item.review_state === opt ? 'text-teal-800 font-semibold' : 'text-gray-500'}`}>
                          {REVIEW_LABELS[opt]}
                        </span>
                      </label>
                    ))}
                  </div>
                  <label className="mt-3 block text-xs font-medium text-gray-700" htmlFor={`rationale-${item.review_key}`}>
                    Reviewer rationale (optional)
                  </label>
                  <textarea
                    id={`rationale-${item.review_key}`}
                    value={rationale}
                    onChange={event => setRationale(event.target.value)}
                    maxLength={4000}
                    rows={3}
                    className="mt-1 w-full rounded-md border border-ivory-200 bg-white p-2 text-sm text-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700"
                  />
                  <button
                    type="button"
                    className="btn-secondary mt-2 self-start text-xs"
                    disabled={isSaving || rationale === item.review_rationale}
                    onClick={() => onUpdate(item.review_key, item.review_state, rationale)}
                  >
                    Save rationale
                  </button>
                  {isSaving && <p className="mt-2 text-xs text-gray-500" role="status">Saving review annotation…</p>}
                  {!isSaving && savedState && item.review_state === savedState && (
                    <p className="mt-2 text-xs text-teal-800" role="status">
                      Saved: {REVIEW_LABELS[savedState]}
                      {item.review_updated_at ? ` · ${new Date(item.review_updated_at).toLocaleString()}` : ''}.
                    </p>
                  )}
                  {item.review_rationale && (
                    <p className="mt-2 whitespace-pre-wrap text-xs text-gray-600">
                      Saved rationale: {item.review_rationale}
                    </p>
                  )}
                  {item.review_history?.length > 0 && (
                    <div className="mt-3 border-t border-ivory-200 pt-3">
                      <p className="section-label mb-2">Review history</p>
                      <ol className="flex flex-col gap-2">
                        {item.review_history.map((event, index) => (
                          <li key={`${event.created_at}-${index}`} className="text-xs text-gray-600">
                            <span className="font-semibold">{REVIEW_LABELS[event.state] ?? event.state}</span>
                            <span className="ml-2 text-gray-400">{new Date(event.created_at).toLocaleString()}</span>
                            {event.rationale && <p className="mt-0.5 whitespace-pre-wrap">{event.rationale}</p>}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function ConsistencyInvestigation() {
  const qc = useQueryClient()
  const [showAll, setShowAll] = useState(false)
  const [patientFilter, setPatientFilter] = useState('')
  const [exportError, setExportError] = useState('')

  const review = useQuery({
    queryKey: ['review', showAll, patientFilter],
    queryFn: () => api.getReview({ show_all: showAll ? 'true' : undefined, patient_id: patientFilter || undefined }),
  })

  const patients = useQuery({ queryKey: ['patients'], queryFn: api.getPatients })

  const updateReview = useMutation({
    mutationFn: ({ key, state, rationale }: { key: string; state: ReviewState; rationale: string }) =>
      api.updateReview(key, state, rationale),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['review'] }),
  })
  const exportReview = useMutation({
    mutationFn: api.downloadReview,
    onSuccess: () => setExportError(''),
    onError: error => setExportError(error.message),
  })

  const items = review.data ?? []
  const statusCounts = items.reduce<Record<string, number>>((acc, item) => {
    acc[item.status] = (acc[item.status] ?? 0) + 1
    return acc
  }, {})

  return (
    <PageWrapper>
      <div>
        <h1 className="page-title">Consistency Investigation</h1>
        <p className="mt-0.5 text-sm text-gray-400">Side-by-side evidence comparison and review decisions</p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-gray-500">Review decisions and rationale are saved locally under this browser session; they do not update clinical records.</p>
        <button
          type="button"
          className="btn-secondary inline-flex items-center gap-2 text-sm"
          onClick={() => exportReview.mutate()}
          disabled={exportReview.isPending}
        >
          <Download size={14} /> {exportReview.isPending ? 'Preparing CSV…' : 'Export reviewed flags'}
        </button>
      </div>
      {exportError && <p className="text-sm text-red-700" role="alert">CSV export failed: {exportError}</p>}
      {review.isError && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">Could not load review flags: {(review.error as Error).message}</p>}
      {updateReview.isError && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">Could not save this decision: {(updateReview.error as Error).message}</p>}

      {/* Controls */}
      <div className="card flex items-center gap-4">
        <SlidersHorizontal size={15} className="text-gray-400" />
        <select
          value={patientFilter}
          onChange={e => setPatientFilter(e.target.value)}
          className="text-sm bg-transparent outline-none text-gray-700 cursor-pointer"
        >
          <option value="">All patients</option>
          {(patients.data ?? []).map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer ml-auto">
          <input
            type="checkbox"
            checked={showAll}
            onChange={e => setShowAll(e.target.checked)}
            className="accent-teal-700"
          />
          Show all statuses
        </label>
      </div>

      {/* Status summary */}
      {Object.keys(statusCounts).length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {Object.entries(statusCounts).map(([status, count]) => (
            <span key={status} className="flex items-center gap-1.5">
              <StatusBadge status={status} />
              <span className="text-xs text-gray-500">×{count}</span>
            </span>
          ))}
        </div>
      )}

      {/* Items */}
      {review.isLoading && <LoadingSpinner label="Loading review queue…" />}
      {!review.isLoading && !review.isError && items.length === 0 && (
        <EmptyState
          icon={Scale}
          title="No flagged items"
          description="No inconsistencies or unclear statuses found for the current filter."
          action={
            !showAll ? (
              <button className="btn-secondary text-sm" onClick={() => setShowAll(true)}>
                Show all items
              </button>
            ) : undefined
          }
        />
      )}

      <div className="flex flex-col gap-3">
        {items.map(item => (
          <ReviewCard
            key={item.review_key}
            item={item}
            onUpdate={(key, state, rationale) => updateReview.mutate({ key, state, rationale })}
            isSaving={updateReview.isPending && updateReview.variables?.key === item.review_key}
            savedState={updateReview.data?.key === item.review_key ? updateReview.data.state : undefined}
          />
        ))}
      </div>

      {/* Context legend */}
      <div className="card">
        <p className="section-label mb-2">Context Legend</p>
        <div className="flex gap-3 flex-wrap">
          {['affirmed','negated','uncertain','resolved','unclear'].map(ctx => (
            <ContextBadge key={ctx} context={ctx} size="sm" />
          ))}
        </div>
      </div>
    </PageWrapper>
  )
}
