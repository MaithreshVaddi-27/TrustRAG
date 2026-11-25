# Palette & button hierarchy — design proposal (25 Nov 2026)

**Status: approved (Option A) and implemented on 25 Nov 2026.**

Implementation record: `--attention*` tokens now alias silver; `lx-btn--attention*`
call sites were migrated to `--primary` / `--secondary`; the focal silver plate
gains a bottom registration hairline; the destructive `--alarm` register is the
only crimson control (confirm-dialog deletions). Sign out was moved off alarm
because ending a session is not destructive. The topbar "Run analysis" is
primary only on `/dashboard` and secondary elsewhere, so every view has at
most one focal action. Verified: zero crimson-filled buttons on all app routes,
one primary per view, crimson 2px focus ring on the silver plate, 390/320 no
overflow, lint clean, 84/84 tests, build with zero warnings.

---

## 1. Analysis — what the system says vs what it does

**Current palette** (`apps/web/src/styles/tokens/color.css`):

| Family | Steps | Role |
|---|---|---|
| Obsidian | `#080808`, `#0c0c0d`, `#101012`, `#141416` | substrate, chrome, panel, card |
| Graphite | `#5a5957` → `#1a1a1d` | rules and dividers |
| Chrome Silver | `#f7f7f6` → `#3d3d3c` | text, accents, the "silver plate" button |
| Laser Crimson | `#f26a68` → `#7a0c0c` | verdict, seal, live, focus, attention, alarm |

The written rule is sound: *"Crimson is a signal, not a decoration"* — it marks five
things (contradiction, active selection, live status, focus, one focal action).

**What actually happens in the code:** crimson is used as the **primary CTA colour**.

- `lx-btn--attention` (crimson fill) appears in roughly 13 places: hero "Start
  auditing", landing CTA, nav "Get started", "Sign in", "Create account",
  "Run analysis" (topbar + playground), the KB create action, and the empty-state
  CTAs on Claims / Evidence / Conflicts / Knowledge Bases.
- **Three views render two crimson-filled buttons at once** — `ClaimsPage.jsx:60,77`,
  `EvidencePage.jsx:59,76`, `KnowledgeBasesPage.jsx:96,190`. The system says two
  crimson actions means the view has no attention at all. It is right.
- Crimson therefore reads as "the brand's action colour", competing with its real
  meaning — a caught contradiction, the registration seal, a live engine dot. The
  one bright element on a screen is no longer reliably the thing that matters.

**Your instinct is supported by the design skills:**

- *unslop*: one bright element per screen; quiet chrome; richness in content, not
  in buttons.
- *anti-ui-slop*: intentional, product-specific choices; no novelty for its own
  sake.
- *ui-ux-pro-max* style search: the closest verified match for this product is
  **Minimalism / Swiss Style** — monochromatic, single accent, high contrast,
  "best for enterprise apps, dashboards, professional tools"; its variable is
  `--accent-color: single primary only`.
- *ui-design-system*: a generated silver ramp from `#cdcbcA` gives
  `#f2f1f1 / #cdcbca / #a4a2a2 / #7b7979 / #525150 / #282828` — close to the
  existing ramp, so no new brand colour is needed.

**Conclusion:** keep the Obsidian / Silver / Crimson palette. Change the *job* of
the colours: **silver becomes the action colour; crimson becomes a pure signal.**

---

## 2. Three palette combinations to choose from

All are dark-mode only and keep the existing obsidian substrate
(`#080808` / `#0c0c0d` / `#101012` / `#141416`) and graphite rules.

### Option A — Chrome Silver (recommended)

| Token | Value | Role |
|---|---|---|
| Focal button fill | `#f7f7f6` (`silver-050`) | the one primary action |
| Focal button text | `#080808` | 17.8:1 on the fill |
| Hover fill | `#e9e9e7` (`silver-100`) | 15.7:1 |
| Body / secondary | `#a3a2a0` / `#8a8987` | unchanged |
| Signal | `#d41514` / `#f04a48` | verdict, seal, live, focus, alarm only |

Effect: closest to the current brand, lowest risk, strongest "instrument" feel.
The silver plate becomes recognisable as *the* action by size and placement.

### Option B — Warm Ivory

| Token | Value | Role |
|---|---|---|
| Focal button fill | `#f2f1ed` | a slightly warm off-white |
| Focal button text | `#0c0a09` | ~16.8:1 |
| Hover fill | `#e6e4dd` | ~14:1 |
| Secondary text | `#b4b1ab` | warm step of the same ramp |
| Signal | `#d41514` / `#f04a48` | unchanged |

Effect: gentler, more editorial/luxury; moves the whole neutral ramp a few degrees
warm. Needs a token-ramp update, not just a button change.

### Option C — Cool Platinum

| Token | Value | Role |
|---|---|---|
| Focal button fill | `#eaf0f3` | a cool, slightly blue platinum |
| Focal button text | `#080d10` | ~16:1 |
| Hover fill | `#dbe5ea` | ~13:1 |
| Secondary text | `#9da9af` | cool step of the same ramp |
| Signal | `#d41514` / `#f04a48` | unchanged — the warm/cool tension is deliberate |

Effect: most "precision instrument", makes crimson read even more sharply as an
alarm. Also needs a ramp update.

**My recommendation: Option A.** It satisfies your idea with the smallest change
surface and no new brand colour; B and C are available if you want a distinct
warm or cool character.

---

## 3. Concrete change list (applies whichever option you choose)

### Button hierarchy
1. Make `--primary` (silver plate) the **focal** action: "Start auditing", "Get
   started", "Sign in", "Create account", "Run analysis", KB create.
2. Retire `--attention` as a fill. Keep a `--signal` concept in `color.css` for
   crimson; do not use it on buttons except `--alarm` (destructive).
3. `--attention-quiet` → replace with `--secondary` (hairline) or a text link.
4. Enforce **one primary per view**: demote the second crimson CTA in
   `ClaimsPage`, `EvidencePage`, `KnowledgeBasesPage` (and check the playground's
   topbar + in-pane Run analysis pair) to `--secondary`.

### Where crimson stays (and only these)
- contradicted verdicts and their record edges
- the registration seal (hero, results header, auth card, outcome band)
- the live engine dot, active tab/scenario selection, comparison column rule
- keyboard focus ring (2px)
- destructive confirmation (`--alarm`)

### Distinctive detail so silver does not become bland
- The focal silver button gets a 1px inner registration hairline at the bottom
  edge — the same "alignment" language as the seal. No glow, no gradient.
- Hierarchy comes from size (`--btn-large`, 52px), padding and placement, not hue.

### Files touched
`tokens/color.css`, `components/button.css`, the ~13 JSX files using
`lx-btn--attention` / `--attention-quiet`, `DESIGN.md` §1–2, and
`docs/design/dark-luxury/02-tokens.md` + `03-components.md`.

### Verification
Contrast re-measure on rendered surfaces (target ≥4.5:1 text, ≥3:1 focus),
one-primary-per-view audit in the browser, full responsive sweep, lint/test/build.

---

## 4. Trade-off to accept

A silver CTA is quieter than a red one. The mitigation is strict hierarchy — one
large silver primary per view, generous space around it, and the registration
detail — plus crimson reserved for moments that genuinely mean something. If a
view ends up with neither a crimson mark nor a focus ring, it should still feel
resolved; that is the intentional cost of the system.
