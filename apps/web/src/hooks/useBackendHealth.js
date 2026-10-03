/**
 * TRUSTRAG — Backend health-check hook.
 *
 * Polls GET /api/v1/health at a configurable interval (default 20 s).
 * Returns { isOnline, isChecking, lastChecked } plus a manual
 * `recheck()` function so callers can force an immediate probe
 * (e.g. after retrying a failed request).
 *
 * On mount it probes immediately, then polls at the interval — an offline
 * backend surfaces on first paint instead of after one full interval.
 *
 * All requests are short-circuit aborted after 5 s so a slow backend
 * never blocks the UI.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import api from '@/lib/api'

const POLL_MS = 20_000
const TIMEOUT_MS = 5_000

export default function useBackendHealth(intervalMs = POLL_MS) {
  const [isOnline, setIsOnline] = useState(null) // null = unknown
  const [isChecking, setIsChecking] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)
  const timerRef = useRef(null)
  const abortRef = useRef(null)

  const probe = useCallback(async () => {
    // Cancel any in-flight probe
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setIsChecking(true)
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)
    try {
      await api.get('/api/v1/health', { signal: controller.signal })
      setIsOnline(true)
    } catch (err) {
      if (err.name !== 'CanceledError' && err.code !== 'ERR_CANCELED') {
        setIsOnline(false)
      }
    } finally {
      clearTimeout(timeoutId)
      setIsChecking(false)
      setLastChecked(Date.now())
    }
  }, [])

  // Probe immediately on mount (so an offline backend surfaces at once),
  // then keep polling at the configured interval.
  useEffect(() => {
    probe()
    timerRef.current = setInterval(probe, intervalMs)
    return () => {
      clearInterval(timerRef.current)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [probe, intervalMs])

  const recheck = useCallback(() => probe(), [probe])

  return { isOnline, isChecking, lastChecked, recheck }
}
