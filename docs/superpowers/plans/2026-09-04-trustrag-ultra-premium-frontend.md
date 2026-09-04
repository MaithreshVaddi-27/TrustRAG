# TrustRAG Ultra-Premium Frontend Upgrade Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform TrustRAG's frontend into an ultra-premium, responsive, production-grade application with external per-component CSS, Apple-design motion principles, full favicon set, and zero bugs.

**Architecture:** Keep Tailwind CSS for utility classes and theming. Add external per-component CSS files for all custom styles, animations, and component-specific design. Split oversized components (LandingPage 1000+ lines) into focused sub-components. Apply Apple Design principles: interruptible spring animations, velocity-aware transitions, translucent materials, optical typography sizing, and reduced-motion accessibility.

**Tech Stack:** React 18, Vite, Tailwind CSS 3.4, Motion (Framer Motion) 13+, React Router 7, TanStack Query 5, Lucide React, Recharts, date-fns, clsx

**Spec:** `TRUSTRAG_specs.md`, Apple Design skill (`~/.agents/skills/apple-design/SKILL.md`), existing `apps/web/src/index.css` and `tailwind.config.js`

---

## Global Constraints

- **Tailwind 3.4** — dark mode via `class` strategy, custom `surface`/`primary`/`cyber` color tokens already defined
- **React 18** — lazy loading already in App.jsx via `React.lazy()`, must preserve code splitting
- **Vite 6** — use `@/` path alias (configured in vite.config.js), no changes to build config
- **Motion 13** — use `motion/react` imports (not `framer-motion`), spring-based animations only
- **Fonts** — Inter (sans) + JetBrains Mono (mono) via Google Fonts, non-blocking load already in index.html
- **Accessibility** — `prefers-reduced-motion`, `prefers-reduced-transparency`, `prefers-contrast` already in index.css
- **No new dependencies** — work with existing package.json only
- **Preserve all existing routes, pages, and functionality** — this is a style/quality upgrade, not a feature change

---

## File Structure (Final State)

### New External CSS Files
```
apps/web/src/styles/
├── landing.css          — LandingPage hero, simulation, capabilities, benchmarks, comparison, footer
├── app-layout.css       — AppLayout sidebar, top navbar, mobile drawer
├── dashboard.css        — DashboardPage charts, cards, pipeline phases
├── playground.css       — PlaygroundPage input, streaming, tabs, results
├── auth.css             — LoginPage, RegisterPage forms
├── knowledge-bases.css  — KnowledgeBasesPage list, modals
├── evidence.css         — EvidencePage table, filters
├── claims.css           — ClaimsPage cards, verdicts
├── conflicts.css        — ConflictsPage resolution UI
├── experiments.css      — ExperimentsPage experiment cards
├── settings.css         — SettingsPage forms, toggles
├── trace.css            — TracePage timeline, events
├── components.css       — Shared workbench components (ReliabilityBadge, ClaimInspector, etc.)
├── animations.css       — All @keyframes, animation utilities, spring presets
├── materials.css        — Glassmorphism, backdrop-filter, translucent surfaces
├── typography.css       — Display, heading, body, caption, code type scale
└── index.css            — Entry point (imports Tailwind + all above)
```

### New Sub-Component Files (LandingPage split)
```
apps/web/src/components/landing/
├── HeroSection.jsx         — Telemetry badge, headline, CTAs, metrics ribbon
├── SimulationSandbox.jsx   — Interactive audit simulation with border-beam
├── CapabilitiesExplorer.jsx— Tabbed code/architecture explorer
├── BentoArchitecture.jsx   — Grid architecture cards
├── BenchmarksSection.jsx   — Accuracy/speed/memory animated bars
├── ComparisonMatrix.jsx    — Naive vs TrustRAG comparison table
├── LandingFooter.jsx       — Footer with links
├── LandingNavbar.jsx       — Sticky top navbar for landing page
└── index.js                — Barrel export
```

### New Favicon Files
```
apps/web/public/icons/
├── favicon.ico           — 16x16, 32x32 multi-size
├── favicon-16x16.png     — 16x16 PNG
├── favicon-32x32.png     — 32x32 PNG
├── apple-touch-icon.png  — 180x180 PNG
├── android-chrome-192.png— 192x192 PNG
├── android-chrome-512.png— 512x512 PNG
└── trustrag-icon.svg     — (existing, keep)
```

---

