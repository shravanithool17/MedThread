import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Activity, AlertTriangle, FileText, Loader2, Users, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import PageWrapper from '../components/PageWrapper'

const QUICK_LINKS = [
  { to: '/journey',      label: 'Patient Journey',    desc: 'Interactive visit timeline',   color: '#0d7377' },
  { to: '/notes',        label: 'Note Explorer',      desc: 'Inline entity highlighting',   color: '#1d4ed8' },
  { to: '/consistency',  label: 'Consistency',        desc: 'Side-by-side evidence review', color: '#b45309' },
  { to: '/intelligence', label: 'Text Intelligence',  desc: 'Concept frequencies & trends', color: '#047857' },
  { to: '/evaluation',   label: 'Evaluation',         desc: 'Precision, recall, F1 scores', color: '#6d28d9' },
]

export default function Home() {
  const qc = useQueryClient()
  const stats = useQuery({ queryKey: ['stats'], queryFn: api.getStats })
  const appState = useQuery({ queryKey: ['app-state'], queryFn: api.getState })
  const review = useQuery({
    queryKey: ['review', 'recent'],
    queryFn: () => api.getReview(),
    enabled: stats.data?.pipeline_run ?? false,
  })

  const loadDemo = useMutation({
    mutationFn: api.loadDemo,
    onSuccess: () => qc.invalidateQueries(),
  })

  if (stats.isLoading) return <LoadingSpinner label="Loading clinical dashboard…" />

  const s = stats.data
  const pipelineRun = s?.pipeline_run ?? false
  const datasetSource = appState.data?.dataset_source
  const datasetLabel = datasetSource === 'synthetic-demo'
    ? 'Synthetic demo data'
    : datasetSource === 'imported'
      ? 'Imported notes'
      : datasetSource === 'manual-entry'
        ? 'Session notes'
        : 'Pipeline active'

  return (
    <PageWrapper>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Clinical Intelligence</h1>
          <p className="mt-1 text-gray-500">See the story behind the notes.</p>
        </div>
        {!pipelineRun && (
          <button
            className="btn-primary"
            onClick={() => loadDemo.mutate()}
            disabled={loadDemo.isPending}
          >
            {loadDemo.isPending ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
            Load Demo Data
          </button>
        )}
        {pipelineRun && (
          <div className="flex items-center gap-2 text-xs text-teal-700 bg-teal-50 border border-teal-100 rounded-full px-3 py-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
            {datasetLabel}
          </div>
        )}
      </div>

      {!pipelineRun ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-md text-center py-16"
        >
          <div className="w-16 h-16 rounded-2xl bg-teal-50 flex items-center justify-center mx-auto mb-4">
            <Zap size={28} className="text-teal-700" />
          </div>
          <h2 className="text-xl font-semibold text-gray-800">Ready to analyse</h2>
          <p className="mt-2 text-gray-500 max-w-sm mx-auto text-sm">
          Import your notes or load the bundled synthetic dataset to run the NLP pipeline and explore the workspace.
          </p>
          <button
            className="btn-primary mt-6"
            onClick={() => loadDemo.mutate()}
            disabled={loadDemo.isPending}
          >
            {loadDemo.isPending ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
            Load Demo Data
          </button>
          <Link to="/import" className="btn-secondary mt-3">
            Import Notes
          </Link>
          <p className="mt-3 text-xs text-gray-300">No API key required. All data is explicitly SYNTHETIC.</p>
        </motion.div>
      ) : (
        <>
          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard value={s!.n_patients}             label="Patients"      icon={Users}         delay={0}    />
            <StatCard value={s!.n_notes}                label="Notes"         icon={FileText}       delay={0.05} />
            <StatCard value={s!.n_mentions}             label="Mentions"      icon={Activity}       delay={0.1}  />
            <StatCard value={s!.n_review_flags}         label="Review Flags"  icon={AlertTriangle}  delay={0.15} accent="#b45309" />
          </div>

          {/* Review signals */}
          <div>
            <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <AlertTriangle size={14} className="text-orange-500" />
              Recent Inconsistency Signals
              {s!.n_possible_inconsistency > 0 && (
                <span className="bg-orange-100 text-orange-700 text-xs rounded-full px-2 py-0.5">
                  {s!.n_possible_inconsistency}
                </span>
              )}
            </h2>
            <div className="flex flex-col gap-2">
              {review.data?.slice(0, 5).map((item) => (
                <motion.div
                  key={item.review_key}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="card flex items-center gap-3 py-3"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-gray-800 capitalize">{item.entity}</span>
                      <StatusBadge status={item.status} />
                      <span className="text-xs text-gray-400">{item.patient_id}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{item.explanation}</p>
                  </div>
                  <Link to="/consistency" className="btn-ghost text-xs">Review →</Link>
                </motion.div>
              ))}
              {(review.data?.length ?? 0) === 0 && (
                <div className="card text-center py-8 text-sm text-gray-400">No inconsistency signals found</div>
              )}
            </div>
          </div>

          {/* Quick nav */}
          <div>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Explore</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {QUICK_LINKS.map(({ to, label, desc, color }) => (
                <Link key={to} to={to}>
                  <motion.div
                    whileHover={{ y: -2 }}
                    className="card hover:shadow-card-md transition-shadow duration-200 cursor-pointer"
                  >
                    <div className="w-2 h-2 rounded-full mb-3" style={{ backgroundColor: color }} />
                    <p className="text-sm font-semibold text-gray-800">{label}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
                  </motion.div>
                </Link>
              ))}
            </div>
            <Link to="/import" className="mt-3 inline-flex text-sm font-semibold text-teal-800 underline">
              Import Notes
            </Link>
          </div>
        </>
      )}
    </PageWrapper>
  )
}
