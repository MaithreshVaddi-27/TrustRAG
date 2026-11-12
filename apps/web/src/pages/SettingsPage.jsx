import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import PageHeader from '@/components/ui/PageHeader'
import ConfirmDialog from '@/components/ConfirmDialog'
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

  const { data: health, isLoading, isError: healthError } = useQuery({
    queryKey: ['backend-health'],
    queryFn: healthService.get,
    refetchInterval: 30000,
  })

  const { data: providersData, isLoading: providersLoading, isError: providersError } = useQuery({
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

        <ClusterPanel
          health={health}
          isLoading={isLoading}
          healthUnknown={healthUnknown}
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
          providersPending={providersLoading && !providersData}
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

        {providersError && (
          <p className="lx-micro">Model provider telemetry is unavailable.</p>
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