### Task 1: CSS Foundation — External Styles Architecture ✅ COMPLETED

**Files:**
- Create: `apps/web/src/styles/index.css` (new entry point)
- Create: `apps/web/src/styles/typography.css`
- Create: `apps/web/src/styles/animations.css`
- Create: `apps/web/src/styles/materials.css`
- Modify: `apps/web/src/index.css` (replace content with imports)
- Modify: `apps/web/src/main.jsx` (update CSS import path)

**Interfaces:**
- Consumes: Existing Tailwind config tokens (colors, fonts, animations)
- Produces: CSS custom properties and utility classes used by all subsequent tasks

- [ ] **Step 1: Create `apps/web/src/styles/` directory**

```bash
mkdir -p apps/web/src/styles
```

- [ ] **Step 2: Create `typography.css` with Apple Design type scale**

```css
/* ── Typography Scale (Apple Design: size-specific tracking, inverse leading) ── */

.text-display {
  font-size: clamp(2.5rem, 5vw, 4.5rem);
  line-height: 1.05;
  letter-spacing: -0.025em;
  font-weight: 800;
  font-optical-sizing: auto;
}

.text-display-sm {
  font-size: clamp(1.75rem, 3.5vw, 3rem);
  line-height: 1.08;
  letter-spacing: -0.02em;
  font-weight: 700;
}

.text-heading-1 {
  font-size: clamp(1.875rem, 3vw, 2.5rem);
  line-height: 1.12;
  letter-spacing: -0.015em;
  font-weight: 700;
}

.text-heading-2 {
  font-size: clamp(1.5rem, 2.5vw, 2rem);
  line-height: 1.2;
  letter-spacing: -0.01em;
  font-weight: 600;
}

.text-heading-3 {
  font-size: clamp(1.125rem, 2vw, 1.5rem);
  line-height: 1.25;
  letter-spacing: -0.005em;
  font-weight: 600;
}

.text-body-lg {
  font-size: 1.125rem;
  line-height: 1.65;
  letter-spacing: 0;
}

.text-body {
  font-size: 1rem;
  line-height: 1.65;
  letter-spacing: 0;
}

.text-body-sm {
  font-size: 0.875rem;
  line-height: 1.6;
  letter-spacing: 0;
}

.text-caption {
  font-size: 0.75rem;
  line-height: 1.5;
  letter-spacing: 0.01em;
}

.text-micro {
  font-size: 0.625rem;
  line-height: 1.4;
  letter-spacing: 0.02em;
  font-family: 'JetBrains Mono', monospace;
}

.text-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  letter-spacing: 0;
}
```

- [ ] **Step 3: Create `animations.css` with all @keyframes and presets**

Move all keyframe definitions and animation utilities from current `index.css` into this file. Include:
- `fadeIn`, `slideUp`, `glow`, `float`, `scan`, `shimmer`
- `radarSweep`, `haloPulse`, `borderGlow`
- `rotateBeam` (for `.border-beam`)
- `shine` (for `.shimmer-text`)
- `scanlineMove` (for `.laser-scanline`)
- All spring-based utility classes using CSS `transition` with `cubic-bezier(0.34, 1.56, 0.64, 1)` for spring feel
- Reduced-motion overrides: all animations→opacity cross-fade only

```css
/* ── Keyframes ─────────────────────────────────────────────────────────────── */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes glow {
  from { filter: drop-shadow(0 0 6px rgba(14, 165, 233, 0.4)); }
  to { filter: drop-shadow(0 0 16px rgba(14, 165, 233, 0.8)); }
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-8px); }
}

@keyframes scan {
  0% { top: 0%; }
  50% { top: 95%; }
  100% { top: 0%; }
}

@keyframes shimmer {
  from { background-position: -200% 0; }
  to { background-position: 200% 0; }
}

@keyframes radarSweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes haloPulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.25); opacity: 0; }
  100% { transform: scale(0.95); opacity: 0; }
}

@keyframes borderGlow {
  0%, 100% {
    border-color: rgba(14, 165, 233, 0.3);
    box-shadow: 0 0 15px rgba(14, 165, 233, 0.15);
  }
  50% {
    border-color: rgba(6, 182, 212, 0.7);
    box-shadow: 0 0 25px rgba(6, 182, 212, 0.35);
  }
}

@property --beam-angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

@keyframes rotateBeam {
  from { --beam-angle: 0deg; }
  to { --beam-angle: 360deg; }
}

@keyframes shine {
  to { background-position: 200% center; }
}

@keyframes scanlineMove {
  0%, 100% { top: 6%; opacity: 0.3; }
  50% { top: 92%; opacity: 1; }
}

/* ── Reduced Motion ────────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  [data-reduced-motion] {
    animation: none !important;
    transition: none !important;
  }
}
```

