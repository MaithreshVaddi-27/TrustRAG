# TrustRAG — Re-deep implementation plan (25 Nov 2026)

Companion to `UI_RE_DEEP_AUDIT_2026-11-25.md`. It keeps the direction of the
earlier revised plan, which was removed in the documentation cleanup (its
history remains in git). Evidence and finding IDs (D1–D5, C1–C5, E1–E3, F1–F3
in the audit) are referenced below.

**Status: IMPLEMENTED (commit `1d9405e`).** The approval block at the end of
this document records the choices that were applied; see the implementation log
for what shipped and the verification results.
Direction chosen by the user: keep and elevate the existing dark-luxury system;
all routes in scope; restrained-luxury motion; audit + plan → approval → build;
full local verification permitted.

---

## Guardrails (all phases)

1. **Meaning** — an effect expresses alignment, verification, progression or state.
   Never atmosphere for its own sake.
2. **Finite** — plays once or tracks scroll/pointer; no idle loops, no
   `animate-pulse`, no breathing.
3. **Interruptible** — pointer/scroll-driven motion follows input via rAF and
   blends back to rest; never locks input.
4. **Quiet** — inside obsidian/silver/crimson; crimson stays a signal. No gradient
   text, emoji, font payload, or new runtime dependency.
5. `prefers-reduced-motion: reduce` → static state or short cross-fade;
   `prefers-reduced-transparency: reduce` → solid surfaces.
6. Keep copy, measured numbers, section order, brand mark, and data sources
   verbatim. One concern per change; tests live beside the module.
7. No model IDs in code; no secrets outside the single repo-root `.env`.

---

## Phase 0 — Defects and foundation cleanup (no visual debate)

Goal: zero warnings, zero rule violations, no dead assembly seams.

1. **D1** — remove hardcoded model IDs from `Navbar.jsx:59,167`,
   `EngineTelemetry.jsx:48,115`, `PipelineTelemetryHUD.jsx:17-19`; read from the
   existing provider/config data and use a neutral fallback. Keep provenance
   comments in landing data (they describe measured runs, not configuration).
2. **D2** — demote `FormattedAnswer.jsx:21` generated `#` from `<h1>` to `<h2>` so
   an answer cannot break the one-`h1` contract. Add a regression test.
3. **D3/D4** — give `CapabilitiesExplorer.jsx:75` an accessible name; add `role`
   and name to the label-only divs in `HeroSection.jsx:59` / `PipelineDiagram.jsx:62`;
   add focus move, trap and restore to `LandingNavbar.jsx:26-38,83-122`.
4. **D5 + dead code** — fix the doc drift (8px→6px or change code to 8px, pick one
   and make both agree); correct `pipeline.css:4-6` to say scroll-linked; remove the
   false `loaders.css:9,89-94` rule; update `data/footer.js:12` and
   `08-verification.md:100`. Delete `.bg-cyber-grid`, `.lx-record__evidence*`,
   `.lx-band__more*`, unused `--reveal-delay`, the duplicate `materials.css` scrollbar,
   and the second `.lx-skeleton` block.
5. **C3 (partial)** — replace off-grid radii at `section.css:85`, `benchmarks.css:63,72`,
   `loaders.css:30` with `radius.css` tokens; keep the brand mark's own colours in
   `TrustRagLogo.jsx` documented as the one intentional exception.

**Gate:** `npm run lint` clean, `npm test -- --run` 84+/84+, `npm run build` with
zero warnings; `grep` finds no `--spring-*`, no banned keyframes, no `rgba()` in
component sheets, no model-ID literal in app JSX.

---

## Phase 1 — Landing showcase (the visible transformation)

No new copy, numbers, sections, dependencies, or images.

1. **Finish the hero object (finding 1).** In `HeroSection.jsx:68-70` set
   `--record-index: index`; add a finite `lx-record-settle` keyframe to
   `animations.css` (12px rise, opacity, 480ms, house curve, 60ms stagger), apply
   it to `.lx-record` only under `prefers-reduced-motion: no-preference`, remove the
   generic `lx-enter` from the preview wrapper, and add the matching `reduce`
   override with the `nth-child` specificity used at `hero.css:365-379`. A single
   bounded light sweep crosses the seal once on load (`hero.css:57-85`), opacity
   only, `prefers-reduced-motion` resolves it to a static seal.
