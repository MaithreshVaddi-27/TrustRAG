import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import AppLayout from '@/layouts/AppLayout'
import { EvidenceViewer } from '@/components/workbench/EvidenceViewer'
import { evidenceService } from '@/services/api'
import { FileSearch, ArrowRight, Database, Hash, GitMerge, FileText } from 'lucide-react'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

export default function EvidencePage() {
  const { data: evidence = [], isLoading, error } = useQuery({
    queryKey: ['all-evidence'],
    queryFn: evidenceService.list,
  })

  return (
    <AppLayout>
      <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6 animate-fade-in stagger-children">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-xs font-mono bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 shadow-sm">
              <FileSearch size={12} />
              <span>Hybrid Ingestion & Provenance</span>
            </div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Evidence <span className="text-cyan-400">Vault</span>
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono">
                {evidence.length} {evidence.length === 1 ? 'Record' : 'Records'}
              </span>
            </div>
            <p className="text-slate-400 text-sm">
              Retrieved evidence chunks across all analyses, with provenance, score breakdown, and integrity audits.
            </p>
          </div>

          <Link
            to="/playground"
            className="self-start sm:self-auto inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-md shadow-primary-950/50 transition-all cursor-pointer"
          >
            <span>Run New Query</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        {/* Body */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-16 space-y-4">
            <ThinkingOrbs size="md" />
            <span className="text-sm text-slate-400">Loading retrieved evidence records...</span>
          </div>
        ) : error ? (
          <div className="glass-card p-6 text-center text-red-400 border border-red-800/40">
            Failed to load evidence: {error.message || 'An unexpected error occurred'}
          </div>
        ) : evidence.length === 0 ? (
          <div className="space-y-6">
            <div className="glass-card p-10 sm:p-14 text-center space-y-5 border-slate-800">
              <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400 shadow-inner">
                <FileSearch size={28} />
              </div>
              <div className="space-y-1.5 max-w-md mx-auto">
                <h3 className="text-base font-semibold text-white tracking-tight">No evidence segments retrieved yet</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Execute an analysis query in the Playground to ingest, score, and persist evidence chunks into the audit vault with verified token spans.
                </p>
              </div>
              <div>
                <Link
                  to="/playground"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-950/60 transition-all cursor-pointer"
                >
                  <span>Launch Playground Analysis</span>
                  <ArrowRight size={13} />
                </Link>
              </div>
            </div>

            {/* Architecture Explainer Card */}
            <div className="p-5 rounded-2xl bg-surface-900/60 border border-slate-800/80 space-y-3.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                <GitMerge size={14} className="text-cyan-400" />
                <span>Dual-Stream Retrieval & Provenance Pipeline</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-cyan-300">
                    <Database size={13} />
                    <span>Dense ONNX Vectors</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Embeddings generated locally with 384-dimensional cosine distance for semantic concept matching.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-primary-300">
                    <Hash size={13} />
                    <span>Sparse BM25 Index</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Porter-stemmed exact keyword matching with inverted document frequency for precise entity recall.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-surface-850/60 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-300">
                    <FileText size={13} />
                    <span>RRF Fusion (k=60)</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Reciprocal Rank Fusion merges dense and sparse scores into a calibrated, tamper-evident ranking.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <EvidenceViewer chunks={evidence} />
        )}
      </div>
    </AppLayout>
  )
}