- [ ] **Step 4: Create `materials.css` with glassmorphism and translucent surfaces**

```css
/* ── Glassmorphism & Translucent Surfaces (Apple Design: material weight = hierarchy) ── */

.glass-card {
  background: rgba(8, 12, 22, 0.8);
  backdrop-filter: blur(12px) saturate(150%);
  -webkit-backdrop-filter: blur(12px) saturate(150%);
  border: 1px solid rgba(30, 41, 59, 0.8);
  border-radius: 1rem;
  box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.5);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.glass-card-hover:hover {
  border-color: rgba(14, 165, 233, 0.4);
  box-shadow: 0 10px 40px -10px rgba(14, 165, 233, 0.15);
  transform: translateY(-2px);
}

.glass-nav {
  background: rgba(4, 7, 17, 0.8);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border-bottom: 1px solid rgba(30, 41, 59, 0.8);
}

.glass-sidebar {
  background: rgba(8, 12, 22, 0.95);
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
}

.glass-surface {
  background: rgba(18, 24, 38, 0.6);
  backdrop-filter: blur(8px) saturate(120%);
  -webkit-backdrop-filter: blur(8px) saturate(120%);
}

/* ── Border Beam ───────────────────────────────────────────────────────────── */
.border-beam {
  position: relative;
}

.border-beam::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  padding: 1px;
  background: conic-gradient(
    from var(--beam-angle, 0deg) at 50% 50%,
    transparent 0%,
    #0284c7 15%,
    #06b6d4 25%,
    #38bdf8 35%,
    transparent 50%
  );
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  animation: rotateBeam 4s linear infinite;
}

/* ── Scrollbar ─────────────────────────────────────────────────────────────── */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: #040711;
}
::-webkit-scrollbar-thumb {
  background: #1e293b;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}
::-webkit-scrollbar-thumb:hover {
  background: #0284c7;
  box-shadow: 0 0 10px rgba(2, 132, 199, 0.5);
}

/* ── Reduced Transparency ──────────────────────────────────────────────────── */
@media (prefers-reduced-transparency: reduce) {
  .glass-card, .glass-nav, .glass-sidebar, .glass-surface {
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    background-color: rgba(4, 7, 17, 0.98) !important;
  }
}

/* ── High Contrast ─────────────────────────────────────────────────────────── */
@media (prefers-contrast: more) {
  :root {
    --border-color: rgba(255, 255, 255, 0.3);
    --text-muted: rgba(255, 255, 255, 0.8);
  }
}
```

- [ ] **Step 5: Update `apps/web/src/index.css` to be an import hub**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ── External CSS imports ──────────────────────────────────────────────────── */
@import './styles/typography.css';
@import './styles/animations.css';
@import './styles/materials.css';

/* ── Base resets ───────────────────────────────────────────────────────────── */
@layer base {
  html {
    scroll-behavior: smooth;
    color-scheme: dark;
  }

  body {
    @apply bg-surface-950 text-slate-100 font-sans antialiased selection:bg-primary-500/20 selection:text-primary-300;
    font-feature-settings: 'cv11', 'ss01';
    font-optical-sizing: auto;
  }

  :focus-visible {
    @apply outline-none ring-2 ring-primary-400 ring-offset-2 ring-offset-surface-950;
  }
}

