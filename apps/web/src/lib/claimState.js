/**
 * Shared claim-state + evidence-source predicates (single implementation).
 * Previously duplicated across ClaimsPage, ClaimInspector, DashboardPage
 * (claim states) and EvidenceViewer x3 (web-source check) — drifting
 * independently. Import from here.
 */

export function normalizeClaimState(c) {
  return String(c?.state ?? c?.status ?? c?.verification_status ?? 'NEUTRAL').toUpperCase()
}

export function isWebSource(c) {
  if (!c) return false
  return Boolean(
    c.url ||
    c.method?.includes('web') ||
    c.method?.includes('mcp') ||
    c.chunk_id?.startsWith('web_')
  )
}

/**
 * Normalize a reliability score to 0–1. Backend may send 0–100; a raw 74
 * must not render as 7400%.
 */
export function normalizeScore(score) {
  if (score == null) return null
  const n = Number(score)
  if (!Number.isFinite(n)) return null
  return n > 1 ? n / 100 : n
}
