/**
 * TRUSTRAG — Playwright E2E configuration.
 *
 * The E2E suite is a smoke test covering the critical user path:
 *   landing → auth (redirect guard) → register/login → dashboard.
 *
 * It expects the FastAPI backend to be reachable at the configured API URL
 * (default http://localhost:8080/api/v1) — run it with:
 *
 *   cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port 8080
 *   cd apps/web && npm run test:e2e
 *
 * The web server (Vite preview on :5173) is started automatically by Playwright
 * with the API URL baked in. No test requires LLM/embedding infrastructure.
 */

import { defineConfig } from '@playwright/test'

const PORT = 5173
// Backend origin (scheme://host[:port]) — the frontend appends /api/v1/… paths
// itself. NOT the full /api/v1 base (that would double the prefix).
const API_ORIGIN = process.env.E2E_API_URL || 'http://localhost:8080'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never' }]]
    : 'list',

  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  webServer: {
    command: `VITE_API_URL=${API_ORIGIN} npm run build && npm run preview -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})