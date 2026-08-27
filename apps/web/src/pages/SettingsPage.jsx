import AppLayout from '@/layouts/AppLayout'

export default function SettingsPage() {
  return (
    <AppLayout>
      <div className="p-6 max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-slate-400 text-sm mt-1">Account and application settings</p>
        </div>

        {/* Model config display (read-only in UI — change in models.yaml) */}
        <div className="glass-card p-5 space-y-4">
          <p className="section-heading">Active Model Configuration</p>
          <p className="text-xs text-slate-500">
            Model IDs and thresholds are centralized in{' '}
            <code className="text-primary-400 bg-surface-800 px-1 rounded">config/models.yaml</code>.
            Changes require a backend restart. Never set API keys here.
          </p>
          <div className="space-y-2 font-mono text-xs">
            {[
              ['LLM', 'gemini-2.5-flash (configurable)'],
              ['Embeddings', 'sentence-transformers/all-MiniLM-L6-v2 · 384-dim'],
              ['Verification', 'gemini-2.5-flash · temp=0.0'],
              ['Reranker', 'disabled (configurable)'],
              ['Fusion', 'RRF (Reciprocal Rank Fusion)'],
              ['Max context chunks', '8'],
              ['Abstain below', '0.50'],
              ['Max recovery attempts', '2'],
            ].map(([k, v]) => (
              <div key={k} className="flex items-start gap-3 py-1.5 border-b border-slate-800 last:border-0">
                <span className="text-slate-500 min-w-[160px] shrink-0">{k}</span>
                <span className="text-slate-300">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-card p-5">
          <p className="section-heading">Account</p>
          <p className="text-slate-500 text-sm">Account management coming in Phase 4.</p>
        </div>
      </div>
    </AppLayout>
  )
}
