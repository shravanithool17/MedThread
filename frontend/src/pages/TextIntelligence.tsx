import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { BarChart2, Download, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ContextBadge from '../components/ContextBadge'
import StatusBadge from '../components/StatusBadge'
import StatCard from '../components/StatCard'
import LoadingSpinner from '../components/LoadingSpinner'
import PageWrapper from '../components/PageWrapper'
import type { ConceptCooccurrence, ExploredConcept, Mention } from '../types'

const CONTEXTS = ['affirmed', 'negated', 'uncertain', 'resolved', 'unclear'] as const
const CONTEXT_COLORS: Record<string, string> = {
  affirmed: '#047857',
  negated: '#b91c1c',
  uncertain: '#b45309',
  resolved: '#1d4ed8',
  unclear: '#374151',
}
const STATUS_COLORS: Record<string, string> = {
  possible_inconsistency: '#ea580c',
  persistent_documented: '#0d7377',
  newly_reported: '#2563eb',
  explicitly_resolved: '#16a34a',
  explicitly_negated: '#dc2626',
  not_documented: '#6b7280',
  unclear: '#ca8a04',
}

interface ExplorerFilters {
  patient_id: string
  start_date: string
  end_date: string
  context: string
}

export default function TextIntelligence() {
  const [filters, setFilters] = useState<ExplorerFilters>({
    patient_id: '',
    start_date: '',
    end_date: '',
    context: '',
  })
  const [selectedConcept, setSelectedConcept] = useState('')
  const [selectedPair, setSelectedPair] = useState('')
  const [entitySearch, setEntitySearch] = useState('')

  const patients = useQuery({ queryKey: ['patients'], queryFn: api.getPatients })
  const explorer = useQuery({
    queryKey: ['concept-explorer', filters],
    queryFn: () => api.getConceptExplorer({
      patient_id: filters.patient_id || undefined,
      start_date: filters.start_date || undefined,
      end_date: filters.end_date || undefined,
      context: filters.context || undefined,
    }),
  })
  const mentions = useQuery({ queryKey: ['mentions'], queryFn: () => api.getMentions() })
  const comparison = useQuery({ queryKey: ['comparison'], queryFn: () => api.getComparison() })
  const stats = useQuery({ queryKey: ['stats'], queryFn: api.getStats })
  const exportMentions = useMutation({ mutationFn: api.downloadMentions })

  const result = explorer.data
  const concepts = result?.concepts ?? []
  const pairs = result?.cooccurrences ?? []
  const selectedConceptData = concepts.find(item => item.entity_normalized === selectedConcept) ?? concepts[0]
  const selectedPairData = pairs.find(pair => pairKey(pair) === selectedPair)
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const item of comparison.data ?? []) counts[item.status] = (counts[item.status] ?? 0) + 1
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [comparison.data])

  const filteredMentions = useMemo(() => {
    let rows = mentions.data ?? []
    if (filters.patient_id) rows = rows.filter(row => row.patient_id === filters.patient_id)
    if (filters.start_date) rows = rows.filter(row => row.visit_date !== null && row.visit_date >= filters.start_date)
    if (filters.end_date) rows = rows.filter(row => row.visit_date !== null && row.visit_date <= filters.end_date)
    if (filters.context) rows = rows.filter(row => row.context === filters.context)
    if (entitySearch) rows = rows.filter(row => row.entity_normalized.toLowerCase().includes(entitySearch.toLowerCase()))
    return rows.slice(0, 100)
  }, [mentions.data, filters, entitySearch])

  function updateFilter<K extends keyof ExplorerFilters>(key: K, value: ExplorerFilters[K]) {
    setFilters(current => ({ ...current, [key]: value }))
    setSelectedConcept('')
    setSelectedPair('')
  }

  if (explorer.isLoading || patients.isLoading) return <LoadingSpinner label="Exploring extracted concepts…" />

  return (
    <PageWrapper>
      <header>
        <h1 className="page-title">Medical Concept Explorer</h1>
        <p className="mt-0.5 text-sm text-gray-400">
          Explore concepts extracted from notes in the active dataset and trace each result to source text.
        </p>
      </header>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-950">
        Counts describe detected text mentions only. Textual co-occurrence does not establish causation,
        diagnosis, disease prevalence, or a clinical relationship.
      </div>

      {(explorer.isError || patients.isError || mentions.isError || comparison.isError || stats.isError) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
          Could not load all concept explorer data:
          {[explorer, patients, mentions, comparison, stats]
            .filter(query => query.isError)
            .map(query => (query.error as Error).message)
            .join(' · ')}
        </div>
      )}

      <section className="card" aria-label="Concept filters">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <label className="text-xs font-medium text-gray-600">
            Patient
            <select
              value={filters.patient_id}
              onChange={event => updateFilter('patient_id', event.target.value)}
              className="mt-1 block w-full rounded-lg border border-ivory-200 bg-ivory-50 px-3 py-2 text-sm"
            >
              <option value="">All patients</option>
              {(patients.data ?? []).map(patient => <option key={patient} value={patient}>{patient}</option>)}
            </select>
          </label>
          <label className="text-xs font-medium text-gray-600">
            From date
            <input
              type="date"
              value={filters.start_date}
              max={filters.end_date || undefined}
              onChange={event => updateFilter('start_date', event.target.value)}
              className="mt-1 block w-full rounded-lg border border-ivory-200 bg-ivory-50 px-3 py-2 text-sm"
            />
          </label>
          <label className="text-xs font-medium text-gray-600">
            Through date
            <input
              type="date"
              value={filters.end_date}
              min={filters.start_date || undefined}
              onChange={event => updateFilter('end_date', event.target.value)}
              className="mt-1 block w-full rounded-lg border border-ivory-200 bg-ivory-50 px-3 py-2 text-sm"
            />
          </label>
          <label className="text-xs font-medium text-gray-600">
            Mention context
            <select
              value={filters.context}
              onChange={event => updateFilter('context', event.target.value)}
              className="mt-1 block w-full rounded-lg border border-ivory-200 bg-ivory-50 px-3 py-2 text-sm"
            >
              <option value="">All contexts</option>
              {CONTEXTS.map(context => <option key={context} value={context}>{context}</option>)}
            </select>
          </label>
        </div>
      </section>

      {stats.data && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard value={stats.data.n_patients} label="Active patients" delay={0} />
          <StatCard value={stats.data.n_notes} label="Active notes" delay={0.05} />
          <StatCard value={result?.mentions ?? 0} label="Filtered mentions" delay={0.1} />
          <StatCard value={concepts.length} label="Concepts in filter" delay={0.15} />
        </div>
      )}

      {explorer.isFetching && <LoadingSpinner label="Updating concept results…" />}
      {result && result.mentions === 0 && (
        <div className="card py-10 text-center" role="status">
          <p className="font-semibold text-gray-700">No extracted mentions match these filters</p>
          <p className="mt-1 text-sm text-gray-500">Try a wider date range, another patient, or a different context.</p>
          <Link to="/import" className="btn-primary mt-4 inline-flex">Import Notes</Link>
        </div>
      )}

      {result && result.mentions > 0 && (
        <>
          <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <div className="card">
              <div className="mb-3">
                <p className="section-label">Concept Frequencies & Contexts</p>
                <p className="mt-1 text-xs text-gray-500">Frequency is mention count in filtered notes, not patient prevalence.</p>
              </div>
              <div className="max-h-[28rem] space-y-2 overflow-y-auto">
                {concepts.map((concept, index) => (
                  <ConceptRow
                    key={concept.entity_normalized}
                    concept={concept}
                    maxCount={concepts[0]?.mention_count ?? 1}
                    selected={selectedConceptData?.entity_normalized === concept.entity_normalized && !selectedPairData}
                    onClick={() => {
                      setSelectedConcept(concept.entity_normalized)
                      setSelectedPair('')
                    }}
                    index={index}
                  />
                ))}
              </div>
            </div>

            <div className="card">
              <div className="mb-3">
                <p className="section-label">Note-Level Co-occurrence</p>
                <p className="mt-1 text-xs text-gray-500">
                  Each connection means both concepts were extracted in the same source note; it is descriptive only.
                </p>
              </div>
              <div className="max-h-[28rem] space-y-2 overflow-y-auto">
                {pairs.map(pair => (
                  <button
                    key={pairKey(pair)}
                    type="button"
                    aria-pressed={selectedPair === pairKey(pair)}
                    onClick={() => {
                      setSelectedPair(pairKey(pair))
                      setSelectedConcept('')
                    }}
                    className={`flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                      selectedPair === pairKey(pair)
                        ? 'border-teal-300 bg-teal-50'
                        : 'border-ivory-200 bg-ivory-50 hover:border-teal-200'
                    }`}
                  >
                    <span className="font-medium text-gray-800">
                      {pair.entity_a} <span className="mx-1 text-gray-400">+</span> {pair.entity_b}
                    </span>
                    <span className="shrink-0 text-xs text-gray-500">{pair.note_count} notes</span>
                  </button>
                ))}
                {pairs.length === 0 && (
                  <p className="py-8 text-center text-sm text-gray-400">
                    No concept pairs were detected together in a source note for this selection.
                  </p>
                )}
              </div>
            </div>
          </section>

          <EvidenceInspector
            concept={selectedPairData ? undefined : selectedConceptData}
            pair={selectedPairData}
          />
        </>
      )}

      <section className="card">
        <p className="section-label mb-4">Consistency Signals</p>
        <p className="mb-3 text-xs text-gray-500">Rule-based statuses from actual extracted mentions; not diagnoses.</p>
        <div className="flex flex-wrap items-end gap-3">
          {statusCounts.map(([status, count]) => {
            const max = Math.max(...statusCounts.map(([, value]) => value), 1)
            return (
              <div key={status} className="flex min-w-[80px] flex-col items-center gap-1.5 text-center">
                <span className="text-sm font-bold text-gray-800">{count}</span>
                <div className="flex h-16 w-full flex-col justify-end overflow-hidden rounded bg-ivory-200">
                  <div className="w-full rounded transition-all" style={{
                    height: `${Math.round(count / max * 100)}%`,
                    backgroundColor: STATUS_COLORS[status] ?? '#6b7280',
                  }} />
                </div>
                <StatusBadge status={status} size="sm" />
              </div>
            )
          })}
          {statusCounts.length === 0 && <p className="text-sm text-gray-400">No comparison data</p>}
        </div>
      </section>

      <section className="card">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <p className="section-label flex-1">Source Mention Browser</p>
          <button
            type="button"
            className="btn-secondary inline-flex items-center gap-1.5 text-xs"
            onClick={() => exportMentions.mutate()}
            disabled={exportMentions.isPending}
          >
            <Download size={13} /> {exportMentions.isPending ? 'Preparing…' : 'Export all CSV'}
          </button>
          <label className="relative">
            <span className="sr-only">Filter mention concepts</span>
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={entitySearch}
              onChange={event => setEntitySearch(event.target.value)}
              placeholder="Filter concept…"
              className="w-36 rounded-lg border border-ivory-200 bg-ivory-50 py-1.5 pl-7 pr-3 text-xs outline-none focus:ring-2 focus:ring-teal-100"
            />
          </label>
          <BarChart2 size={15} className="text-gray-300" />
        </div>
        {exportMentions.isError && <p className="mb-3 text-xs text-red-700" role="alert">Export failed: {exportMentions.error.message}</p>}
        {mentions.isLoading ? <LoadingSpinner label="Loading source mentions…" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ivory-200">
                  {['Patient', 'Note', 'Date', 'Concept', 'Context', 'Sentence'].map(label => (
                    <th key={label} className="pb-2 pr-4 text-left text-xs font-semibold text-gray-500">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredMentions.map((mention, index) => <MentionRow key={`${mention.note_id}-${index}`} mention={mention} />)}
              </tbody>
            </table>
            {filteredMentions.length === 0 && <p className="py-8 text-center text-sm text-gray-400">No mentions match the selected filters.</p>}
            {filteredMentions.length === 100 && <p className="pt-2 text-center text-xs text-gray-400">Showing first 100 matches.</p>}
          </div>
        )}
      </section>
    </PageWrapper>
  )
}

