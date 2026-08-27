import { Link, NavLink, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  BarChart3, BookOpen, Brain, Database, FileSearch,
  FlaskConical, GitMerge, LayoutDashboard, LogOut,
  Settings, Swords, Terminal, Zap,
} from 'lucide-react'
import { authStore } from '@/store/authStore'

const NAV = [
  { label: 'Dashboard',       to: '/dashboard',       icon: LayoutDashboard },
  { label: 'Playground',      to: '/playground',      icon: Zap },
  null, // divider
  { label: 'Knowledge Bases', to: '/knowledge-bases', icon: Database },
  { label: 'Evidence',        to: '/evidence',        icon: FileSearch },
  { label: 'Claims',          to: '/claims',          icon: Brain },
  { label: 'Conflicts',       to: '/conflicts',       icon: GitMerge },
  null,
  { label: 'Experiments',     to: '/experiments',     icon: FlaskConical },
  null,
  { label: 'Settings',        to: '/settings',        icon: Settings },
]

export default function AppLayout({ children }) {
  const navigate = useNavigate()

  function handleLogout() {
    authStore.clearSession()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-surface-950 overflow-hidden">
      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside className="w-56 shrink-0 flex flex-col border-r border-slate-800 bg-surface-900">
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-slate-800">
          <Link to="/dashboard" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-lg bg-primary-600 flex items-center justify-center shadow-lg shadow-primary-900/50 group-hover:bg-primary-500 transition-colors">
              <Swords size={14} className="text-white" />
            </div>
            <span className="font-bold text-sm tracking-tight text-white">
              TRUST<span className="text-primary-400">RAG</span>
            </span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {NAV.map((item, i) =>
            item === null ? (
              <div key={i} className="my-2 border-t border-slate-800/60" />
            ) : (
              <SidebarLink key={item.to} {...item} />
            )
          )}
        </nav>

        {/* Bottom actions */}
        <div className="border-t border-slate-800 p-2">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-500 hover:text-slate-300 hover:bg-surface-800 transition-colors group"
          >
            <LogOut size={15} className="group-hover:text-red-400 transition-colors" />
            Logout
          </button>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 shrink-0 flex items-center justify-between px-6 border-b border-slate-800 bg-surface-900/50">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-mono">
            <Terminal size={12} />
            AI Reliability Workbench
          </div>
          <div className="flex items-center gap-3">
            <StatusPill />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

function SidebarLink({ to, label, icon: Icon }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => clsx(
        'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors group',
        isActive
          ? 'bg-primary-600/20 text-primary-300 border border-primary-700/40'
          : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800',
      )}
    >
      <Icon size={15} className="shrink-0" />
      {label}
    </NavLink>
  )
}

function StatusPill() {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-900/30 border border-green-800/40">
      <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
      <span className="text-xs text-green-400 font-mono">API</span>
    </div>
  )
}
