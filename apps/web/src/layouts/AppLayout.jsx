import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import useBackendHealth from '@/hooks/useBackendHealth'
import { useSidebar } from '@/hooks/useSidebar'
import { Sidebar } from '@/components/layout/Sidebar'
import { Navbar } from '@/components/layout/Navbar'
import { MobileDrawer } from '@/components/layout/MobileDrawer'
import { BackendBanner } from '@/components/layout/BackendBanner'
import { modelService } from '@/services/api'

/**
 * AppLayout — the application shell.
 *
 * Obsidian surfaces, chrome-silver hairlines, mono for telemetry. The
 * cursor spotlight that used to live here is gone; the shell is chrome, and
 * chrome does not follow the pointer around.
 *
 * The shell owns three pieces of state and nothing else: whether the
 * sidebar is collapsed, whether the mobile drawer is open, and what the
 * backend and the provider registry currently report.
 */
export default function AppLayout({ children }) {
  const location = useLocation()
  const { isOnline, isChecking, recheck } = useBackendHealth()
  const { isCollapsed, toggleSidebar, sidebarWidth } = useSidebar()
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // The engine's state belongs in the sidebar footer, so the shell reads it
  // once and hands it down. React Query dedupes the request against the
  // header's own query on the same key.
  const { data: providersData } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
    staleTime: 30000,
  })

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
      />

      <BackendBanner isOnline={isOnline} recheck={recheck} />

      <div className="lx-shell__body">
        <Sidebar
          isCollapsed={isCollapsed}
          sidebarWidth={sidebarWidth}
          toggleSidebar={toggleSidebar}
          isOnline={isOnline}
          isChecking={isChecking}
          providersData={providersData}
        />

        <MobileDrawer isMobileOpen={isMobileOpen} setIsMobileOpen={setIsMobileOpen} />

        <main
          id="main-content"
          tabIndex={-1}
          aria-label="Main content"
          className="lx-main"
        >
          {children}
        </main>
      </div>
    </div>
  )
}
