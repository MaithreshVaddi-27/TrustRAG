import { Server, Database, Layers, ShieldCheck, Clock, AlertTriangle } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

/**
 * ClusterPanel — where the data lives and what is running.
 *
 * A specification table rather than four cards. Each service is a row: what
 * it is, what it holds, and whether it answers. A disconnected service is the
 * one row that carries crimson, because it is the one row that matters.
 */
const SERVICES = [
  {
    key: 'mongodb',
    label: 'MongoDB',
    icon: Database,
    role: 'Document store, audit traces and verifiable claim state',
    endpoint: '27017',
  },
  {
    key: 'qdrant',
    label: 'Qdrant',
    icon: Layers,
    role: 'Dense and sparse hybrid vector collection indexing',
    endpoint: '6333',
  },
]

export default function ClusterPanel({ health, isLoading, healthUnknown, onRetry = null }) {
  const isUp = (key) => health?.services?.[key] === 'ok'
  const anyDown = SERVICES.some(({ key }) => !isUp(key))

  return (
    <section className="lx-panel-block" aria-labelledby="cluster-heading">
      <div className="lx-panel-block__head">
        <h2 id="cluster-heading" className="lx-panel-block__title flex items-center gap-2">
          <Server size={16} strokeWidth={1.5} aria-hidden="true" />
          Cluster infrastructure and storage
        </h2>
        {isLoading && (
          <ThinkingOrbs size="sm" />
        )}
      </div>

      <div className="lx-panel-block__body">
        <dl className="lx-deflist">
          {SERVICES.map(({ key, label, icon: Icon, endpoint }) => {
            const connected = isUp(key)
            const unknown = healthUnknown
            return (
              <div key={key} className="lx-deflist__row">
                <dt className="lx-deflist__key flex items-center gap-2">
                  <Icon size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
                  <span className="text-silver-300">{label}</span>
                  <span className="lx-micro">: {endpoint}</span>
                </dt>
                <dd
                  className={
                    !unknown && !connected
                      ? 'lx-deflist__value lx-signal'
                      : 'lx-deflist__value'
                  }
                >
                  {unknown ? 'Unknown' : connected ? 'Connected' : 'Disconnected'}
                </dd>
              </div>
            )
          })}

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key flex items-center gap-2">
              <ShieldCheck size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
              <span className="text-silver-300">Environment</span>
            </dt>
            <dd className="lx-deflist__value capitalize">
              {health?.environment || 'development'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key flex items-center gap-2">
              <Clock size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
              <span className="text-silver-300">Release</span>
            </dt>
            <dd className="lx-deflist__value">
              {health?.version || (healthUnknown ? 'Unknown' : '0.1.0')}
            </dd>
          </div>
        </dl>

        {!isLoading && !healthUnknown && anyDown && (
          <div className="lx-message lx-message--alarm mt-4" role="alert">
            <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <span className="lx-message__title">A storage service is not answering</span>
              <span className="lx-message__body">Checks and ingestion that need it will fail until it reconnects.</span>
            </div>
            {onRetry && (
              <button type="button" onClick={onRetry} className="lx-btn lx-btn--secondary shrink-0">
                Retry
              </button>
            )}
          </div>
        )}
      </div>

      <div className="lx-panel-block__foot">
        <p className="lx-micro">
          {SERVICES.map((s) => s.role).join(' · ')}
        </p>
      </div>
    </section>
  )
}
