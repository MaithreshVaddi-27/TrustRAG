# 07 — Migration

How the surfaces that were built before this system map onto it, and what
is still to do.

---

## The bug that started this

`src/styles/design-tokens.css` was committed with the full token set —
colour ramps, type scale, spacing, radii, motion — and **was never
imported by `src/index.css`.**

Every one of the 172 `var(--…)` references across six stylesheets resolved
to nothing. The failure was silent and total:

- `.glass-card` computed `border-width: 0`, `border-radius: 0` and no
  shadow. All 22 surfaces using it rendered as borderless rectangles.
- `.shimmer-text` and `.text-gradient` set `color: transparent` over a
  `background-clip: text` gradient that did not resolve. **The text was
  rendered invisible** — the landing hero's second headline line, the
  dashboard's `Workbench`, the knowledge-bases page's `Bases`.
- The focus ring, every `transition-duration`, every `border-radius`, every
  `z-index` and every spacing token silently fell back to its initial
  value.

Worse, it was *intermittent in appearance*: under
`prefers-reduced-motion: reduce`, the fallback rule set the colour back to
the inherited text colour, so the headline reappeared. The accessibility
path rescued the text that the default path destroyed.

The lesson is now structural: **tokens are imported first, and the CSS
layer is split so a missing import cannot take half the system with it.**

---

## What changed

### The token layer

| Before | After |
|---|---|
| One monolithic `styles/design-tokens.css` | `styles/tokens/` split by concern |
| Never imported | Imported first by `styles/index.css` |
| 175 `var()` references resolving to nothing | All resolve |
| `styles/index.css` held tokens, resets and components together | `tokens/` · `base.css` · `utilities.css` · `components/` · `app/` |

### The palette

The product was cyan-on-slate with green, amber and red semantics. It is
now obsidian, chrome silver and crimson.

Tailwind's older families were re-pointed rather than rewritten, so the
application surfaces inherited the new palette without a per-component
edit:

| Legacy | Now |
|---|---|
| `primary`, `cyan`, `slate` | the silver ramp |
| `cyber` | the graphite ramp |
| `surface` | the obsidian ramp |
| `emerald` | silver — supported |
| `amber` | silver, dimmer — unsupported |
| `red` | crimson — contradicted |
| `gold` | retired → silver steps |

`tokens/compat.css` does the same for the older *CSS custom property*
names, in one direction only, with no raw values of its own.

### Typography

| Before | After |
|---|---|
| `Iowan Old Style / Palatino` display — a wedding invitation | `Didot / Bodoni 72` — a Didone, luxury editorial |
| `Inter` body | `system-ui` / SF Pro — Apple's own interface face |
| `JetBrains Mono` telemetry | `ui-monospace` / SF Mono |
| Weights up to 800 | Weights 400 and 500 only |

All three families are system faces, so the air-gapped guarantee holds.

### Surfaces

`.glass-card` was a 16px-blurred translucent panel with a coloured gradient
edge. It is now an opaque obsidian surface with a 1px chrome-silver
hairline. The brief excludes excessive glassmorphism, and on a dark theme
depth comes from surface steps and hairlines.

The consequence: a card's border, radius and shadow are now all real
values rather than fallbacks, and the whole surface system is visible
again.

### Motion

| Removed | Why |
|---|---|
| Cursor spotlight following the pointer | Chrome should not chase the mouse |
| Ambient radial flares | Colour blobs behind content |
| Floating cards on an infinite loop | Motion with no meaning |
| Shimmer headings | Loop with no meaning |
| Rotating border beams | Loop with no meaning |
| Breathing glows | Loop with no meaning |

What remains: one entrance on load, one scroll reveal per section, the
pipeline sweep, hover colour changes and press feedback. Loops remain
only on genuinely live elements, where they report something true.

### Dead code removed

| Removed | Reason |
|---|---|
| `hooks/useCursorGlow.js` | The spotlight |
| `styles/app-layout.css` | 9 of its 10 classes were used by nothing |
| `.glass-nav`, `.glass-sidebar`, `.glass-surface`, `.glass-overlay` | Unused after the shell rebuild |
| `.text-gradient`, `.shimmer-text`, `.laser-scanline` | Made text invisible or were unused |
| `components/landing/AnimatedPipeline.jsx` | Replaced by `PipelineDiagram` |
| `components/landing/BentoArchitecture.jsx` | Content folded into `CapabilitiesExplorer` |
| `components/landing/ProblemSolutionNarrative.jsx` | Replaced by the sandbox ledger |
| 30 unused animation and utility classes | Pruned from the stylesheets |

