import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Calendar, FileText, Search, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ContextBadge from '../components/ContextBadge'
import HighlightedText from '../components/HighlightedText'
import LoadingSpinner from '../components/LoadingSpinner'
import EmptyState from '../components/EmptyState'
import PageWrapper from '../components/PageWrapper'
import type { Mention } from '../types'

export default function NoteExplorer() {
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get('note_id'),
  )
  const [selectedMention, setSelectedMention] = useState<Mention | null>(null)
  const [filter, setFilter] = useState('')
  const notes = useQuery({ queryKey: ['notes'], queryFn: () => api.getNotes() })
  const noteDetail = useQuery({
    queryKey: ['note', selectedNoteId],
    queryFn: () => api.getNote(selectedNoteId!),
    enabled: !!selectedNoteId,
  })
  useEffect(() => {
    const requestedNote = new URLSearchParams(window.location.search).get('note_id')
    if (requestedNote && notes.data?.some(note => note.note_id === requestedNote)) {
      setSelectedNoteId(requestedNote)
    }
  }, [notes.data])
  useEffect(() => setSelectedMention(null), [selectedNoteId])

  const allNotes = notes.data ?? []
  const filtered = filter
    ? allNotes.filter(n =>
        n.note_id.toLowerCase().includes(filter.toLowerCase()) ||
        n.patient_id.toLowerCase().includes(filter.toLowerCase()) ||
        n.text_preview.toLowerCase().includes(filter.toLowerCase()),
      )
    : allNotes

  const detail = noteDetail.data

  return (
    <PageWrapper>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="page-title">Note Explorer</h1>
          <p className="mt-0.5 text-sm text-gray-400">Document view with inline entity highlighting</p>
        </div>
        <Link to="/import" className="btn-secondary">Import Notes</Link>
      </div>
      {notes.isError && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">Could not load notes: {(notes.error as Error).message}</p>}

      <div className="flex min-h-[600px] flex-col gap-5 md:flex-row">
        {/* Left: note list */}
        <div className="flex w-full shrink-0 flex-col gap-2 md:w-64">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="Filter notes…"
              className="w-full pl-8 pr-8 py-2 bg-white border border-ivory-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-teal-200"
            />
            {filter && (
              <button onClick={() => setFilter('')} className="absolute right-2.5 top-1/2 -translate-y-1/2">
                <X size={13} className="text-gray-400 hover:text-gray-600" />
              </button>
            )}
          </div>

          <div className="flex flex-col gap-1.5 overflow-y-auto max-h-[560px] pr-1">
            {notes.isLoading && <LoadingSpinner />}
            {filtered.map(note => (
              <button
                key={note.note_id}
                onClick={() => setSelectedNoteId(note.note_id)}
                className={`text-left rounded-lg px-3 py-2.5 border transition-colors duration-150 ${
                  selectedNoteId === note.note_id
                    ? 'bg-teal-50 border-teal-200 text-teal-800'
                    : 'bg-white border-ivory-200 text-gray-700 hover:bg-ivory-50'
                }`}
              >
                <p className="text-xs font-semibold">{note.note_id}</p>
                <p className="text-[11px] text-gray-400 mt-0.5">{note.patient_id}</p>
                {note.visit_date && (
                  <p className="text-[11px] text-gray-300 flex items-center gap-1 mt-0.5">
                    <Calendar size={10} />{note.visit_date}
                  </p>
                )}
                <p className="text-[11px] text-gray-500 mt-1 line-clamp-2">{note.text_preview}</p>
              </button>
            ))}
            {filtered.length === 0 && !notes.isLoading && (
              <p className="text-xs text-gray-400 text-center py-4">No notes match</p>
            )}
          </div>
        </div>

        {/* Right: note detail */}
        <div className="flex-1 min-w-0">
          {!selectedNoteId && (
            <EmptyState
              icon={FileText}
              title="Select a note"
              description="Choose a clinical note from the list to view it with entity highlights."
            />
          )}

          {noteDetail.isLoading && <LoadingSpinner label="Loading note…" />}
          {noteDetail.isError && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">Could not load note: {(noteDetail.error as Error).message}</p>}

          {detail && (
            <motion.div
              key={detail.note_id}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex flex-col gap-5"
            >
              {/* Note header */}
              <div className="card">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-bold text-gray-900">{detail.note_id}</h2>
                    <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                      <span>{detail.patient_id}</span>
                      {detail.visit_date && (
                        <span className="flex items-center gap-1">
                          <Calendar size={12} />{detail.visit_date}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs text-gray-400">{detail.mentions.length} entities</span>
                </div>
              </div>

              {/* Note text */}
              <div className="card">
                <p className="section-label mb-3">Clinical Note</p>
                <div className="bg-ivory-50 rounded-lg p-4 text-sm">
                  <HighlightedText
                    text={detail.text}
                    mentions={detail.mentions}
                    selectedMention={selectedMention}
                    onMentionClick={setSelectedMention}
                    className="text-gray-700"
                  />
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  A missing highlighted mention is not evidence that a symptom is absent.
                </p>
                {selectedMention && (
                  <div className="mt-3 rounded-lg border border-teal-100 bg-teal-50/60 p-4" aria-live="polite">
                    <p className="section-label mb-2">Selected entity evidence</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <ContextBadge context={selectedMention.context} />
                      <span className="font-semibold capitalize text-gray-800">{selectedMention.entity_normalized}</span>
                      <span className="text-xs text-gray-600">
                        {selectedMention.extraction_method ?? 'Extraction method not provided by API'}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-gray-700">{selectedMention.sentence}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {selectedMention.reason ?? 'No additional context explanation.'}
                      {selectedMention.time_expression ? ` · Time: ${selectedMention.time_expression}` : ''}
                      {selectedMention.normalized_event_date ? ` · Interpreted date: ${selectedMention.normalized_event_date}` : ''}
                    </p>
                  </div>
                )}
                {detail.mentions.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {['affirmed','negated','uncertain','resolved','unclear'].map(ctx => (
                      <span key={ctx} className="flex items-center gap-1 text-xs text-gray-500">
                        <ContextBadge context={ctx} /> highlight
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Mentions */}
              {detail.mentions.length > 0 && (
                <div className="card">
                  <p className="section-label mb-3">Detected Entities ({detail.mentions.length})</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-ivory-200">
                          <th className="text-left pb-2 font-semibold text-gray-600 text-xs">Entity</th>
                          <th className="text-left pb-2 font-semibold text-gray-600 text-xs">Context</th>
                          <th className="text-left pb-2 font-semibold text-gray-600 text-xs">Temporal</th>
                          <th className="text-left pb-2 font-semibold text-gray-600 text-xs">Evidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.mentions.map((m, i) => (
                          <tr
                            key={i}
                            className="border-b border-ivory-100 last:border-0 hover:bg-teal-50/40"
                          >
                            <td className="py-2 pr-3 font-medium text-gray-800 capitalize">
                              <button
                                type="button"
                                onClick={() => setSelectedMention(m)}
                                className="text-left underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700"
                              >
                                {m.entity_normalized}
                              </button>
                            </td>
                            <td className="py-2 pr-3"><ContextBadge context={m.context} /></td>
                            <td className="py-2 pr-3 text-xs text-teal-700">{m.time_expression ?? '—'}</td>
                            <td className="py-2 text-xs text-gray-500 max-w-xs truncate" title={m.sentence}>{m.sentence}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </PageWrapper>
  )
}
