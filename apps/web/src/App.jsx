import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

// Auth pages
import LoginPage    from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'

// App pages
import DashboardPage      from '@/pages/DashboardPage'
import PlaygroundPage     from '@/pages/PlaygroundPage'
import KnowledgeBasesPage from '@/pages/KnowledgeBasesPage'
import EvidencePage       from '@/pages/EvidencePage'
import ClaimsPage         from '@/pages/ClaimsPage'
import ConflictsPage      from '@/pages/ConflictsPage'
import ExperimentsPage    from '@/pages/ExperimentsPage'
import SettingsPage       from '@/pages/SettingsPage'
import TracePage          from '@/pages/TracePage'

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
    <Routes>
      {/* ── Public ──────────────────────────────────────────── */}
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

      {/* ── Defaults ───────────────────────────────────────── */}
      <Route path="/"  element={<Navigate to="/dashboard" replace />} />
      <Route path="*"  element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