`styles/animations.css` fell from 425 lines to 241; `styles/materials.css`
from 237 to 135.

---

## The landing page

### Before

Eight sections, but two of them covered the same six capabilities: a
four-item "capabilities" panel with code, and a six-card "bento" grid
listing the same subjects in prose. The page ran 7,527px, and the hero
headline was half invisible.

### After

Seven sections, no overlap. The six capabilities live in one list with
one panel, each with its own code. The page runs 6,339px and 591 DOM
nodes, down from 1,028.

| Change | Reason |
|---|---|
| Hero is a split, not a centred stack | Everything-stacked-and-centred is the template default |
| The hero visual is a real evidence record | The hero should show something true |
| The pipeline is linework with one sweep | A diagram that explains a mechanism |
| The sandbox is a case file | Proof, not decoration |
| Capabilities became one list, not two | The same six subjects were presented twice |
| The comparison is a specification table | A document, not a grid of cards |
| The benchmarks are ranked rows with a caption | A figure without its provenance is a claim, not a measurement |

The landing chunk dropped from **94.4 kB to 35.1 kB** (20.4 kB to 10.6 kB
gzipped) because the landing page no longer pulls in the motion library.

---

## The application shell

| Before | After |
|---|---|
| Cursor glow following the pointer | Removed |
| Sidebar rows with a cyan pill and a glowing bar | 36px rows, a 2px crimson rule for the active one |
| "Live" as a coloured pill | Quiet mono text with a crimson dot |
| Engine telemetry as a row of coloured pills | Quiet mono text with a status dot |
| A green / amber / red backend banner | One crimson band |
| Glass sidebar with a 28px blur | An opaque obsidian surface with a hairline |
| A mobile drawer that slid in a bordered sheet | A full-height sheet with a focus-trapped close button |

---

## Authentication

| Before | After |
|---|---|
| A glass card with a coloured gradient edge | One hairline card, no colour wash |
| An ambient cyan blob behind the form | Nothing |
| 38px inputs | 44px inputs, set in 16px so iOS does not zoom |
| A 15px password toggle | A 44px hit area with `aria-pressed` |
| Errors in a red box with no `role` | `role="alert"`, crimson |
| An "AI-powered"-style wordmark in cyan | A flat Didot wordmark |

---

## Migration complete

Every item below is done.

| # | Task | Result |
|---|---|---|
| 1 | Migrate the application surfaces to the `lx-*` vocabulary | Done — dashboard, playground, results, workbench, knowledge bases, claims, evidence, conflicts, settings |
| 2 | Delete `tokens/compat.css` | Deleted — no stylesheet references the legacy custom property names |
| 3 | Delete `styles/legacy-components.css` | Deleted, along with `styles/typography.css` |
| 4 | Adopt `PageHeader` on every route | Done |
| 5 | Adopt the shared button vocabulary | Done — `.lx-btn` with `--primary`, `--secondary`, `--quiet` and `--alarm` |
| 6 | Replace the remaining `.badge-*` classes | Done — `VerdictBadge` and `ReliabilityBadge` carry every verdict |
| 7 | Lazy-load the charts | Done, and more than that — recharts was replaced by two purpose-built SVG charts, removing a 386 kB vendor chunk |
| 8 | Give `/playground` an `h1` | Done — the query pane's heading |
| 9 | Migrate `tailwind.config.js` off the duplicated legacy ramps | The remap works; `primary` and `silver` still hold the same values in two places, which is the price of not touching every class name at once |

The landing page's chunk fell from **94.4 kB to 35.1 kB** (20.4 kB to
10.7 kB gzipped) when it stopped pulling in the motion library. The
playground chunk fell from **215.9 kB to 37.8 kB** when recharts and the
Markdown renderer left the initial load.

The page-by-page programme that followed the migration is recorded in
[09 — Pages](./09-pages.md). It ran from P4.1 (the application shell)
through P4.10 (authentication) and closed with P4.11, a layout-stability
pass over every route. Two surfaces were added along the way: a document
record at `/documents/:id`, and the trace page's account of the run it
belongs to.

---

## How to work on this system

1. **Read the tokens, not the CSS.** If a value exists as a token, use it.
2. **Never introduce a hue.** If something needs to be distinguished, step
   along the silver ramp. If it needs to be alarmed, it is crimson, and
   it means a failure, a live state, a selection or focus.
3. **Never add a second accent.** Chrome Silver is the accent.
4. **Reach for a specification before a card.** A record, a ledger, a
   layer stack, a table, a diagram.
5. **Check the render, not the intent.** The token layer is loaded first
   on purpose; if you reorder the imports, the failure is silent.
