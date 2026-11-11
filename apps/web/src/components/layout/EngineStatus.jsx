import { Activity, ServerOff, Circle, CircleSlash } from 'lucide-react'
import { providerShortLabel, shortModelId } from '@/lib/modelLabels'

/**
 * EngineStatus — the real state of the platform.
 *
 * This used to be a hardcoded "Self-healing loop · StateGraph v1.0 active",
 * which claimed the pipeline was running whether or not anything was
 * listening. It now reports what the health probe and the provider
 * registry actually say.
 *
 * Four states, and each one names the problem rather than glossing it:
 * unreachable, not yet known, not configured, and running.
 */
export function EngineStatus({ isOnline, providersData }) {
  const activeProvider = providersData?.active_provider
  const engine = activeProvider ? providersData?.providers?.[activeProvider] : null

  // ── The backend did not answer ────────────────────────────────────────────
  if (isOnline === false) {
    return (
      <div className="lx-sidebar__status lx-sidebar__status--alarm">
        <ServerOff
          size={15}
          strokeWidth={1.5}
          aria-hidden="true"
          focusable="false"
          className="shrink-0"
        />
        <div className="min-w-0">
          <p className="lx-sidebar__status-title truncate">Engine unreachable</p>
          <p className="lx-sidebar__status-meta truncate">API server not responding</p>
        </div>
      </div>
    )
  }

  // ── We have never had an answer ───────────────────────────────────────────
  if (isOnline === null) {
    return (
      <div className="lx-sidebar__status">
        <Circle
          size={15}
          strokeWidth={1.5}
          aria-hidden="true"
          focusable="false"
          className="shrink-0 text-silver-500"
        />
        <div className="min-w-0">
          <p className="lx-sidebar__status-title truncate">Checking engine</p>
          <p className="lx-sidebar__status-meta truncate">Probing the health endpoint</p>
        </div>
      </div>
    )
  }

  // ── The backend answered, but the registry names no engine ─────────────────
  if (!activeProvider) {
    return (
      <div className="lx-sidebar__status">
        <CircleSlash
          size={15}
          strokeWidth={1.5}
          aria-hidden="true"
          focusable="false"
          className="shrink-0 text-silver-500"
        />
        <div className="min-w-0">
          <p className="lx-sidebar__status-title truncate">Engine not configured</p>
          <p className="lx-sidebar__status-meta truncate">
            No active provider in the registry
          </p>
        </div>
      </div>
    )
  }

  // ── The provider is named but is not answering ────────────────────────────
  if (engine && !engine.connected) {
    return (
      <div className="lx-sidebar__status">
        <CircleSlash
          size={15}
          strokeWidth={1.5}
          aria-hidden="true"
          focusable="false"
          className="shrink-0 text-silver-500"
        />
        <div className="min-w-0">
          <p className="lx-sidebar__status-title truncate">
            {providerShortLabel(activeProvider)} not responding
          </p>
          <p className="lx-sidebar__status-meta truncate">
            {engine.error || 'The inference server is unreachable'}
          </p>
        </div>
      </div>
    )
  }

  // ── Running ───────────────────────────────────────────────────────────────
  return (
    <div className="lx-sidebar__status">
      <Activity
        size={15}
        strokeWidth={1.5}
        aria-hidden="true"
        focusable="false"
        className="shrink-0 text-silver-400"
      />
      <div className="min-w-0">
        <p className="lx-sidebar__status-title truncate">Engine online</p>
        <p className="lx-sidebar__status-meta truncate">
          {providerShortLabel(activeProvider)}
          {engine?.default_model ? ` · ${shortModelId(engine.default_model)}` : ''}
        </p>
      </div>
    </div>
  )
}
