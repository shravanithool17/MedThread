import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FlaskConical, Info, Loader2, Target } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ContextBadge from '../components/ContextBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import PageWrapper from '../components/PageWrapper'

function MetricTile({ value, label, color = '#0d7377' }: { value: number | null; label: string; color?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card text-center"
    >
      <p className="text-3xl font-bold tabular-nums" style={{ color }}>
        {value !== null && Number.isFinite(value) ? (value * 100).toFixed(1) + '%' : '—'}
      </p>
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mt-1">{label}</p>
    </motion.div>
  )
}

function ConfusionMatrix({ matrix, labels }: { matrix: number[][]; labels: string[] }) {
  const maxVal = Math.max(...matrix.flat())
  return (
    <div>
      <p className="section-label mb-3">Confusion Matrix</p>
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-1.5 text-gray-400 text-right text-[10px]">Pred →<br/>Gold ↓</th>
              {labels.map(l => (
                <th key={l} className="p-1.5 font-semibold text-gray-600 text-center">
                  <ContextBadge context={l} size="sm" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, ri) => (
              <tr key={ri}>
                <td className="p-1.5 font-semibold text-gray-600">
                  <ContextBadge context={labels[ri]} size="sm" />
                </td>
                {row.map((cell, ci) => {
                  const intensity = maxVal > 0 ? cell / maxVal : 0
                  const bg = ri === ci
                    ? `rgba(13,115,119,${0.1 + intensity * 0.6})`
                    : cell > 0 ? `rgba(185,28,28,${0.06 + intensity * 0.3})` : 'transparent'
                  return (
                    <td
                      key={ci}
                      className="p-1.5 text-center rounded font-medium tabular-nums"
                      style={{ backgroundColor: bg, color: cell > 0 ? (ri === ci ? '#0d7377' : '#b91c1c') : '#d1d5db', minWidth: 36 }}
                    >
                      {cell}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Evaluation() {
  const eval_ = useQuery({
    queryKey: ['evaluation'],
    queryFn: api.getEvaluation,
    retry: false,
  })

  const d = eval_.data
  const overall = d?.overall ?? {}

  return (
    <PageWrapper>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title">Evaluation Studio</h1>
          <p className="mt-0.5 text-sm text-gray-400">Computed pipeline metrics against explicitly labeled examples</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs text-blue-700">
          <Info size={13} />
          Gold labels: <code className="font-mono">data/gold_annotations.csv</code>
        </div>
      </div>

      {eval_.isLoading && <LoadingSpinner label="Running evaluation against gold annotations…" />}
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-950">
        Evaluation uses only source-aligned examples from the bundled synthetic set. Annotations are not independently reviewed or exhaustive and do not establish clinical validity. Predictions without matching gold annotations are reported as unscorable, not false positives.
      </div>

      {eval_.error && (
        <div className="card border-red-100 bg-red-50 text-red-700 text-sm">
          <div className="flex items-center gap-2 font-semibold mb-1">
            <FlaskConical size={15} /> Evaluation failed
          </div>
          <p className="text-xs">{(eval_.error as Error).message}</p>
        </div>
      )}

      {d && d.n_samples === 0 && (
        <div className="card text-center py-10" role="status">
          <FlaskConical size={26} className="mx-auto mb-3 text-gray-400" />
          <p className="font-semibold text-gray-700">No labeled examples for the active notes</p>
          <p className="mt-1 text-sm text-gray-500">
            {d.message ?? 'Metrics are not calculated when the active note set has no matching gold annotations.'}
          </p>
          <p className="mt-2 text-xs text-gray-400">Restore the synthetic demo to view its labeled evaluation results.</p>
        </div>
      )}

      {d && (
        <section className="card">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="section-label">Benchmark & Annotation Status</p>
              <p className="mt-1 text-sm font-semibold text-gray-800">
                {d.benchmark.benchmark_id ?? 'Benchmark metadata unavailable'}
                {d.benchmark.benchmark_version ? ` · v${d.benchmark.benchmark_version}` : ''}
              </p>
            </div>
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-900">
              {String(d.benchmark.annotation_status ?? 'status not recorded')}
            </span>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-gray-600">{d.benchmark.provenance}</p>
          <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-gray-600 sm:grid-cols-3">
            <p>{d.benchmark.note_count ?? '—'} synthetic source notes · {d.benchmark.patient_group_count ?? '—'} patient groups</p>
            <p>{d.benchmark.context_annotation_count ?? '—'} context annotations · {d.n_context_samples} matched context samples</p>
            <p>{d.benchmark.split_method}</p>
          </div>
          <p className="mt-2 text-xs text-amber-900">{d.benchmark.entity_annotation_coverage}</p>
        </section>
      )}

      {d && (
        <>
          {/* Overall metrics */}
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <MetricTile value={overall.accuracy ?? null}        label="Accuracy"      color="#0d7377" />
            <MetricTile value={overall.macro_precision ?? null} label="Macro precision" color="#1d4ed8" />
            <MetricTile value={overall.macro_recall ?? null}    label="Macro recall"    color="#b45309" />
            <MetricTile value={overall.macro_f1 ?? null}        label="Macro F1"         color="#047857" />
            <MetricTile value={overall.weighted_precision ?? null} label="Weighted precision" color="#1d4ed8" />
            <MetricTile value={overall.weighted_recall ?? null}    label="Weighted recall"    color="#b45309" />
            <MetricTile value={overall.weighted_f1 ?? null}        label="Weighted F1"         color="#047857" />
          </div>
          {d.n_samples > 0 && (
            <p className="text-xs text-gray-400 -mt-2">
              Context metrics use {d.n_context_samples} correctly aligned mentions only; missed extractions are reported separately.
            </p>
          )}

          <section className="card">
            <p className="section-label mb-3">Entity Extraction Coverage</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <MetricTile value={d.entity_metrics.recall} label="Recall on annotated examples" color="#047857" />
              <MetricTile value={d.entity_metrics.precision} label="Precision" color="#1d4ed8" />
              <MetricTile value={d.entity_metrics.f1} label="F1" color="#b45309" />
            </div>
            <p className="mt-3 text-xs text-gray-600">
              {d.entity_metrics.n_matched_examples} matched of {d.entity_metrics.n_annotated_examples - d.entity_metrics.n_unscorable_examples} eligible annotated examples;
              {' '}{d.entity_metrics.n_missed_extractions} missed extractions and {d.entity_metrics.n_unscorable_examples} unscorable alignments.
            </p>
            <p className="mt-1 text-xs text-gray-500">{d.entity_metrics.matching_method}. {d.entity_metrics.limitation}</p>
          </section>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="card py-4 text-center">
              <p className="text-2xl font-bold tabular-nums text-red-700">{d.error_counts.false_positive_context}</p>
              <p className="mt-1 text-[11px] text-gray-500">False-positive context labels</p>
            </div>
            <div className="card py-4 text-center">
              <p className="text-2xl font-bold tabular-nums text-amber-700">{d.error_counts.false_negative_context}</p>
              <p className="mt-1 text-[11px] text-gray-500">False-negative gold labels</p>
            </div>
            <div className="card py-4 text-center">
              <p className="text-2xl font-bold tabular-nums text-amber-700">{d.error_counts.missed_extraction}</p>
              <p className="mt-1 text-[11px] text-gray-500">Gold mentions not predicted</p>
            </div>
            <div className="card py-4 text-center">
              <p className="text-2xl font-bold tabular-nums text-blue-700">{d.error_counts.context_confusion}</p>
              <p className="mt-1 text-[11px] text-gray-500">Context confusions</p>
            </div>
          </div>

          {/* Per-class metrics */}
          {d.per_class.length > 0 && (
            <div className="card">
              <p className="section-label mb-3">Per-Class Metrics</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-ivory-200">
                      {['Context','Precision','Recall','F1','Support'].map(h => (
                        <th key={h} className="text-left pb-2 pr-4 text-xs font-semibold text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.per_class.map((row, i) => {
                      const context = String(row.context ?? row.label ?? `class-${i}`)
                      const fmt = (v: unknown) => typeof v === 'number' ? v.toFixed(3) : '—'
                      return (
                        <tr key={i} className="border-b border-ivory-100 last:border-0">
                          <td className="py-2 pr-4"><ContextBadge context={context} /></td>
                          <td className="py-2 pr-4 tabular-nums">{fmt(row.precision)}</td>
                          <td className="py-2 pr-4 tabular-nums">{fmt(row.recall)}</td>
                          <td className="py-2 pr-4 tabular-nums font-semibold">{fmt(row.f1)}</td>
                          <td className="py-2 pr-4 text-gray-500">{row.support ?? '—'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Confusion matrix */}
          {d.confusion_matrix && d.confusion_labels.length > 0 && (
            <div className="card">
              <ConfusionMatrix matrix={d.confusion_matrix} labels={d.confusion_labels} />
            </div>
          )}

          {/* Errors */}
          {d.errors.length > 0 && (
            <div className="card">
              <div className="mb-3">
                <p className="section-label">Gold-Labeled Error & Confusion Examples ({d.errors.length})</p>
                <p className="mt-1 text-xs text-gray-500">
                  Each example links the expected label and pipeline prediction to the exact annotated source sentence.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-ivory-200">
                      {['Source','Concept','Expected / predicted','Error category','Exact source sentence'].map(h => (
                        <th key={h} className="text-left pb-2 pr-4 text-xs font-semibold text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.errors.slice(0, 50).map((e, i) => (
                      <tr key={i} className="border-b border-ivory-100 last:border-0 hover:bg-ivory-50">
                        <td className="py-2 pr-4 text-xs">
                          {e.note_id
                            ? <Link className="text-teal-800 underline" to={`/notes?note_id=${encodeURIComponent(String(e.note_id))}`}>{String(e.note_id)}</Link>
                            : '—'}
                        </td>
                        <td className="py-2 pr-4 text-xs font-medium text-gray-800 capitalize">{String(e.entity_normalized ?? e.entity ?? '—')}</td>
                        <td className="py-2 pr-4">
                          <div className="flex flex-col items-start gap-1">
                            <span className="text-[10px] text-gray-400">Expected</span>
                            <ContextBadge context={String(e.gold_context ?? 'unclear')} />
                            <span className="mt-1 text-[10px] text-gray-400">Predicted</span>
                            <ContextBadge context={String(e.pred_context ?? 'unclear')} />
                          </div>
                        </td>
                        <td className="py-2 pr-4 text-xs text-gray-600">
                          {e.error_category === 'missed_extraction'
                            ? 'False negative — mention not predicted'
                            : `Context confusion — FP ${String(e.false_positive_label ?? '—')} / FN ${String(e.false_negative_label ?? '—')}`}
                        </td>
                        <td className="py-2 text-xs leading-relaxed text-gray-600">
                          {String(e.sentence ?? 'Source sentence not available')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {d.errors.length > 50 && (
                  <p className="text-xs text-gray-300 text-center pt-2">Showing first 50 of {d.errors.length} errors</p>
                )}
              </div>
            </div>
          )}

          {d.errors.length === 0 && (
            <div className="card text-center py-8">
              <Target size={24} className="text-teal-600 mx-auto mb-2" />
              <p className="text-sm font-semibold text-gray-700">No errors found</p>
              <p className="text-xs text-gray-400 mt-1">No mismatches were returned for the available labeled examples</p>
            </div>
          )}
        </>
      )}

      {d && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <section className="card">
            <p className="section-label">Unscorable Predictions & Exclusions</p>
            <p className="mt-1 text-xs text-gray-600">
              {d.unscorable_predictions.total} predictions have no exact gold match and are excluded from precision/error claims:
              {' '}{d.unscorable_predictions.classification}.
            </p>
            {d.unscorable_predictions.examples.length > 0 && (
              <ul className="mt-3 max-h-48 space-y-1 overflow-y-auto text-xs text-gray-600">
                {d.unscorable_predictions.examples.map((item, index) => (
                  <li key={`${item.note_id}-${item.entity_normalized}-${index}`}>
                    {item.note_id} · {item.entity_normalized} · {item.reason}
                  </li>
                ))}
              </ul>
            )}
            {d.exclusions.length > 0 && (
              <div className="mt-3 border-t border-ivory-200 pt-2">
                <p className="text-xs font-medium text-gray-700">Excluded gold rows: {d.exclusions.length}</p>
                <ul className="mt-1 space-y-1 text-xs text-gray-500">
                  {d.exclusions.slice(0, 20).map((item, index) => (
                    <li key={`${item.note_id}-${item.entity_normalized}-${index}`}>
                      {item.note_id} · {item.entity_normalized} · {item.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {d.annotation_warnings.map((warning, index) => (
              <p key={index} className="mt-2 text-xs text-amber-800">{warning}</p>
            ))}
          </section>
          <section className="card">
            <p className="section-label">Temporal & Longitudinal Evaluation</p>
            <p className="mt-2 text-xs text-gray-600">
              Temporal: {d.temporal_metrics.available ? 'metrics available' : d.temporal_metrics.reason}
            </p>
            <p className="mt-2 text-xs text-gray-600">
              Longitudinal: {d.longitudinal_metrics.available ? 'metrics available' : d.longitudinal_metrics.reason}
            </p>
            <p className="mt-3 text-xs text-gray-500">
              No ML model is fitted. The current benchmark has no train/test split; these are development checks, not held-out estimates.
            </p>
          </section>
        </div>
      )}

      {!eval_.isLoading && !d && !eval_.error && (
        <div className="card text-center py-16">
          <FlaskConical size={28} className="text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Evaluation results will appear here</p>
          <button
            className="btn-primary mt-4"
            onClick={() => eval_.refetch()}
          >
            <Loader2 size={14} className={eval_.isFetching ? 'animate-spin' : ''} />
            Run Evaluation
          </button>
        </div>
      )}
    </PageWrapper>
  )
}
