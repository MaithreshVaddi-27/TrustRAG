# TrustRAG — Re-deep UI/UX audit (25 Nov 2026)

**Scope:** all routes (landing, auth, 404, and the full authenticated workbench).
**Direction:** keep and elevate the existing **Obsidian / Chrome Silver / Laser
Crimson** dark-luxury system; world = registration press / proof lab; signature =
registration seal. No new identity, no new dependency, no invented claim.
**Status:** audit only — no UI code changed.

This supersedes neither prior document; it is a verification pass on top of
`UI_DEEP_AUDIT_2026-11-25.md` and `UI_REVISED_PLAN_2026-11-25.md`, both of which
claimed all phases complete. The question here is whether that claim still holds
and what remains before the site reads as a deliberately designed product rather
than a well-set document.

---

## 1. Method and evidence

Read: `apps/web/DESIGN.md`, `docs/design/dark-luxury/*`, both prior design docs,
all landing components and their style sheets, all token files, `animations.css`,
`base.css`, `materials.css`, `utilities.css`, `loaders.css`, the landing hooks,
the app shell/layouts, every route component, the workbench components and their
sheets, and the auth/404 components. Two independent read-only audits were run
in parallel (landing + foundation; app routes + auth) and their findings are
reconciled below.

Local gates, run from `apps/web`:

| Gate | Result |
|---|---|
| `npm run lint` | clean, 0 warnings |
| `npm test -- --run` | 18 files, 84/84 tests pass |
| `npm run build` | succeeds, **zero CSS warnings** |
| `python scripts/serve.py doctor` | all checks PASS |
| `python scripts/serve.py serve --detach` | mongodb / ollama / backend / frontend UP |

Live pass with **Brave DevTools MCP** (remote debugging) against
`http://127.0.0.1:5173` at **1440×900**, **390×844 (DPR 2, touch)**, and
**1440×900 with `prefers-reduced-motion: reduce`**, on `/`, `/login` (isolated
browser context, cleared session), `/register` (redirects to `/dashboard` when
authenticated), `/dashboard`, `/playground`, `/knowledge-bases`, `/evidence`,
`/claims`, `/conflicts`, `/settings`, `/does-not-exist`. Auth pages were checked
both with a cleared session and with the existing local session.

Lighthouse (desktop, navigation, landing): **Accessibility 100, Best Practices
100, SEO 100, Agentic Browsing 100; 59 audits passed, 0 failed.**

Console: **no error, warning, or issue messages** on any inspected route.

Screenshots: `/private/var/folders/47/cg6bqvzs45s_np6jssyms5cr0000gn/T/opencode/reaudit-*.png`.
Lighthouse reports: `…/lighthouse-reaudit/report.{json,html}`.

---

## 2. Verified good — do not regress

- **The prior Phase 0/1/2 work is genuinely on disk, not just documented.**
  Invalid `--spring-*` tokens and the stale `lib/motion.js` comment are gone
  (`tokens/motion.css:11-29`); all five banned keyframes are gone
  (`animations.css`); every alpha literal is owned by `tokens/color.css:58-186`
  (zero `rgba(...)` in component/landing/app sheets); shell meta text is 12px in
  nine places (`app/shell.css`); `:active` press scale is scoped to controls
  (`animations.css:15-24`); the 404 has a `<main>` (`NotFoundPage.jsx:6`).
- **State motion is real and consumed.** Verdict settle, claim stagger, trace
  enter and results seal are all keyframed and applied with remount keys
  (`animations.css:41-82`, `ReliabilityBadge.jsx:62,65,101,103`,
  `ClaimInspector.jsx:189`, `ExecutionTrace.jsx:68`, `ResultsPanel.jsx:126-130`);
  all four exist only under `prefers-reduced-motion: no-preference`.
- **Live structural health.** Every inspected route has exactly one `h1` and one
  `main`, `scrollWidth === clientWidth` at both 1440 and 390, no text below 12px
  in the landing DOM, no gradient text, no colour blobs, no emoji-as-icon, no
  `transition-all`, and **no infinite animations after load settles**
  (dashboard and playground: `infinite: 0` once data resolves).
