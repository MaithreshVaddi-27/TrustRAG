/**
 * TRUSTRAG — Centralized Axios client + SSE trace stream helper.
 *
 * All service modules (services/api.js, services/auth.js) and pages
 * that open a live trace stream (PlaygroundPage) import from here.
 */

import axios from 'axios'
import { authStore } from '@/store/authStore'

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  ''
).replace(/\/$/, '')

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach the JWT (if present) to every outgoing request.
// Strip Content-Type for FormData so Axios/browser computes multipart boundary.
api.interceptors.request.use((config) => {
  const { token } = authStore.getState()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    delete config.headers['Content-Type']
    delete config.headers['content-type']
  }
  return config
})

// On 401, the session is no longer valid — clear it so the UI redirects to login.
// Also normalize the error message: axios's default err.message is a generic
// "Request failed with status code NNN", not the backend's actual message. Pages
// like LoginPage/RegisterPage display err.message directly, so without this they
// always show a generic string instead of e.g. "Invalid email or password".
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      authStore.clearSession()
    }
    const resData = error.response?.data
    let rawMsg = resData?.error?.message || resData?.detail || error.message
    if (Array.isArray(rawMsg)) {
      rawMsg = rawMsg
        .map((m) => {
          if (typeof m === 'object' && m !== null) {
            const field = Array.isArray(m.loc) ? m.loc.filter((l) => l !== 'body' && l !== 'query' && l !== 'path').join('.') : ''
            return field ? `${field}: ${m.msg || 'Field required'}` : m.msg || 'Validation error'
          }
          return String(m)
        })
        .join('; ')
    } else if (typeof rawMsg === 'object' && rawMsg !== null) {
      rawMsg = rawMsg.msg || rawMsg.message || JSON.stringify(rawMsg)
    }
    if (rawMsg) {
      error.message = String(rawMsg)
    }
    return Promise.reject(error)
  }
)

export default api

/**
 * Open a Server-Sent Events stream for live analysis trace updates.
 *
 * Uses a short-lived, single-use stream ticket (POST /stream-ticket) — the JWT
 * is NEVER placed in the URL, where it would leak into server logs, proxy logs,
 * and browser history. If ticket issuance fails, onError is invoked so callers
 * can fall back to polling (no stream is opened).
 *
 * Backend route: GET /api/v1/analyses/{analysisId}/stream?ticket=<ticket>
 *
 * @param {string} analysisId
 * @param {{ onEvent?: (data: any) => void, onError?: (err: Event|Error) => void, onComplete?: () => void }} handlers
 * @returns {Promise<EventSource|null>}
 */
export async function openAnalysisStream(analysisId, { onEvent, onError, onComplete } = {}) {
  const TERMINAL_EVENTS = new Set(['analysis.completed', 'analysis.abstained', 'analysis.failed'])

  // Mint a short-lived ticket — keeps the JWT out of the URL entirely.
  let streamUrl
  try {
    const ticketRes = await api.post(`/api/v1/analyses/${analysisId}/stream-ticket`)
    const ticket = ticketRes.data?.ticket
    if (!ticket) throw new Error('Stream ticket endpoint returned no ticket')
    streamUrl = `${API_BASE_URL}/api/v1/analyses/${analysisId}/stream?ticket=${encodeURIComponent(ticket)}`
  } catch (err) {
    onError?.(err)
    return null
  }

  const source = new EventSource(streamUrl)

  source.onmessage = (evt) => {
    let payload
    try {
      payload = JSON.parse(evt.data)
    } catch {
      return
    }

    // Ignore server keep-alive ping heartbeats
    if (payload.event === 'ping') {
      return
    }

    onEvent?.(payload)

    if (TERMINAL_EVENTS.has(payload.event)) {
      try {
        source.close()
      } catch {
        // ignore
      }
      onComplete?.()
    }
  }

  source.onerror = (err) => {
    try {
      source.close()
    } catch {
      // ignore
    }
    onError?.(err)
  }

  return source
}
