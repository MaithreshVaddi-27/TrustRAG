# TrustRAG — Ultra-Premium Design System

**Date:** 2026-11-07 · **Direction (v3):** "The Ledger" + champagne luxury. Ink-black surfaces, ivory display type, restrained cyan (primary accent), champagne gold `#d8c9a3` (the single luxury accent — verdicts and CTA edges only, never status), hairlines, tabular mono telemetry, generous spacing. Built with ui-ux-pro-max, anti-ui-slop (`new-work.md`) and apple-design (WWDC fluid-interfaces) principles.

**v3 delta (this pass):** luxury color system, type refinement (serif weights 600–700), gold CTA edge + gradient, `.live-dot` status effect, `.stat-value` numerals, component-by-component detailing (LandingNavbar, QueryInput emoji→Lucide, QueryPanel/ResultsPanel 44px + a11y, HeroBanner gold rule). v1/v2 history retained below.

## 1. Visual Identity

- **Surfaces:** obsidian stack `surface-950 #040711 → surface-700 #1e293b` with translucent glass materials (`.glass-card/nav/sidebar/surface`), bright top-edge highlights, layered shadows — plus Ledger `ink`/`parchment` aliases (`ink-950 #040711`, `parchment #f2ede3` for display type).
- **Primary:** one restrained cyan accent (`#38bdf8/#22d3ee`); gradients `primary-600 → cyan-600` reserved for primary CTAs only (no neon overload).
- **Semantic:** emerald `#10b981` (verified), crimson `#ef4444` (contradicted), amber `#f59e0b` (unsupported/caution), slate (unknown).
- **Type:** editorial serif display (`font-display`: Iowan Old Style / Palatino / Georgia — system faces only, air-gapped safe) for verdict titles and metric values; Inter body with `tnum` tabular numerals; JetBrains Mono for hashes/telemetry. Size-specific tracking (negative on display, neutral on body), inverse leading.
- **Depth:** subtle film grain (`.grain`, 3.5% SVG noise), cursor spotlight on landing, ambient radial flares, `.lift-hover` elevation on cards.
- **Motion (Apple):** springs everywhere (critically damped `bounce:0`, response ~0.3–0.4 s); press feedback on pointer-down-ish `:active` scale (80–150 ms); interruptible/reversible entrances; `prefers-reduced-motion` collapses to cross-fades; `prefers-reduced-transparency`/`prefers-contrast` honored.

## 2. Tokens (single source of truth)

`src/styles/design-tokens.css` is imported first by `src/index.css` and mirrors `tailwind.config.js`:

- Color ramps (primary, cyber, surface, verified/contradicted/unsupported/unknown, trust bands, ink/parchment, hairlines)
- Type scale (`--text-display` → `--text-heading-3`, leading/tracking)
- Spacing (4pt grid: `--space-1 → -8`, `--space-section`, `--space-chapter`), radii, elevations (`--shadow-card/nav/lift/glow-*`)
- Icons (token sizes `--icon-sm/md/lg` = 16/20/24, stroke 1.5 px)
- Motion (`--ease-out-expo`, `--ease-spring`, durations; `prefers-reduced-motion` collapses to 1 ms)
- Z-index (`--z-base → -overlay`)

**Rule:** change a token here → change it in `tailwind.config.js` too. The CSS file is the documentation layer; Tailwind is the build layer.

## 3. Component Library (`src/components/ui/`)

| Primitive | Purpose |
|---|---|
| `PageHeader` | Editorial rhythm for every app screen: `.kicker` (mono uppercase + hairline rule) → `h1` serif (parchment, gradient accent) → supporting copy → actions slot. Accepts `eyebrow`, `title`+`accent`, `description`, `countLabel`, `actions`, `children`. |
| `Card` | Glass surface; `hover` adds `.lift-hover` premium lift; `dashed` for empty states. |
| `Badge` | Semantic claim badges with status dot (color never alone): `supported/contradicted/neutral/unsupported/unknown`. |
| `.kicker` / `.meta` / `.hairline` / `.lift-hover` / `.link-ledger` | Shared utilities in `index.css`. |
| `.btn-primary/secondary/danger` | All min-height 44px, press feedback 150 ms, `cursor-pointer`, `touch-manipulation`. |

Existing system classes retained: `.glass-*`, `.border-beam`, `.text-gradient`, `.text-editorial`, `.code-block`, `.trace-event`, `.section-heading`, type scale (`.text-display…` in `typography.css`), glass/scan/shimmer utilities (`materials.css`, `animations.css`, `loaders.css`).

### Shell

| Component | Treatment |
|---|---|
| `Sidebar` | Section labels (WORKBENCH / EVIDENCE / SYSTEM), 44px links, 20px icons (1.5 stroke), spring active pill + indicator bar, `aria-expanded` collapse toggle. |
| `Navbar` | 44px targets (hamburger, sidebar toggle, Run Analysis, logout), serif lockup, telemetry pills with stale/offline states, `aria-hidden` decorative icons. |
| `HeroBanner` | Editorial hero: live kicker, serif verdict title, dual CTAs (primary + secondary), hairline rule. |
| `MetricsGrid` | Ledger stat cards: hairline top rules, 44px icon tiles, serif tabular values, trust band pill, deep links. |
| `Auth` (`AuthLayout`, Login, Register) | Serif card title, 16px inputs (no iOS zoom), 44px fields/buttons, 44px password toggle (`aria-pressed`), `role="alert"` errors. |
| `Landing` (`HeroSection` + sections) | Serif hero with `text-balance`, 52px CTAs, mono stat cards, cursor spotlight, grain. |

