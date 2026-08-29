import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { useAuthStore, authStore } from '@/store/authStore'
import { healthService } from '@/services/api'
import {
  Server,
  ShieldCheck,
  Cpu,
  Database,
  User,
  Copy,
  Check,
  LogOut,
  Layers,
  Activity,
  FileText,
  Clock,
  Loader2,
} from 'lucide-react'

export default function SettingsPage() {
  const { user } = useAuthStore()
  const [copied, setCopied] = useState(false)

  const { data: health, isLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: healthService.get,
    refetchInterval: 30000,
  })

  const copyUserId = () => {
    if (user?.id) {
      navigator.clipboard.writeText(user.id)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleLogout = () => {
    if (confirm('Are you sure you want to sign out?')) {
      authStore.clearSession()
      window.location.href = '/login'
    }
  }

  const mongoStatus = health?.services?.mongodb === 'ok'
  const qdrantStatus = health?.services?.qdrant === 'ok'
  const models = health?.models || {}
  const supportedFormats = health?.supported_formats || [
    'pdf',
    'txt',
    'md',
    'docx',
    'csv',
    'json',
    'html',
    'htm',
  ]

  return (
    <AppLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
              <Activity className="text-primary-400" size={24} />
              Settings & Diagnostics
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Live system health, multi-tenant partitioning, and active AI model configurations.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                health?.status === 'ok'
                  ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'
                  : 'bg-amber-950/80 text-amber-400 border-amber-800/60'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  health?.status === 'ok' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
              System {health?.status === 'ok' ? 'Operational' : 'Degraded'}
            </span>
          </div>
        </div>

        {/* Cluster Infrastructure Status */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <Server size={18} className="text-primary-400" />
              <h2 className="font-semibold text-slate-200 text-base">
                Cluster Infrastructure & Storage
              </h2>
            </div>
            {isLoading && <Loader2 size={16} className="animate-spin text-slate-500" />}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* MongoDB Card */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-slate-300 font-medium text-sm">
                    <Database size={15} className="text-emerald-400" /> MongoDB
                  </div>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      mongoStatus ? 'bg-emerald-400' : 'bg-red-400'
                    }`}
                  />
                </div>
                <p className="text-xs text-slate-400">
                  Document store, audit traces & verifiable claim state
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-700/40 flex items-center justify-between text-xs">
                <span className="text-slate-500">Status</span>
                <span
                  className={`font-semibold ${mongoStatus ? 'text-emerald-400' : 'text-red-400'}`}
                >
                  {mongoStatus ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>

            {/* Qdrant Card */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-slate-300 font-medium text-sm">
                    <Layers size={15} className="text-primary-400" /> Qdrant
                  </div>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      qdrantStatus ? 'bg-emerald-400' : 'bg-red-400'
                    }`}
                  />
                </div>
                <p className="text-xs text-slate-400">
                  Dense & sparse hybrid vector collection indexing
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-700/40 flex items-center justify-between text-xs">
                <span className="text-slate-500">Status</span>
                <span
                  className={`font-semibold ${qdrantStatus ? 'text-emerald-400' : 'text-red-400'}`}
                >
                  {qdrantStatus ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>

            {/* Environment Card */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-slate-300 font-medium text-sm">
                    <ShieldCheck size={15} className="text-amber-400" /> Environment
                  </div>
                </div>
                <p className="text-xs text-slate-400">
                  Runtime execution profile and isolation policy
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-700/40 flex items-center justify-between text-xs">
                <span className="text-slate-500">Mode</span>
                <span className="font-semibold text-slate-200 capitalize">
                  {health?.environment || 'development'}
                </span>
              </div>
            </div>

            {/* Version Card */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-slate-300 font-medium text-sm">
                    <Clock size={15} className="text-blue-400" /> Version
                  </div>
                </div>
                <p className="text-xs text-slate-400">Platform release and ontology specification</p>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-700/40 flex items-center justify-between text-xs">
                <span className="text-slate-500">Release</span>
                <span className="font-semibold text-slate-200 font-mono">
                  {health?.version || '0.1.0'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Active AI Model Pipeline Configuration */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <Cpu size={18} className="text-primary-400" />
              <h2 className="font-semibold text-slate-200 text-base">Active Model Registry</h2>
            </div>
            <span className="text-xs text-slate-500 font-mono">config/models.yaml</span>
          </div>

          <div className="divide-y divide-slate-800/60 text-xs">
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-slate-400 font-medium">Grounded Generator (LLM)</span>
              <span className="font-mono text-slate-200 bg-surface-800 px-2 py-0.5 rounded border border-slate-700/60">
                {models.llm_model || 'gemini-3.5-flash-lite'}
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-slate-400 font-medium">Dense Vector Embeddings</span>
              <span className="font-mono text-slate-200 bg-surface-800 px-2 py-0.5 rounded border border-slate-700/60">
                {models.embedding_model || 'sentence-transformers/all-MiniLM-L6-v2'} (384-dim)
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-slate-400 font-medium">NLI Claim Verifier</span>
              <span className="font-mono text-slate-200 bg-surface-800 px-2 py-0.5 rounded border border-slate-700/60">
                {models.verification_model || 'gemini-3.5-flash-lite'} (temp=0.0)
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-slate-400 font-medium">CrossEncoder Neural Reranker</span>
              <span className="font-mono text-slate-200 bg-surface-800 px-2 py-0.5 rounded border border-slate-700/60">
                {models.reranker_enabled ? models.reranker_model : 'disabled (on-demand)'}
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-slate-400 font-medium">Retrieval Fusion Strategy</span>
              <span className="text-slate-300">Reciprocal Rank Fusion (RRF, k=60)</span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-slate-400 font-medium">Adaptive Recovery Ceiling</span>
              <span className="text-slate-300">
                Max 2 rewrites &bull; Max 2 context expansions
              </span>
            </div>
          </div>

          {/* Supported Formats */}
          <div className="pt-2">
            <p className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
              <FileText size={14} className="text-primary-400" />
              Supported Document Ingestion Formats
            </p>
            <div className="flex flex-wrap gap-2">
              {supportedFormats.map((fmt) => (
                <span
                  key={fmt}
                  className="px-2.5 py-1 bg-surface-800/80 border border-slate-700/80 rounded-lg text-xs font-mono text-slate-300 uppercase tracking-wider"
                >
                  .{fmt}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Authenticated User & Multi-Tenant Partitioning */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <User size={18} className="text-primary-400" />
              <h2 className="font-semibold text-slate-200 text-base">
                Account & Multi-Tenant Isolation
              </h2>
            </div>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 bg-red-950/60 hover:bg-red-900/80 border border-red-800/80 text-red-300 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5"
            >
              <LogOut size={13} /> Sign Out
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="bg-surface-800/40 border border-slate-700/50 rounded-xl p-3.5 space-y-1">
              <span className="text-slate-500 font-medium">Authenticated Account</span>
              <p className="font-semibold text-slate-200 text-sm">{user?.email || 'Active User'}</p>
              <p className="text-slate-500 text-[11px] mt-1">
                Partitioned workspace scoped to this user session.
              </p>
            </div>

            <div className="bg-surface-800/40 border border-slate-700/50 rounded-xl p-3.5 space-y-1">
              <span className="text-slate-500 font-medium">Tenant ID</span>
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-slate-300 text-xs truncate max-w-[220px]">
                  {user?.id || '64ee39d09c6292376e191981'}
                </span>
                <button
                  onClick={copyUserId}
                  className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-surface-700 transition-colors"
                  title="Copy Tenant ID"
                >
                  {copied ? (
                    <Check size={14} className="text-emerald-400" />
                  ) : (
                    <Copy size={14} />
                  )}
                </button>
              </div>
              <p className="text-slate-500 text-[11px] mt-1">
                Unique identifier enforcing compound index boundaries.
              </p>
            </div>
          </div>

          <div className="p-3.5 bg-primary-950/30 border border-primary-800/40 rounded-xl text-xs text-primary-300 flex items-start gap-2.5">
            <ShieldCheck size={16} className="text-primary-400 shrink-0 mt-0.5" />
            <p>
              <strong className="text-primary-200">Strict Tenant Partitioning Active:</strong> All
              knowledge base records, decomposed claims, retrieved evidence, and Qdrant vector points
              are filtered strictly by your Tenant ID. Cross-tenant access is prohibited at the API
              gateway and database layer.
            </p>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