2. **Keep the signature on mobile (finding 1).** In `pipeline.css:190-194`, keep
   the connector visible below 900px as a vertical progress hairline driven by the
   existing `--pipeline-progress`; hide only the horizontal sweep. Stage activation
   already works (`PipelineDiagram.jsx:81`). Verify at 390px that the line and the
   active stage are both visible.
3. **Let the verdict resolve (finding 1).** Reuse `lx-verdict-settle`
   (`animations.css:41-44`) on the contradicted verdict in `ledger.css` under
   `no-preference`, ~320ms at 180ms delay. No new colour; the crimson contradiction
   stays the only bright thing.
4. **De-centre the close (finding 3).** In `footer.css:76-109` drop the centred
   text/auto margins; at ≥1024px use a two-column grid (statement left, actions
   right, aligned bottom) keeping `surface-panel`, top rule, radius and padding.
   Add one finite top-rule draw. Same words, same two buttons.
5. **One lead benchmark chart (finding 3).** In `benchmarks.css:78-101` / `data/benchmarks.js`
   give the reliability row the accent, a drawn line and the largest footprint;
   demote the other two tables to quiet lists. No new figures.
6. **Nav material** — keep `nav.css:7-24` as is; verify `prefers-reduced-transparency`
   flattening still holds after the above changes.

**Review gate:** show landing at **1440 / 1024 / 390** and with reduced motion
before touching any app route. Confirm the three authored beats are visible and
that no infinite animation exists after load.

---

## Phase 2 — App routes and auth (after landing review)

1. **One loader vocabulary (finding 2).** Replace every `animate-spin` `Loader2`
   with `ThinkingOrbs size="sm"` (auth, document, trace, dashboard, cluster,
   hardware, document table/row, create form); drop the duplicate auth spinner.
2. **Make loading finite (finding 2).** Retire `orb-breathe`, `skel-breathe`,
   `lx-breathe` and the `.lx-live-dot` pulse in favour of static placeholders or
   the existing one-shot settle; keep reduced-motion paths.
3. **Bring recovery onto the house pattern (finding 2, E1).**
   `ErrorBoundary.jsx:35-58` gets `lx-message lx-message--alarm`, `role="alert"`,
   a visible `h1`, and one primary + one secondary control. `SettingsPage.jsx:138-140`
   and `ClusterPanel.jsx:54-63` use the same pattern with Retry. Trace and Document
   empty/loading states adopt `AsyncState` conventions.
4. **One bright moment in results (E2).** Keep one `ReliabilityBadge` in
   `ResultsPanel.jsx`; let the seal + verdict settle together as a single 60ms
   alignment event.
5. **Type and touch floor (C1/C2).** Replace all `text-[0.625rem]` /
   `text-[0.6875rem]` with `var(--size-micro)` (12px). Stop overriding
   `.lx-icon-btn` below 40px; give `.lx-chip`-as-button a coarse-pointer 44px
   min-height. No layout change on the tokenised scale.

**Gate:** every route has one `h1`/`main`, no overflow, no text <12px, no infinite
animation, focus ring visible, all states reachable and on-brand.

---

## Phase 3 — Verification (same bar as the prior plan)

- `npm run lint && npm test -- --run && npm run build` — zero warnings.
- Brave DevTools MCP sweep at **1440 / 1280 / 1024 / 768 / 390 / 320** on all
  routes: overflow, invisible text, focus ring, target size, console, reduced
  motion, reduced transparency.
- Contrast re-measured on rendered surfaces (AA: 4.5:1 body, 3:1 large).
- Lighthouse desktop + mobile on landing (target: 100/100/100/100 as measured today).
- One real analysis run to see the results seal in situ (Ollama is up locally).

---

## Watch-outs

- `prefers-reduced-motion` overrides must keep the `nth-child` specificity used
  for the seal rules (`hero.css:365-375`) or they silently lose.
- `animations.css` is imported before surfaces/components
  (`styles/index.css:17,27`): any new keyframe must be defined in `animations.css`
  or the importing sheet that uses it.
- The pipeline is scroll-linked, not one-shot — keep copy and docs in sync.
- Local test accounts from prior sessions still exist on the local backend;
  clean them if local data needs to be pristine.

---

## Approval block

Before any UI edit, please confirm:

