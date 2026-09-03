# UI/UX Audit — TrustRAG ui-redesign (`apps/web`)

**⚠️ PARTIAL COVERAGE — read this first.** The dedicated UI/UX audit pass died mid-run (context exhaustion) after completing: routing, Tailwind styling-correctness, and the Settings page. Landing/Playground/Workbench UX below is reconstructed from the completed Frontend audit (FRONTEND.md) wherever the two lenses overlap. Treat this file as evidence-complete for what it lists, not exhaustive for the whole UI. Items marked *cross-ref* live in FRONTEND.md with full detail.

---

## Findings from the completed pass

**[High] Orphaned route: `/traces/:id` registered but reachable from nowhere** (Confirmed)
- Location: `src/App.jsx:76` — route defined; zero `Link`/`navigate` targets exist for it anywhere in the app.
- Impact: Dead navigation surface; a user who hand-types the URL gets an untested page with no back-path affordances designed around it; maintenance cost with zero user value.
- Recommendation: Either link it (from analysis history rows / Execution Trace panel "open full trace" action) or delete the route.

**[High] Invalid Tailwind classes silently render unstyled — `w-18`, `py-0.2`** (Confirmed)
- Location: `EvidenceViewer.jsx:154` (`w-18`), `AppLayout.jsx:195`, `ClaimsPage.jsx:71` (`py-0.2`), `PlaygroundPage.jsx:490,503,604,617,630`
- Evidence: Tailwind v3.4.7's static scale has no `18` width or `0.2` spacing step — these classes generate no CSS; the elements fall back to browser defaults with no console warning. Verified against `tailwind.config.js` (no extended scale for these).
- Impact: Sizing/spacing in the flagship workbench silently differs from design intent — a "polished" UI with invisible regressions where the designer assumed the utility worked.
- Recommendation: Replace with valid steps (`w-16`/`w-20`, `py-0.5`) or add the values to the config scale; add a lint rule (`eslint-plugin-tailwindcss` `no-invalid-classnames` or a CI check) so invalid utilities fail builds.

**[Medium] Settings page shows "Degraded/Disconnected" during ordinary initial load** (Confirmed)
- Location: `src/pages/SettingsPage.jsx` — provider status cards render from `health?.status` without gating on `isLoading`.
- Impact: Every visit opens with failure-state badges that resolve to "connected" a beat later — the app cries wolf about the exact thing (model health) users came to check, in a trust product.
- Recommendation: Gate on `isLoading` with skeleton states; render "checking…" not "disconnected".

**[Medium] Trim-memory action fails silently** (Confirmed)
- Location: `SettingsPage.jsx` — the memory-trim handler only `console.error`s on failure; no toast, no inline state change.
- Impact: User clicks "Trim", nothing visibly happens (also true on success — no feedback either way).
- Recommendation: Success/failure toasts + button state (spinning → done). *(Pairs with SECURITY.md/BACKEND.md: the endpoint behind it is unauthenticated and unthrottled.)*

**[Low] Settings hardcodes active-model names and a fake tenant-ID fallback** (Confirmed) — the page asserts which model is "active" from a hardcoded list rather than the providers payload, and fabricates a tenant ID when none exists. A user reading Settings is shown guesses presented as facts.
**[Low] Third duplicate polling of the providers endpoint under a different cache key** (Confirmed) — Settings polls `/models/providers` on `['settings-model-providers']` while AppLayout and Playground use `['model-providers']` — two cadences, two copies that can disagree, visible as status flapping. (Cross-ref FRONTEND.md Medium; fix is a shared key.)

## Verified valid (checked, not bugs)

- `surface-850` + `animate-fade-in`/`float`/`pulse-slow` — all defined in `tailwind.config.js:34` extended theme/animations.
- `line-clamp-4` — core in v3.4.7, no plugin needed.
- `react-markdown` v10 `inline` prop removal — real, but owned by FRONTEND.md High (FormattedAnswer.jsx:70) — every inline-code span renders as a block; the single most visible rendering defect in the app.

## Cross-referenced UX findings (from FRONTEND.md — the user-visible worst)

- **Copy buttons silently do nothing on LAN HTTP** (clipboard `writeText` rejects in non-secure contexts; no `.catch` anywhere) — the exact deployment of a local-first tool.
- **"API Online" badge is hardcoded** — stays green during outages (AppLayout.jsx:118-121).
- **Deletes fail silently** — no `onError` on delete mutations; users see items "removed" that weren't.
- **The recovery indicator can never light up** — dead event names in the telemetry HUD hide the product's flagship self-healing feature from the user watching for it (PipelineTelemetryHUD.jsx:27).
- **Model selection snaps back mid-interaction** — 15s provider-sync overwrites the user's dropdown choice.
- **One malformed date unmounts the whole page** into the ErrorBoundary (`formatDistanceToNow` on unvalidated data).
- **Dashboard defaults to 3-5s polling forever** — the app keeps fighting the local model server while idle.
- **Landing page presents invented benchmark numbers** ("99.4%", "SOTA S-Tier", "Evaluated against HaluEval, RAGTruth…") as real results (LandingPage.jsx:189-228) — and ExperimentsPage persists the same invented numbers into the database (FRONTEND.md Critical 2). For a verification product, on-screen fabrication is the single most damaging UX-adjacent trust defect.

## Accessibility

Not audited in depth (agent died before the a11y pass). Structural positives observed: semantic `aria-*` usage on status badges in AppLayout, keyboard-navigable nav. Unknowns: focus management on modal/route transitions, color-contrast on the dark surface palette, reduced-motion handling for the `float`/`pulse-slow` animations, screen-reader labels on the workbench's custom controls (HUD, evidence inspector). Flagging a11y as an open gap rather than inventing findings.

---

## UI/UX Score: 5 / 10 (provisional — partial coverage, ~40% of surface audited)

**Justification (within coverage):** The visual system is genuinely built out — a coherent dark surface palette, real custom animations, a workbench layout with live telemetry. But the polish is repeatedly undermined by *things that claim to be what they aren't*: statuses that lie (hardcoded "Online", "Degraded" during load, fake active-models, fake tenant ID, invented benchmarks, unverifiable "VERIFIED" web evidence), actions that silently do nothing (copy, delete, trim), CSS classes that silently don't apply, and a recovery feature the UI literally cannot show. The theme of this UI is that its displays are disconnected from its data — which in a trust product is not a cosmetic complaint. Score is provisional pending the full a11y and flow passes; the cross-referenced Frontend findings skew the true number toward FRONTEND.md's 5.5.

## Top 5 quick wins

1. **Kill the fabricated benchmarks in-app** (ExperimentsPage + LandingPage claims) — one-line each; the highest trust-per-diff fix in the UI.
2. **Fix the invalid Tailwind classes** (9 usages) and add a lint rule so they can't return.
3. **Gate Settings status badges on `isLoading`** — stop showing failure during ordinary load.
4. **Make copy/delete/trim actions report success and failure** (toasts + `onError`) — three small diffs covering every silent action on the page.
5. **Link or delete the orphaned `/traces/:id` route.**
