# Frontend Audit — TrustRAG ui-redesign (`apps/web`)

**Scope reviewed:** `package.json`, `vite.config.js`, `src/main.jsx`, `src/App.jsx`, `src/lib/api.js`, `src/services/api.js`, `src/services/auth.js`, `src/store/authStore.js`, both layouts, all 12 pages, all 7 workbench components, `dist/` output, env files.

---

## ✅ UI Polish Fixes (Completed — commits `91746b1`, `bbcfe53`)

The following audit findings have been addressed in the `ui-redesign` branch:

| Finding | Status | Commit | Detail |
|---------|--------|--------|--------|
| **react-markdown v10 `inline` prop** (Critical) | ✅ Fixed | `e4eb783` | Removed deprecated `inline` prop; inline code renders correctly |
| **Fabricated benchmark metrics POSTed** (Critical) | ⚠️ Pending Phase 1.6 | — | Requires backend change to accept config_name only |
| **SSE/polling race** (Critical) | ⚠️ Pending Phase 2.9 | — | Requires `finalizedRef` guard |
| **Stale closure trace fallback** (High) | ⚠️ Pending Phase 2.9 | — | Requires `traceEventsRef` |
| **Delete mutations no `onError`** (High) | ⚠️ Pending Phase 1.7 | — | Requires `onError` callbacks |
| **Settings logout hard reload** (Low) | ✅ Fixed | `e4eb783` | Now uses `navigate('/login')` consistently |
| **NotFoundPage 404** (Low) | ✅ Fixed | `e4eb783` | Proper 404 page with navigation |
| **Brand casing inconsistency** | ✅ Fixed | `91746b1` | Normalized to "TrustRAG" everywhere |
| **"Get Started" CTA routing** | ✅ Fixed | `91746b1` | Now routes to `/register` instead of `/login` |
| **Internal detail leakage** | ✅ Fixed | `91746b1` | "Qdrant Cloud", "tenant collection" replaced with user-friendly copy |
| **Invalid Tailwind classes** (9 sites) | ⚠️ Pending Phase 1.7 | — | `w-18`, `py-0.2` still need replacement |
| **Hardcoded tenant ID** | ✅ Fixed | `91746b1` | Shows "Not available" instead of MongoDB ObjectId |
| **Missing aria-label on modal close** | ✅ Fixed | `91746b1` | Experiments modal close button now has `aria-label` |
| **Font sizes below legible minimum** | ✅ Fixed | `91746b1` | `text-[9px]` → `text-[10px]` across 11 files |
| **Missing press feedback** | ✅ Fixed | `91746b1` | Global `:active` on all buttons/links/interactive elements |
| **Inconsistent spring damping** | ✅ Fixed | `bbcfe53` | Standardized to damping: 15, stiffness: 150 (Apple HIG) |
| **Missing useReducedMotion** | ✅ Fixed | `bbcfe53` | Added to EvidenceViewer, PlaygroundPage (AppLayout already had it) |
| **No staggered entrance animations** | ✅ Fixed | `bbcfe53` | CSS `--stagger-delay` + `.stagger-children` utility |
| **Inconsistent page padding** | ✅ Fixed | `bbcfe53` | Standardized to `p-4 sm:p-6 lg:p-8` across all pages |
| **Inconsistent card padding** | ✅ Fixed | `bbcfe53` | p-3.5 (list items), p-5 (content cards) |
| **Duplicate keyframes cascade** | ✅ Fixed | `91746b1` | Removed duplicate `fadeIn`/`slideUp` from landing.css |
| **glass-card-hover wrong border color** | ✅ Fixed | `91746b1` | Emerald → primary/cyan |
| **btn-danger rounded inconsistency** | ✅ Fixed | `91746b1` | rounded-lg → rounded-xl |
| **Vendor chunk optimization** | ✅ Fixed | `320386c` | motion/react extracted to 127 kB vendor chunk |

## Critical

**[Critical] SSE stream and fallback polling race — both can finalize the same analysis concurrently** (Confirmed)
- Location: `src/pages/PlaygroundPage.jsx:184-229` (handleSubmit), `:167-182` (startFallbackPolling), `:239-317` (fetchFinalAnalysis)
- Evidence: `handleSubmit` opens the SSE stream AND starts `startFallbackPolling()`; the SSE terminal events (`onComplete`/`onError`) and the 2s `setInterval` poll both invoke `fetchFinalAnalysis` with no shared "finished" flag; the interval's catch is silent (`} catch (err) { /* keep polling */ }`).
- Impact: Duplicate `GET /analyses/{id}` calls, last-writer-wins state overwrites (a slower stale response can clobber a fresher one), double toasts, "finalizing" spinners that never resolve.
- Recommendation: A single `finalizedRef = useRef(false)` guard set inside `fetchFinalAnalysis`; clear the polling interval in SSE `onComplete`/`onError`.

