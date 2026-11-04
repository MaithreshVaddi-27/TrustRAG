/**
 * TRUSTRAG — Knowledge Base and Analysis services.
 * All API calls go through the centralized Axios client.
 * Uses standardized response handling with retry logic.
 */

import api from '@/lib/api'
import { withRetryAndResponse, ERROR_CODES } from '@/lib/apiResponse'

// ─── Helper: unwrap standardized response or throw ────────────────────────────
function unwrap(response) {
  if (response.error) {
    const err = new Error(response.error.message)
    err.code = response.error.code
    err.status = response.error.status
    err.details = response.error.details
    err.requestId = response.error.requestId
    throw err
  }
  return response.data
}

// ─── Knowledge Bases ──────────────────────────────────────────────────────────
const kbServiceBase = {
  list: () => api.get('/api/v1/knowledge-bases'),
  create: (body) => api.post('/api/v1/knowledge-bases', body),
  delete: (id) => api.delete(`/api/v1/knowledge-bases/${id}`),

  uploadDocument: (kbId, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/api/v1/knowledge-bases/${kbId}/documents`, form)
  },

  listDocuments: (kbId) =>
    api.get(`/api/v1/knowledge-bases/${kbId}/documents`),

  deleteDocument: (docId) =>
    api.delete(`/api/v1/documents/${docId}`),
}

// Wrap with retry for read operations, no retry for mutations
export const kbService = {
  list: () => withRetryAndResponse(kbServiceBase.list).then(unwrap),
  create: (body) => withRetryAndResponse(() => kbServiceBase.create(body)).then(unwrap),
  delete: (id) => withRetryAndResponse(() => kbServiceBase.delete(id)).then(unwrap),

  uploadDocument: (kbId, file) => withRetryAndResponse(() => kbServiceBase.uploadDocument(kbId, file)).then(unwrap),

  listDocuments: (kbId) => withRetryAndResponse(() => kbServiceBase.listDocuments(kbId)).then(unwrap),
  deleteDocument: (docId) => withRetryAndResponse(() => kbServiceBase.deleteDocument(docId)).then(unwrap),
}

// ─── Analyses ──────────────────────────────────────────────────────────────────
const analysisServiceBase = {
  create: (body) => api.post('/api/v1/analyses', body),
  get: (id) => api.get(`/api/v1/analyses/${id}`),
  list: () => api.get('/api/v1/analyses'),
  claims: (id) => api.get(`/api/v1/analyses/${id}/claims`),
  evidence: (id) => api.get(`/api/v1/analyses/${id}/evidence`),
  trace: (id) => api.get(`/api/v1/analyses/${id}/trace`),
  detail: (id) => api.get(`/api/v1/analyses/${id}/detail`),
}

// Analysis creation: retry on network/server errors, not on validation
// Analysis reads: retry with exponential backoff
export const analysisService = {
  create: (body) => withRetryAndResponse(() => analysisServiceBase.create(body), {
    maxAttempts: 2, // Only one retry for creation
    retryConfig: {
      retryableCodes: new Set([ERROR_CODES.NETWORK_ERROR, ERROR_CODES.TIMEOUT, ERROR_CODES.SERVER_ERROR, ERROR_CODES.SERVICE_UNAVAILABLE]),
    },
  }).then(unwrap),

  get: (id) => withRetryAndResponse(() => analysisServiceBase.get(id)).then(unwrap),
  list: () => withRetryAndResponse(analysisServiceBase.list).then(unwrap),
  claims: (id) => withRetryAndResponse(() => analysisServiceBase.claims(id)).then(unwrap),
  evidence: (id) => withRetryAndResponse(() => analysisServiceBase.evidence(id)).then(unwrap),
  trace: (id) => withRetryAndResponse(() => analysisServiceBase.trace(id)).then(unwrap),
  detail: (id) => withRetryAndResponse(() => analysisServiceBase.detail(id)).then(unwrap),
}

// ─── Evidence ──────────────────────────────────────────────────────────────────
export const evidenceService = {
  list: () => withRetryAndResponse(() => api.get('/api/v1/evidence')).then(unwrap),
}

// ─── Claims ────────────────────────────────────────────────────────────────────
export const claimService = {
  list: () => withRetryAndResponse(() => api.get('/api/v1/claims')).then(unwrap),
}

// ─── Conflicts ─────────────────────────────────────────────────────────────────
export const conflictService = {
  list: () => withRetryAndResponse(() => api.get('/api/v1/conflicts')).then(unwrap),
}

// ─── Health & Diagnostics ──────────────────────────────────────────────────────
export const healthService = {
  get: () => withRetryAndResponse(() => api.get('/api/v1/health/detailed')).then(unwrap),
}

// ─── Models & AI Providers ──────────────────────────────────────────────────────
export const modelService = {
  getProviders: () => withRetryAndResponse(() => api.get('/api/v1/models/providers')).then(unwrap),
  trimMemory: () => withRetryAndResponse(() => api.post('/api/v1/models/memory/trim')).then(unwrap),
}

// ─── Export error codes for consumers ──────────────────────────────────────────
export { ERROR_CODES } from '@/lib/apiResponse'