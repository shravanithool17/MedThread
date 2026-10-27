import type { ContextType } from '../types'

const CONFIG: Record<ContextType, { label: string; classes: string }> = {
  affirmed:  { label: 'Affirmed',  classes: 'bg-clinical-affirmed-bg text-clinical-affirmed border border-clinical-affirmed-border' },
  negated:   { label: 'Negated',   classes: 'bg-clinical-negated-bg text-clinical-negated border border-clinical-negated-border' },
  uncertain: { label: 'Uncertain', classes: 'bg-clinical-uncertain-bg text-clinical-uncertain border border-clinical-uncertain-border' },
  resolved:  { label: 'Resolved',  classes: 'bg-clinical-resolved-bg text-clinical-resolved border border-clinical-resolved-border' },
  unclear:   { label: 'Unclear',   classes: 'bg-clinical-unclear-bg text-clinical-unclear border border-clinical-unclear-border' },
}

interface Props {
  context: string
  size?: 'sm' | 'md'
}

export default function ContextBadge({ context, size = 'sm' }: Props) {
  const cfg = CONFIG[context as ContextType] ?? {
    label: context,
    classes: 'bg-gray-100 text-gray-600 border border-gray-200',
  }
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'
  return (
    <span className={`inline-flex items-center rounded-full font-medium ${sizeClass} ${cfg.classes}`}>
      {cfg.label}
    </span>
  )
}
