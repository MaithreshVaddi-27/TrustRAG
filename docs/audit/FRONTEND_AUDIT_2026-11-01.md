# TrustRAG Frontend Audit Report

## Executive Summary

The TrustRAG React frontend is a well-structured, production-grade application with modern patterns (React 18, Vite, TanStack Query v5, Motion, React Router v7). The codebase demonstrates strong architectural decisions: centralized Axios client with interceptors, custom auth store without external dependencies, SSE stream handling with ticket-based auth, and comprehensive test coverage (33 tests passing).

## Architecture Overview

### Tech Stack
- **Framework**: React 18.3.1 + Vite 6.4.2
- **Routing**: React Router DOM v7.1.5
- **State**: TanStack Query v5 (server) + Custom pub/sub auth store (client)
- **Animation**: Motion (framer-motion v13)
- **Charts**: Recharts v2.15.4
- **HTTP**: Axios v1.7.3
- **Markdown**: React Markdown v10 + remark-gfm
- **Icons**: Lucide React v0.408
- **Testing**: Vitest + React Testing Library + Playwright

### Route Structure (11 routes)
| Route | Protection | Component |
|-------|------------|-----------|
| `/` | Public | LandingPage |
| `/login` | RedirectIfAuth | LoginPage |
| `/register` | RedirectIfAuth | RegisterPage |
| `/dashboard` | RequireAuth | DashboardPage |
| `/playground` | RequireAuth | PlaygroundPage |
| `/knowledge-bases` | RequireAuth | KnowledgeBasesPage |
| `/evidence` | RequireAuth | EvidencePage |
| `/claims` | RequireAuth | ClaimsPage |
| `/conflicts` | RequireAuth | ConflictsPage |
| `/settings` | RequireAuth | SettingsPage |
| `/traces/:id` | RequireAuth | TracePage |
| `*` | Public | NotFoundPage |

### Component Hierarchy
```
App
├── ErrorBoundary
├── QueryClientProvider
├── BrowserRouter
├── MotionProvider
└── AppLayout (sidebar + navbar + content)
    ├── DashboardPage
    ├── PlaygroundPage
    │   ├── QueryPanel (25+ props)
    │   └── ResultsPanel (14 props)
    │       ├── ExecutionTrace
    │       ├── ClaimInspector (memo)
    │       ├── EvidenceViewer (memo)
    │       ├── FormattedAnswer
    │       ├── PipelineTelemetryHUD
    │       └── RecoveryTimeline
    ├── KnowledgeBasesPage
    ├── EvidencePage
    ├── ClaimsPage
    ├── ConflictsPage
    ├── SettingsPage
    ├── TracePage
    └── LandingPage
        ├── LandingNavbar
        ├── HeroSection
        ├── SimulationSandbox
        ├── CapabilitiesExplorer
        ├── BentoArchitecture
        ├── BenchmarksSection
        ├── ComparisonMatrix
        └── LandingFooter
```

---

## Findings

### Critical (Must Fix)

| ID | File | Issue | Impact |
|----|------|-------|--------|
| C1 | `PlaygroundPage.jsx:11-373` | **God component** - 373 lines handling query state, SSE streaming, polling, model selection, KB selection, error handling, and rendering | High - unmaintainable, hard to test, excessive re-renders |
| C2 | `QueryPanel.jsx:17-500` | **Prop drilling** - 25+ props passed from PlaygroundPage; component does KB selection, model selection, web search toggle, query input, presets | High - tight coupling, violates single responsibility |
| C3 | `ResultsPanel.jsx:45-320` | **Excessive props** - 14 props; handles 4 tabs, copy/export, reliability badge, trace events, recovery timeline | High - should be split by tab |
| C4 | `AppLayout.jsx:40-637` | **Monolithic layout** - 637 lines handling sidebar, mobile drawer, navbar, telemetry pills, cursor glow, auth, logout | Medium - hard to navigate, multiple responsibilities |
| C5 | `DashboardPage.jsx:64-728` | **Dashboard god component** - 728 lines with 5 queries, 3 charts, stats computation, skeleton loading, pipeline phases | Medium - should delegate to child components |