- **Landing reveal is safe.** Six `.lx-reveal--pending` blocks are opacity 0
  until scrolled into view; under `prefers-reduced-motion: reduce` they are all
  visible (`hiddenElements: []`, zero keyframe animations — only transitions).
  A full-page screenshot taken without scrolling therefore shows blank bands;
  that is a capture artifact, not dead layout. Users who scroll see the content.
- **Auth and workbench are restrained and professional.** The seal sits in the
  auth card header (`AuthLayout.jsx:36-39`); the dashboard is a real instrument
  with one crimson signal, measured figures and tabular numbers; mobile
  navigation collapses cleanly.
- **Palette discipline is real.** No raw colour outside the token layer except
  one documented case (`TrustRagLogo.jsx:37-43`, the brand mark itself) and a
  few inline style colours in settings/query telemetry.

The failure mode is still the opposite of generic slop: the site is honest,
quiet and exact. What is missing is *completion and composition* — the authored
moments are half-built, off-system in the states users see when things go wrong,
and absent on mobile.

---

## 3. Top three material findings (ordered by user impact)

### 1. The signature moment is incomplete on desktop and invisible on mobile

The plan promised a hero ledger that settles 12px with a 60ms record stagger and
a single light sweep across the seal, and a scroll-linked pipeline sweep that
carries the "one loop, six stages" story.

Evidence:
- The hero preview reuses the generic 14px `.lx-enter` and its records have no
  entrance (`HeroSection.jsx:59,68-70`; `utilities.css:289-298`). No seal sweep
  exists (`hero.css:57-85`). The 8px parallax promise is actually 6px
  (`hero.css:50-54`) and the plan says 8px — a doc/code drift.
- The pipeline sweep and connectors are both hidden below 900px
  (`components/pipeline.css:190-194,207-211`), so at 390px the product's one
  authored journey is only text. Verified live: the 390px screenshot shows no
  connector or progress line.
- The verdict on the simulation band has no alignment animation of its own
  (`Verdict.jsx:30-34`); the row/outcome stagger exists (`ledger.css:82-91,
  209-234`) but the resolving beat isn't the verdict itself.

Impact: the "restrained luxury" brief is spent on restraint only. The one thing
that should be remembered never fully lands, and most mobile visitors never see
it at all.

Smallest correction: finish the three authored beats within the existing tokens
— record settle with `--record-index`, a vertical progress hairline on mobile,
and reuse `lx-verdict-settle` on the contradicted verdict. No new effect type.

### 2. Loading and error states are the last off-system surface

Evidence:
- Three infinite breathing loops remain: `.orb-breathe 1.6s … infinite` with a
  radial-gradient crimson core and `box-shadow` glow (`loaders.css:27-64`),
  `.skel-breathe 2.4s … infinite` (`loaders.css:70-87`), and `.lx-breathe
  2.4s … infinite` (`surfaces.css:648,752` — the skeleton block is defined
  twice with different declarations). `.lx-live-dot` adds a 2.4s pulse and a
  3px halo (`utilities.css:151-175`).
- Live: dashboard/settings showed 28–30 infinite animations (`spin`,
  `lx-breathe`, `skel-breathe`) while loading; they drop to 0 once data settles,
  so this is transient — but it is the state a user sees first.
- Generic `animate-spin` `Loader2` appears in ~13 places (auth, document, trace,
  dashboard, cluster/hardware panels, document table, create form); auth renders
  two spinners at once (`LoginPage.jsx:53,108`; `RegisterPage.jsx:69,181`).
