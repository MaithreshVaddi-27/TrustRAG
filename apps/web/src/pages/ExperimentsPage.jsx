import AppLayout from '@/layouts/AppLayout'
import { FlaskConical, Plus } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const EXPERIMENT_CONFIGS = [
  { name: 'baseline_rag',      label: 'Baseline RAG' },
  { name: 'hybrid_rag',        label: 'Hybrid RAG' },
  { name: 'hybrid_rerank',     label: 'Hybrid + Rerank' },
  { name: 'verified_rag',      label: 'Verified RAG' },
  { name: 'trustrag_full',     label: 'TRUSTRAG Full' },
]

// Placeholder chart data — replaced by real experiment results in Phase 11
const PLACEHOLDER_DATA = [
  { config: 'Baseline', evidence_coverage: 0, claim_support: 0, citation_correctness: 0 },
  { config: 'Hybrid',   evidence_coverage: 0, claim_support: 0, citation_correctness: 0 },
  { config: 'TRUSTRAG', evidence_coverage: 0, claim_support: 0, citation_correctness: 0 },
]

export default function ExperimentsPage() {
  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Experiments</h1>
            <p className="text-slate-400 text-sm mt-1">Compare RAG configurations with objective metrics</p>
          </div>
          <button id="new-experiment" className="btn-primary flex items-center gap-2">
            <Plus size={14} /> New Experiment
          </button>
        </div>

        {/* Config cards */}
        <div>
          <p className="section-heading">Available Configurations</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {EXPERIMENT_CONFIGS.map(({ name, label }) => (
              <div key={name} className="glass-card p-3 flex items-center gap-3">
                <FlaskConical size={14} className="text-primary-400 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-slate-200">{label}</p>
                  <p className="text-xs text-slate-500 font-mono">{name}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Metrics chart (empty until experiments run) */}
        <div className="glass-card p-5">
          <p className="section-heading">Metric Comparison</p>
          <p className="text-xs text-slate-600 mb-4">No experiment results yet. Run experiments to populate this chart.</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={PLACEHOLDER_DATA} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="config" tick={{ fill: '#64748b', fontSize: 12 }} />
              <YAxis tick={{ fill: '#64748b', fontSize: 12 }} domain={[0, 1]} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#94a3b8' }}
              />
              <Legend wrapperStyle={{ color: '#64748b', fontSize: 12 }} />
              <Bar dataKey="evidence_coverage"   name="Evidence Coverage"    fill="#6366f1" radius={[4,4,0,0]} />
              <Bar dataKey="claim_support"        name="Claim Support Rate"   fill="#22c55e" radius={[4,4,0,0]} />
              <Bar dataKey="citation_correctness" name="Citation Correctness" fill="#f59e0b" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-slate-600 mt-3 italic">
            No fabricated results. All metrics come from actual system runs. See docs/evaluation/methodology.md.
          </p>
        </div>
      </div>
    </AppLayout>
  )
}