**[Critical] Fabricated benchmark metrics are POSTed to the backend as real experiment records** (Confirmed)
- Location: `src/pages/ExperimentsPage.jsx:8-14` (EXPERIMENT_CONFIGS), `:41-49` (handleCreateExperiment), `:51-63` (chartData)
- Evidence: `metrics: { evidence_coverage: 0.95, claim_support: 0.98, citation_correctness: 0.99 }` hardcoded; `createMutation.mutate({..., metrics: configObj.metrics})` persists them; `chartData` falls back to `EXPERIMENT_CONFIGS.map(...)` when the DB is empty, rendering fake numbers as benchmark results.
- Impact: Users can persist invented metrics into the experiment store of a *reliability/verification* product with one click; the empty-state chart misrepresents fake data as measured results. A credibility/data-integrity defect, not cosmetic.
- Recommendation: Delete the metrics POST (send `config_name` only, let the backend evaluate); render an empty state instead of the hardcoded fallback chart.

## High

**[High] Stale closure: trace fallback is always the submit-time empty array** (Confirmed)
- Location: `src/pages/PlaygroundPage.jsx:279`
- Evidence: `trace: (trace && trace.length > 0) ? trace : traceEvents` inside `fetchFinalAnalysis` — `traceEvents` is captured from the render closure at fetch time (typically `[]`).
- Impact: Execution Trace panel shows empty even though events were streamed and displayed live; the recorded dossier/trace silently loses data.
- Recommendation: `traceEventsRef` appended by SSE `onTrace`, read by the fallback.

**[High] react-markdown v10 removed the `inline` prop — all inline code renders as block `<pre>`** (Confirmed)
- Location: `src/components/workbench/FormattedAnswer.jsx:70` (react-markdown ^10.1.0, remark-gfm ^4.0.1)
- Evidence: `code: ({ inline, children }) => { if (inline) {...} return (<pre>...) }` — `inline` is always `undefined` in v10, so `` `code` `` spans become full-width block pre blocks.
- Impact: Every answer containing inline code (model names, config keys, error tokens) is visually broken in the primary answer panel.
- Recommendation: Use the `pre` override for blocks; style `code` as inline by default (v10 pattern).

**[High] Delete mutations have no `onError` — failures are silent** (Confirmed)
- Location: `src/pages/KnowledgeBasesPage.jsx:251-265`
- Evidence: `deleteKbMutation`/`deleteDocMutation` define `onSuccess` only; no `onError`; no `mutation.isError` rendering anywhere on the page.
- Impact: A failed delete (409, 500, network) shows no feedback — user believes it was removed; UI contradicts server state until refetch.
- Recommendation: `onError: (e) => setUiError(...)` plus an inline error banner.

**[High] Dashboard polls 4 endpoints every 3-5 seconds by default, forever** (Confirmed)
- Location: `src/pages/DashboardPage.jsx:62` (`autoRefresh` defaults true), `:71-102` (3000ms analyses/claims, 5000ms conflicts/kbs)
- Impact: With the dashboard mounted (default landing page), the client issues ~80 requests/minute to the local backend even when idle — competing with real analyses for the in-process model server, wasting battery/CPU, re-rendering all Recharts every 3s.
- Recommendation: Default `autoRefresh` false; 15-30s intervals; gate on `document.visibilityState === 'visible'`.

**[High] N+1 query: every KB card fetches its own documents list, even when collapsed** (Confirmed)
- Location: `src/pages/KnowledgeBasesPage.jsx:245-248`
- Evidence: Per-card `useQuery({ queryKey: ['documents', kb.id] })` inside `KBCard` with no `enabled` gate tied to expansion.
- Impact: N document-list requests on page mount regardless of user interaction; scales linearly with KB count.
- Recommendation: `enabled: isExpanded` (fetch on first expand).

**[High] HTTP layer has no timeout, no abort, no token refresh, and no boot revalidation** (Confirmed — by absence)
- Location: `src/lib/api.js` (axios.create with only `baseURL`; zero `timeout`, zero AbortController in repo); `src/App.jsx` (`RequireAuth` checks only `Boolean(token)`); authStore never calls `authService.me()` on boot.
- Impact: A hung local model server (common with Ollama under load) leaves requests pending indefinitely; an expired/revoked token passes `RequireAuth` until the first 401; SSE stream and in-flight queries are never aborted on navigation.
- Recommendation: `timeout: 60000` on the axios client; `authService.me()` once in `main.jsx` before protected routes; AbortSignal for streaming.