/* ── Selection ─────────────────────────────────────────────────────────────── */
::selection {
  background: rgba(2, 132, 199, 0.35);
  color: #38bdf8;
}
```

- [ ] **Step 6: Update `apps/web/src/main.jsx` CSS import**

Change line 6 from `import './index.css'` to `import './styles/index.css'` — wait, we're keeping `index.css` as the hub. Keep as-is.

- [ ] **Step 7: Verify build compiles**

Run: `cd apps/web && npm run build`
Expected: Successful build with no CSS errors.

- [ ] **Step 8: Commit**

```bash
git add apps/web/src/styles/ apps/web/src/index.css
git commit -m "feat(css): create external CSS architecture with typography, animations, materials"
```

---

### Task 2: Fix All Bugs and CSS Duplications ✅ COMPLETED

**Files:**
- Modify: `apps/web/src/index.css` — remove duplicated rules
- Modify: `apps/web/src/components/workbench/FormattedAnswer.jsx` — fix `inline` prop
- Modify: `apps/web/src/pages/SettingsPage.jsx` — fix logout navigation
- Modify: `apps/web/src/App.jsx` — add 404 page route
- Create: `apps/web/src/pages/NotFoundPage.jsx`

**Interfaces:**
- Consumes: Task 1 CSS foundation
- Produces: Clean, bug-free codebase for styling work

- [ ] **Step 1: Remove duplicated CSS rules from `index.css`**

The following rules appear twice (once in `@layer base`, once raw below). Remove the raw duplicates:
- `html { scroll-behavior: smooth; color-scheme: dark; }` (lines 207-210)
- `::selection { ... }` (lines 213-216)
- `::-webkit-scrollbar` rules (lines 218-234)
- `:focus-visible` rules (lines 237-240)

After Task 1 restructuring, these should only exist in the appropriate `styles/` file.

- [ ] **Step 2: Fix ReactMarkdown `inline` prop bug in `FormattedAnswer.jsx`**

Find the `<ReactMarkdown>` component usage and remove any `inline` prop (ReactMarkdown v10 doesn't accept it — it caused all code blocks to render as inline).

- [ ] **Step 3: Fix SettingsPage logout — use React Router navigation**

In `SettingsPage.jsx`, find `window.location.href = '/login'` and replace with `navigate('/login')` using `useNavigate()` hook, matching the pattern in `AppLayout.jsx:119-122`.

- [ ] **Step 4: Create NotFoundPage.jsx**

```jsx
import { Link } from 'react-router-dom'
import { ShieldAlert, ArrowLeft } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-surface-900 border border-slate-800 flex items-center justify-center">
          <ShieldAlert size={32} className="text-slate-500" />
        </div>
        <h1 className="text-display-sm text-white mb-3">404</h1>
        <p className="text-body text-slate-400 mb-8">This page doesn't exist or has been moved.</p>
        <Link
          to="/"
          className="btn-primary inline-flex"
        >
          <ArrowLeft size={16} />
          <span>Return Home</span>
        </Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Add 404 route in App.jsx**

Replace the fallback route (line 79):
```jsx
// Before:
<Route path="*" element={<Navigate to="/" replace />} />

// After:
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))
// ... (add import at top with other lazy imports)
<Route path="*" element={<NotFoundPage />} />
```

- [ ] **Step 6: Build and verify**

