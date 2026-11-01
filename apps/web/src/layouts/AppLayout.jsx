import { useState, useEffect, useCallback, useRef } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { motion, useReducedMotion, useMotionValue, useSpring, AnimatePresence } from 'motion/react'
import { useQuery } from '@tanstack/react-query'
import {
  Brain, Database, FileSearch,
  GitMerge, LayoutDashboard, LogOut,
  Settings, Swords, Zap, Menu, X, ChevronLeft, ChevronRight,
  ShieldCheck, Cpu, Layers, RefreshCw
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/auth'
import { modelService } from '@/services/api'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'
import { SPRING_SNAPPY, SPRING_GENTLE } from '@/lib/motionConfig'
import useBackendHealth from '@/hooks/useBackendHealth'
import { useSidebar } from '@/hooks/useSidebar'
import { useCursorGlow } from '@/hooks/useCursorGlow'
import { Sidebar } from '@/components/layout/Sidebar'
import { Navbar } from '@/components/layout/Navbar'
import { MobileDrawer } from '@/components/layout/MobileDrawer'
import { EngineTelemetry } from '@/components/layout/EngineTelemetry'
import { BackendBanner } from '@/components/layout/BackendBanner'

const NAV = [
  { label: 'Dashboard',       to: '/dashboard',       icon: LayoutDashboard, badge: null },
  { label: 'Playground',      to: '/playground',      icon: Zap,             badge: 'Live' },
  null,
  { label: 'Knowledge Bases', to: '/knowledge-bases', icon: Database,        badge: null },
  { label: 'Evidence',        to: '/evidence',        icon: FileSearch,      badge: null },
  { label: 'Claims',          to: '/claims',          icon: Brain,           badge: null },
  { label: 'Conflicts',       to: '/conflicts',       icon: GitMerge,        badge: null },
  null,
  { label: 'Settings',        to: '/settings',        icon: Settings,        badge: null },
]

/**
 * AppLayout - Main application layout with sidebar, navbar, and mobile drawer
 * Replaces: Original AppLayout.jsx (637 lines)
 * Called by: App.jsx (line 43)
 * Reads: localStorage 'trustrag_sidebar_collapsed', 'trustrag.playground.engine'
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export default function AppLayout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const reducedMotion = useReducedMotion()
  const { isOnline, isChecking, recheck } = useBackendHealth()

  // Sidebar state
  const { isCollapsed, toggleSidebar, sidebarWidth } = useSidebar()

  // Mobile drawer state
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // Cursor glow
  const { glowX, glowY } = useCursorGlow(reducedMotion)

  // Close mobile drawer on route change
  useEffect(() => {
    setIsMobileOpen(false)
  }, [location.pathname])

  async function handleLogout() {
    await authService.logout()
    navigate('/login')
  }

  return (
    <div className="flex flex-col h-screen supports-[height:100dvh]:h-dvh bg-surface-950 text-slate-100 overflow-hidden">
      {/* Skip link — keyboard / screen-reader fast path to content */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-3 focus:py-2 focus:rounded-lg focus:bg-surface-800 focus:text-white focus:ring-2 focus:ring-primary-400"
      >
        Skip to main content
      </a>

      {/* ── CURSOR GLOW ──────────────────────────────────────────────────── */}
      {!reducedMotion && (
        <motion.div
          aria-hidden="true"
          className="cursor-glow hidden md:block"
          style={{ left: glowX, top: glowY }}
        />
      )}

      {/* ── TOP NAVBAR ─────────────────────────────────────────────────── */}
      <Navbar
        isOnline={isOnline}
        isChecking={isChecking}
        recheck={recheck}
        isCollapsed={isCollapsed}
        setIsMobileOpen={setIsMobileOpen}
      />

      {/* ── BACKEND-DOWN BANNER ─────────────────────────────────────────── */}
      <BackendBanner isOnline={isOnline} recheck={recheck} />

      {/* ── ENGINE TELEMETRY (Mobile) ───────────────────────────────────── */}
      <EngineTelemetry isOnline={isOnline} isChecking={isChecking} recheck={recheck} />

      {/* ── BODY (SIDEBAR + CONTENT) ───────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden relative">
        {/* Desktop Sidebar */}
        <Sidebar
          isCollapsed={isCollapsed}
          sidebarWidth={sidebarWidth}
          toggleSidebar={toggleSidebar}
        />

        {/* Mobile Drawer */}
        <MobileDrawer
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
        />

        {/* ── MAIN CONTENT AREA ─────────────────────────────────────────── */}
        <main id="main-content" tabIndex={-1} aria-label="Main content" className="flex-1 min-w-0 overflow-y-auto bg-surface-950 bg-cyber-grid relative h-full flex flex-col">
          {children}
        </main>
      </div>
    </div>
  )
}