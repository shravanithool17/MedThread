import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileUp, FileText, RotateCcw, Upload } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import EmptyState from '../components/EmptyState'
import LoadingSpinner from '../components/LoadingSpinner'
import PageWrapper from '../components/PageWrapper'
import type { ImportNote, ImportPreview } from '../types'

type ImportMode = 'upload' | 'manual' | 'loaded'

function localDate(): string {
  const today = new Date()
  const offset = today.getTimezoneOffset()
  return new Date(today.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <pre className="whitespace-pre-wrap rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
      {message}
    </pre>
  )
}

export default function ImportNotes() {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<ImportMode>('upload')
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [filename, setFilename] = useState('')
  const [selectedPatient, setSelectedPatient] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [patientId, setPatientId] = useState('')
  const [noteId, setNoteId] = useState('')
  const [visitDate, setVisitDate] = useState(localDate)
  const [text, setText] = useState('')

  const notes = useQuery({ queryKey: ['notes'], queryFn: () => api.getNotes() })
  const patients = useMemo(
    () => [...new Set((notes.data ?? []).map(note => note.patient_id))].sort(),
    [notes.data],
  )
  const visibleNotes = (notes.data ?? []).filter(
    note => !selectedPatient || note.patient_id === selectedPatient,
  )

  const previewUpload = useMutation({
    mutationFn: api.previewNotes,
    onSuccess: result => {
      setPreview(result)
      setSuccessMessage('')
    },
  })
  const importNotes = useMutation({
    mutationFn: ({ rows, strategy }: { rows: ImportNote[]; strategy: 'replace' | 'append' }) =>
      api.importNotes(rows, strategy),
    onSuccess: async result => {
      setSuccessMessage(`${result.message} ${result.total_notes} notes are now loaded; the NLP pipeline extracted ${result.mention_count} mentions.`)
      setPreview(null)
      setFilename('')
      setText('')
      setNoteId('')
      await queryClient.invalidateQueries()
      setMode('loaded')
    },
  })
  const restoreDemo = useMutation({
    mutationFn: api.loadDemo,
    onSuccess: async result => {
      setSuccessMessage(`Restored the bundled synthetic demo dataset (${result.n_notes} notes).`)
      setPreview(null)
      await queryClient.invalidateQueries()
      setMode('loaded')
    },
  })

  function submitManual(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSuccessMessage('')
    importNotes.mutate({
      strategy: 'append',
      rows: [{ patient_id: patientId, note_id: noteId, visit_date: visitDate, text }],
    })
  }

  function selectMode(nextMode: ImportMode) {
    setMode(nextMode)
    setSuccessMessage('')
    previewUpload.reset()
    importNotes.reset()
  }

  const importError = importNotes.error?.message
  const previewError = previewUpload.error?.message
  const demoError = restoreDemo.error?.message

  return (
    <PageWrapper>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="page-title">Clinical Notes</h1>
          <p className="mt-1 text-sm text-gray-500">Import and manage the in-memory note set used by the NLP workspace.</p>
        </div>
        <button
          type="button"
          className="btn-secondary inline-flex items-center gap-2"
          onClick={() => restoreDemo.mutate()}
          disabled={restoreDemo.isPending}
        >
          <RotateCcw size={15} />
          {restoreDemo.isPending ? 'Restoring demo…' : 'Restore synthetic demo'}
        </button>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-amber-950">
        Use synthetic or de-identified notes only. Data remains in backend process memory and is not saved to permanent storage.
        Uploading a file replaces the active note set; manual entry adds a note to the current set.
      </div>

      {successMessage && (
        <div className="rounded-lg border border-teal-200 bg-teal-50 p-4 text-sm text-teal-900" role="status">
          {successMessage}
        </div>
      )}
      {demoError && <ErrorMessage message={`Could not restore the synthetic demo: ${demoError}`} />}
      {notes.isError && <ErrorMessage message={`Could not load notes: ${(notes.error as Error).message}`} />}

      <div className="flex flex-wrap gap-2 border-b border-ivory-200" role="tablist" aria-label="Clinical note workspace">
        {([
          ['upload', 'Upload CSV/JSON'],
          ['manual', 'Enter Manually'],
          ['loaded', 'Loaded Notes'],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            id={`import-tab-${key}`}
            type="button"
            role="tab"
            aria-selected={mode === key}
            aria-controls={`import-panel-${key}`}
            onClick={() => selectMode(key)}
            className={`border-b-2 px-4 py-3 text-sm font-medium ${
              mode === key ? 'border-teal-700 text-teal-800' : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {mode === 'upload' && (
        <section id="import-panel-upload" role="tabpanel" aria-labelledby="import-tab-upload" className="flex flex-col gap-5">
          <div className="card">
            <div className="flex items-start gap-3">
              <FileUp size={19} className="mt-0.5 shrink-0 text-teal-800" />
              <div>
                <h2 className="font-semibold text-gray-800">Choose a CSV or JSON file</h2>
                <p className="mt-1 text-sm text-gray-500">
                  Required fields: <code>patient_id</code>, <code>note_id</code>, <code>visit_date</code>, and <code>text</code>.
                  Dates must be valid; duplicate note IDs are rejected.
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  CSV uses a header row. JSON must be an array of objects. Maximum file size: 10 MB.
                </p>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <label className="btn-primary cursor-pointer">
                <Upload size={15} /> Select CSV/JSON
                <input
                  type="file"
                  accept=".csv,.json,application/json,text/csv"
                  className="sr-only"
                  aria-label="Select CSV or JSON notes file"
                  onChange={event => {
                    const file = event.target.files?.[0]
                    event.target.value = ''
                    if (!file) return
                    setFilename(file.name)
                    setPreview(null)
                    setSuccessMessage('')
                    previewUpload.mutate(file)
                  }}
                />
              </label>
              {filename && <span className="text-sm text-gray-600">{filename}</span>}
            </div>
          </div>

          {previewUpload.isPending && <LoadingSpinner label="Checking rows and dates…" />}
          {previewError && <ErrorMessage message={`Could not preview this file: ${previewError}`} />}

          {preview && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <div className="card py-4">
                  <p className="text-2xl font-bold text-teal-800">{preview.valid_count}</p>
                  <p className="text-xs text-gray-500">Valid rows</p>
                </div>
                <div className="card py-4">
                  <p className="text-2xl font-bold text-red-700">{preview.invalid_count}</p>
                  <p className="text-xs text-gray-500">Invalid rows</p>
                </div>
                <div className="card col-span-2 py-4 sm:col-span-1">
                  <p className="text-2xl font-bold text-gray-700">{preview.row_count}</p>
                  <p className="text-xs text-gray-500">Rows found</p>
                </div>
              </div>

              {preview.errors.length > 0 && (
                <div className="card border-red-100">
                  <h2 className="mb-3 text-sm font-semibold text-red-800">Validation issues</h2>
                  <ul className="flex flex-col gap-2">
                    {preview.errors.map((issue, index) => (
                      <li key={`${issue.row}-${issue.field}-${index}`} className="text-sm text-red-800">
                        <span className="font-semibold">
                          {issue.row > 0 ? `Row ${issue.row}` : 'File'} · {issue.field}:
                        </span>{' '}
                        {issue.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="card">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="font-semibold text-gray-800">Preview of valid notes</h2>
                    <p className="text-xs text-gray-500">Invalid rows are excluded. Review this preview before importing.</p>
                  </div>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={preview.valid_count === 0 || importNotes.isPending}
                    onClick={() => importNotes.mutate({ rows: preview.valid_notes, strategy: 'replace' })}
                  >
                    {importNotes.isPending ? 'Processing NLP…' : `Import ${preview.valid_count} valid notes`}
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-ivory-200 text-xs text-gray-500">
                        <th className="py-2 pr-3">Patient ID</th>
                        <th className="py-2 pr-3">Note ID</th>
                        <th className="py-2 pr-3">Visit date</th>
                        <th className="py-2">Note text preview</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.valid_notes.slice(0, 25).map(note => (
                        <tr key={note.note_id} className="border-b border-ivory-100 align-top">
                          <td className="py-2 pr-3 text-gray-700">{note.patient_id}</td>
                          <td className="py-2 pr-3 text-gray-700">{note.note_id}</td>
                          <td className="py-2 pr-3 text-gray-500">{note.visit_date}</td>
                          <td className="py-2 text-gray-600">{note.text.slice(0, 200)}{note.text.length > 200 ? '…' : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {preview.valid_notes.length > 25 && (
                    <p className="pt-3 text-center text-xs text-gray-400">Showing first 25 of {preview.valid_notes.length} valid notes.</p>
                  )}
                  {preview.valid_notes.length === 0 && (
                    <EmptyState icon={FileText} title="No valid notes to preview" description="Fix the validation issues and select the file again." />
                  )}
                </div>
              </div>
              {importError && <ErrorMessage message={`Import failed: ${importError}`} />}
            </div>
          )}
        </section>
      )}

      {mode === 'manual' && (
        <section id="import-panel-manual" role="tabpanel" aria-labelledby="import-tab-manual" className="card">
          <div className="mb-5">
            <h2 className="font-semibold text-gray-800">Enter a clinical note</h2>
            <p className="mt-1 text-sm text-gray-500">The note is validated, added to the active set, and processed by the same NLP pipeline.</p>
          </div>
          <form onSubmit={submitManual} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
                Patient ID
                <input
                  required maxLength={256} value={patientId} onChange={event => setPatientId(event.target.value)}
                  className="rounded-lg border border-ivory-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200"
                  placeholder="e.g. PATIENT_001"
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
                Note ID
                <input
                  required maxLength={256} value={noteId} onChange={event => setNoteId(event.target.value)}
                  className="rounded-lg border border-ivory-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200"
                  placeholder="Unique note identifier"
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700 sm:col-span-2">
                Visit date
                <input
                  required type="date" value={visitDate} onChange={event => setVisitDate(event.target.value)}
                  className="max-w-sm rounded-lg border border-ivory-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200"
                />
              </label>
            </div>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
              Note text
              <textarea
                required maxLength={250_000} rows={7} value={text} onChange={event => setText(event.target.value)}
                className="resize-y rounded-lg border border-ivory-200 px-3 py-2 text-sm font-normal outline-none focus:ring-2 focus:ring-teal-200"
                placeholder="Enter synthetic or de-identified clinical note text…"
              />
              <span className="text-right text-xs font-normal text-gray-400">{text.length.toLocaleString()} / 250,000 characters</span>
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <button type="submit" className="btn-primary" disabled={importNotes.isPending}>
                {importNotes.isPending ? 'Processing NLP…' : 'Add Note & Run NLP'}
              </button>
              {importError && <p className="text-sm text-red-700" role="alert">{importError}</p>}
            </div>
          </form>
        </section>
      )}

      {mode === 'loaded' && (
        <section id="import-panel-loaded" role="tabpanel" aria-labelledby="import-tab-loaded" className="card">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-semibold text-gray-800">Loaded notes</h2>
              <p className="mt-1 text-sm text-gray-500">
                {visibleNotes.length} of {(notes.data ?? []).length} notes in the active in-memory dataset.
              </p>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              Filter by patient
              <select
                value={selectedPatient}
                onChange={event => setSelectedPatient(event.target.value)}
                className="rounded-lg border border-ivory-200 bg-white px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200"
              >
                <option value="">All patients</option>
                {patients.map(patient => <option key={patient} value={patient}>{patient}</option>)}
              </select>
            </label>
          </div>
          {notes.isLoading && <LoadingSpinner label="Loading notes…" />}
          {visibleNotes.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-ivory-200 text-xs text-gray-500">
                    <th className="py-2 pr-3">Patient</th>
                    <th className="py-2 pr-3">Note ID</th>
                    <th className="py-2 pr-3">Visit date</th>
                    <th className="py-2">Text preview</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleNotes.map(note => (
                    <tr key={note.note_id} className="border-b border-ivory-100 align-top">
                      <td className="py-2 pr-3 text-gray-700">{note.patient_id}</td>
                      <td className="py-2 pr-3">
                        <Link className="text-teal-800 underline" to={`/notes?note_id=${encodeURIComponent(note.note_id)}`}>{note.note_id}</Link>
                      </td>
                      <td className="py-2 pr-3 text-gray-500">{note.visit_date ?? 'Unknown'}</td>
                      <td className="max-w-lg py-2 text-gray-600">{note.text_preview}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!notes.isLoading && visibleNotes.length === 0 && (
            <EmptyState icon={FileText} title="No notes loaded" description="Upload a file, enter a note, or restore the synthetic demo dataset." />
          )}
        </section>
      )}
    </PageWrapper>
  )
}