1. **Approve** this plan as written, or name the phases to drop/defer.
2. **Landing review cadence:** pause after Phase 1 for your visual sign-off
   (recommended), or run straight through Phases 1–2.
3. **Parallax value:** align code and docs at **6px** (current code, recommended —
   lower risk) or change to **8px** (the original plan's number).
4. **Infinite loader loops:** remove them (recommended) or keep them as explicit
   "live/system active" indicators in a documented exception.

No code will be changed until you approve.

---

## Implementation log — 25 Nov 2026 (approved, executed)

**Approved defaults:** keep 6px parallax; remove all idle loader loops; run all
phases; full local verification.

- **Phase 0** — model-ID fallbacks removed from `Navbar.jsx`, `EngineTelemetry.jsx`
  and `PipelineTelemetryHUD.jsx`; generated markdown headings demoted one level
  (`FormattedAnswer.jsx`, test updated and a second-h1 regression test added);
  landing drawer now moves, traps and restores focus (`LandingNavbar.jsx`);
  label-only divs given roles and the code block an accessible name; dead CSS
  removed (`.bg-cyber-grid`, `.lx-record__evidence*`, `.lx-band__more*`,
  `.stream-beam`, `.lx-live-dot`, duplicate `.lx-skeleton`, duplicate scrollbar,
  unused `--reveal-delay`); off-grid radii tokenised; doc drift corrected.
- **Phase 1** — hero records settle 12px with a 60ms stagger and a single finite
  seal light sweep; the pipeline progress hairline is now vertical on <900px;
  the contradicted verdict settles once; the CTA is a left/statement + right/
  actions grid with a finite top-rule draw; the first benchmark set leads with
  a stronger rule, taller measure and larger figures.
- **Phase 2** — all generic spinners replaced by `ThinkingOrbs`; idle breathe /
  pulse loops removed (loaders now align or fade in once); `ErrorBoundary`,
  settings provider/cluster errors and playground errors use the house
  `lx-message lx-message--alarm` + Retry pattern; Trace/Document states completed;
  12px type floor and 40px icon buttons / 44px coarse chip targets applied;
  the duplicate results badge removed.

**Verification:** lint clean; 85/85 tests; build with zero warnings; Impeccable
detector returned no findings. Brave DevTools MCP sweep at 1440 and 390 (touch)
plus `prefers-reduced-motion: reduce`: one `h1`/`main` per route, no overflow,
no text <12px, **zero infinite animations after load**, zero keyframes under
reduced motion, no console errors/warnings. Lighthouse desktop **and** mobile:
Accessibility 100 · Best Practices 100 · SEO 100 · Agentic Browsing 100
(59 passed, 0 failed). Screenshots and reports under the session temp folder.

**Watch-outs:** the pipeline is scroll-linked — keep its copy and docs in sync;
reduced-motion overrides must retain the `nth-child` specificity in `hero.css`;
new keyframes belong in `animations.css` (imported before component sheets).

---

## Follow-up verification — 26 Nov 2026

Fresh review of the committed build at **1440 / 1280 / 1024 / 768 / 390 / 320**,
11 routes × 3 newly checked widths (1280 / 768 / 320) = 33 renders, plus a
scroll-through of every landing section:

- 0 navigation failures, 0 horizontal overflow, 0 console errors;
- exactly one `h1` and one `main` on every route, including `/does-not-exist`;
- smallest rendered text 12px on every route;
- reduced motion: 0 running animations, decorative effects resolve to static;
- landing at 1440 and 390 visually reviewed: the hero ledger, six-stage loop,
  simulation tabs and single lead benchmark bar are authored product views,
  not generic filler.

**One new defect found and fixed:** at 768px the dashboard description collapsed
into a one-word-per-line column because the `PageHeader` action group was
`shrink-0`. The header now wraps (`sm:flex-wrap`) and the title group has
`sm:basis-[24rem]`; the description renders in two 480px lines at 768px, with
no regression at 1024 or 1280. Verified by rendered screenshots.

Gates after the fix: lint clean, 85/85 tests, `check:tokens` clean, build with
zero warnings, Impeccable detector `[]`, `ruff check .` clean.

**CI note:** the remaining red job was the compose smoke. The official Qdrant
slim image ships no `curl` or `wget`, so its HTTP healthcheck could never pass;
the API image has `curl` but its healthcheck called `wget`. Both are corrected
in `docker-compose.yml`, which now validates with `docker compose config`.

