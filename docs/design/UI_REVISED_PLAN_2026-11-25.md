# TrustRAG — Revised implementation plan (25 Nov 2026)

Supersedes the plan in `UI_DEEP_AUDIT_2026-11-25.md` §5. The audit findings and
verified-good baseline still stand.

**Revisions requested:** all four — defects first; landing page as the first
showcase; visibly higher visual ambition; motion prohibitions loosened for a
luxury feel; app-route craft deferred until the landing result is reviewed.

---

## What changed from the original plan

| Axis | Original | Revised |
|---|---|---|
| Order | all phases together | **P0 → P1 → landing → review → app routes** |
| Visual ambition | "one quiet hierarchy move per band" | a composed **proof-lab** scene per key band; hero becomes one authored object |
| Motion | only one-shot entrance + sweep | scroll-linked progression, finite light sweeps, subtle depth parallax, state transitions |
| Effects | glows/glass/parallax banned | **allowed when they carry brand meaning**; still bounded by quality guardrails |

### Quality guardrails that replace the blanket bans

Loosened does not mean unconstrained. Every effect must pass all four:

1. **Meaning** — it expresses alignment, verification, progression or state.
   Never atmosphere for its own sake.
2. **Finite** — it plays once or tracks scroll/pointer; no idle loops, no
   `animate-pulse`, no breathing.
3. **Interruptible** — pointer/scroll-driven motion follows input via rAF and
   blends back to rest; it never locks input during a transition.
4. **Quiet** — inside the obsidian/silver/crimson palette; crimson stays a
   signal (verdict, selection, live, focus, one focal action). No gradient
   text, no emoji, no font payload, no new runtime dependency.

`prefers-reduced-motion: reduce` collapses every new effect to a static state
or a short cross-fade. `prefers-reduced-transparency` makes glass surfaces
solid. Contrast targets (4.5:1 body / 3:1 large) remain unchanged.

---

## Phase 0 — Defects (do first, no visual debate)

1. `tokens/motion.css` — delete the four invalid `--spring-*` declarations and
   the stale `lib/motion.js` comment. `animations.css` — delete five unused
   keyframes (`fadeIn`, `slideUp`, `haloPulse`, `rotateBeam`, `scanlineMove`).
   Gate: `npm run build` with **zero warnings**.
2. `NotFoundPage.jsx` — wrap content in `<main>`; add the route to the
   verification sweep.
3. `tokens/color.css` — promote the repeated `rgba()` overlays to named tokens;
   substitute in `hero.css`, `nav.css`, `matrix.css`, `shell.css`,
   `ledger.css`, `surfaces.css`, `utilities.css`.
4. Shell meta text 11px → 12px; scope `:active` press scale to controls only.

## Phase 1 — Landing showcase (the visible transformation)

Direction stays **Obsidian / Chrome Silver / Laser Crimson**, world stays
**registration press / proof lab**, signature stays the **registration seal**.

1. **Hero — one composed object.** Keep the asymmetric split. The right column
   becomes a layered verification instrument: backing plate, evidence ledger,
   and the seal. On load, a finite ~900ms sequence draws the hairline, moves
   the crimson point into alignment, and settles the ledger 12px into place
   with a 60ms stagger. A single restrained light sweep crosses the seal once.
   Pointer parallax on the ledger is capped at 8px, rAF-driven and
   interruptible. The crimson contradiction remains the only bright thing.
2. **Pipeline band — scroll-linked journey.** Replace the one-shot sweep with
   a sweep whose progress is driven by scroll position; each of the six stages
   activates as the connector reaches it. Connectors draw with
   `stroke-dashoffset`. Stops when the band leaves the viewport.
3. **Simulation band — verdicts resolve.** Each measured run's verdict snaps
   into alignment with its evidence on entry, once, with a short transform +
   opacity transition. No count-up loops; figures stay tabular and exact.
4. **Benchmarks — one lead chart.** The reliability chart gets a finite
   line-draw on entry and the accent; the other figures stay quiet. This is the
   one chart that leads, so the band no longer reads as a table dump.
5. **Comparison — meaningful light.** The TrustRAG column keeps its crimson
   hairline and gains a barely-there inner edge light, so the selected column
   reads instantly. No colored glow around the whole table.
6. **Chrome — real material.** The nav becomes a quiet translucent layer
   (`backdrop-filter`) over the page, frostier under
   `prefers-reduced-transparency`. The hero ledger is the only floating
   surface and keeps the system's one shadow.

Copy, measured numbers, section order, brand mark and data sources stay
verbatim. No invented claims.

**Review gate:** show the landing at 1440 / 1024 / 390 and with reduced motion
before touching any app route.

## Phase 2 — App routes (after landing review)

State-driven motion for verdict / stage / claim changes; the registration-seal
"alignment" moment in the workbench; the seal carried into the auth card
header. Same guardrails, no new dependencies.

## Phase 3 — Verification

`npm run lint && npm run test && npm run build` (zero warnings); browser sweep
at 1440 / 1280 / 1024 / 768 / 390 / 320 across all routes for overflow,
invisible text, focus, target size, console, and reduced motion; contrast
re-measured on rendered surfaces.

---

## Session handoff — 25 Nov 2026

**Done (25 Nov, first session):** Phase 0 and Phase 1 implemented and verified.

**Done (25 Nov, resumed session):** Phase 2 and Phase 3 complete. Workbench
state motion (verdict settle, claim stagger, trace enter, results seal) and
the auth-card seal are implemented. Lint clean, 84/84 tests, build with zero
warnings. All 11 routes verified at 1440 / 1280 / 1024 / 768 / 390 / 320:
one `h1`/`main`, no invisible text, no overflow, no console errors. Contrast
re-measured on rendered surfaces (lowest 5.0:1 on the crimson button, 5.38:1
signal, 5.59:1 meta, 5.73:1 micro — all above AA). Focus ring 2px crimson.
Reduced motion verified for every new effect: animation-name resolves to
`none` under `prefers-reduced-motion: reduce`.

**Remaining optional work:** Lighthouse re-run if desired; a real analysis run
to see the results-panel seal in situ needs Ollama running (it was stopped).

**Key files:** `HeroSection.jsx`, `usePointerParallax.js`, `PipelineDiagram.jsx`,
`SimulationSandbox.jsx`, `BenchmarksSection.jsx`, `LandingPage.jsx`,
`NotFoundPage.jsx`, `tokens/color.css`, `tokens/motion.css`, `animations.css`,
and the component sheets under `src/styles/components/`.

**Watch-outs:** the pipeline is now scroll-linked, not one-shot — keep its
copy and docs in sync if it changes again. `prefers-reduced-motion` overrides
must match the `nth-child` specificity of the seal rules or they silently
lose. The 11px shell text was raised to 12px in nine places in `app/shell.css`.

**Local test accounts:** `audit-temp-20261124@example.com` (first session) and
`audit-phase2@example.com` (resumed session) were registered on the local
backend; delete them if local data needs to be clean. The resumed session
started the API with a local-only `JWT_SECRET` because the repo ships no API
`.env`; that invalidated the earlier browser token.

**Resume by:** reading this file + `UI_DEEP_AUDIT_2026-11-25.md`, then starting
Phase 2 only after a fresh visual review of the landing page.
