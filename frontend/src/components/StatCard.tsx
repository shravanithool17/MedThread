import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface Props {
  value: number | string
  label: string
  icon?: LucideIcon
  accent?: string
  delay?: number
}

export default function StatCard({ value, label, icon: Icon, accent = '#0d7377', delay = 0 }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className="card flex flex-col gap-3"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">{label}</span>
        {Icon && (
          <span className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${accent}15` }}>
            <Icon size={16} style={{ color: accent }} />
          </span>
        )}
      </div>
      <span className="text-3xl font-bold text-gray-900 tabular-nums">{value}</span>
    </motion.div>
  )
}