### High (Should Fix)

| ID | File | Issue | Impact |
|----|------|-------|--------|
| H1 | `services/api.js` | **Inconsistent error handling** - some services `.then(r => r.data)`, others don't normalize; no retry config | Medium - unpredictable error shapes |
| H2 | `lib/api.js:85-137` | **SSE helper tightly coupled** - `openAnalysisStream` hardcodes terminal events, ticket endpoint path | Medium - hard to test, inflexible |
| H3 | `hooks/useBackendHealth.js` | **No initial probe on mount** - first check deferred to interval, causing UI flash | Medium - UX regression |
| H4 | `components/workbench/ExecutionTrace.jsx` | **Re-renders on every trace event** - no memoization despite `compactTraceEvents` | Medium - performance during streaming |
| H5 | `lib/modelLabels.js` | **Duplicate provider normalization** - logic also in `providerShortLabel` and `shortModelId` | Low - maintenance burden |
| H6 | `components/workbench/ReliabilityBadge.jsx` | **VerdictBadge + ClaimStateBadge alias** - confusing export, same component twice | Low - API confusion |

### Medium (Nice to Fix)

| ID | File | Issue | Impact |
|----|------|-------|--------|
| M1 | Multiple | **No TypeScript** - JSDoc only; no compile-time safety for props/API contracts | Medium - refactor risk |
| M2 | `components/landing/*.jsx` | **6 separate landing components** - each <100 lines; could be sections in one file | Low - file count |
| M3 | `lib/motionConfig.js` | **Only 2 springs** - could add `SPRING_PAGE`, `SPRING_MODAL` for consistency | Low - design system |
| M4 | `components/workbench/EmptyState.jsx` | **Hardcoded feature cards** - not data-driven | Low - extensibility |
| M5 | `pages/PlaygroundPage.test.jsx` | **Only 2 tests** - critical page under-tested | Medium - regression risk |

### Code Duplication

| Pattern | Locations | Fix |
|---------|-----------|-----|
| `normalizeClaimState` | `DashboardPage.jsx`, `ClaimInspector.jsx`, `claimState.js` | ✅ Already centralized in `lib/claimState.js` |
| `isWebSource` | `EvidenceViewer.jsx`, `ClaimInspector.jsx`, `claimState.js` | ✅ Already centralized |
| `providerShortLabel` | `AppLayout.jsx`, `ResultsPanel.jsx`, `modelLabels.js` | ✅ Already centralized |
| `shortModelId` | `QueryPanel.jsx`, `ResultsPanel.jsx`, `modelLabels.js` | ✅ Already centralized |

---

## Refactoring Plan

### Phase 1: Split God Components (High Impact)

#### 1.1 PlaygroundPage → Split into:
- `PlaygroundPage.jsx` (orchestrator, <100 lines)
- `hooks/useAnalysisStream.js` (SSE + polling logic)
- `hooks/useModelSelection.js` (provider/model state)
- `hooks/useKnowledgeBaseSelection.js` (KB state)
- `components/playground/QuerySection.jsx` (query input + presets)
- `components/playground/EngineSection.jsx` (model/embedding selection)
- `components/playground/WebSearchSection.jsx` (web search toggle)

#### 1.2 QueryPanel → Split into:
- `QueryPanel.jsx` (shell, <50 lines)
- `components/playground/KnowledgeBaseSelector.jsx`
- `components/playground/AIEngineSelector.jsx`
- `components/playground/WebSearchToggle.jsx`
- `components/playground/EmbeddingModelDisplay.jsx`
- `components/playground/QueryInput.jsx`
- `components/playground/PresetButtons.jsx`
- `components/playground/RunButton.jsx`

#### 1.3 ResultsPanel → Split by tab:
- `ResultsPanel.jsx` (shell + tabs)
- `components/results/AnswerTab.jsx`
- `components/results/EvidenceTab.jsx`
- `components/results/ClaimsTab.jsx`
- `components/results/TraceTab.jsx`