## 4. Screen System

All screens keep identical copy, routes and behavior; only the presentation layer changed:

| Screen | Treatment |
|---|---|
| Landing (`/`) | Editorial serif hero (text-balance), 52px CTAs, mono stat cards, cursor spotlight, ambient flares, `.grain` — screenshot `screenshots/landing.png`. |
| Auth (`/login`, `/register`) | Centered glass card, 56px framed emblem, serif lockup + card title, 16px/44px inputs, 44px password toggle, `role="alert"` errors, back-to-overview 44px. |
| Dashboard (`/dashboard`) | Editorial `HeroBanner` (live kicker, dual CTAs) + observability bar + Ledger `MetricsGrid` + lazy charts + recent feed + pipeline diagram. |
| Knowledge Bases (`/knowledge-bases`) | Shared `PageHeader` + search bar + card grid + formats reference. |
| Playground (`/playground`) | Unchanged two-pane workbench (query panel + results) — deliberately untouched to protect the SSE streaming flow and its test. |
| Claims / Evidence / Conflicts | Shared `PageHeader` with live count pills and Run-Query CTA. |
| Trace (`/traces/:id`) | Shared `PageHeader` (eyebrow, title, `Analysis {id}` description). |
| Settings (`/settings`) | Shared `PageHeader`; live System Operational/Degraded badge as header action with `aria-live`. |
| 404 | Unchanged.

Every state preserved: loading (ThinkingOrbs/skeletons), empty, error (`role="alert"`), success, disabled, responsive (`sm/md/lg`, mobile drawer, safe-area insets, `100dvh`).

## 5. Motion (Apple fluid interfaces)

- Springs everywhere (critically damped): route transitions (AnimatePresence, 0.2 s expo), page-header entrance (0.3 s expo), sidebar pill/section staggers, card lift (200 ms expo), press scale 80 ms — all interruptible/reversible.
- Feedback is continuous during interaction (hover lift, active scale), never only at the end; no locked-out input during transitions; enter/exit along the same path.
- `MotionConfig` in `main.jsx` honors OS reduced-motion globally (cross-fade fallback); `prefers-reduced-motion` collapses token durations to 1 ms.

## 6. Accessibility (ui-ux-pro-max priorities 1–2)

- Contrast: body ≥ 4.5:1 on obsidian (slate remapped lighter); trust/semantic color always paired with text/dot (never color alone).
- Targets: all interactive controls ≥ 44×44 px; 8 px+ gaps; `touch-manipulation` (no 300 ms delay); visible `:focus-visible` ring.
- Semantics: skip link, sequential headings (one `h1` per screen via `PageHeader`), icon controls named, decorative icons `aria-hidden`, form labels + inline `role="alert"` errors with `aria-pressed` toggles, live regions for status (`aria-live`).
- Adaptive: `prefers-reduced-motion`, `prefers-reduced-transparency` (flattens glass), `prefers-contrast: more` overrides; safe-area insets; `100dvh`; no horizontal scroll at 375/768/1024/1440 (verified 375 + 1440).
- Verified: 0 console errors, 0 horizontal overflow (desktop 1440 px + mobile 375 px), keyboard focus visible on all routes.

## 7. Light theme — deferred (deliberate)

Dark is canonical (`<html class="dark">`, `color-scheme: dark`). A full light theme requires remapping every explicit `surface-*`/`slate-*` class across 30+ components; shipping a half-broken toggle would be worse than a coherent dark-only product. Tokens in §2 are theme-agnostic groundwork for a future `data-theme="light"` ramp. Tracked as deferred work in the Validation Report.

## 8. v3 — Luxury refinement (2026-11-07)

- **Color:** champagne gold (`--color-gold-300/400/500`: `#e5d5a8`/`#d8c9a3`/`#c9ab6e`, Tailwind `gold`) blended into the existing theme: verdict gradient `ivory → cyan → gold` (`.text-gradient`), hairline hero rule (HeroBanner), CTA edge light (`btn-primary::after`). Status colors untouched.
- **Typography:** serif weights refined (`heading-1` 600, `display` 700); `.text-balance`/`.text-pretty`; `.stat-value` serif tabular numerals; `.live-dot` status pulse (reduced-motion safe).
- **Effects:** hover underlines (LandingNavbar cyan→gold), 200 ms expo lifts, press scales 80–150 ms, border-beam retained for streams, shimmer hero gradient, cursor spotlight, grain.
- **Every component checked:** LandingNavbar (44px, serif, underline), Sidebar (sections, 44px), Navbar (44px, telemetry), HeroBanner (gold rule), MetricsGrid (serif values), QueryInput (Lucide presets — emoji removed, 16px), QueryPanel (44px reset), ResultsPanel (44px tabs + `role=tab`/`aria-selected`, 44px export), PageHeader/Card/Badge (editorial), Auth (16px/44px, `role=alert`), Landing CTAs (52px).
