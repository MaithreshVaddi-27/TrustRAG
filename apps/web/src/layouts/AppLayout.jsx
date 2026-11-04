import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, useReducedMotion } from 'motion/react'
import useBackendHealth from '@/hooks/useBackendHealth'
import { useSidebar } from '@/hooks/useSidebar'
import { useCursorGlow } from '@/hooks/useCursorGlow'
import { Sidebar } from '@/components/layout/Sidebar'
import { Navbar } from '@/components/layout/Navbar'
import { MobileDrawer } from '@/components/layout/MobileDrawer'
import { EngineTelemetry } from '@/components/layout/EngineTelemetry'
import { BackendBanner } from '@/components/layout/BackendBanner'

/**
 * AppLayout - Main application layout with sidebar, navbar, and mobile drawer
 * Provides the application shell, skip navigation, cursor glow, and responsive containers.
 */
export default function AppLayout({ children }) {
  const location = useLocation()
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
        setIsMobileOpen={setIsMobileOpen}
        isCollapsed={isCollapsed}
        toggleSidebar={toggleSidebar}
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