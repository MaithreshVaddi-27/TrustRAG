/**
 * TRUSTRAG — Backend health-check hook.
 *
 * Polls GET /api/v1/health at a configurable interval (default 20 s).
 * Returns { isOnline, isChecking, lastChecked } plus a manual
 * `recheck()` function so callers can force an immediate probe
 * (e.g. after retrying a failed request).
 *
 * On mount it does NOT immediately ping — the first health check is
 * deferred to the next interval tick.  This avoids a cascade of
 * requests when the user has many tabs open.
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
    try {
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)
      await api.get('/api/v1/health', { signal: controller.signal })
      clearTimeout(timeoutId)
      setIsOnline(true)
    } catch (err) {
      if (err.name !== 'CanceledError' && err.code !== 'ERR_CANCELED') {
        setIsOnline(false)
      }
    } finally {
      setIsChecking(false)
      setLastChecked(Date.now())
    }
  }, [])

  // Start polling after the first render — skip the initial tick
  useEffect(() => {
    timerRef.current = setInterval(probe, intervalMs)
    return () => {
      clearInterval(timerRef.current)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [probe, intervalMs])

  const recheck = useCallback(() => probe(), [probe])

  return { isOnline, isChecking, lastChecked, recheck }
}
