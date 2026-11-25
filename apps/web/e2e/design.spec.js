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

function uniqueUser() {
  const stamp = `${Date.now()}${Math.random().toString(36).slice(2, 8)}`
  return {
    email: `design-${stamp}@example.com`,
    password: 'TrustRagE2E!2026',
    full_name: 'Design Guard',
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

test.describe('design system', () => {
  test('public surfaces have at most one focal action above the fold', async ({ page }) => {
    for (const route of ['/', '/login', '/register', '/does-not-exist']) {
      await page.goto(route)
      const count = await primaryControlsInViewport(page)
      expect(count, `${route} has ${count} focal controls above the fold`).toBeLessThanOrEqual(1)
      await expect(page.locator('.lx-btn--attention')).toHaveCount(0)
    }
  })

  test('authenticated surfaces have at most one focal action per view', async ({ page, request }) => {
    const user = uniqueUser()
    const registration = await request.post(`${API}/auth/register`, { data: user })
    expect(registration.status()).toBe(201)

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
