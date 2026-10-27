import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, ChevronDown, ChevronRight, User } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ContextBadge from '../components/ContextBadge'
import StatusBadge from '../components/StatusBadge'
import HighlightedText from '../components/HighlightedText'
import LoadingSpinner from '../components/LoadingSpinner'
import EmptyState from '../components/EmptyState'
import PageWrapper from '../components/PageWrapper'
import type { Mention, TimelineVisit } from '../types'

function VisitNode({
  visit,
  index,
  selectedMention,
  onSelectMention,
}: {
  visit: TimelineVisit
  index: number
  selectedMention: Mention | null
  onSelectMention: (mention: Mention) => void
}) {
  const [open, setOpen] = useState(false)
  const contextCounts = visit.mentions.reduce<Record<string, number>>((acc, m) => {
    acc[m.context] = (acc[m.context] ?? 0) + 1
    return acc
  }, {})

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.07 }}
      className="relative pl-10"
    >
      {/* Timeline line */}
      <div className="absolute left-3.5 top-0 bottom-0 w-px bg-ivory-200" />
      {/* Dot */}
      <div className="absolute left-2 top-3.5 w-3 h-3 rounded-full bg-teal-700 ring-2 ring-white" />

      <div className="card mb-3">
        {/* Visit header */}
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-3 text-left"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-gray-800 text-sm">{visit.note_id}</span>
              {visit.visit_date && (
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <Calendar size={11} />
                  {visit.visit_date}
                </span>
              )}
              <span className="text-xs text-gray-400">{visit.mentions.length} mention{visit.mentions.length !== 1 ? 's' : ''}</span>
            </div>
            {/* Context summary chips */}
            <div className="flex gap-1.5 flex-wrap mt-1.5">
              {Object.entries(contextCounts).map(([ctx, count]) => (
                <span key={ctx} className="flex items-center gap-1">
                  <ContextBadge context={ctx} size="sm" />
                  <span className="text-xs text-gray-400">×{count}</span>
                </span>
              ))}
              {visit.mentions.length === 0 && (
                <span className="text-xs text-gray-400 italic">No entities detected</span>
              )}
            </div>
          </div>
          {open ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
        </button>

        {/* Expanded note content */}
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22 }}
              className="overflow-hidden"
            >
              <div className="mt-4 pt-4 border-t border-ivory-200">
                <p className="section-label mb-2">Note Text</p>
                <div className="bg-ivory-50 rounded-lg p-4 text-sm text-gray-700">
                  <HighlightedText
                    text={visit.note_text}
                    mentions={visit.mentions}
                    selectedMention={selectedMention}
                    onMentionClick={onSelectMention}
                  />
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  No detected mention means only that this note did not match the current lexicon; it does not mean the symptom was absent.
                </p>

                {visit.mentions.length > 0 && (
                  <div className="mt-4">
                    <p className="section-label mb-2">Documented symptom events</p>
                    <div className="flex flex-col gap-2">
                      {visit.mentions.map((m, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => onSelectMention(m)}
                          aria-pressed={selectedMention === m}
                          className={`w-full rounded-md border p-3 text-left text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700 ${
                            selectedMention === m ? 'border-teal-300 bg-white' : 'border-transparent hover:bg-white'
                          }`}
                        >
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold capitalize text-gray-800">{m.entity_normalized}</span>
                            <ContextBadge context={m.context} />
                            {m.journey_status && <StatusBadge status={m.journey_status} />}
                          </span>
                          <span className="mt-2 block text-[11px] text-gray-500">
                            Source: {m.note_id} · {m.visit_date ?? 'Date not recorded'}
                          </span>
                          <span className="mt-1 block text-xs text-gray-700">{m.sentence}</span>
                          <span className="mt-1 block text-xs text-gray-500">
                            {m.reason ?? 'No additional context explanation.'}
                            {m.time_expression ? ` · Time: ${m.time_expression}` : ''}
                            {m.normalized_event_date ? ` · Interpreted date: ${m.normalized_event_date}` : ''}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {selectedMention?.note_id === visit.note_id && (
                  <div className="mt-4 rounded-lg border border-teal-100 bg-teal-50/60 p-4" aria-live="polite">
                    <p className="section-label mb-2">Mention evidence</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <ContextBadge context={selectedMention.context} />
                      {selectedMention.journey_status && <StatusBadge status={selectedMention.journey_status} />}
                      {selectedMention.time_expression && (
                        <span className="text-xs text-teal-800">Time: {selectedMention.time_expression}</span>
                      )}
                      {selectedMention.normalized_event_date && (
                        <span className="text-xs text-teal-800">Interpreted date: {selectedMention.normalized_event_date}</span>
                      )}
                    </div>
                    <p className="mt-2 text-sm text-gray-700">{selectedMention.sentence}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {selectedMention.reason ?? 'No additional context explanation.'}
                      {selectedMention.extraction_method ? ` · ${selectedMention.extraction_method}` : ''}
                    </p>
                    <Link
                      className="mt-3 inline-flex text-xs font-semibold text-teal-800 underline"
                      to={`/notes?note_id=${encodeURIComponent(visit.note_id)}`}
                    >
                      Open note in NLP inspector
                    </Link>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default function PatientJourney() {
  const [selectedPatient, setSelectedPatient] = useState<string>(
    () => new URLSearchParams(window.location.search).get('patient_id') ?? '',
  )
  const [selectedMention, setSelectedMention] = useState<Mention | null>(null)
  const patients = useQuery({ queryKey: ['patients'], queryFn: api.getPatients })
  const timeline = useQuery({
    queryKey: ['timeline', selectedPatient],
    queryFn: () => api.getTimeline(selectedPatient),
    enabled: !!selectedPatient,
  })

  const patientList = patients.data ?? []
  useEffect(() => {
    if (!patients.data) return
    if (!selectedPatient || !patients.data.includes(selectedPatient)) {
      setSelectedPatient(patients.data[0] ?? '')
    }
  }, [patients.data, selectedPatient])
  useEffect(() => setSelectedMention(null), [selectedPatient])

  return (
    <PageWrapper>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Patient Journey</h1>
          <p className="mt-0.5 text-sm text-gray-400">Interactive clinical visit timeline</p>
        </div>
      </div>

      {patients.isError && (
        <div className="card border-red-200 bg-red-50 text-sm text-red-800" role="alert">
          Could not load patients: {(patients.error as Error).message}
        </div>
      )}
      {!patients.isLoading && !patients.isError && patientList.length === 0 && (
        <EmptyState
          icon={User}
          title="No patients in the active dataset"
          description="Import notes to build a patient-specific journey."
          action={<Link className="btn-primary" to="/import">Import Notes</Link>}
        />
      )}
      {/* Patient selector */}
      <div className="card flex items-center gap-3">
        <User size={16} className="text-gray-400 shrink-0" />
        <select
          className="flex-1 bg-transparent text-sm font-medium text-gray-800 outline-none cursor-pointer"
          value={selectedPatient}
          onChange={e => setSelectedPatient(e.target.value)}
        >
          {patients.isLoading && <option>Loading…</option>}
          {patientList.map(p => <option key={p} value={p}>{p}</option>)}
          {patientList.length === 0 && !patients.isLoading && <option value="">No data loaded</option>}
        </select>
        {timeline.data && (
          <span className="text-xs text-gray-400">{timeline.data.visits.length} visits</span>
        )}
      </div>

      {/* Timeline */}
      {timeline.isLoading && <LoadingSpinner label="Building timeline…" />}
      {timeline.isError && (
        <div className="card border-red-200 bg-red-50 text-sm text-red-800" role="alert">
          Could not load this patient timeline: {(timeline.error as Error).message}
        </div>
      )}
      {!selectedPatient && !timeline.isLoading && (
        <EmptyState icon={User} title="Select a patient" description="Choose a patient from the dropdown above." />
      )}
      {timeline.data && (
        <div className="relative">
          {timeline.data.visits.map((visit, i) => (
            <VisitNode
              key={visit.note_id}
              visit={visit}
              index={i}
              selectedMention={selectedMention}
              onSelectMention={setSelectedMention}
            />
          ))}
          {timeline.data.visits.length === 0 && (
            <EmptyState icon={Calendar} title="No visits found" description="This patient has no notes in the dataset." />
          )}
        </div>
      )}
    </PageWrapper>
  )
}
