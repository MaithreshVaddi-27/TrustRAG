import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import useBackendHealth from '@/hooks/useBackendHealth'
import { useSidebar } from '@/hooks/useSidebar'
import { Sidebar } from '@/components/layout/Sidebar'
import { Navbar } from '@/components/layout/Navbar'
import { MobileDrawer } from '@/components/layout/MobileDrawer'
import { EngineTelemetry } from '@/components/layout/EngineTelemetry'
import { BackendBanner } from '@/components/layout/BackendBanner'

/**
 * AppLayout — the application shell.
 *
 * Obsidian surfaces, chrome-silver hairlines, mono for telemetry. The
 * cursor spotlight that used to live here is gone; the shell is chrome, and
 * chrome does not follow the pointer around.
 */
export default function AppLayout({ children }) {
  const location = useLocation()
  const { isOnline, isChecking, recheck } = useBackendHealth()
  const { isCollapsed, toggleSidebar, sidebarWidth } = useSidebar()
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // Close the mobile drawer on route change.
  useEffect(() => {
    setIsMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="lx-shell">
      <a href="#main-content" className="lx-skip-link">
        Skip to main content
      </a>

      <Navbar
        isOnline={isOnline}
        isChecking={isChecking}
        recheck={recheck}
        setIsMobileOpen={setIsMobileOpen}
        isCollapsed={isCollapsed}
        toggleSidebar={toggleSidebar}
      />

      <BackendBanner isOnline={isOnline} recheck={recheck} />

      <EngineTelemetry isOnline={isOnline} isChecking={isChecking} recheck={recheck} />

      <div className="flex flex-1 min-h-0 overflow-hidden relative">
        <Sidebar
          isCollapsed={isCollapsed}
          sidebarWidth={sidebarWidth}
          toggleSidebar={toggleSidebar}
        />

        <MobileDrawer
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
        />

        <main
          id="main-content"
          tabIndex={-1}
          aria-label="Main content"
          className="lx-main bg-cyber-grid"
        >
          {children}
        </main>
      </div>
    </div>
  )
}
