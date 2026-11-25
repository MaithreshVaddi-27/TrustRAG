# TrustRAG — Deep UI/UX audit (25 Nov 2026)

**Scope:** all routes. **Direction:** preserve and elevate the established
dark-luxury system. **Status:** audit only — no UI code has been changed.

---

## 1. Method and evidence

Read: `apps/web/DESIGN.md`, `docs/design/dark-luxury/*`, the landing components,
the app shell, the token layer, `animations.css`, `useScrollReveal.js`,
`authStore.js`, and the route components.

Ran, from `apps/web`:

| Gate | Result |
|---|---|
| `npm run lint` | clean, 0 warnings |
| `npm run test` | 18 files, 84 tests pass |
| `npm run build` | succeeds **with 4 CSS syntax warnings** |

Live browser pass on the already-running dev server (Brave DevTools) at
**1440×900** and **390×844**, on `/`, `/login`, `/register`, `/dashboard`,
`/playground`, `/knowledge-bases`, `/evidence`, `/claims`, `/conflicts`,
`/settings`, and `/does-not-exist`. Auth pages were checked with a cleared
session; app pages with a temporary registered account. Screenshots:
`/private/var/folders/47/cg6bqvzs45s_np6jssyms5cr0000gn/T/opencode/route-*.png`
and `mobile-auth-*.png`.

---

## 2. Verified good — do not regress

- No horizontal page overflow at 1440 or 390 on any route
  (`scrollWidth === clientWidth`); no console errors or warnings.
- Exactly one `<main>` and one `<h1>` on all eleven primary routes; no
  invisible text nodes; focus tokens and verdict colours are consistent.
- The palette, the three-face type system, the 4px grid, and the "Overlap"
  brand mark are coherent and applied consistently. There is **no AI slop** in
  the usual sense: no emoji icons, gradient text, glows, color blobs, or
  floating decoration.
- Landing typography has no text under 12px. The CTA section gap is 112px —
  measured, and correct section rhythm, not a dead band.
- Auth screens and the app shell are restrained and professional; mobile
  navigation collapses cleanly to a drawer; no elements overflow on mobile.

The failure mode here is the *opposite* of slop: the landing page is
under-authored — it reads as a well-set document rather than a product with
one memorable moment. The premium brief has to be spent on craft, not effects.

---

## 3. Findings

### P0 — defects (fix before any styling work)

**F1. Invalid motion tokens break the build cleanly.**
`src/styles/tokens/motion.css:26-29` declares CSS custom properties with
JavaScript object values:

```css
--spring-critical: { type: spring, bounce: 0, duration: 0.35 };
```

esbuild rejects all four (`Expected identifier but found whitespace`), so the
tokens never exist at runtime. `--spring-critical`, `--spring-momentum`,
`--spring-snappy`, `--spring-gentle` have **zero consumers** in `src/`. The
comment on line 25 says they are "mirrored in `lib/motion.js`" — that file does
not exist. Fix: delete the four declarations and the stale comment, or replace
them with valid duration tokens if a spring API is ever added. Target: **0
build warnings**.

**F2. The 404 route has no `<main>` landmark.**
`src/pages/NotFoundPage.jsx:6` wraps the page in `<div className="lx-auth">`.
Live check on `/does-not-exist`: `h1=1, main=0`. This breaks the design
system's own rule (`DESIGN.md` §8, `docs/design/dark-luxury/08-verification.md`
§7): exactly one `<main>` per route. The documented twelve-route sweep omits
this route, which is why it was never caught.

### P1 — design-system drift (craft debt)

**F3. Dead animation keyframes that the system explicitly bans.**
`src/styles/animations.css` defines five keyframes — `fadeIn` (11), `slideUp`
(20), `haloPulse` (31), `rotateBeam` (52), `scanlineMove` (61) — and **none is
referenced anywhere in `src/`**. `haloPulse` and `rotateBeam` are precisely the
breathing glow and rotating beam that `DESIGN.md` §4 and unslop prohibit.
Delete them; keep the functional press feedback.

**F4. Raw colour values outside the token layer.**
`DESIGN.md` §6 states: "a raw colour value lives in `tokens/color.css` and
nowhere else." There are roughly 50 `rgba(...)` literals in component sheets —
e.g. `components/hero.css:157,211,221`, `components/matrix.css:96`,
`components/nav.css:11,21,135`, `app/shell.css` (15 occurrences),
`components/ledger.css` (5), `app/surfaces.css` (7). Some are already tokenised
in `color.css` (`--rule`, `--color-alarm-wash`, `--color-alarm-rule`) but are
duplicated by hand. Promote the repeated ones to tokens and substitute; leave
genuinely one-off values documented.

**F5. 11px meta text in the workbench shell.**
Live check on `/dashboard`: 17–21 elements per route compute to 11px —
`lx-topbar__meta`, `lx-sidebar__group-label`, `lx-sidebar__status-meta`, avatar
initials. These are metadata, not body copy, so it is not a WCAG failure, but
on a dark instrument UI they read as noise. Raise to 12px with
`letter-spacing: 0.005em`, keeping `tabular-nums`.