- `ErrorBoundary.jsx:35-58` is fully off-system (`rounded-2xl`, `crimson-950/30`,
  `text-slate-400`, `bg-surface-800`, `text-xs`, `<h2>` with no `h1`, two
  unstyled buttons) and replaces the entire route. `SettingsPage.jsx:138-140`
  renders `providersError` as a bare `<p className="lx-micro">` with no
  `role="alert"` and no retry; `ClusterPanel.jsx:54-63` communicates health
  failure as the words "Unknown"/"Disconnected" in a `<dd>`.
- Smaller gaps: Trace empty state is a bare sentence (`ExecutionTrace.jsx:41-45`);
  Document has no loading announcement (`DocumentPage.jsx:91-96,184`);
  `ErrorDisplay.jsx:20-27` offers dismiss but no retry.

Impact: everything designed is excellent; everything *broken or pending* is
generic. For a product whose entire promise is trust before publication, the
recovery surface is where the design should be strongest.

Smallest correction: one loader vocabulary (`ThinkingOrbs` everywhere), retire
the idle loops, and bring `ErrorBoundary` / settings / cluster errors onto the
existing `lx-message lx-message--alarm` + Retry + `role="alert"` pattern.

### 3. The close and the benchmark lead are template-shaped

Evidence:
- `LandingCTA.jsx:12-27` + `components/footer.css:76-109`: centred headline,
  centred lede, centred button row inside a card — the standard SaaS closer.
  Visually confirmed at 1440 (`reaudit-landing-6780.png`).
