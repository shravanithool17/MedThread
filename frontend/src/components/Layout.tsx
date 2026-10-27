import NavSidebar from './NavSidebar'

interface Props {
  children: React.ReactNode
}

export default function Layout({ children }: Props) {
  return (
    <div className="flex min-h-screen flex-col bg-ivory-50 md:flex-row">
      <NavSidebar />
      <main className="flex-1 min-w-0 overflow-x-hidden">
        <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
