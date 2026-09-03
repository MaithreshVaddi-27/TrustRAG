/**
 * TRUSTRAG — Knowledge Base and Analysis services.
 * All API calls go through the centralized Axios client.
 */

import api from '@/lib/api'

// ── Knowledge Bases ───────────────────────────────────────────────────────
export const kbService = {
  list: ()       => api.get('/api/v1/knowledge-bases').then(r => r.data),
  get:  (id)     => api.get(`/api/v1/knowledge-bases/${id}`).then(r => r.data),
  create: (body) => api.post('/api/v1/knowledge-bases', body).then(r => r.data),
  delete: (id)   => api.delete(`/api/v1/knowledge-bases/${id}`).then(r => r.data),

  uploadDocument: (kbId, file) => {
    const form = new FormData()
    form.append('file', file)
    // Content-Type is automatically removed for FormData by the Axios request
    // interceptor in lib/api.js — no need to override it here.
    return api.post(`/api/v1/knowledge-bases/${kbId}/documents`, form).then(r => r.data)
  },

  listDocuments: (kbId) =>
    api.get(`/api/v1/knowledge-bases/${kbId}/documents`).then(r => r.data),

  deleteDocument: (docId) =>
    api.delete(`/api/v1/documents/${docId}`).then(r => r.data),
}

// ── Analyses ──────────────────────────────────────────────────────────────
export const analysisService = {
  create: (body) => api.post('/api/v1/analyses', body).then(r => r.data),
  get:    (id)   => api.get(`/api/v1/analyses/${id}`).then(r => r.data),
  list:   ()     => api.get('/api/v1/analyses').then(r => r.data),
  claims:   (id) => api.get(`/api/v1/analyses/${id}/claims`).then(r => r.data),
  evidence: (id) => api.get(`/api/v1/analyses/${id}/evidence`).then(r => r.data),
  trace:    (id) => api.get(`/api/v1/analyses/${id}/trace`).then(r => r.data),
}

// ── Experiments ───────────────────────────────────────────────────────────
export const experimentService = {
  list:   ()     => api.get('/api/v1/experiments').then(r => r.data),
  get:    (id)   => api.get(`/api/v1/experiments/${id}`).then(r => r.data),
  create: (body) => api.post('/api/v1/experiments', body).then(r => r.data),
}

// ── Evidence ──────────────────────────────────────────────────────────────
export const evidenceService = {
  list: () => api.get('/api/v1/evidence').then(r => r.data),
}

// ── Claims ────────────────────────────────────────────────────────────────
export const claimService = {
  list: () => api.get('/api/v1/claims').then(r => r.data),
}

// ── Conflicts ─────────────────────────────────────────────────────────────
export const conflictService = {
  list: () => api.get('/api/v1/conflicts').then(r => r.data),
}

// ── Health & Diagnostics ──────────────────────────────────────────────────
export const healthService = {
  get: () => api.get('/api/v1/health').then(r => r.data),
}

// ── Models & AI Providers ──────────────────────────────────────────────────
export const modelService = {
  getProviders: () => api.get('/api/v1/models/providers').then(r => r.data),
  getHardware:  () => api.get('/api/v1/models/hardware').then(r => r.data),
  trimMemory:   () => api.post('/api/v1/models/memory/trim').then(r => r.data),
}
