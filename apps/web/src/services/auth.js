/**
 * Auth service — API calls for auth endpoints.
 * Phase 4 will wire these to the real FastAPI /api/v1/auth/* routes.
 */

import api from '@/lib/api'
import { authStore } from '@/store/authStore'

export const authService = {
  async login(email, password) {
    const { data } = await api.post('/api/v1/auth/login', { email, password })
    authStore.setSession(data.access_token, data.user)
    return data
  },

  async register(email, password, fullName) {
    const { data } = await api.post('/api/v1/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    return data
  },

  async me() {
    const { data } = await api.get('/api/v1/auth/me')
    return data
  },

  async logout() {
    // P0-SEC FIX (2026-09-06 audit): previously only cleared local state,
    // leaving the JWT valid server-side until expiry (SEC-H1 bypass).
    // Now revokes via POST /auth/logout so the denylist blocks reuse.
    try {
      await api.post('/api/v1/auth/logout')
    } catch {
      // ignore — still clear local session even if revoke fails/offline
    } finally {
      authStore.clearSession()
    }
  },
}
