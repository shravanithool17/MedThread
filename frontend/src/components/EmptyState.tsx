import type { LucideIcon } from 'lucide-react'

interface Props {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
}

export default function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      {Icon && (
        <div className="w-14 h-14 rounded-full bg-ivory-200 flex items-center justify-center">
          <Icon size={24} className="text-gray-400" />
        </div>
      )}
      <div>
        <p className="text-base font-semibold text-gray-700">{title}</p>
        {description && <p className="mt-1 text-sm text-gray-400">{description}</p>}
      </div>
      {action}
    </div>
  )
}
