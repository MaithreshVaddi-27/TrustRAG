/**
 * TRUSTRAG — k6 API load smoke test (TEST-M2 / Phase 3 "Load testing in CI").
 *
 * Exercises the cheap, LLM-free hot paths so the gate stays deterministic in CI:
 *   - GET /api/v1/health            (public, liveness)
 *   - GET /api/v1/knowledge-bases   (authenticated, MongoDB read path)
 *
 * Auth is minted once in setup() and shared across VUs to stay well under the
 * per-IP auth rate ceiling; /knowledge-bases is intentionally NOT rate-limited.
 *
 * Run locally against a live backend:
 *   k6 run load-test/smoke.js
 *   API_BASE_URL=http://localhost:8080 k6 run load-test/smoke.js
 */

import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  scenarios: {
    // Short ramp suited to a CI gate: 5 → 10 → 0 VUs over ~35s.
    load: {
      executor: 'ramping-vus',
      stages: [
        { duration: '10s', target: 5 },
        { duration: '15s', target: 10 },
        { duration: '10s', target: 0 },
      ],
      gracefulRampDown: '5s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300', 'p(99)<500'],
    checks: ['rate>0.98'],
  },
}

const API_BASE = (__ENV.API_BASE_URL || 'http://localhost:8080').replace(/\/$/, '')

export function setup() {
  const email = `k6-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`
  const register = http.post(
    `${API_BASE}/api/v1/auth/register`,
    JSON.stringify({ email, password: 'K6LoadTest123!', full_name: 'k6 Load Test' }),
    { headers: { 'Content-Type': 'application/json' } }
  )

  const login = http.post(
    `${API_BASE}/api/v1/auth/login`,
    JSON.stringify({ email, password: 'K6LoadTest123!' }),
    { headers: { 'Content-Type': 'application/json' } }
  )
  const token = JSON.parse(login.body)?.access_token
  if (!token) {
    // Fail fast: a load gate that silently runs zero requests is useless.
    throw new Error(
      `setup() could not authenticate — register=${register.status} login=${login.status}`
    )
  }
  return { token }
}

export default function (data) {
  const token = data?.token || ''
  const headers = { Authorization: `Bearer ${token}` }

  const health = http.get(`${API_BASE}/api/v1/health`)
  check(health, {
    'health returns 200': (r) => r.status === 200,
    'health reports healthy': (r) => {
      const body = JSON.parse(r.body || '{}')
      return body.status === 'ok' && body.services?.mongodb === 'ok' && body.services?.qdrant === 'ok'
    },
  })

  const kbs = http.get(`${API_BASE}/api/v1/knowledge-bases`, { headers })
  check(kbs, {
    'knowledge-bases returns 200': (r) => r.status === 200,
    'knowledge-bases is a list': (r) => Array.isArray(JSON.parse(r.body).items ?? JSON.parse(r.body)),
  })

  sleep(0.1)
}