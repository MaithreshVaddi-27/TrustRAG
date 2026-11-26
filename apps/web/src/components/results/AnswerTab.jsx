import { lazy, Suspense, useState } from 'react'
import { Sparkles, Clock, Copy, Check, Download, AlertTriangle } from 'lucide-react'
import { RecoveryTimeline } from '@/components/workbench/ExecutionTrace'
import { copyToClipboard } from '@/lib/clipboard'

// The Markdown renderer and its parser stack are the heaviest dependency in
// the app, and the answer is the only thing that needs them. Loading it on
// demand keeps it out of the playground's initial chunk.
//
// The module exports the component by name, so the chunk is mapped onto the
// default shape React.lazy expects. Passing the namespace straight through
// left React.lazy with no component to render.
const FormattedAnswer = lazy(() =>
  import('@/components/workbench/FormattedAnswer').then((module) => ({
    default: module.FormattedAnswer,
  })),
)

/**
 * AnswerTab — the grounded synthesis.
 *
 * The answer is the product. It gets a panel with a header that states what
 * produced it, the answer itself in reading measure, and the two failures
 * that can precede it: a failed run and an abstention.
 */
export function AnswerTab({ analysis, selectedProvider, recoveryRuns, onExportDossier }) {
  const [copied, setCopied] = useState(false)

  if (!analysis) return null

  const answerWordCount = analysis?.answer
    ? analysis.answer.trim().split(/\s+/).filter(Boolean).length
    : 0
  const estimatedReadTime = Math.max(1, Math.ceil(answerWordCount / 180))

  const handleCopy = async () => {
    if (!analysis?.answer) return
    const ok = await copyToClipboard(analysis.answer)
    if (!ok) return
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const failed =
    analysis.status === 'failed' ||
    analysis.status === 'outage' ||
    analysis.reliability?.status === 'FAILED'

  const abstained =
    analysis.status === 'abstained' || analysis.reliability?.status === 'ABSTAINED'

  return (
    <div className="space-y-5">
      {failed && (
        <div className="lx-message lx-message--alarm" role="alert">
          <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <span className="lx-message__title">
              {analysis.status === 'failed' || analysis.status === 'outage'
                ? 'The analysis failed'
                : 'The reliability check failed'}
            </span>
            <span className="lx-message__body">
              {analysis.diagnosis?.failures?.[0] ||
                'Thresholds were not met for this run.'}
            </span>
          </div>
        </div>
      )}

      {abstained && (
        <div className="lx-message" role="status">
          <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <span className="lx-message__title">The agent abstained</span>
            <span className="lx-message__body">
              The retrieved segments did not contain enough factual evidence to
              answer this question reliably. Try naming a specific section, or
              check that your documents cover this topic.
            </span>
          </div>
        </div>
      )}

      {analysis.answer && analysis.answer !== 'ABSTAIN' && (
        <section className="lx-panel-block">
          <div className="lx-panel-block__head">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <Sparkles
                size={14}
                strokeWidth={1.75}
                aria-hidden="true"
                className="text-silver-500"
              />
              <h3 className="lx-panel-block__title">Grounded synthesis</h3>
              <span className="lx-micro flex items-center gap-1">
                <Clock size={11} strokeWidth={1.75} aria-hidden="true" />
                {answerWordCount < 120
                  ? `${selectedProvider || 'local'} · terse by design`
                  : `~${estimatedReadTime} min read · ${answerWordCount} words`}
              </span>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={handleCopy}
                className="lx-btn lx-btn--quiet"
                title="Copy the answer to the clipboard"
                aria-label="Copy the answer to the clipboard"
              >
                {copied ? (
                  <Check size={13} strokeWidth={2} aria-hidden="true" />
                ) : (
                  <Copy size={13} strokeWidth={1.75} aria-hidden="true" />
                )}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                type="button"
                onClick={onExportDossier}
                className="lx-btn lx-btn--secondary"
                title="Export the verification audit report as JSON-LD"
                aria-label="Export the verification audit report"
              >
                <Download size={13} strokeWidth={1.75} aria-hidden="true" />
                <span>Export</span>
              </button>
            </div>
          </div>

          <div className="lx-panel-block__body">
            <Suspense
              fallback={<div className="lx-skeleton h-40 w-full" aria-busy="true" />}
            >
              <FormattedAnswer content={analysis.answer} />
            </Suspense>
          </div>
        </section>
      )}

      {analysis.claims?.some(
        (claim) => claim.state === 'NEUTRAL' || claim.state === 'CONTRADICTED',
      ) && (
        <div className="lx-message lx-message--alarm" role="alert">
          <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
          <span>
            Some claims could not be verified against the citation corpus. Open
            the claims tab for the proposition-level breakdown.
          </span>
        </div>
      )}

      <RecoveryTimeline recoveryRuns={recoveryRuns} />
    </div>
  )
}
