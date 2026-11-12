import { Zap, Activity, Loader2 } from 'lucide-react'

/**
 * HardwarePanel — what the machine can actually do.
 *
 * Three readings and one action. The readings are a specification list; the
 * action is the heap compaction, which is destructive enough to deserve its
 * own control rather than being buried in a list.
 */
export default function HardwarePanel({
  hardware,
  isOptimal,
  trimming,
  trimResult,
  onTrim,
}) {
  const memory = hardware?.memory ?? {}
  const usage = memory.usage_pct ?? 0
  const pressure = usage > 85
  // Nothing is known until the registry answers. A reading of zero is a
  // measurement, and reporting one for a machine we have not measured is a
  // claim the page cannot support.
  const known = Boolean(hardware)

  return (
    <section className="lx-panel-block" aria-labelledby="hardware-heading">
      <div className="lx-panel-block__head">
        <h2 id="hardware-heading" className="lx-panel-block__title flex items-center gap-2">
          <Zap size={16} strokeWidth={1.5} aria-hidden="true" />
          Hardware acceleration and system health
        </h2>

        <div className="flex items-center gap-3">
          <span className={`lx-chip${isOptimal ? '' : ' lx-chip--alarm'}`}>
            {isOptimal ? 'System healthy' : 'Resource pressure'}
          </span>
          <button
            type="button"
            onClick={onTrim}
            disabled={trimming}
            className="lx-btn lx-btn--secondary"
          >
            {trimming ? (
              <Loader2 size={13} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
            ) : (
              <Activity size={13} strokeWidth={1.75} aria-hidden="true" />
            )}
            <span>{trimming ? 'Compacting' : 'Compact heap'}</span>
          </button>
        </div>
      </div>

      {trimResult && (
        <div className="border-b border-[color:var(--rule-faint)] px-5 py-2.5">
          <p className="lx-micro">
            Heap compacted. Process RSS is now {trimResult.after_mb} MB, freed{' '}
            {trimResult.freed_mb} MB.
          </p>
        </div>
      )}

      <div className="lx-panel-block__body">
        <dl className="lx-deflist">
          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Hardware accelerator</dt>
            <dd className="lx-deflist__value">
              {known ? hardware.accelerator_name : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Engine / machine</dt>
            <dd className="lx-deflist__value">
              {known
                ? `${(hardware.accelerator || 'cpu').toUpperCase()} · ${hardware.machine}`
                : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Host memory</dt>
            <dd
              className="lx-deflist__value"
              style={pressure ? { color: 'var(--color-crimson-300)' } : undefined}
            >
              {known
                ? `${memory.used_gb ?? '—'} / ${memory.total_gb ?? '—'} GB · ${usage}%`
                : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Process RSS</dt>
            <dd className="lx-deflist__value">{hardware?.process_rss_mb || 0} MB</dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Optimal LLM</dt>
            <dd className="lx-deflist__value">
              {known
                ? (hardware.recommendations?.primary_llm ?? '—')
                : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Optimal embedding</dt>
            <dd className="lx-deflist__value">
              {known
                ? (hardware.recommendations?.primary_embedding ?? '—')
                : 'Detecting…'}
            </dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Safe concurrency</dt>
            <dd className="lx-deflist__value">
              {known
                ? `${hardware.recommendations?.max_concurrency ?? '—'} concurrent runs`
                : 'Detecting…'}
            </dd>
          </div>
        </dl>
      </div>
    </section>
  )
}