**F6. Press feedback is too broad.**
`animations.css:78-87` applies `transform: scale(0.97)` to **every** link,
button and role=button on `:active`, including inline text links. That is the
blunt instrument version of Apple's "respond on pointer-down"; scope it to
actual controls (`.lx-btn`, buttons, cards that are interactive) so inline
links do not jump.

### P2 — experience and premium feel (the actual redesign work)

**F7. Landing has one bright moment and then five flat bands.**
Hero (serif display + real evidence ledger + one crimson contradiction) is
strong. Sections 2–6 (pipeline, simulation, capabilities, benchmarks,
comparison) are hairline grids and small-data tables. They are honest and
legible, but visually interchangeable with any technical documentation. The
fix is hierarchy and one authored moment per band — not decoration: a
provenance line that resolves, a verdict that aligns with its evidence, a
single chart that leads and the rest that stay quiet.

**F8. The motion budget is spent almost entirely on the pipeline sweep.**
`useScrollReveal` (one 16px rise, once) and the pipeline sweep are the whole
story. There is no state-driven motion when a verdict resolves, a stage
advances, or a claim changes state — exactly the places where motion would
*explain* something. Apple-design criterion 3 (interruptibility) and 4
(springs) are currently represented only by the global press-scale.

**F9. Workbench empty states are honest but inert.**
"Awaiting a query", "No delivered answers yet", "No claims decomposed yet"
are well written but static. A single staggered, non-looping entrance for the
stage list, plus a quiet state transition when a verdict lands, would make the
pipeline feel like an instrument rather than a form.

**F10. Auth screens repeat the same stack without the signature.**
Mark → wordmark → subtitle → card on both routes is correct but generic. The
registration seal (the product's one signature detail) can carry the brand
inside the card header without adding an asset or a claim.

---

## 4. Direction (five lines, per unslop)

- **Product.** TrustRAG is a claim-level verification workbench: it splits an
  answer into atomic claims, checks each against cited evidence, and shows the
  audit trail. For teams who must trust a RAG answer before a reader finds the
  gap.
- **Character.** exact, instrumented, quiet. (Not clean, modern, or premium —
  those describe every template.)
- **World.** a registration press / proof lab: alignment targets, registration
  seals, proof ledgers, measured figures. This is already the world of the
  brand mark and the signature seal — the redesign extends it, it does not
  invent a new one.
- **Moments.** (1) the hero evidence ledger, where one crimson contradiction
  is the only bright thing; (2) the pipeline sweep, the one authored journey
  through six stages; (3) a claim-and-evidence "alignment" moment in the
  workbench, where a verdict settles into registration with its source. One
  bright element per surface.
- **Signature.** the registration seal — two opposing corner brackets and a
  single crimson point — extended consistently to the alignment moment. One
  detail, not five.

**Motion policy.** Restrained premium: keep the house curve
`cubic-bezier(0.16, 1, 0.3, 1)`, 80/150/220/320ms, one entrance, one stagger,
one authored sweep. Add velocity-aware-feeling state transitions on
opacity/transform only. No glows, no loops, no parallax, no cursor spotlight,
no gradient text, no new dependency, no font payload. `prefers-reduced-motion`
becomes a cross-fade, never a missing state.

---

## 5. Proposed work plan (awaiting approval — no code touched yet)

**Phase 0 — defects**
1. Remove invalid spring tokens + stale comment; remove 5 dead keyframes.
   Verify `npm run build` emits zero warnings.
2. Wrap `NotFoundPage` content in `<main>`.

**Phase 1 — token discipline**
3. Promote repeated rgba overlays to `tokens/color.css`; replace usages in
   `hero.css`, `nav.css`, `matrix.css`, `shell.css`, `ledger.css`,
   `surfaces.css`, `utilities.css`.
4. Raise 11px shell meta text to 12px; scope press feedback to real controls.

**Phase 2 — premium craft, by surface**
5. Landing: give each band one quiet hierarchy move (a lead figure, a
   provenance line, a verdict that resolves). Keep all copy and all measured
   data; no invented claims. Reuse existing tokens and the 60ms stagger.
6. Workbench: state transitions for verdict/stage/claim changes, scoped to
   transform+opacity; the "alignment" moment uses the registration seal.
7. Auth: carry the seal into the card header.

**Phase 3 — verify**
8. `npm run lint && npm run test && npm run build` (zero warnings).
9. Browser sweep at 1440 / 1280 / 1024 / 768 / 390 / 320 on every route:
   overflow, invisible text, focus ring, target size, console, reduced motion.
10. Contrast re-measure on rendered surfaces; Lighthouse if the local setup
    still supports it.

**Constraints honoured:** no new dependencies, no generated image assets, no
font payload, no invented claims, no change to product scope or section order.
