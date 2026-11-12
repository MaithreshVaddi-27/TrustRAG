import { useRef, useCallback } from 'react'
import { analysisService } from '@/services/api'
import { openAnalysisStream } from '@/lib/api'

const TERMINAL_EVENTS = new Set([
  'analysis.completed',
  'analysis.abstained',
  'analysis.failed',
  'analysis.outage',
])

const MAX_POLL_ATTEMPTS = 45

// How long the run waits for the detail bundle before it finishes without
// it. The answer, the claims and the evidence are worth having, but a run
// that has already completed must not sit on "Pipeline running…" because
// one of those endpoints is slow.
const DETAIL_WAIT_MS = 10_000

/**
 * Race a promise against a deadline.
 *
 * Rejects with a timeout when the deadline passes first, so a caller can
 * treat "too slow" the same way it treats "failed". The loser is
 * abandoned, not cancelled — the caller has already moved on.
 */
function withDeadline(promise, ms) {
  return new Promise((resolve, reject) => {
    let settled = false
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true
        reject(new Error(`Timed out after ${ms}ms`))
      }
    }, ms)
    promise.then(
      (value) => {
        if (!settled) {
          settled = true
          clearTimeout(timer)
          resolve(value)
        }
      },
      (error) => {
        if (!settled) {
          settled = true
          clearTimeout(timer)
          reject(error)
        }
      },
    )
  })
}

export function useAnalysisStream() {
  const streamRef = useRef(null)
  const pollTimerRef = useRef(null)
  const finalizedRef = useRef(false)
  const traceEventsRef = useRef([])

  const cleanup = useCallback(() => {
    if (streamRef.current) {
      try {
        streamRef.current.close()
      } catch {
        // ignore
      }
      streamRef.current = null
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const fetchFinalAnalysis = useCallback(async (analysisId, onTraceUpdate, onComplete, onError) => {
    if (finalizedRef.current) return
    finalizedRef.current = true
    let attempts = 0
    let lastFetched = null

    try {
      while (attempts < MAX_POLL_ATTEMPTS) {
        attempts++
        try {
          const finalAnalysis = await analysisService.get(analysisId)
          lastFetched = finalAnalysis

          if (finalAnalysis.status === 'pending' || finalAnalysis.status === 'processing') {
            try {
              const traceList = await analysisService.trace(analysisId)
              if (traceList && traceList.length > 0) {
                traceEventsRef.current = traceList
                onTraceUpdate?.(traceList)
              }
            } catch {
              // trace endpoint may 404 while still processing
            }
            await new Promise((r) => setTimeout(r, 1500))
            continue
          }

          let claims = []
          let evidence = []
          let trace = []
          // Whether the evidence list is genuinely empty or simply could not
          // be read. The two are different answers, and only the request
          // knows which one it is.
          let evidenceUnavailable = false
          try {
            const detail = await withDeadline(
              analysisService.detail(analysisId),
              DETAIL_WAIT_MS,
            )
            claims = detail?.claims || []
            evidence = detail?.evidence || []
            trace = detail?.trace || []
          } catch {
            const [claimsRes, evidenceRes, traceRes] = await Promise.allSettled([
              withDeadline(analysisService.claims(analysisId), DETAIL_WAIT_MS),
              withDeadline(analysisService.evidence(analysisId), DETAIL_WAIT_MS),
              withDeadline(analysisService.trace(analysisId), DETAIL_WAIT_MS),
            ])
            claims = claimsRes.status === 'fulfilled' ? claimsRes.value || [] : []
            evidence = evidenceRes.status === 'fulfilled' ? evidenceRes.value || [] : []
            trace = traceRes.status === 'fulfilled' ? traceRes.value || [] : []
            evidenceUnavailable = evidenceRes.status !== 'fulfilled'
          }

          const fullAnalysis = {
            ...finalAnalysis,
            claims: claims || [],
            evidence: evidence || [],
            trace: (trace && trace.length > 0) ? trace : traceEventsRef.current,
            evidenceUnavailable,
          }

          onComplete?.(fullAnalysis)
          return
        } catch (err) {
          console.error('Polling error fetching analysis status:', err)
          await new Promise((r) => setTimeout(r, 2000))
        }
      }

      if (lastFetched) {
        onComplete?.(lastFetched)
      } else {
        onError?.(new Error('Analysis execution timed out. Please check again in a few moments.'))
      }
    } catch (err) {
      console.error('Failed to fetch final analysis data:', err)
      const detail = err.response?.data?.error?.message || err.response?.data?.detail || err.message || 'Failed to fetch analysis'
      onError?.(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)))
    } finally {
      cleanup()
    }
  }, [cleanup])

  const startFallbackPolling = useCallback((analysisId, onTraceUpdate, onComplete, onError) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)

    pollTimerRef.current = setInterval(async () => {
      try {
        const snap = await analysisService.get(analysisId)
        if (snap && ['completed', 'abstained', 'failed'].includes(snap.status)) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
          if (!finalizedRef.current) {
            await fetchFinalAnalysis(analysisId, onTraceUpdate, onComplete, onError)
          }
        }
      } catch {
        // ignore background polling errors
      }
    }, 2000)
  }, [fetchFinalAnalysis])

  const startAnalysis = useCallback(async (params, { onEvent, onComplete, onError }) => {
    const { kbId, query, enableWebSearch, webSearchProvider, llmProvider, llmModel } = params

    finalizedRef.current = false
    traceEventsRef.current = []

    try {
      const analysisCreated = await analysisService.create({
        knowledge_base_id: kbId,
        query: query.trim(),
        enable_web_search: enableWebSearch,
        web_search_provider: webSearchProvider,
        llm_provider: llmProvider,
        llm_model: llmModel,
      })

      streamRef.current = await openAnalysisStream(analysisCreated.id, {
        onEvent: (eventData) => {
          traceEventsRef.current = [...traceEventsRef.current, eventData]
          onEvent?.(eventData)

          if (TERMINAL_EVENTS.has(eventData.event)) {
            if (!finalizedRef.current) {
              fetchFinalAnalysis(analysisCreated.id, onEvent, onComplete, onError)
            }
          }
        },
        onError: () => {
          if (!finalizedRef.current) {
            fetchFinalAnalysis(analysisCreated.id, onEvent, onComplete, onError)
          }
        },
        onComplete: () => {
          if (!finalizedRef.current) {
            fetchFinalAnalysis(analysisCreated.id, onEvent, onComplete, onError)
          }
        },
      })

      startFallbackPolling(analysisCreated.id, onEvent, onComplete, onError)

      return analysisCreated
    } catch (err) {
      console.error('Failed to start analysis:', err)
      const detail = err.response?.data?.error?.message || err.response?.data?.detail || err.message || 'Failed to start analysis'
      onError?.(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)))
      throw err
    }
  }, [fetchFinalAnalysis, startFallbackPolling])

  return {
    startAnalysis,
    cleanup,
    getTraceEvents: () => traceEventsRef.current,
  }
}