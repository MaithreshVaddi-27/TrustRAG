/**
 * Auth store — minimal global state for the current user session.
 * Uses localStorage to persist the token across page refreshes.
 * No external state library needed for MVP.
 */

import { useState, useCallback, useEffect } from 'react'

const TOKEN_KEY = 'trustrag_token'
const USER_KEY  = 'trustrag_user'

/**
 * Decode a JWT payload without verifying its signature.
 * This is safe for client-side expiry checks — the server still validates
 * the signature on every API request.
 */
function decodeJwtPayload(token) {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return null
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return null
  }
}

/**
 * Return true if the token is absent or its `exp` claim has already passed.
 * Adds a 10-second buffer to account for clock skew.
 */
function isTokenExpired(token) {
  if (!token) return true
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return false  // No exp claim — treat as non-expiring
  return Date.now() / 1000 > payload.exp - 10  // 10s skew buffer
}

/** Hydrate user from localStorage on startup. */
function loadUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

// Module-level state + subscribers (lightweight pub/sub without React context re-renders)
let _user  = loadUser()
let _token = localStorage.getItem(TOKEN_KEY)

// Auto-clear expired token on module initialization
if (isTokenExpired(_token)) {
  _token = null
  _user  = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

const _subscribers = new Set()

function notify() {
  _subscribers.forEach((fn) => fn())
}

export const authStore = {
  getState: () => {
    // Lazily evict expired tokens so any part of the app calling getState()
    // always sees a consistent, non-expired auth state.
    if (isTokenExpired(_token)) {
      _token = null
      _user  = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    }
    return { user: _user, token: _token, isAuthenticated: !!_token }
  },

  setSession(token, user) {
    _token = token
    _user  = user
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    notify()
  },

  clearSession() {
    _token = null
    _user  = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    notify()
  },

  subscribe(fn) {
    _subscribers.add(fn)
    return () => _subscribers.delete(fn)
  },
}

/**
 * React hook — subscribes to auth state changes.
 * Uses useEffect (not useState) for subscription lifecycle — fixes blank white page.
 */
export function useAuthStore() {
  const [state, setState] = useState(() => authStore.getState())

  const sync = useCallback(() => {
    setState(authStore.getState())
  }, [])

  useEffect(() => {
    // Subscribe on mount, unsubscribe on unmount
    const unsub = authStore.subscribe(sync)
    // Sync immediately in case state changed between render and effect
    sync()
    return unsub
  }, [sync])

  return state
}
