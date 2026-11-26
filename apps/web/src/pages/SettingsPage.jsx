import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/common/PageHeader'
import ConfirmDialog from '@/components/kb/ConfirmDialog'
import ClusterPanel from '@/components/settings/ClusterPanel'
import HardwarePanel from '@/components/settings/HardwarePanel'
import LocalLLMPanel from '@/components/settings/LocalLLMPanel'
import EmbeddingPanel from '@/components/settings/EmbeddingPanel'
import ModelRegistryPanel from '@/components/settings/ModelRegistryPanel'
import AccountPanel from '@/components/settings/AccountPanel'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/auth'
import { healthService, modelService } from '@/services/api'
import { copyToClipboard } from '@/lib/clipboard'
import { SettingsSkeleton } from '@/components/settings/SettingsSkeleton'

/**
 * SettingsPage — the diagnostics screen.
 *
 * The page itself only composes the panels and owns the three pieces of
 * state that cross them: whether the session is ending, whether the tenant
 * ID has been copied, and whether the heap is being compacted.
 */
export default function SettingsPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [copied, setCopied] = useState(false)
  const [trimming, setTrimming] = useState(false)
  const [trimResult, setTrimResult] = useState(null)
  const [confirmLogout, setConfirmLogout] = useState(false)

  const {
    data: health,
    isLoading,
    isError: healthError,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['backend-health'],
    queryFn: healthService.get,
    refetchInterval: 30000,
  })

  const {
    data: providersData,
    isLoading: providersLoading,
    isError: providersError,
    refetch: refetchProviders,
  } = useQuery({
    queryKey: ['model-providers'],
    queryFn: modelService.getProviders,
    refetchInterval: 30000,
  })

  const handleTrimMemory = async () => {
    setTrimming(true)
    try {
      const res = await modelService.trimMemory()
      setTrimResult(res)
      setTimeout(() => setTrimResult(null), 4000)
    } catch (err) {
      console.error('Failed to trim memory', err)
    } finally {
      setTrimming(false)
    }
  }

  const copyUserId = async () => {
    if (!user?.id) return
    const ok = await copyToClipboard(user.id)
    if (!ok) return
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const doLogout = async () => {
    setConfirmLogout(false)
    await authService.logout()
    navigate('/login')
  }

  const healthUnknown = healthError || (!isLoading && !health)
  const isOperational = !healthUnknown && health?.status === 'ok'
  const hardware = providersData?.hardware
  const models = health?.models || {}

  // The panels report readings, and a reading is longer or shorter than
  // the placeholder it replaces. Rendering them before the registry has
  // answered means every panel below the first one moves when the data
  // lands. The whole stack waits instead, and arrives in one piece.
  const providersPending = providersLoading && !providersData
  const ready = !isLoading && !providersPending

  return (
    <AppLayout>
      <div className="lx-page lx-stack">
        <PageHeader
          title="System"
          accent="diagnostics"
          countLabel={
            healthUnknown ? 'Status unknown' : isOperational ? 'Operational' : 'Degraded'
          }
          description="Live system health, multi-tenant partitioning, and the active AI model configuration."
        />

        {!ready ? (
          <SettingsSkeleton />
        ) : (
          <>
            <ClusterPanel
              health={health}
              isLoading={isLoading}
              healthUnknown={healthUnknown}
              onRetry={() => refetchHealth()}
            />

            <HardwarePanel
              hardware={hardware}
              isOptimal={providersData?.hardware?.health?.status === 'optimal'}
              trimming={trimming}
              trimResult={trimResult}
              onTrim={handleTrimMemory}
            />

            <LocalLLMPanel
              providers={providersData?.providers}
              providersPending={providersPending}
            />

            <EmbeddingPanel
              activeModel={providersData?.active_embedding_model}
              embedding={providersData?.embedding}
            />

            <ModelRegistryPanel
              models={models}
              supportedFormats={health?.supported_formats}
              healthUnknown={healthUnknown}
            />

            <AccountPanel
              user={user}
              copied={copied}
              onCopyId={copyUserId}
              onSignOut={() => setConfirmLogout(true)}
            />

            {healthError && (
              <div className="lx-message lx-message--alarm" role="alert">
                <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <span className="lx-message__title">Cluster telemetry unavailable</span>
                  <span className="lx-message__body">Service health could not be read from the backend.</span>
                </div>
                <button
                  type="button"
                  onClick={() => refetchHealth()}
                  className="lx-btn lx-btn--secondary shrink-0"
                >
                  Retry
                </button>
              </div>
            )}

            {providersError && (
              <div className="lx-message lx-message--alarm" role="alert">
                <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <span className="lx-message__title">Model telemetry unavailable</span>
                  <span className="lx-message__body">Provider state could not be read from the backend.</span>
                </div>
                <button
                  type="button"
                  onClick={() => refetchProviders()}
                  className="lx-btn lx-btn--secondary shrink-0"
                >
                  Retry
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <ConfirmDialog
        open={confirmLogout}
        title="Sign out?"
        message="End this session and return to the login screen."
        confirmLabel="Sign out"
        danger={false}
        onCancel={() => setConfirmLogout(false)}
        onConfirm={doLogout}
      />
    </AppLayout>
  )
}

/**
 * SettingsSkeleton — the diagnostics screen's shape, held while the
 * registry answers.
 *
 * It is a different component from the panel stack it stands in for, so
 * the panels arrive as new elements rather than as ones that moved.
 */
