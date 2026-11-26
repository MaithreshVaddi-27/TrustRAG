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
 * unreachable, not yet known, not configured, and running. "Not yet known"
 * and "not configured" are different answers, and a registry that has not
 * been read yet must never be reported as an empty one.
 */
export function EngineStatus({ isOnline, providers }) {
  const { data, isLoading, isError } = providers

  const activeProvider = data?.active_provider
  const engine = activeProvider ? data?.providers?.[activeProvider] : null

  // ── The backend did not answer ────────────────────────────────────────────
  if (isOnline === false) {
    return (
      <Status
        icon={<ServerOff size={15} strokeWidth={1.5} aria-hidden="true" focusable="false" />}
        title="Engine unreachable"
        meta="API server not responding"
        alarm
      />
    )
  }

  // ── We have never had an answer ───────────────────────────────────────────
  if (isOnline === null) {
    return (
      <Status
        icon={
          <Circle
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
            className="text-silver-500"
          />
        }
        title="Checking engine"
        meta="Probing the health endpoint"
      />
    )
  }

  // ── The registry has not been read yet ─────────────────────────────────────
  if (isLoading && !data) {
    return (
      <Status
        icon={
          <Circle
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
            className="text-silver-500"
          />
        }
        title="Checking engine"
        meta="Reading the registry"
      />
    )
  }

  // ── The registry could not be read ─────────────────────────────────────────
  if (isError && !data) {
    return (
      <Status
        icon={
          <CircleSlash
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
            className="text-silver-500"
          />
        }
        title="Registry unavailable"
        meta="The provider list could not be read"
      />
    )
  }

  // ── The registry names no engine ───────────────────────────────────────────
  if (!activeProvider) {
    return (
      <Status
        icon={
          <CircleSlash
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
            className="text-silver-500"
          />
        }
        title="Engine not configured"
        meta="No active provider in the registry"
      />
    )
  }

  // ── The provider is named but is not answering ────────────────────────────
  if (engine && !engine.connected) {
    return (
      <Status
        icon={
          <CircleSlash
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
            className="text-silver-500"
          />
        }
        title={`${providerShortLabel(activeProvider)} not responding`}
        meta={engine.error || 'The inference server is unreachable'}
      />
    )
  }

  // ── Running ───────────────────────────────────────────────────────────────
  // The model that answers queries is the *active* model. The provider's
  // default_model is whatever the registry lists first, which is not
  // necessarily enabled for that provider — reporting it here told the
  // operator the engine was running a model that was not in use.
  const activeModel = data?.active_model ?? engine?.default_model

  return (
    <Status
      icon={
        <Activity
          size={15}
          strokeWidth={1.5}
          aria-hidden="true"
          focusable="false"
          className="text-silver-400"
        />
      }
      title="Engine online"
      meta={`${providerShortLabel(activeProvider)}${
        activeModel ? ` · ${shortModelId(activeModel)}` : ''
      }`}
    />
  )
}

function Status({ icon, title, meta, alarm = false }) {
  return (
    <div className={`lx-sidebar__status${alarm ? ' lx-sidebar__status--alarm' : ''}`}>
      <span className="shrink-0">{icon}</span>
      <div className="min-w-0">
        <p className="lx-sidebar__status-title truncate">{title}</p>
        <p className="lx-sidebar__status-meta truncate">{meta}</p>
      </div>
    </div>
  )
}