function pairKey(pair: ConceptCooccurrence): string {
  return `${pair.entity_a}\u0000${pair.entity_b}`
}

function ConceptRow({
  concept, maxCount, selected, onClick, index,
}: {
  concept: ExploredConcept
  maxCount: number
  selected: boolean
  onClick: () => void
  index: number
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`w-full rounded-lg border px-3 py-2.5 text-left transition-colors ${
        selected ? 'border-teal-300 bg-teal-50' : 'border-ivory-200 hover:border-teal-200'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium capitalize text-gray-800">{concept.entity_normalized}</span>
        <span className="shrink-0 text-xs text-gray-500">
          {concept.mention_count} mentions · {concept.note_count} notes
        </span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ivory-200" aria-hidden="true">
        <div className="h-full rounded-full bg-teal-700" style={{ width: `${Math.max(4, concept.mention_count / maxCount * 100)}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {Object.entries(concept.context_counts).map(([context, count]) => (
          <span key={context} className="inline-flex items-center gap-1 text-[11px] text-gray-600">
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: CONTEXT_COLORS[context] ?? '#9ca3af' }} />
            {context} {count}
          </span>
        ))}
      </div>
      <span className="sr-only">Concept rank {index + 1}</span>
    </button>
  )
}

function EvidenceInspector({ concept, pair }: { concept?: ExploredConcept; pair?: ConceptCooccurrence }) {
  if (pair) {
    return (
      <section className="card" aria-live="polite">
        <div className="mb-3">
          <p className="section-label">Relationship Evidence</p>
          <h2 className="mt-1 font-semibold text-gray-800">{pair.entity_a} + {pair.entity_b}</h2>
          <p className="text-xs text-gray-500">Detected together in {pair.note_count} source notes.</p>
        </div>
        <EvidenceNotes notes={pair.evidence.map(source => ({
          patient_id: source.patient_id,
          note_id: source.note_id,
          visit_date: source.visit_date,
          mentions: source.mentions,
        }))} />
      </section>
    )
  }
  if (!concept) return null
  return (
    <section className="card" aria-live="polite">
      <div className="mb-3">
        <p className="section-label">Concept Evidence</p>
        <h2 className="mt-1 font-semibold capitalize text-gray-800">{concept.entity_normalized}</h2>
        <p className="text-xs text-gray-500">{concept.mention_count} extracted mentions across {concept.note_count} notes.</p>
      </div>
      <EvidenceNotes notes={groupConceptEvidence(concept)} />
    </section>
  )
}