Run: `cd apps/web && npm run build`
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "fix: resolve CSS duplications, ReactMarkdown inline prop, settings logout, add 404 page"
```

---

### Task 3: Full Favicon Set ✅ COMPLETED

**Files:**
- Create: `apps/web/public/icons/favicon.ico`
- Create: `apps/web/public/icons/favicon-16x16.png`
- Create: `apps/web/public/icons/favicon-32x32.png`
- Create: `apps/web/public/icons/apple-touch-icon.png`
- Create: `apps/web/public/icons/android-chrome-192.png`
- Create: `apps/web/public/icons/android-chrome-512.png`
- Modify: `apps/web/index.html` — update favicon links
- Create: `apps/web/public/manifest.json` — update if needed

**Interfaces:**
- Consumes: Existing `trustrag-icon.svg`
- Produces: Complete favicon set referenced by index.html

- [ ] **Step 1: Generate PNG favicons from existing SVG**

Use the existing `trustrag-icon.svg` as source. Generate all sizes programmatically (or create minimal placeholder PNGs that match the brand):

```bash
# If you have ImageMagick:
cd apps/web/public/icons
convert ../trustrag-icon.svg -resize 16x16 favicon-16x16.png
convert ../trustrag-icon.svg -resize 32x32 favicon-32x32.png
convert ../trustrag-icon.svg -resize 180x180 apple-touch-icon.png
convert ../trustrag-icon.svg -resize 192x192 android-chrome-192.png
convert ../trustrag-icon.svg -resize 512x512 android-chrome-512.png
convert favicon-16x16.png favicon-32x32.png favicon.ico
```

If ImageMagick is not available, create minimal PNG files as placeholders.

- [ ] **Step 2: Update `apps/web/index.html` favicon links**

```html
<!-- Replace existing favicon links (lines 13-14) with: -->
<link rel="icon" type="image/svg+xml" href="/trustrag-icon.svg" />
<link rel="icon" type="image/png" sizes="16x16" href="/icons/favicon-16x16.png" />
<link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32x32.png" />
<link rel="icon" type="image/x-icon" href="/icons/favicon.ico" />
<link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png" />
<link rel="manifest" href="/manifest.json" />
<meta name="msapplication-TileColor" content="#040711" />
```

- [ ] **Step 3: Update `apps/web/public/manifest.json`**

```json
{
  "name": "TRUSTRAG — AI Reliability Workbench",
  "short_name": "TRUSTRAG",
  "description": "Autonomous Hallucination Detection & Closed-Loop Recovery Platform",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#040711",
  "theme_color": "#040711",
  "icons": [
    { "src": "/icons/android-chrome-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/android-chrome-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 4: Build and verify**

Run: `cd apps/web && npm run build`
Check: `dist/icons/` contains all generated files.

- [ ] **Step 5: Commit**

```bash
git add apps/web/public/icons/ apps/web/public/manifest.json apps/web/index.html
git commit -m "feat(assets): add full favicon set with multi-size PNGs and updated manifest"
```

---

### Task 4: Split LandingPage into Sub-Components ✅ COMPLETED

**Files:**
- Create: `apps/web/src/components/landing/LandingNavbar.jsx`
- Create: `apps/web/src/components/landing/HeroSection.jsx`
- Create: `apps/web/src/components/landing/SimulationSandbox.jsx`
- Create: `apps/web/src/components/landing/CapabilitiesExplorer.jsx`
- Create: `apps/web/src/components/landing/BentoArchitecture.jsx`
- Create: `apps/web/src/components/landing/BenchmarksSection.jsx`
- Create: `apps/web/src/components/landing/ComparisonMatrix.jsx`
- Create: `apps/web/src/components/landing/LandingFooter.jsx`
- Create: `apps/web/src/components/landing/index.js`
- Modify: `apps/web/src/pages/LandingPage.jsx` (slim to ~50 lines, imports sub-components)

**Interfaces:**
- Consumes: LandingPage current data/constants (SCENARIOS, CAPABILITIES, BENCHMARKS, COMPARISON_*)
- Produces: Clean composable landing page

- [ ] **Step 1: Create `components/landing/` directory**

```bash
mkdir -p apps/web/src/components/landing
```

- [ ] **Step 2: Extract LandingNavbar.jsx**

Move lines 390-523 (sticky header + mobile drawer) from LandingPage.jsx into `LandingNavbar.jsx`. Accept props: `isAuthenticated`, `isMobileNavOpen`, `setIsMobileNavOpen`.

- [ ] **Step 3: Extract HeroSection.jsx**

Move lines 527-622 (hero section with floating cards, telemetry badge, headline, CTAs, metrics ribbon) into `HeroSection.jsx`. Accept props: `navigate`, `isAuthenticated`.

- [ ] **Step 4: Extract SimulationSandbox.jsx**

Move lines 624-821 (simulation sandbox with border-beam, claims matrix, self-healing banner) into `SimulationSandbox.jsx`. Accept props: `selectedScenarioKey`, `handleSelectScenario`, `runSimulation`, `isSimulating`, `simStep`, `currentScenario`.

- [ ] **Step 5: Extract CapabilitiesExplorer.jsx**

Move lines 823-899 (capabilities tabbed explorer) into `CapabilitiesExplorer.jsx`. Accept props: `activeCapKey`, `setActiveCapKey`, `currentCapability`.

- [ ] **Step 6: Extract BentoArchitecture.jsx**

Move lines 901+ (bento grid architecture section) into `BentoArchitecture.jsx`.

- [ ] **Step 7: Extract BenchmarksSection.jsx**

Move the benchmarks section into `BenchmarksSection.jsx`. Accept props: `activeBenchmarkKey`, `setActiveBenchmarkKey`, `currentBenchmark`.

- [ ] **Step 8: Extract ComparisonMatrix.jsx**

Move the comparison section into `ComparisonMatrix.jsx`. Accept props: `activeCompareCategory`, `setActiveCompareCategory`, `compareViewMode`, `setCompareViewMode`, `expandedRowIndex`, `setExpandedRowIndex`, `filteredComparisonRows`.

- [ ] **Step 9: Extract LandingFooter.jsx**

Move footer into `LandingFooter.jsx`.

- [ ] **Step 10: Create barrel export `index.js`**

```js
export { default as LandingNavbar } from './LandingNavbar'
export { default as HeroSection } from './HeroSection'
export { default as SimulationSandbox } from './SimulationSandbox'
export { default as CapabilitiesExplorer } from './CapabilitiesExplorer'
export { default as BentoArchitecture } from './BentoArchitecture'
export { default as BenchmarksSection } from './BenchmarksSection'
export { default as ComparisonMatrix } from './ComparisonMatrix'
export { default as LandingFooter } from './LandingFooter'
```

- [ ] **Step 11: Rewrite LandingPage.jsx as slim orchestrator**

~50 lines: import all sub-components, manage state, compose layout.

- [ ] **Step 12: Build and verify**

Run: `cd apps/web && npm run build`
Expected: No errors, all imports resolve.

- [ ] **Step 13: Commit**

```bash
git add apps/web/src/components/landing/ apps/web/src/pages/LandingPage.jsx
git commit -m "refactor: split LandingPage into 8 focused sub-components"
```

---

### Task 5: Per-Component External CSS Files ✅ COMPLETED

**Files:**
- Create: `apps/web/src/styles/landing.css`
- Create: `apps/web/src/styles/app-layout.css`
- Create: `apps/web/src/styles/dashboard.css`
- Create: `apps/web/src/styles/playground.css`
- Create: `apps/web/src/styles/auth.css`
- Create: `apps/web/src/styles/knowledge-bases.css`
- Create: `apps/web/src/styles/evidence.css`
- Create: `apps/web/src/styles/claims.css`
- Create: `apps/web/src/styles/conflicts.css`
- Create: `apps/web/src/styles/experiments.css`
- Create: `apps/web/src/styles/settings.css`
- Create: `apps/web/src/styles/trace.css`
- Create: `apps/web/src/styles/components.css`
- Modify: `apps/web/src/styles/index.css` — add all new imports

**Interfaces:**
- Consumes: Task 1 CSS foundation, Task 4 component structure
- Produces: Complete external CSS for every page and component

- [ ] **Step 1: Create `landing.css`**

Extract all LandingPage-specific styles:
- Hero section gradients, floating cards
- Simulation sandbox window chrome
- Capability explorer tabs
- Benchmark bars with gradient fills
- Comparison matrix card/table styles
- Shimmer text, laser scanline
- Cyber radar screen styles
- Neon verdict card variants
- Mobile drawer animations

Include Apple Design refinements:
- Smooth `cubic-bezier(0.34, 1.56, 0.64, 1)` spring transitions on all interactive elements
- `will-change: transform` on animated elements
- Proper `prefers-reduced-motion` fallbacks for each animation

- [ ] **Step 2: Create `app-layout.css`**

Extract AppLayout-specific styles:
- Sidebar width transitions (collapsed/expanded)
- Mobile drawer slide + rubber-band
- Active nav indicator bar
- Collapsed tooltip positioning
- Telemetry badge styles
- User avatar ring

- [ ] **Step 3: Create `dashboard.css`**

Extract DashboardPage styles:
- Pipeline phase cards
- AreaChart/BarChart custom tooltip
- Metric cards with hover glow
- Auto-refresh toggle
- History window selector

- [ ] **Step 4: Create `playground.css`**

Extract PlaygroundPage styles:
- Query input area
- Streaming trace event rows
- Tab navigation (Answer/Claims/Evidence/Trace)
- SSE connection status indicator
- Copy-to-clipboard feedback
- Knowledge base selector dropdown

- [ ] **Step 5: Create `auth.css`**

Extract LoginPage + RegisterPage styles:
- Form card glassmorphism
- Input field focus states (Apple Design: immediate visual response)
- Submit button gradient + hover
- Error message styling
- Brand logo display

- [ ] **Step 6: Create remaining page CSS files**

`knowledge-bases.css`, `evidence.css`, `claims.css`, `conflicts.css`, `experiments.css`, `settings.css`, `trace.css` — extract and refine styles for each page.

- [ ] **Step 7: Create `components.css`**

Shared workbench component styles:
- ReliabilityBadge variants (high/medium/low)
- ClaimInspector layout
- EvidenceViewer citation cards
- ExecutionTrace timeline
- PipelineTelemetryHUD
- FormattedAnswer markdown rendering

- [ ] **Step 8: Update `styles/index.css` with all imports**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import './typography.css';
@import './animations.css';
@import './materials.css';
@import './landing.css';
@import './app-layout.css';
@import './dashboard.css';
@import './playground.css';
@import './auth.css';
@import './knowledge-bases.css';
@import './evidence.css';
@import './claims.css';
@import './conflicts.css';
@import './experiments.css';
@import './settings.css';
@import './trace.css';
@import './components.css';

@layer base { /* base resets */ }
::selection { /* selection styles */ }
```

- [ ] **Step 9: Remove inline Tailwind classes that are now in external CSS**

Systematically go through each page/component and replace verbose inline Tailwind class strings with the corresponding external CSS class. Focus on:
- Complex multi-class patterns (glass cards, buttons, badges)
- Repeated patterns across components
- Keep simple utility classes (flex, p-4, text-xs) inline

- [ ] **Step 10: Build and verify**

Run: `cd apps/web && npm run build`
Expected: Successful build, smaller bundle (more CSS in external files).

- [ ] **Step 11: Commit**

```bash
git add apps/web/src/styles/
git commit -m "feat(css): add per-component external CSS files for all pages and components"
```

---

### Task 6: Apple Design Motion & Interaction Polish ✅ COMPLETED

**Files:**
- Modify: All component JSX files
- Modify: `apps/web/src/styles/animations.css`
- Modify: `apps/web/src/styles/materials.css`

**Interfaces:**
- Consumes: Tasks 1-5 (CSS foundation + component structure)
- Produces: Fluid, interruptible, velocity-aware interactions across the entire app

- [ ] **Step 1: Add spring transitions to all interactive elements**

Replace CSS `transition-all duration-200` with Apple Design spring curves:
```css
/* Spring transition for interactive elements */
.spring-interactive {
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1),
              background-color 0.15s ease,
              border-color 0.15s ease,
              box-shadow 0.2s ease;
}
```

Apply to: buttons, cards, nav links, inputs, toggles.

- [ ] **Step 2: Fix button press feedback (Apple Design: respond on pointer-down)**

All buttons should have instant `:active` response:
```css
.btn-primary:active,
.btn-secondary:active {
  transform: scale(0.97);
  transition: transform 80ms ease-out;
}
```

- [ ] **Step 3: Add translucent nav bars with scroll-under effect**

Update `.glass-nav` to have content scroll underneath (Apple Design: translucent layers, not opaque bars):
```css
.glass-nav {
  position: sticky;
  top: 0;
  z-index: 40;
  background: rgba(4, 7, 17, 0.72);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
}
```

- [ ] **Step 4: Add reduced-motion graceful fallbacks**

Ensure every animated element has a CSS fallback:
```css
@media (prefers-reduced-motion: reduce) {
  .spring-interactive { transition: none; }
  .glass-card { transform: none !important; }
}
```

- [ ] **Step 5: Add haptic-style visual feedback to key actions**

For the Playground "Run Analysis" button and similar CTAs, add a brief scale pulse:
```css
.action-feedback:active {
  transform: scale(0.95);
  transition: transform 60ms ease-out;
}
.action-feedback:active ~ .action-feedback-pulse {
  animation: actionPulse 0.3s ease-out;
}
```

- [ ] **Step 6: Build and verify**

Run: `cd apps/web && npm run build`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(motion): apply Apple Design spring interactions, press feedback, translucent materials"
```

---

### Task 7: Responsive Design Audit & Fixes ✅ COMPLETED

**Files:**
- Modify: All page JSX files
- Modify: Relevant CSS files

**Interfaces:**
- Consumes: Tasks 1-6
- Produces: Pixel-perfect responsive behavior across mobile (375px), tablet (768px), desktop (1280px+)

- [ ] **Step 1: Test all pages at mobile breakpoint (375px)**

Audit each page for:
- Overflow issues (horizontal scroll)
- Touch targets < 44px (Apple HIG minimum)
- Text too small to read
- Sidebar behavior on mobile

- [ ] **Step 2: Fix LandingPage mobile responsiveness**

- Hero headline: ensure `text-3xl` on mobile, not `text-7xl`
- Metrics ribbon: stack to 2x2 grid on mobile
- Floating cards: hide on xl only (already done)
- Simulation sandbox: horizontal scroll for code blocks

- [ ] **Step 3: Fix AppLayout mobile sidebar**

- Ensure mobile drawer overlay covers full screen
- Touch-friendly nav items (min 44px height)
- Smooth drawer close on swipe

- [ ] **Step 4: Fix DashboardPage responsive grid**

- Pipeline phases: stack on mobile, grid on desktop
- Charts: ensure `ResponsiveContainer` works at all widths
- Metric cards: responsive grid

- [ ] **Step 5: Fix PlaygroundPage responsive layout**

- Input area: full-width on mobile
- Results tabs: horizontal scroll on mobile
- Trace events: no overflow

- [ ] **Step 6: Fix all other pages for mobile**

LoginPage, RegisterPage, KnowledgeBasesPage, EvidencePage, ClaimsPage, ConflictsPage, ExperimentsPage, SettingsPage, TracePage.

- [ ] **Step 7: Add viewport meta tag refinements**

Ensure `viewport-fit=cover` (already present) and safe area insets for notched devices:
```css
body {
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
  padding-bottom: env(safe-area-inset-bottom);
}
```

- [ ] **Step 8: Build and verify**

Run: `cd apps/web && npm run build`
Manual test at 375px, 768px, 1280px widths.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "fix(responsive): audit and fix all pages for mobile/tablet/desktop breakpoints"
```

---

### Task 8: Performance Optimization ✅ COMPLETED

**Files:**
- Modify: Various component files
- Modify: `apps/web/vite.config.js` (if needed)
- Modify: `apps/web/src/styles/animations.css`

**Interfaces:**
- Consumes: Tasks 1-7
- Produces: Optimized bundle, smooth 60fps animations, fast initial load

- [ ] **Step 1: Add React.memo to frequently re-rendered components**

Identify and wrap with `React.memo`:
- `ReliabilityBadge`
- `ClaimInspector`
- `EvidenceViewer`
- `SidebarLink` (in AppLayout)
- All landing sub-components

- [ ] **Step 2: Optimize Motion imports for tree-shaking**

Check that all `motion/react` imports are from the correct path and allow tree-shaking. Remove any unused motion imports.

- [ ] **Step 3: Add `will-change` hints for imminent animations**

```css
.will-animate-transform {
  will-change: transform;
}
.will-animate-opacity {
  will-change: opacity;
}
```

Apply to: sidebar, mobile drawer, floating cards, simulation steps.

- [ ] **Step 4: Optimize CSS delivery**

The external CSS files should be loaded in this order for optimal rendering:
1. `typography.css` (content needs font metrics)
2. `materials.css` (background/blur needs to paint early)
3. `animations.css` (keyframes should be defined before use)
4. Page-specific CSS files

- [ ] **Step 5: Lazy-load heavy chart components**

Wrap Recharts components in `React.lazy()` for DashboardPage:
```jsx
const AreaChart = React.lazy(() => import('recharts').then(m => ({ default: m.AreaChart })))
```

- [ ] **Step 6: Remove unused CSS classes**

Audit all CSS files and remove any classes not referenced in JSX.

- [ ] **Step 7: Build and verify bundle size**

Run: `cd apps/web && npm run build`
Compare bundle size before/after.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "perf: optimize React.memo, CSS delivery, lazy-loading, bundle size"
```

---

### Task 9: Final Polish & Integration Testing ✅ COMPLETED

**Files:**
- All files touched in previous tasks

**Interfaces:**
- Consumes: Tasks 1-8
- Produces: Production-ready, ultra-premium frontend

- [ ] **Step 1: Full build verification**

```bash
cd apps/web && npm run build
```

- [ ] **Step 2: Visual regression test at all breakpoints**

Open the built app and manually verify:
- Landing page at 375px, 768px, 1280px, 1920px
- Login/Register pages
- Dashboard with charts
- Playground with query execution
- All other pages

- [ ] **Step 3: Animation quality check**

Verify:
- All spring transitions feel natural (no jank)
- Reduced motion mode works correctly
- Translucent surfaces degrade properly
- Border beam animation is smooth
- Floating cards animate smoothly

- [ ] **Step 4: Accessibility check**

- Tab navigation works through all interactive elements
- Focus rings visible (primary-400 color)
- Color contrast meets WCAG AA
- Screen reader can navigate all sections

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final polish and integration verification"
```

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-04-trustrag-ultra-premium-frontend.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