#### 1.4 AppLayout → Split into:
- `AppLayout.jsx` (shell)
- `components/layout/Sidebar.jsx`
- `components/layout/Navbar.jsx`
- `components/layout/MobileDrawer.jsx`
- `components/layout/EngineTelemetry.jsx`
- `components/layout/UserMenu.jsx`
- `hooks/useSidebar.js`
- `hooks/useCursorGlow.js`

#### 1.5 DashboardPage → Split into:
- `DashboardPage.jsx` (orchestrator)
- `components/dashboard/HeroBanner.jsx`
- `components/dashboard/MetricsGrid.jsx`
- `components/dashboard/ObservabilityBar.jsx`
- `components/dashboard/ReliabilityChart.jsx`
- `components/dashboard/ClaimDistributionChart.jsx`
- `components/dashboard/RecentAnalysesFeed.jsx`
- `components/dashboard/PipelineArchitecture.jsx`

### Phase 2: Extract Custom Hooks (Medium Impact)

| Hook | Extracted From | Responsibility |
|------|----------------|----------------|
| `useAnalysisStream` | PlaygroundPage | SSE connection, polling fallback, final fetch |
| `useModelSelection` | PlaygroundPage | Provider/model state, localStorage sync |
| `useKnowledgeBaseSelection` | PlaygroundPage | KB list, auto-select first, pin mismatch |
| `useBackendHealth` | (exists) | Add initial probe option |
| `useSidebar` | AppLayout | Collapse state, localStorage, animation |
| `useCursorGlow` | AppLayout | Mouse tracking, reduced motion |
| `useAutoRefresh` | DashboardPage | Toggle, interval management |

### Phase 3: API Layer Hardening (Medium Impact)

1. **Standardize service responses** - all services return `r.data`
2. **Add request/response interceptors** for consistent error shape
3. **Extract SSE helper config** - terminal events, endpoints as constants
4. **Add retry with exponential backoff** for GET queries

### Phase 4: TypeScript Migration (Long-term)

1. Add `tsconfig.json` with strict mode
2. Rename `.jsx` → `.tsx` incrementally
3. Add types for API responses, component props, store state

### Phase 5: Testing Expansion (Ongoing)

| Target | Current | Target |
|--------|---------|--------|
| PlaygroundPage | 2 tests | 15+ tests |
| QueryPanel | 0 tests | 10+ tests |
| ResultsPanel | 0 tests | 10+ tests |
| ClaimInspector | 1 test | 5+ tests |
| EvidenceViewer | 0 tests | 5+ tests |
| AppLayout | 0 tests | 5+ tests |

---

## Implementation Priority

```
Week 1: Phase 1.1-1.3 (Playground, QueryPanel, ResultsPanel split)
Week 2: Phase 1.4-1.5 (AppLayout, DashboardPage split)
Week 3: Phase 2 (Custom hooks extraction)
Week 4: Phase 3 (API layer hardening) + Phase 5 (test expansion)
Ongoing: Phase 4 (TypeScript migration)
```

---

## Metrics to Track

| Metric | Current | Target |
|--------|---------|--------|
| Largest component (lines) | 728 (DashboardPage) | <200 |
| Average component size | ~180 | <100 |
| Props per component (max) | 25 (QueryPanel) | <10 |
| Test coverage (lines) | ~35% | >80% |
| Re-renders during streaming | High (no memo) | Minimal (memo + selectors) |
| Bundle size (gzipped) | ~180KB | <150KB |

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Split PlaygroundPage | High - core user flow | Test each hook independently; E2E test full flow |
| Split QueryPanel | Medium - many props | Keep same prop interface initially; verify in Storybook |
| Extract hooks | Low - pure logic | Unit test hooks in isolation |
| API layer changes | Medium - all calls affected | Add integration tests; feature flag rollout |

---

## Documentation Updates Needed

1. `README.md` - Add architecture diagram, component hierarchy, development workflow
2. `docs/COMPONENT_GUIDE.md` - Component patterns, hooks, state management
3. `docs/API_CONTRACTS.md` - Service methods, response shapes, error codes
4. `docs/TESTING_GUIDE.md` - Unit/E2E patterns, mocking strategies
5. `docs/MOTION_GUIDE.md` - Spring configs, reduced motion, performance tips