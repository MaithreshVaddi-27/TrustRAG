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

  logout() {
    authStore.clearSession()
  },
}
