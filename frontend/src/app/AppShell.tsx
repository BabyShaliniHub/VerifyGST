import { NavLink, Outlet } from 'react-router-dom'
import { navItems } from './navigation'

const linkBase = 'flex items-center gap-3 rounded-md px-3 py-2 text-base whitespace-nowrap'

function linkClass({ isActive }: { isActive: boolean }) {
  return `${linkBase} ${isActive ? 'bg-sunken font-semibold text-forest' : 'hover:bg-canvas'}`
}

export default function AppShell() {
  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="hidden w-64 shrink-0 border-r border-line bg-surface md:block">
        <div className="px-5 py-6">
          <p className="text-xl font-semibold">VerifiGST</p>
          <p className="text-base text-ink/70">GST invoice intelligence</p>
        </div>
        <nav aria-label="Main" className="flex flex-col gap-1 px-3">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass}>
              <Icon size={20} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <nav
        aria-label="Main (compact)"
        className="flex gap-1 overflow-x-auto border-b border-line bg-surface px-2 py-2 md:hidden"
      >
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={linkClass}>
            <Icon size={20} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-line bg-surface px-8 py-4">
          <p className="text-base text-ink/70">
            Digital Invoice Authentication and GST Fraud Intelligence
          </p>
        </header>
        <main className="flex-1 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
