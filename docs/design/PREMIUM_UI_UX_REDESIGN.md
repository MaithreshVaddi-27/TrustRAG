# TrustRAG — Premium UI/UX Redesign

**Date:** 2026-11-07
**Branch:** `reliability-phase1` (frontend on top of `ui-redesign`)
**Scope:** Design system, typography, surfaces, motion, accessibility, and cross-screen consistency.
**Verification:** ESLint 0 errors/0 warnings, Vite build success, Vitest 33/33, Brave DevTools console clean.

---

## 1. Design Direction

TrustRAG is an AI reliability & hallucination audit workbench. The redesign targets an
**editorial, precision-engineering aesthetic** rather than a generic AI dashboard:

- **Obsidian surfaces** (`surface-950` → `surface-700`) with subtle translucent glass materials.
- **Electric Cyber Azure** primary (`primary-500` `#0084ff`) paired with **Cyber Cyan** telemetry accents.
- **Semantic status colors**: Emerald (verified), Crimson (contradicted), Amber (caution).
- **Editorial display serif** (`font-display`: Iowan Old Style / Palatino / Georgia) for hero and section leads, giving a crafted, publication-grade feel distinct from SaaS templates.
- **Sans body** (Inter system stack) with optical sizing and tabular numerals for telemetry.
- **Mono** (JetBrains Mono) for code, hashes, IDs, and telemetry labels.

Air-gapped safe: no CDN fonts; all faces are system-available.

## 2. Design-System Decisions

### Typography
- Added `font-display` family (system serif stack) in `tailwind.config.js`.
- Body uses `font-feature-settings: 'cv11', 'ss01', 'tnum'` + `font-variant-numeric: tabular-nums` for aligned numerals.
- `text-rendering: optimizeLegibility` for crisp headings.
- `.text-editorial` utility for serif display leads.
- Existing scale retained: `.text-display`, `.text-heading-1..3`, `.text-body*`, `.text-caption`, `.text-micro`, `.text-code`.

### Surfaces & Depth
- Glass materials (`.glass-card`, `.glass-nav`, `.glass-sidebar`, `.glass-surface`) with bright top edges and layered shadows.
- Reduced-transparency and high-contrast media queries preserved.
- Added `.grain` overlay utility (subtle SVG fractal noise, `mix-blend-mode: overlay`, 3.5% opacity) for premium depth on hero/section containers. Disabled under `prefers-reduced-motion`.

### Motion
- Purposeful micro-interactions only: hover lift, focus rings, indeterminate loading bar, AnimatePresence route transitions.
- All animations gated by `prefers-reduced-motion` where applicable.
- No decorative or looping animations on data surfaces.

### Accessibility
- Single consolidated `:focus-visible` ring (2px sky, 2px offset).
- All form controls have `id`/`name`/`htmlFor`/`aria-label` (prior audit).
- WCAG AA contrast maintained on obsidian surfaces (slate 500/600 remapped lighter).
- Keyboard navigation preserved; reduced-motion and reduced-transparency respected.

## 3. Screens Redesigned / Refined

| Screen | Changes |
|---|---|
| Landing (Hero) | Hero `h1` now uses `font-display` serif for editorial authority; spacing/leading tightened. |
| Design system | Added `font-display`, `.text-editorial`, `.grain` utilities; refined body typography. |
| All app screens | Inherit refined typography, tabular numerals, focus ring, scrollbar, selection. |

No backend, API, or data contract changes. All existing RAG workflows preserved.

## 4. Components Changed

- `tailwind.config.js` — added `fontFamily.display`.
- `src/index.css` — body typography refinement (`tnum`, `optimizeLegibility`).
- `src/styles/materials.css` — added `.text-editorial` and `.grain` utilities.
- `src/components/landing/HeroSection.jsx` — hero heading uses `font-display`.

## 5. Browser Validation

- Brave DevTools: navigated `http://localhost:5174/` (landing) and dashboard; console clean (no errors/warnings beyond Vite HMR info).
- Full-page screenshot captured for visual review.
- Responsive: existing breakpoints (sm/md/lg/2xl) retained; mobile drawer and safe-area insets preserved.

## 6. Accessibility Checks

- Focus ring present and single-sourced.
- Form semantics from prior audit intact (id/name/htmlFor/aria-label).
- Reduced-motion and reduced-transparency media queries intact.
- High-contrast mode overrides intact.

## 7. Performance Observations

- Build: 3292 modules, ~3.4s. CSS 88.5 kB (gzip 15.2 kB). No new dependencies added.
- No layout shifts introduced (typography refinements are CSS-only).
- Lazy-loaded charts and pages unchanged.

## 8. Remaining Issues / Next Steps

- Full light-theme variant not implemented (app is dark-only by design; `color-scheme: dark`).
- Further screen-level polish (Dashboard, Playground, Evidence, Claims) can iterate using the new `.grain`/`.text-editorial` primitives.
- Consider adding a serif display face via self-hosted font files for richer editorial identity in air-gapped installs.
