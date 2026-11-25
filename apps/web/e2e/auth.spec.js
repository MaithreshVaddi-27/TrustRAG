/**
 * TRUSTRAG — E2E smoke tests.
 *
 * Verifies the critical user path against a live backend:
 *   1. Unauthenticated users are bounced to /login (route guard).
 *   2. Registration via API (password rules, public endpoint).
 *   3. Login through the real UI → authenticated session → dashboard.
 *   4. Server-side token revocation: after POST /auth/logout the JWT can no
 *      longer authenticate (SEC-H1).
 *
 * These tests need the API only for auth + health — no LLM, embedding, or
 * Qdrant collection is required.
 */

import { test, expect } from '@playwright/test'

const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000'
const API = `${API_ORIGIN}/api/v1`

function testUser() {
  // /auth/register is deliberately capped at 3/hour per IP. Re-running the
  // suite against a long-lived local API exhausts it; set these two vars to
  // reuse an existing synthetic account and skip only the registration step.
  // CI starts a fresh API, so the default path keeps the strict 201 assertion.
  const email = process.env.E2E_TEST_EMAIL
  const password = process.env.E2E_TEST_PASSWORD
  if (email && password) {
    return { email, password, full_name: 'E2E Tester', existing: true }
  }
  const ts = `${Date.now()}${Math.random().toString(36).slice(2, 8)}`
  return {
    email: `e2e-${ts}@example.com`,
    password: 'TrustRagE2E!2026',
    full_name: 'E2E Tester',
    existing: false,
  }
}

test.describe('auth smoke', () => {
  test('unauthenticated /dashboard redirects to /login', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible()
  })

  test('register → UI login → dashboard → logout revokes token (SEC-H1)', async ({
    page,
    request,
  }) => {
    const user = testUser()

    // 1. Health endpoint is live so failures here are E2E failures, not flakes.
    const health = await request.get(`${API}/health`)
    expect(health.ok()).toBeTruthy()

    // 2. Register via the public API (returns 201, no auto-login). Skipped only
    //    when an existing account is supplied for repeated local runs.
    if (!user.existing) {
      const reg = await request.post(`${API}/auth/register`, {
        data: {
          email: user.email,
          password: user.password,
          full_name: user.full_name,
        },
      })
      expect(reg.status()).toBe(201)
    }

    // 3. Login through the real UI.
    await page.goto('/login')
    await page.fill('#login-email', user.email)
    await page.fill('#login-password', user.password)
    await page.getByRole('button', { name: /^Sign in$/ }).click()

    // 4. Session established → redirected to the dashboard.
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })
    // The dashboard's own heading. It used to be "AI Reliability"; the page
    // was redesigned to "Overview", and this assertion was never updated —
    // so the spec was failing on a dashboard that had rendered correctly.
    await expect(
      page.getByRole('heading', { name: /^Overview$/ }),
    ).toBeVisible()

    // 5. Fetch the JWT from the session and prove logout revokes it.
    const token = await page.evaluate(() => localStorage.getItem('trustrag_token'))
    expect(token).toBeTruthy()

    const logout = await request.post(`${API}/auth/logout`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(logout.status()).toBe(204)

    const meAfterLogout = await request.get(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(meAfterLogout.status()).toBe(401)

    // 6. The cached session is gone client-side too.
    await page.reload()
    await expect(page).toHaveURL(/\/login/)
  })
})