- `data/benchmarks.js:60,128,161` + `components/benchmarks.css:78-101`: the band
  is three quiet bar tables with a finite bar grow; there is no single lead
  chart, so the section reads as a data dump (the original audit's F7).
- Leftover assembly seams: dead `.bg-cyber-grid` (`landing.css:6-11`), dead
  `.stream-beam` rule (`loaders.css:89-94`), duplicate conflicting scrollbar
  (`base.css:91-108` vs `materials.css:13-30`), unused `.lx-record__evidence*`
  (`hero.css:271-290`), unused `.lx-band__more*` (`section.css:44-64`), unused
  `--reveal-delay` (`utilities.css:242`).

Impact: a visitor who scrolls to the end gets a generic invitation instead of
the product's own closing gesture. This is what keeps the site in the "well-set
document" category despite strong parts.

Smallest correction: de-centre the CTA into a two-column close with a finite
top-rule draw, and let one benchmark chart lead while the other figures stay
quiet. Same words, same numbers, same section order.

---

## 4. Full evidence register

### P1 — defects and rule violations (fix before styling)

| ID | Finding | Evidence |
|---|---|---|
| D1 | Hardcoded model IDs in JSX violate `CONTRIBUTING.md` ("No model IDs in code. All model identifiers go in `apps/api/config/models.yaml`"). | `Navbar.jsx:59,167`; `EngineTelemetry.jsx:48,115`; `PipelineTelemetryHUD.jsx:17-19`. (Provenance comments in landing data are descriptive of measured runs, not configuration, and may stay.) |
| D2 | Model-generated markdown `#` becomes a literal `<h1>`, so an answer can inject a second `h1` on `/playground`. Static structure is fine; live rendering is not guaranteed. | `FormattedAnswer.jsx:21`, rendered at `AnswerTab.jsx:137`. |
| D3 | Two `<div>`s carry `aria-label` without a role; generic element labels are not reliably exposed. `CapabilitiesExplorer.jsx:75` is a focusable `<pre>` with no accessible name. | `HeroSection.jsx:59`; `PipelineDiagram.jsx:62`; `CapabilitiesExplorer.jsx:75`. |
| D4 | Landing mobile drawer has Escape and scroll lock but no focus move, trap, or restore (the app drawer has all three). | `LandingNavbar.jsx:26-38,83-122`. |
| D5 | Docs ↔ code drift: parallax 8px vs 6px; pipeline CSS still calls the sweep one-shot; `loaders.css` import-order and `.border-beam` claims are false; footer still mentions a removed competitor column; verification doc says 82 tests vs 84. | `UI_REVISED_PLAN_2026-11-25.md:64`; `pipeline.css:4-6`; `loaders.css:9,89-94`; `data/footer.js:12`; `08-verification.md:100`. |

### P2 — craft debt (design-system drift)

| ID | Finding | Evidence |
|---|---|---|
| C1 | 10–11px text via Tailwind arbitrary values despite the 12px token floor. | `EvidenceViewer.jsx:154`; `ClaimInspector.jsx:135`; `EmptyState.jsx:123`; `RunButton.jsx:28,36`; `AIEngineSelector.jsx:118`; `ReliabilityAreaChart.jsx:211`. Live: `evidence` 2 elements, `claims` 4 at 10px. |
| C2 | Touch floor below 44px: `.lx-chip` as quick-prompt button (~20px); icon buttons overridden to 28px/32px; coarse-pointer rescue covers nav rows only. Landing has two 17px inline links. | `QueryInput.jsx:85-96`; `surfaces.css:151-164`; `shell.css:213-219,549-554`; landing audit (390px). |
| C3 | Off-grid radii and spacing, and raw hex in the brand mark/inline styles. | `section.css:85` (4px); `benchmarks.css:63,72` (3px); `loaders.css:30` (9999px); `hero.css:229,395`; `nav.css:44,167`; `TrustRagLogo.jsx:37-43`; `ClusterPanel.jsx:56-60`; `QueryInput.jsx:59`. |
| C4 | Two inline "Read the methodology" links are 147×17px — acceptable as inline text but not as touch targets on mobile. | Live 390px measurement; landing audit. |
| C5 | `.lx-skeleton` duplicated with different declarations; `.lx-live-dot` has no JSX consumer; redundant `.lx-icon-btn:active` scale. | `surfaces.css:645-666,748-760`; `utilities.css:151-175`; `shell.css:234-236`. |

### P3 — experience gaps

| ID | Finding | Evidence |
|---|---|---|
| E1 | Settings and cluster health have the weakest recovery states; Trace/Document have partial empty/loading states. | `SettingsPage.jsx:138-140`; `ClusterPanel.jsx:54-63`; `ExecutionTrace.jsx:41-45`; `DocumentPage.jsx:91-96,184`. |
| E2 | Results header renders the same `ReliabilityBadge` twice, splitting the one bright moment. | `ResultsPanel.jsx:122-125,174-180`. |
| E3 | The benchmark band has no single lead chart; the CTA is centred-template. | `benchmarks.css:78-101`; `footer.css:76-109`. |

---

## 5. Direction (unchanged, per unslop)

- **Product.** TrustRAG is a claim-level verification workbench: it splits an
  answer into atomic claims, checks each against cited evidence, and shows the
  audit trail — for teams who must trust a RAG answer before a reader finds the gap.
- **Character.** exact, instrumented, quiet.
- **World.** a registration press / proof lab: alignment targets, registration
  seals, proof ledgers, measured figures.
- **Moments.** (1) the hero ledger, where one crimson contradiction is the only
  bright thing; (2) the pipeline sweep, the authored journey through six stages;
  (3) a claim-and-evidence alignment in the workbench, where a verdict settles
  into registration with its source. One bright element per surface.
- **Signature.** the registration seal — opposing corner brackets and one
  crimson point — extended consistently to the alignment moment. One detail.

**Motion policy (restrained luxury).** House curve `cubic-bezier(0.16, 1, 0.3, 1)`
with 80/150/220/320ms; one entrance, one stagger, one authored sweep. Effects
must be meaningful, finite, interruptible and quiet. No idle loops, no breathing,
no gradient text, no cursor spotlight, no new runtime dependency, no font payload.
`prefers-reduced-motion: reduce` collapses everything to a static state or short
cross-fade; `prefers-reduced-transparency: reduce` flattens glass.

---

## 6. Constraints honoured

No invented claims or numbers; no change to section order, copy, brand mark,
measured data, or product scope; no new dependency; no generated image assets;
no code changed in this pass. The next step is a written implementation plan,
then explicit approval before any UI edit.
