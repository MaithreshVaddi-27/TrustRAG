import { lazy, Suspense, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import ErrorBoundary from '@/components/ErrorBoundary'

// Public Landing page
const LandingPage = lazy(() => import('@/pages/LandingPage'))

// Auth pages
const LoginPage    = lazy(() => import('@/pages/LoginPage'))
const RegisterPage = lazy(() => import('@/pages/RegisterPage'))

// App pages
const DashboardPage      = lazy(() => import('@/pages/DashboardPage'))
const PlaygroundPage     = lazy(() => import('@/pages/PlaygroundPage'))
const KnowledgeBasesPage = lazy(() => import('@/pages/KnowledgeBasesPage'))
const EvidencePage       = lazy(() => import('@/pages/EvidencePage'))
const ClaimsPage         = lazy(() => import('@/pages/ClaimsPage'))
const ConflictsPage      = lazy(() => import('@/pages/ConflictsPage'))
const ExperimentsPage    = lazy(() => import('@/pages/ExperimentsPage'))
const SettingsPage       = lazy(() => import('@/pages/SettingsPage'))
const TracePage          = lazy(() => import('@/pages/TracePage'))
const NotFoundPage       = lazy(() => import('@/pages/NotFoundPage'))

function PageLoading() {
  return (
    <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center">
      <div className="flex items-center gap-3 px-5 py-3 rounded-2xl bg-surface-900 border border-slate-800 shadow-2xl">
        <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
        <span className="text-sm font-medium text-slate-300">Loading module...</span>
      </div>
    </div>
  )
}

/**
 * RequireAuth — redirects to /login if no token is present.
 * Phase 4 will add server-side token validation (/api/v1/auth/me).
 */
function RequireAuth({ children }) {
  const { isAuthenticated } = useAuthStore()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return children
}

/**
 * RedirectIfAuth — redirects authenticated users away from login/register.
 */
function RedirectIfAuth({ children }) {
  const { isAuthenticated } = useAuthStore()
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  return children
}

/**
 * Wraps a route element in an ErrorBoundary so a crash on one page
 * shows a recovery UI instead of unmounting the entire app (FE-H3).
 */
function guarded(element) {
  return <ErrorBoundary>{element}</ErrorBoundary>
}

const PATH_TITLES = {
  '/': 'TRUSTRAG — AI Reliability & Hallucination Audit Workbench',
  '/login': 'Sign In — TRUSTRAG',
  '/register': 'Create Account — TRUSTRAG',
  '/dashboard': 'Dashboard — TRUSTRAG',
  '/playground': 'Playground — TRUSTRAG',
  '/knowledge-bases': 'Knowledge Bases — TRUSTRAG',
  '/evidence': 'Evidence Vault — TRUSTRAG',
  '/claims': 'Claim Inspector — TRUSTRAG',
  '/conflicts': 'Source & Claim Conflicts — TRUSTRAG',
  '/experiments': 'Experiments — TRUSTRAG',
  '/settings': 'Settings — TRUSTRAG',
}

function TitleSync() {
  const { pathname } = useLocation()
  useEffect(() => {
    const title = PATH_TITLES[pathname]
    if (title) document.title = title
    else if (pathname.startsWith('/traces/')) document.title = 'Execution Trace — TRUSTRAG'
  }, [pathname])
  return null
}

export default function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <TitleSync />
      <Routes>
        {/* ── Public ──────────────────────────────────────────── */}
        <Route path="/"         element={guarded(<LandingPage />)} />
        <Route path="/login"    element={guarded(<RedirectIfAuth><LoginPage /></RedirectIfAuth>)} />
        <Route path="/register" element={guarded(<RedirectIfAuth><RegisterPage /></RedirectIfAuth>)} />

        {/* ── Protected ───────────────────────────────────────── */}
        <Route path="/dashboard"       element={guarded(<RequireAuth><DashboardPage /></RequireAuth>)} />
        <Route path="/playground"      element={guarded(<RequireAuth><PlaygroundPage /></RequireAuth>)} />
        <Route path="/knowledge-bases" element={guarded(<RequireAuth><KnowledgeBasesPage /></RequireAuth>)} />
        <Route path="/evidence"        element={guarded(<RequireAuth><EvidencePage /></RequireAuth>)} />
        <Route path="/claims"          element={guarded(<RequireAuth><ClaimsPage /></RequireAuth>)} />
        <Route path="/conflicts"       element={guarded(<RequireAuth><ConflictsPage /></RequireAuth>)} />
        <Route path="/experiments"     element={guarded(<RequireAuth><ExperimentsPage /></RequireAuth>)} />
        <Route path="/settings"        element={guarded(<RequireAuth><SettingsPage /></RequireAuth>)} />
        <Route path="/traces/:id"      element={guarded(<RequireAuth><TracePage /></RequireAuth>)} />

        {/* ── Fallback ────────────────────────────────────────── */}
        <Route path="*" element={guarded(<NotFoundPage />)} />
      </Routes>
    </Suspense>
  )
}
