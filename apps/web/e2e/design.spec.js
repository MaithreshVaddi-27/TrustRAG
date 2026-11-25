import { test, expect } from '@playwright/test'

/**
 * Design-system guard: one focal action per view.
 *
 * Silver is the action colour and a view with two focal plates has no focus.
 * This walks the routes after a real sign-in and counts only the primary
 * controls inside the current viewport, so a long landing page can keep one
 * CTA per section without failing.
 *
 * Needs the API (register + login) but no LLM, embedding or vector store.
 */

const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8000'
const API = `${API_ORIGIN}/api/v1`

const APP_ROUTES = [
  '/dashboard',
  '/playground',
  '/knowledge-bases',
  '/evidence',
  '/claims',
  '/conflicts',
  '/settings',
]

function account() {
  // The register route is deliberately capped at 3/hour per IP. On a
  // long-lived local API, repeated runs exhaust it; point these two env vars
  // at an existing synthetic account to skip registration entirely. CI
  // starts a fresh API, so the default path stays a strict 201 assertion.
  const email = process.env.E2E_TEST_EMAIL
  const password = process.env.E2E_TEST_PASSWORD
  if (email && password) return { email, password, existing: true }
  const stamp = `${Date.now()}${Math.random().toString(36).slice(2, 8)}`
  return {
    email: `design-${stamp}@example.com`,
    password: 'TrustRagE2E!2026',
    existing: false,
  }
}

async function primaryControlsInViewport(page) {
  return page.locator('.lx-btn--primary').evaluateAll((elements) =>
    elements.filter((el) => {
      const rect = el.getBoundingClientRect()
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        rect.top < window.innerHeight &&
        rect.bottom > 0
      )
    }).length,
  )
}

/**
 * Crimson is a signal, never an action fill. Detect it by the computed colour
 * rather than by a class name: a class-based assertion went vacuous the moment
 * the deprecated `--attention` button was deleted, and would pass forever.
 */
async function crimsonFilledVisibleButtons(page) {
  return page.locator('.lx-btn').evaluateAll((elements) =>
    elements
      .filter((el) => {
        const rect = el.getBoundingClientRect()
        if (rect.width === 0 || rect.height === 0) return false
        const bg = getComputedStyle(el).backgroundColor
        const m = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/)
        if (!m) return false
        const [r, g, b] = [Number(m[1]), Number(m[2]), Number(m[3])]
        const alpha = m[4] === undefined ? 1 : Number(m[4])
        return alpha > 0.5 && r > 120 && r > g * 1.8 && r > b * 1.8
      })
      .map((el) => el.textContent.trim()),
  )
}

test.describe('design system', () => {
  test('public surfaces have at most one focal action above the fold', async ({ page }) => {
    for (const route of ['/', '/login', '/register', '/does-not-exist']) {
      await page.goto(route)
      const count = await primaryControlsInViewport(page)
      expect(count, `${route} has ${count} focal controls above the fold`).toBeLessThanOrEqual(1)
      const crimson = await crimsonFilledVisibleButtons(page)
      expect(crimson, `${route} has crimson-filled actions: ${crimson.join(', ')}`).toEqual([])
    }
  })

  test('authenticated surfaces have at most one focal action per view', async ({ page, request }) => {
    const user = account()
    if (!user.existing) {
      const registration = await request.post(`${API}/auth/register`, {
        data: { email: user.email, password: user.password, full_name: 'Design Guard' },
      })
      expect(registration.status()).toBe(201)
    }

    await page.goto('/login')
    await page.fill('#login-email', user.email)
    await page.fill('#login-password', user.password)
    await page.getByRole('button', { name: /^Sign in$/ }).click()
    await expect(page).toHaveURL(/\/dashboard/)

    for (const route of APP_ROUTES) {
      await page.goto(route)
      await expect(page.locator('main')).toHaveCount(1)
      const count = await primaryControlsInViewport(page)
      expect(count, `${route} has ${count} focal controls above the fold`).toBeLessThanOrEqual(1)
    }
  })
})
