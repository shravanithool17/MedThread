const CONFIG: Record<string, { label: string; classes: string }> = {
  possible_inconsistency: { label: 'Possible Inconsistency', classes: 'bg-orange-50 text-orange-700 border border-orange-200' },
  persistent_documented:  { label: 'Persistent Documented', classes: 'bg-teal-50 text-teal-700 border border-teal-200' },
  newly_reported:         { label: 'Newly Documented',       classes: 'bg-blue-50 text-blue-700 border border-blue-200' },
  explicitly_resolved:    { label: 'Explicitly Resolved',    classes: 'bg-green-50 text-green-700 border border-green-200' },
  explicitly_negated:     { label: 'Explicitly Negated',     classes: 'bg-red-50 text-red-700 border border-red-200' },
  not_documented:         { label: 'Not Documented',         classes: 'bg-gray-100 text-gray-600 border border-gray-200' },
  unclear:                { label: 'Unclear',                classes: 'bg-yellow-50 text-yellow-700 border border-yellow-200' },
}

interface Props {
  status: string
  size?: 'sm' | 'md'
}

export default function StatusBadge({ status, size = 'sm' }: Props) {
  const cfg = CONFIG[status] ?? {
    label: status.replace(/_/g, ' '),
    classes: 'bg-gray-100 text-gray-600 border border-gray-200',
  }
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'
  return (
    <span className={`inline-flex items-center rounded-full font-medium ${sizeClass} ${cfg.classes}`}>
      {cfg.label}
    </span>
  )
}
