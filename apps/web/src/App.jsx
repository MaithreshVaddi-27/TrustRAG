import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

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

export default function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        {/* ── Public ──────────────────────────────────────────── */}
        <Route path="/"         element={<LandingPage />} />
        <Route path="/login"    element={<RedirectIfAuth><LoginPage /></RedirectIfAuth>} />
        <Route path="/register" element={<RedirectIfAuth><RegisterPage /></RedirectIfAuth>} />

        {/* ── Protected ───────────────────────────────────────── */}
        <Route path="/dashboard"       element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="/playground"      element={<RequireAuth><PlaygroundPage /></RequireAuth>} />
        <Route path="/knowledge-bases" element={<RequireAuth><KnowledgeBasesPage /></RequireAuth>} />
        <Route path="/evidence"        element={<RequireAuth><EvidencePage /></RequireAuth>} />
        <Route path="/claims"          element={<RequireAuth><ClaimsPage /></RequireAuth>} />
        <Route path="/conflicts"       element={<RequireAuth><ConflictsPage /></RequireAuth>} />
        <Route path="/experiments"     element={<RequireAuth><ExperimentsPage /></RequireAuth>} />
        <Route path="/settings"        element={<RequireAuth><SettingsPage /></RequireAuth>} />
        <Route path="/traces/:id"      element={<RequireAuth><TracePage /></RequireAuth>} />

        {/* ── Fallback ────────────────────────────────────────── */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