function groupConceptEvidence(concept: ExploredConcept) {
  const groups = new Map<string, {
    patient_id: string
    note_id: string
    visit_date: string | null
    mentions: ExploredConcept['evidence']
  }>()
  for (const mention of concept.evidence) {
    const group = groups.get(mention.note_id) ?? {
      patient_id: mention.patient_id,
      note_id: mention.note_id,
      visit_date: mention.visit_date,
      mentions: [],
    }
    group.mentions.push(mention)
    groups.set(mention.note_id, group)
  }
  return [...groups.values()]
}

function EvidenceNotes({ notes }: { notes: Array<{
  patient_id: string
  note_id: string
  visit_date: string | null
  mentions: Mention[] | ExploredConcept['evidence']
}> }) {
  return (
    <div className="max-h-[28rem] space-y-3 overflow-y-auto">
      {notes.map(note => (
        <article key={`${note.patient_id}-${note.note_id}`} className="rounded-lg border border-ivory-200 bg-ivory-50 p-3">
          <header className="mb-2 flex flex-wrap items-center gap-2 text-xs">
            <Link className="font-semibold text-teal-800 underline" to={`/notes?note_id=${encodeURIComponent(note.note_id)}`}>
              {note.note_id}
            </Link>
            <span className="text-gray-500">{note.patient_id} · {note.visit_date ?? 'Date not recorded'}</span>
          </header>
          <div className="space-y-2">
            {note.mentions.map((mention, index) => (
              <div key={`${mention.entity_normalized}-${index}`} className="border-t border-ivory-200 pt-2 first:border-0 first:pt-0">
                <div className="mb-1 flex items-center gap-2 text-xs">
                  <span className="font-medium capitalize text-gray-700">{mention.entity_normalized}</span>
                  <ContextBadge context={mention.context} />
                </div>
                <p className="text-sm leading-relaxed text-gray-700">{mention.sentence}</p>
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  )
}

function MentionRow({ mention }: { mention: Mention }) {
  return (
    <tr className="border-b border-ivory-100 last:border-0 hover:bg-ivory-50">
      <td className="py-2 pr-4 text-xs text-gray-600">{mention.patient_id}</td>
      <td className="py-2 pr-4 text-xs">
        <Link className="text-teal-800 underline" to={`/notes?note_id=${encodeURIComponent(mention.note_id)}`}>
          {mention.note_id}
        </Link>
      </td>
      <td className="py-2 pr-4 text-xs text-gray-400">{mention.visit_date ?? '—'}</td>
      <td className="py-2 pr-4 text-xs font-medium capitalize text-gray-800">{mention.entity_normalized}</td>
      <td className="py-2 pr-4"><ContextBadge context={mention.context} /></td>
      <td className="max-w-sm py-2 text-xs text-gray-500">{mention.sentence}</td>
    </tr>
  )
}
