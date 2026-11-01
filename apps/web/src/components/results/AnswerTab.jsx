import { useState } from 'react'
import { motion } from 'motion/react'
import { Sparkles, Clock, Copy, Check, Download } from 'lucide-react'
import { clsx } from 'clsx'
import { SPRING_SNAPPY } from '@/lib/motionConfig'
import { ReliabilityBadge } from '@/components/workbench/ReliabilityBadge'
import { FormattedAnswer } from '@/components/workbench/FormattedAnswer'
import { RecoveryTimeline } from '@/components/workbench/ExecutionTrace'
import { copyToClipboard } from '@/lib/clipboard'
import { shortModelId, providerShortLabel } from '@/lib/modelLabels'

export function AnswerTab({ analysis, selectedProvider, selectedModel, selectedEmbeddingModel, enableWebSearch, recoveryRuns, onExportDossier, onCopyAnswer }) {
  if (!analysis) return null

  const answerWordCount = analysis?.answer ? analysis.answer.trim().split(/\s+/).filter(Boolean).length : 0
  const estimatedReadTime = Math.max(1, Math.ceil(answerWordCount / 180))
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!analysis?.answer) return
    const ok = await copyToClipboard(analysis.answer)
    if (!ok) return
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <motion.div
      key="answer"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={SPRING_SNAPPY}
      className="space-y-5"
    >
      {(analysis.status === 'failed' || analysis.status === 'outage' || analysis.reliability?.status === 'FAILED') && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/30 p-4 shadow-glow-crimson animate-fade-in">
          <p className="text-sm font-medium text-red-300">
            {analysis.status === 'failed' || analysis.status === 'outage'
              ? `Analysis failed: ${analysis.diagnosis?.failures?.[0] || 'Retrieval service is temporarily unavailable'}`
              : `Reliability check failed: ${analysis.diagnosis?.failures?.[0] || 'Thresholds not met'}`}
          </p>
        </div>
      )}

      {(analysis.status === 'abstained' || analysis.reliability?.status === 'ABSTAINED') && (
        <div className="rounded-xl border border-amber-800/50 bg-amber-950/30 p-4 shadow-glow-amber animate-fade-in">
          <p className="text-sm font-medium text-amber-300">
            ⊘ The agent abstained from answering because the retrieved document segments did not contain sufficient factual evidence to answer this question reliably without hallucinating.
          </p>
          <p className="text-xs text-amber-400/90 mt-1.5">
            Tip: Try phrasing your question using specific section names or verify that your uploaded documents cover this topic.
          </p>
        </div>
      )}

      {analysis.answer && analysis.answer !== 'ABSTAIN' && (
        <div className="glass-card p-5 sm:p-6 relative overflow-hidden border-slate-700/60 hover:border-cyan-500/40 transition-all shadow-lg">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800/80 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
                <Sparkles size={14} />
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                Grounded Synthesis
              </span>
              <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1 ml-2">
                <Clock size={11} />{' '}
                {answerWordCount < 120
                  ? `${selectedProvider || 'local'} · terse by design`
                  : `~${estimatedReadTime} min read (${answerWordCount} words)`}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleCopy}
                className="text-xs text-slate-400 hover:text-cyan-300 flex items-center gap-1.5 transition-all px-3 py-1.5 rounded-lg bg-surface-800/90 border border-slate-700/60 hover:border-cyan-500/50 shadow-sm"
                title="Copy answer to clipboard"
                aria-label="Copy answer to clipboard"
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                <span className={copied ? 'text-emerald-400 font-medium' : ''}>
                  {copied ? 'Copied!' : 'Copy Answer'}
                </span>
              </button>
              <button
                type="button"
                onClick={onExportDossier}
                title="Export Verification Audit Report (JSON-LD)"
                aria-label="Export verification audit report"
                className="px-3 py-1.5 text-xs border border-slate-700 hover:border-cyan-500/50 rounded-xl text-slate-300 hover:text-white flex items-center gap-1.5 transition-all bg-surface-800/90 hover:bg-surface-700/80 shadow-sm"
              >
                <Download size={13} className="text-cyan-400" />
                <span className="font-medium">Export</span>
              </button>
            </div>
          </div>
          <FormattedAnswer content={analysis.answer} />
        </div>
      )}

      {analysis.claims?.some(c => c.state === 'NEUTRAL' || c.state === 'CONTRADICTED') && (
        <div className="rounded-xl border border-amber-800/40 bg-amber-950/20 px-4 py-3">
          <p className="text-xs text-amber-300">
            ⚠ Some claims could not be verified against the citation corpus. Inspect the Claims tab for proposition-level breakdown.
          </p>
        </div>
      )}

      <RecoveryTimeline recoveryRuns={recoveryRuns} />
    </motion.div>
  )
}