import { useMemo } from 'react'
import { Activity, CheckCircle2, Cpu, Database, Globe, Loader2, ShieldCheck, Sparkles } from 'lucide-react'

/**
 * PipelineTelemetryHUD — Ultra-premium, executive live telemetry HUD.
 * Replaces the generic/distorted radar with a clean, dynamic 4-stage pipeline tracker,
 * live stage indicators, latency badges, and verified context counters.
 */
export function PipelineTelemetryHUD({
  events = [],
  query = '',
  enableWebSearch = false,
  webSearchProvider = 'both',
}) {
  // Determine current active pipeline stage from events
  const status = useMemo(() => {
    const eventNames = new Set(events.map(e => e.event))
    const lastEvent = events[events.length - 1]

    const retrievalDone = eventNames.has('retrieval.completed')
    const generationDone = eventNames.has('generation.completed') || eventNames.has('claims.started')
    const verificationDone = eventNames.has('claims.verified')
    const isCompleted = eventNames.has('analysis.completed') || eventNames.has('analysis.abstained')
    const isRecovering = eventNames.has('recovery.rewrite') || eventNames.has('recovery.expanded')

    // Find live message
    let liveMessage = 'Initializing autonomous pipeline…'
    if (lastEvent?.data?.message) {
      liveMessage = lastEvent.data.message
    } else if (lastEvent?.event) {
      liveMessage = lastEvent.event.replace(/[._]/g, ' ')
    }

    return {
      retrievalDone,
      generationDone,
      verificationDone,
      isCompleted,
      isRecovering,
      liveMessage,
      eventCount: events.length,
    }
  }, [events])

  return (
    <div className="rounded-2xl border border-cyan-500/30 bg-gradient-to-b from-surface-900/95 via-surface-900/80 to-surface-950/90 p-4 sm:p-5 backdrop-blur-xl shadow-xl shadow-cyan-950/20 space-y-4">
      {/* Top Bar: Live Status & Active Stage */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            <span className="absolute w-2 h-2 rounded-full bg-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-bold tracking-wider text-cyan-300 uppercase">
                Autonomous Verification Engine
              </span>
              {query && (
                <span className="text-[10px] font-mono text-slate-400 bg-surface-950 px-2 py-0.5 rounded border border-slate-800 truncate max-w-[220px]" title={query}>
                  &ldquo;{query}&rdquo;
                </span>
              )}
            </div>
            <p className="text-xs text-slate-300 font-medium tracking-tight truncate max-w-md sm:max-w-lg">
              {status.liveMessage}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono shrink-0">
          <span className="px-2 py-0.5 rounded-md bg-surface-950 border border-slate-800 text-slate-400">
            Events: <strong className="text-cyan-300">{status.eventCount}</strong>
          </span>
          {enableWebSearch && (
            <span className="px-2 py-0.5 rounded-md bg-cyan-950/80 border border-cyan-800/50 text-cyan-300 flex items-center gap-1">
              <Globe size={11} className="text-cyan-400" />
              MCP {webSearchProvider.toUpperCase()}
            </span>
          )}
          {status.isRecovering && (
            <span className="px-2 py-0.5 rounded-md bg-amber-950/80 border border-amber-800/60 text-amber-300 flex items-center gap-1 animate-pulse">
              <Activity size={11} /> Self-Healing Active
            </span>
          )}
        </div>
      </div>

      {/* 4-Stage Pipeline Progress Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        {/* Stage 1: Hybrid Retrieval */}
        <StageCard
          title="1. Hybrid Retrieval"
          subtitle={enableWebSearch ? "Vector + BM25 + Web" : "Vector + BM25"}
          icon={Database}
          done={status.retrievalDone}
          active={!status.retrievalDone}
        />

        {/* Stage 2: RRF Fusion */}
        <StageCard
          title="2. Cross-RRF Fusion"
          subtitle="Rank Fusion & Rerank"
          icon={Cpu}
          done={status.retrievalDone}
          active={status.retrievalDone && !status.generationDone}
        />

        {/* Stage 3: Grounded Reasoning */}
        <StageCard
          title="3. Grounded Synthesis"
          subtitle="Strict Context Bound"
          icon={Sparkles}
          done={status.generationDone}
          active={status.retrievalDone && !status.generationDone}
        />

        {/* Stage 4: NLI Verification */}
        <StageCard
          title="4. Claim Entailment"
          subtitle="Atomic NLI Verifier"
          icon={ShieldCheck}
          done={status.verificationDone || status.isCompleted}
          active={status.generationDone && !status.verificationDone}
        />
      </div>
    </div>
  )
}

function StageCard({ title, subtitle, icon: Icon, done, active }) {
  return (
    <div
      className={`rounded-xl p-3 border transition-all duration-300 flex flex-col justify-between ${
        done
          ? 'bg-surface-900/90 border-emerald-500/40 text-emerald-300 shadow-sm shadow-emerald-950/20'
          : active
          ? 'bg-cyan-950/30 border-cyan-500/60 text-cyan-200 shadow-glow-cyan'
          : 'bg-surface-900/40 border-slate-800/80 text-slate-500'
      }`}
    >
      <div className="flex items-center justify-between gap-1.5 mb-1.5">
        <div className="flex items-center gap-1.5">
          <Icon size={14} className={done ? 'text-emerald-400' : active ? 'text-cyan-400 animate-pulse' : 'text-slate-500'} />
          <span className="text-xs font-semibold tracking-tight">{title}</span>
        </div>
        {done ? (
          <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
        ) : active ? (
          <Loader2 size={13} className="text-cyan-400 animate-spin shrink-0" />
        ) : (
          <span className="w-2 h-2 rounded-full bg-slate-700 shrink-0" />
        )}
      </div>
      <p className="text-[11px] text-slate-400 leading-tight">
        {subtitle}
      </p>
    </div>
  )
}