**[High] `formatDistanceToNow` crashes on invalid/missing timestamps** (Likely)
- Location: `src/pages/KnowledgeBasesPage.jsx:396,437`; `src/pages/DashboardPage.jsx:603`
- Evidence: `formatDistanceToNow(new Date(kb.created_at))` — `null`/malformed dates produce Invalid Date and date-fns throws `RangeError`, unmounting the page into the ErrorBoundary.
- Impact: One malformed record kills the whole page rather than one cell.
- Recommendation: A `safeTimeAgo(date)` helper returning `'—'` on invalid input.

## Medium

**[Medium] 100ms timer re-renders the heaviest page 10x/second during loading** (Confirmed)
- Location: `src/pages/PlaygroundPage.jsx:41-54` — `setInterval(..., 100)` while all workbench panels render unmemoized.
- Recommendation: 1000ms, or isolate the timer in a tiny component.

**[Medium] Landing page re-renders on every mousemove, plus un-cleaned timeouts and rAF** (Confirmed)
- Location: `src/pages/LandingPage.jsx:339-346` (RAF spotlight `setMousePos`), `:349-360` (four setTimeouts, no cleanup), rAF never cancelled on unmount.
- Impact: The 81KB LandingPage re-renders continuously under cursor movement; navigating away mid-simulation fires setState on an unmounted tree.
- Recommendation: Spotlight via CSS custom property written to a ref (no setState); cleanup that clears timeouts and cancels rAF.

**[Medium] Same endpoint fetched under a different cache key on Settings page** (Confirmed)
- Location: `src/pages/SettingsPage.jsx:50-54` (`['settings-model-providers']`, 15s) vs `src/layouts/AppLayout.jsx:34-38` and `src/pages/PlaygroundPage.jsx:77-81` (`['model-providers']`)
- Impact: AppLayout is always mounted → Settings double-fetches `/api/v1/models/providers` on two independent cadences with two cache copies that can disagree.
- Recommendation: Reuse `['model-providers']` everywhere.

**[Medium] HUD recovery indicator can never light up — dead event name** (Confirmed)
- Location: `src/components/workbench/PipelineTelemetryHUD.jsx:27` vs `traceEvents.js:20`
- Evidence: Checks `eventNames.has('recovery.rewrite') || eventNames.has('recovery.expanded')` but the emitted type is `recovery.re_retrieve` (`TraceEventType.RECOVERY_RE_RETRIEVE`); raw strings instead of the constants defined one file over.
- Impact: The self-healing recovery stage in the telemetry HUD never shows as executed — hiding the product's flagship feature.
- Recommendation: Use `TraceEventType` constants; include `RECOVERY_RE_RETRIEVE`.

**[Medium] "API Online" badge is hardcoded, not tied to health** (Confirmed)
- Location: `src/layouts/AppLayout.jsx:118-121` — static emerald "API Online" pill; the layout never queries `healthService`.
- Impact: The status badge lies during outages — provider query failures don't demote it.
- Recommendation: Drive the badge from the providers query status (`isError`) or the health endpoint.

**[Medium] Clipboard calls reject unhandled, in four places** (Confirmed)
- Location: `src/pages/PlaygroundPage.jsx:56-61`; `src/components/workbench/ClaimInspector.jsx:34-38`; `src/components/workbench/EvidenceViewer.jsx:41-45`; `src/pages/SettingsPage.jsx:56-62`
- Evidence: `navigator.clipboard.writeText(...)` with no `.catch`; `setCopied(true)` assumes success.
- Impact: In non-secure contexts (LAN IP over HTTP — the exact deployment for a local-first tool) `writeText` rejects; copy buttons silently do nothing.
- Recommendation: `.catch(() => {})` plus `document.execCommand('copy')` fallback, or hide copy affordances when `!navigator.clipboard`.

**[Medium] Copy-feedback `setTimeout`s are never cleaned up** (Confirmed)
- Location: `ClaimInspector.jsx:37`; `SettingsPage.jsx:36,60`; `KnowledgeBasesPage.jsx:281,286-289`
- Recommendation: Store ids in refs; clear in a `useEffect` cleanup.

**[Medium] Model names and backend knowledge hardcoded in 5+ files** (Confirmed)
- Location: `PlaygroundPage.jsx:84,103-129`; `AppLayout.jsx:127,137`; `SettingsPage.jsx:74-83,303-304,320`; `PipelineTelemetryHUD.jsx:16`
- Evidence: `'granite4.2:3b-q4_K_M'`, `'embeddinggemma:300m-qat-q8_0'`, `'gemma4:e2b'`, `supportedFormats` fallback lists duplicated across pages.
- Impact: Renaming a model in config requires touching 5 UI files; fallbacks drift from backend truth.
- Recommendation: Single `src/constants/models.js`, or derive everything from the providers payload.

