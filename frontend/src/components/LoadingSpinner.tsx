interface Props { size?: number; label?: string }

export default function LoadingSpinner({ size = 32, label }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-gray-400">
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        className="animate-spin"
        style={{ color: '#0d7377' }}
      >
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeOpacity="0.2" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      {label && <span className="text-sm">{label}</span>}
    </div>
  )
}
