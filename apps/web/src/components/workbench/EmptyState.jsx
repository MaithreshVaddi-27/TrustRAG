import { Database, Cpu, Brain, ShieldCheck, Sparkles, Globe, Terminal, CornerDownLeft } from 'lucide-react'

/**
 * EmptyState — what the playground does before you ask it anything.
 *
 * The five pipeline stages are ordered, and the order is the information, so
 * they read as plates in a stack rather than five equal cards. A row of
 * equal cards makes the reader hunt for the stage that matters; a stack
 * says "this is the sequence, and it runs in this order".
 */
const PIPELINE_PREVIEW = [
  {
    step: '01',
    title: 'Hybrid retrieval',
    tag: 'Dense + BM25',
    desc: 'Dense ONNX 384d vector similarity fused with sparse BM25 keyword rankings.',
    icon: Database,
  },
  {
    step: '02',
    title: 'Evidence synthesis',
    tag: 'Strict grounding',
    desc: 'Zero-temperature local generation conditioned strictly on the retrieved chunks.',
    icon: Cpu,
  },
  {
    step: '03',
    title: 'Claim extraction',
    tag: 'Subject-predicate-object',
    desc: 'Decomposes the generated answer into atomic, falsifiable factual claims.',
    icon: Brain,
  },
  {
    step: '04',
    title: 'NLI entailment',
    tag: 'Fact verification',
    desc: 'Checks every claim against its citations: supported, contradicted, or neutral.',
    icon: ShieldCheck,
  },
  {
    step: '05',
    title: 'Closed-loop healing',
    tag: 'LangGraph StateGraph',
    desc: 'Triggers a query rewrite or context expansion when reliability drops below 75%.',
    icon: Sparkles,
  },
]

export function EmptyState({ enableWebSearch = false }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="px-5 py-8 sm:px-8 sm:py-10">
        <div className="mx-auto w-full max-w-3xl space-y-8">
          <div>
            <p className="lx-micro flex items-center gap-2">
              <span className="lx-dot lx-dot--live" aria-hidden="true" />
              Interactive verification workbench
            </p>

            <h2 className="lx-h2 mt-3">Awaiting a query</h2>

            <p className="lx-body mt-3 max-w-[62ch]">
              Ask a question against an indexed knowledge base and the pipeline
              will retrieve, synthesise, decompose and verify it — reporting
              every step as it happens.
            </p>
          </div>

          <div>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h3 className="lx-workbench__label !mb-0 flex items-center gap-2">
                Reliability pipeline stages
              </h3>
              <span className="lx-micro">Autonomous orchestration</span>
            </div>

            <div className="lx-layers">
              {PIPELINE_PREVIEW.map((phase) => {
                const Icon = phase.icon
                return (
                  <article key={phase.step} className="lx-layer">
                    <span className="lx-layer__index">{phase.step}</span>

                    <div>
                      <h4 className="lx-layer__title">
                        <Icon
                          size={16}
                          strokeWidth={1.5}
                          className="lx-layer__icon"
                          aria-hidden="true"
                        />
                        {phase.title}
                      </h4>
                      <p className="lx-layer__desc">{phase.desc}</p>
                      <div className="lx-layer__tags">
                        <span className="lx-layer__tag">{phase.tag}</span>
                      </div>
                    </div>

                    <div className="lx-layer__spec">
                      <div className="lx-layer__spec-row">
                        <span className="lx-layer__spec-key">Stage</span>
                        <span className="lx-layer__spec-val">{phase.step}</span>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[color:var(--rule-faint)] pt-5">
            <p className="lx-micro flex items-center gap-2">
              <Terminal size={13} strokeWidth={1.75} aria-hidden="true" />
              Ready to verify. Press{' '}
              <kbd className="inline-flex items-center gap-0.5 rounded border border-[color:var(--rule)] bg-surface-inset px-1.5 py-0.5 font-mono text-[0.625rem] text-silver-300">
                <CornerDownLeft size={10} aria-hidden="true" /> ⌘↵
              </kbd>{' '}
              to run.
            </p>

            {enableWebSearch && (
              <span className="lx-chip">
                <Globe size={11} strokeWidth={1.75} aria-hidden="true" />
                MCP web grounding enabled
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
