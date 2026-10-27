import { NavLink } from 'react-router-dom'
import { Activity, BookOpen, ChevronRight, FileText, FileUp, FlaskConical, Home, Scale, Search } from 'lucide-react'

const NAV = [
  { to: '/',             label: 'Clinical Home',     icon: Home },
  { to: '/import',       label: 'Import Notes',      icon: FileUp },
  { to: '/journey',      label: 'Patient Journey',   icon: Activity },
  { to: '/notes',        label: 'Note Explorer',     icon: FileText },
  { to: '/consistency',  label: 'Consistency',       icon: Scale },
  { to: '/intelligence', label: 'Text Intelligence', icon: Search },
  { to: '/evaluation',   label: 'Evaluation',        icon: FlaskConical },
]

export default function NavSidebar() {
  return (
    <nav className="flex w-full shrink-0 flex-col border-b border-ivory-200 bg-white md:min-h-screen md:w-60 md:border-b-0 md:border-r">
      {/* Logo */}
      <div className="border-b border-ivory-200 px-4 py-3 sm:px-5 md:py-5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-teal-800 flex items-center justify-center">
            <BookOpen size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-gray-900 leading-tight">MedThread</p>
            <p className="text-[10px] text-gray-400 uppercase tracking-wider leading-tight">Clinical Intelligence</p>
          </div>
        </div>
      </div>

      {/* Links */}
      <div className="flex flex-row gap-0.5 overflow-x-auto px-2 py-2 md:flex-1 md:flex-col md:overflow-visible md:px-3 md:py-4">
        <p className="section-label mb-2 hidden px-2 md:block">Navigation</p>
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `group flex shrink-0 items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors duration-150 ${
                isActive
                  ? 'bg-teal-50 text-teal-800 font-semibold'
                  : 'text-gray-600 hover:bg-ivory-100 hover:text-gray-900'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} className={isActive ? 'text-teal-700' : 'text-gray-400 group-hover:text-gray-600'} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight size={12} className="text-teal-600" />}
              </>
            )}
          </NavLink>
        ))}
      </div>

      {/* Footer note */}
      <div className="hidden border-t border-ivory-200 px-5 py-4 md:block">
        <p className="text-[10px] text-gray-300 leading-relaxed">
          All demo data is explicitly <span className="font-semibold">SYNTHETIC</span>. No real patient data.
        </p>
      </div>
    </nav>
  )
}
