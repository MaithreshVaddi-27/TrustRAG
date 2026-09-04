import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '@/layouts/AppLayout'
import { useAuthStore, authStore } from '@/store/authStore'
import { healthService, modelService } from '@/services/api'
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
  Terminal,
  Sparkles,
  Zap,
} from 'lucide-react'

export default function SettingsPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [copied, setCopied] = useState(false)
  const [trimming, setTrimming] = useState(false)
  const [trimResult, setTrimResult] = useState(null)

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

  const { data: health, isLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: healthService.get,
    refetchInterval: 30000,
  })

  const { data: providersData } = useQuery({
    queryKey: ['settings-model-providers'],
    queryFn: modelService.getProviders,
    refetchInterval: 15000,
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
      navigate('/login')
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
      <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6 animate-fade-in stagger-children">
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

        {/* Hardware Acceleration & System Health */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <Zap size={18} className="text-amber-400" />
              <h2 className="font-semibold text-slate-200 text-base">
                Hardware Acceleration & System Health
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${
                providersData?.hardware?.health?.status === 'optimal'
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/40'
                  : 'bg-amber-950/80 text-amber-300 border-amber-800/40'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${providersData?.hardware?.health?.status === 'optimal' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                {providersData?.hardware?.health?.status === 'optimal' ? 'System Healthy' : 'Resource Pressure'}
              </span>
              <button
                type="button"
                onClick={handleTrimMemory}
                disabled={trimming}
                className="px-2.5 py-1 text-xs rounded-lg bg-surface-800 hover:bg-surface-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
              >
                {trimming ? <Loader2 size={12} className="animate-spin" /> : <Activity size={12} className="text-cyan-400" />}
                <span>Compact Heap</span>
              </button>
            </div>
          </div>

          {trimResult && (
            <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-xs text-emerald-300 animate-fade-in flex items-center justify-between">
              <span>Heap memory compacted successfully. Current process RSS: {trimResult.after_mb} MB</span>
              <span className="font-mono text-[10px] text-emerald-400">Freed: {trimResult.freed_mb} MB</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Accelerator */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 space-y-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold block">Hardware Accelerator</span>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-100 text-sm">
                  {providersData?.hardware?.accelerator_name || 'Detecting...'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Engine: <code className="text-amber-400 font-mono">{providersData?.hardware?.accelerator?.toUpperCase() || 'CPU'}</code> &bull; Machine: <code className="text-slate-300 font-mono">{providersData?.hardware?.machine || 'arm64'}</code>
              </p>
            </div>

            {/* Memory & VRAM */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 space-y-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold block">Host Memory (RAM)</span>
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-100 text-sm">
                  {providersData?.hardware?.memory?.used_gb || 0} / {providersData?.hardware?.memory?.total_gb || 8} GB
                </span>
                <span className="font-mono text-xs text-cyan-400">
                  {providersData?.hardware?.memory?.usage_pct || 0}%
                </span>
              </div>
              <div className="w-full bg-surface-900 rounded-full h-1.5 border border-slate-800 overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 rounded-full ${
                    (providersData?.hardware?.memory?.usage_pct || 0) > 85 ? 'bg-amber-400' : 'bg-cyan-500'
                  }`}
                  style={{ width: `${Math.min(100, providersData?.hardware?.memory?.usage_pct || 0)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Process RSS: <span className="text-slate-300 font-mono">{providersData?.hardware?.process_rss_mb || 0} MB</span>
              </p>
            </div>

            {/* Hardware-Adaptive Recommendations */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 space-y-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold block">Auto-Tuned Recommendation</span>
              <div className="space-y-1 text-xs text-slate-300">
                <div>Optimal LLM: <code className="text-emerald-300 font-mono">{providersData?.hardware?.recommendations?.primary_llm || 'granite4.2:3b-q4_K_M'}</code></div>
                <div>Optimal Embed: <code className="text-cyan-300 font-mono">{providersData?.hardware?.recommendations?.primary_embedding || 'embeddinggemma:300m-qat-q8_0'}</code></div>
                <div>Safe Concurrency: <span className="text-slate-400">{providersData?.hardware?.recommendations?.max_concurrency || 2} concurrent runs</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* Local LLM Infrastructure (Ollama & llama.cpp) */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <Terminal size={18} className="text-emerald-400" />
              <h2 className="font-semibold text-slate-200 text-base">
                Local LLM Infrastructure (Private & Offline)
              </h2>
            </div>
            <span className="text-xs text-slate-500 font-mono">localhost:11434 / localhost:8081</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Ollama Engine */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col justify-between space-y-3">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
                    <Cpu size={15} className="text-emerald-400" /> Ollama Engine
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono ${
                    providersData?.providers?.ollama?.connected
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
                      : 'bg-amber-950/80 text-amber-400 border border-amber-800/40'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${providersData?.providers?.ollama?.connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                    {providersData?.providers?.ollama?.connected ? 'Online' : 'Unreachable'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Native local inference server. Active model: <code className="text-emerald-300 font-mono">granite4.2:3b-q4_K_M</code>
                </p>
                <div className="mt-2 text-[11px] text-slate-400 space-y-1">
                  <div>Endpoint: <code className="text-slate-300 font-mono">http://localhost:11434</code></div>
                  <div>Discovery Command: <code className="text-emerald-400 font-mono">ollama list</code></div>
                  <div>Configured LLMs: <span className="text-slate-300 font-mono">{providersData?.providers?.ollama?.models?.join(', ') || 'granite4.2:3b-q4_K_M, qwen3.5:4b, gemma4:e2b-it-qat'}</span></div>
                  <div>Dense Embeddings: <span className="text-emerald-300 font-mono">{providersData?.embedding_providers?.ollama?.models?.map(m => m.id).join(', ') || 'embeddinggemma:300m-qat-q8_0'}</span></div>
                </div>
              </div>

              {!providersData?.providers?.ollama?.connected && (
                <div className="p-2.5 bg-amber-950/40 border border-amber-800/40 rounded-lg text-[11px] text-amber-300">
                  💡 Start Ollama by running <code className="bg-surface-900 px-1 py-0.5 rounded text-amber-200 font-mono">ollama serve</code> and <code className="bg-surface-900 px-1 py-0.5 rounded text-amber-200 font-mono">ollama pull granite4.2:3b-q4_K_M</code>.
                </div>
              )}
            </div>

            {/* llama.cpp Engine */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col justify-between space-y-3">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
                    <Terminal size={15} className="text-cyan-400" /> llama.cpp Server
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono ${
                    providersData?.providers?.llama_cpp?.connected
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
                      : 'bg-amber-950/80 text-amber-400 border border-amber-800/40'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${providersData?.providers?.llama_cpp?.connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                    {providersData?.providers?.llama_cpp?.connected ? 'Online' : 'Standby'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  OpenAI-compatible server. Active model: <code className="text-cyan-300 font-mono">ibm-granite/granite-4.2-3b-GGUF:Q4_K_M</code>
                </p>
                <div className="mt-2 text-[11px] text-slate-400 space-y-1">
                  <div>Endpoint: <code className="text-slate-300 font-mono">http://localhost:8081/v1</code></div>
                  <div>Discovery Command: <code className="text-cyan-400 font-mono">llama-server --cache-list</code></div>
                  <div>Cache GGUF Models: <span className="text-slate-300 font-mono">{providersData?.providers?.llama_cpp?.cache_models?.join(', ') || 'ggml-org/embeddinggemma-300M-GGUF:Q8_0'}</span></div>
                  <div>Configured LLMs: <span className="text-cyan-300 font-mono">{providersData?.providers?.llama_cpp?.models?.join(', ') || 'ibm-granite/granite-4.2-3b-GGUF:Q4_K_M, psychopenguin/Qwen3.5-4B-Q4_K_M-GGUF:Q4_K_M, google/gemma-4-E2B-it-qat-q4_0-gguf:Q4_0'}</span></div>
                </div>
              </div>

              {!providersData?.providers?.llama_cpp?.connected && (
                <div className="p-2.5 bg-surface-900/60 border border-slate-700/50 rounded-lg text-[11px] text-slate-400">
                  💡 Start server: <code className="bg-surface-950 px-1 py-0.5 rounded text-cyan-300 font-mono">llama-server -m granite-4.2-3b.gguf --port 8081</code>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Dense Vector Embedding Infrastructure */}
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <Layers size={18} className="text-cyan-400" />
              <h2 className="font-semibold text-slate-200 text-base">
                Dense Vector Embedding Infrastructure
              </h2>
            </div>
            <span className="text-xs text-slate-500 font-mono">Active: {providersData?.active_embedding_model || 'embeddinggemma:300m-qat-q8_0'}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {/* Local Ollama Embeddings */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-3.5 flex flex-col justify-between space-y-2">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-200 font-semibold text-xs">Local Ollama</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">768d</span>
                </div>
                <p className="text-[11px] text-slate-400">Dense vectors via Ollama /api/embed.</p>
              </div>
              <div className="pt-2 border-t border-slate-700/40 text-[10px] text-emerald-300 font-mono truncate" title="embeddinggemma:300m-qat-q8_0">
                embeddinggemma:300m-qat-q8_0
              </div>
            </div>

            {/* Local llama.cpp GGUF Embeddings */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-3.5 flex flex-col justify-between space-y-2">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-200 font-semibold text-xs">llama.cpp GGUF</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-950/80 text-amber-400 border border-amber-800/40">768d</span>
                </div>
                <p className="text-[11px] text-slate-400">Offline GGUF embeddings over port 8081.</p>
              </div>
              <div className="pt-2 border-t border-slate-700/40 text-[10px] text-amber-300 font-mono truncate" title="ggml-org/embeddinggemma-300M-GGUF:Q8_0">
                embeddinggemma-300M (Q8_0)
              </div>
            </div>

            {/* Local HuggingFace BGE */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-3.5 flex flex-col justify-between space-y-2">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-200 font-semibold text-xs">HuggingFace BGE</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950/80 text-cyan-400 border border-cyan-800/40">384d</span>
                </div>
                <p className="text-[11px] text-slate-400">Local PyTorch / CPU. Zero API cost.</p>
              </div>
              <div className="pt-2 border-t border-slate-700/40 text-[10px] text-cyan-300 font-mono truncate" title="BAAI/bge-small-en-v1.5">
                bge-small-en-v1.5
              </div>
            </div>

            {/* Google Gemini Embeddings */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-3.5 flex flex-col justify-between space-y-2">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-200 font-semibold text-xs">Google Gemini</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/80 text-indigo-400 border border-indigo-800/40">384d</span>
                </div>
                <p className="text-[11px] text-slate-400">Matryoshka API embeddings.</p>
              </div>
              <div className="pt-2 border-t border-slate-700/40 text-[10px] text-indigo-300 font-mono truncate" title="models/gemini-embedding-001">
                gemini-embedding-001
              </div>
            </div>

            {/* NVIDIA NIM Embeddings */}
            <div className="bg-surface-800/60 border border-slate-700/60 rounded-xl p-3.5 flex flex-col justify-between space-y-2">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-200 font-semibold text-xs">NVIDIA NIM</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-950/80 text-purple-400 border border-purple-800/40">384d</span>
                </div>
                <p className="text-[11px] text-slate-400">Enterprise cloud endpoints.</p>
              </div>
              <div className="pt-2 border-t border-slate-700/40 text-[10px] text-purple-300 font-mono truncate" title="nvidia/nv-embedqa-e5-v5">
                nv-embedqa-e5-v5
              </div>
            </div>
          </div>

          {/* Model Context Protocol (MCP) Interface */}
          <div className="pt-3 border-t border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                <Sparkles size={14} className="text-cyan-400" />
                <span>Model Context Protocol (MCP) Protocol Interface</span>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800/40">
                stdio & in-process active
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Standardized MCP server exposing TrustRAG and local LLM tools to Cursor, Claude Desktop, Antigravity IDE, and external agents:
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 text-[11px] font-mono">
              <div className="p-2 bg-surface-900/80 border border-slate-800 rounded-lg text-slate-300">
                <span className="text-cyan-400 font-semibold block">trustrag_search</span>
                <span className="text-[10px] text-slate-500 font-sans">Hybrid RRF Search</span>
              </div>
              <div className="p-2 bg-surface-900/80 border border-slate-800 rounded-lg text-slate-300">
                <span className="text-cyan-400 font-semibold block">trustrag_verify_claim</span>
                <span className="text-[10px] text-slate-500 font-sans">NLI Verification</span>
              </div>
              <div className="p-2 bg-surface-900/80 border border-slate-800 rounded-lg text-slate-300">
                <span className="text-cyan-400 font-semibold block">duckduckgo_search</span>
                <span className="text-[10px] text-slate-500 font-sans">Free Web Grounding</span>
              </div>
              <div className="p-2 bg-surface-900/80 border border-slate-800 rounded-lg text-slate-300">
                <span className="text-cyan-400 font-semibold block">local_llm_chat</span>
                <span className="text-[10px] text-slate-500 font-sans">Ollama/llama.cpp MCP</span>
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
              <span className="text-slate-400 font-medium">Active LLM Engine</span>
              <span className="font-mono text-emerald-300 bg-surface-800 px-2 py-0.5 rounded border border-slate-700/60 uppercase">
                {models.llm_provider || 'ollama'} ({models.llm_model || 'gemma4:e2b'})
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
                  {user?.id || 'Not available'}
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