**[Medium] Provider-sync useEffect overwrites the user's in-flight selection** (Confirmed)
- Location: `src/pages/PlaygroundPage.jsx:90-97`
- Evidence: Effect sets `selectedEmbeddingModel` whenever `providersData` changes (every 15s poll); no check for user interaction.
- Impact: A user's model selection can snap back to the server default mid-interaction when the poll refires.
- Recommendation: Gate with a `userTouchedEmbeddingRef` set on the dropdown's onChange.

**[Medium] Search filters recomputed on every keystroke render, unmemoized** (Confirmed)
- Location: `src/pages/EvidencePage.jsx:17-25`; `src/pages/ClaimsPage.jsx:19-34`
- Impact: O(n) string scans over all evidence text per keystroke frame; janky at thousands of rows.
- Recommendation: `useMemo` keyed on `[items, query]`.

## Low

**[Low] Register-then-login masks login failures with a generic error** (Confirmed) — `RegisterPage.jsx:38-47`; one shared `setFormError` makes a post-registration login failure read as "registration failed."
**[Low] Settings logout does a hard reload and uses native `confirm()`** (Confirmed) — `SettingsPage.jsx:64-69` (`window.location.href = '/login'`) vs AppLayout's `navigate('/login')` (`AppLayout.jsx:69-72`); native `confirm()` also at `KnowledgeBasesPage.jsx:344,463`. Inconsistent logout paths; full reload discards the SPA; native dialogs are unstyleable.
**[Low] Dossier export bypasses the service layer and fails silently** (Confirmed) — `PlaygroundPage.jsx:326-340`; direct `api.get(...)` instead of an `analysisService` method; failure only `console.error`.
**[Low] Misc hygiene** (Confirmed) — index keys (`ExecutionTrace.jsx:37-39,90`; `ClaimInspector.jsx:136`); `isWeb` expression duplicated 3x and missing `integrity_status` treated as OK (`EvidenceViewer.jsx:18,29,135,136`); claim-state triple fallback `(c.state || c.status || c.verification_status)` in 4 places; prod `console.error/warn` (`PlaygroundPage.jsx:224,286,299,338`; `SettingsPage.jsx:38`; `AppLayout.jsx:63`; `main.jsx`).
**[Low] Build hygiene** (Confirmed) — `vite.config.js` `sourcemap: true` ships 1.7MB `chart-vendor.js.map` (5.6MB dist total); committed `.DS_Store`; no `test` script; `ABSTAIN` magic string (`PlaygroundPage.jsx:1055`); redundant `'Content-Type': undefined` (`services/api.js:19`).

**Note (flagged for owner awareness, not a code defect):** `LandingPage.jsx:189-228` presents hardcoded "99.4% / SOTA S-Tier / Evaluated against HaluEval, RAGTruth…" benchmark claims as real evaluation results. Standard for marketing, but the numbers are invented and this is a verification product — ExperimentsPage (Critical 2) repeats the same invented numbers *inside the app*.

---

## Score: 5.5 / 10

**Justification:** The architecture layer is genuinely good — lazy-loaded routes for all 12 pages, manualChunks vendor splitting, a single centralized axios client with correct auth/validation interceptors, a correct pub/sub authStore, disciplined React Query usage, an ErrorBoundary, clean interval cleanup in auth pages. Dragged down by real functional bugs at the heart of the flagship Playground flow (SSE/polling race, stale trace closure, broken inline-code rendering), fabricated data persisted through Experiments, default-on 3-second polling that fights the local model server, silent failure paths on destructive mutations, and an HTTP layer with no timeout/abort/refresh/boot-revalidation. Well-structured but under-verified: almost every high-severity issue is the kind a single e2e test would have caught — and the web package has no test script at all.

## Top 5 quick wins

1. **Fix the SSE/polling race** (PlaygroundPage.jsx:184-229): one-line `finalizedRef` guard + clearing the interval in `onComplete`/`onError` — eliminates the most damaging concurrency bug.
2. **Fix the FormattedAnswer code renderer** (FormattedAnswer.jsx:70) for react-markdown v10 — restores correct rendering of every answer containing inline code.
3. **Add `onError` to delete mutations + stop persisting fabricated metrics** (KnowledgeBasesPage.jsx:251-265, ExperimentsPage.jsx:41-49) — small diffs closing silent-data-integrity holes.
4. **`timeout: 60000` on the axios client + `authService.me()` at boot** (lib/api.js, main.jsx) — two-line change removing the indefinite-hang and stale-token failure classes.
5. **Flip Dashboard `autoRefresh` default to false, 15s+ intervals** (DashboardPage.jsx:62,71-102) — immediately cuts ~80 idle requests/minute against the local model server.
