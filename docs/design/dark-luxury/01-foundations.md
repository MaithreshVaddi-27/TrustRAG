# 01 — Foundations

The raw material. Six decisions: colour, typography, space, radius, depth,
motion.

---

## 1. Colour

### The substrate — Obsidian

Obsidian is the room everything sits in. It is not black-for-black's-sake;
it is a four-step ramp so that surfaces can separate without a shadow.

| Token | Value | Use |
|---|---|---|
| `--color-obsidian-950` | `#080808` | The page. The default background. |
| `--color-obsidian-900` | `#0c0c0d` | Raised chrome: top bar, sidebar. |
| `--color-obsidian-850` | `#101012` | A panel that holds a record or a ledger. |
| `--color-obsidian-800` | `#141416` | A card. |

The steps are deliberately close. On a dark theme, separation comes from a
1px hairline; the surface steps only have to be *different*, not distant.

### The structure — Graphite

Graphite is the non-text ramp: rules, dividers, inactive strokes, the fills
of meters.

| Token | Value |
|---|---|
| `--color-graphite-300` | `#5a5957` |
| `--color-graphite-400` | `#4a4a49` |
| `--color-graphite-500` | `#3a3a3c` |
| `--color-graphite-600` | `#2e2e33` |
| `--color-graphite-700` | `#232327` |
| `--color-graphite-800` | `#1a1a1d` |
| `--color-graphite-900` | `#141416` |

### The voice — Chrome Silver

Three text roles, and a ramp behind them. The brand neutral is
`--color-silver-300`, `#cdcbcA` — a warm-neutral chrome, not a pure grey.

| Token | Value | Role | Contrast on obsidian |
|---|---|---|---|
| `--color-silver-050` | `#f7f7f6` | On-accent text, highest emphasis | 19.4:1 |
| `--color-silver-100` | `#e9e9e7` | Primary body text | 16.6:1 |
| `--color-silver-200` | `#d8d7d5` | Emphasis inside a block, "supported" verdict | 14.1:1 |
| `--color-silver-300` | `#cdcbcA` | **Chrome Silver** — the brand neutral, the accent | 12.0:1 |
| `--color-silver-400` | `#a3a2a0` | Secondary text | 7.6:1 |
| `--color-silver-500` | `#8a8987` | Muted text | 5.6:1 |
| `--color-silver-600` | `#5a5957` | **Decorative only — never text** | 2.9:1 |
| `--color-silver-700` | `#3d3d3c` | Hairlines on light fills | — |

`--color-silver-600` fails AA for text. It exists for icons, borders and
meter fills. The `lx-micro` utility deliberately steps up to
`--color-silver-500` so that mono metadata stays readable.

### The alarm — Laser Crimson

| Token | Value | Role | Contrast on obsidian |
|---|---|---|---|
| `--color-crimson-300` | `#f26a68` | Light crimson text | 6.8:1 |
| `--color-crimson-400` | `#f04a48` | **Focus ring**, contradicted verdict | 5.5:1 |
| `--color-crimson-500` | `#d41514` | **Laser Crimson** — the brand mark | 3.7:1 (large text / graphics) |
| `--color-crimson-600` | `#a81010` | Pressed states, deep fills | — |
| `--color-crimson-700` | `#7a0c0c` | Borders on crimson fills | — |
| `--color-crimson-950` | `#1a0707` | Crimson-tinted background | — |

`--color-crimson-500` at 3.7:1 is a large-text and non-text colour. Use
`--color-crimson-400` for any crimson that has to carry text.

### Where crimson is allowed

Crimson marks exactly four things. Used anywhere else, it stops meaning
anything.

1. **A caught contradiction** — the verdict, its record edge, its seal.
2. **The active selection** — the sidebar's left rule, the active tab, the
   active scenario, the TrustRAG column in the comparison matrix.
3. **A live status** — the engine dot, the "unrecoverable" outcome.
4. **Keyboard focus.**

### The rules — chrome silver at low opacity

The single structural device of the interface.

| Token | Value | Use |
|---|---|---|
| `--rule-faint` | `rgba(205, 203, 202, 0.08)` | Dividers inside a block |
| `--rule` | `rgba(205, 203, 202, 0.16)` | The default border of a card or panel |
| `--rule-strong` | `rgba(205, 203, 202, 0.28)` | A raised or hovered border |

### The verdict family

Verdicts are a monochrome ramp plus one alarm, so a failed claim is the
only thing on screen that carries colour. Colour never travels alone: every
verdict also carries an icon shape and a word.

| Verdict | Colour | Icon | Label |
|---|---|---|---|
| Supported | `--color-silver-200` | `Check` | Supported |
| Unsupported | `--color-silver-400` | `CircleDashed` | Unsupported / Neutral |
| Unknown | `--color-silver-500` | `Circle` / `HelpCircle` | Unknown / Unverified |
| Contradicted | `--color-crimson-400` | `X` | Contradicted |

### The accent

On a dark theme the primary action is an **off-white plate with dark text**.
It reads more deliberate than a coloured button, it gives the highest
contrast of any button on the page, and it keeps crimson free to mean
"attention".

```css
--color-accent: var(--color-silver-050);   /* #f7f7f6 */
--color-accent-hover: #ffffff;
--color-on-accent: var(--color-obsidian-950); /* #080808 */
```

---

## 2. Typography

Three system faces, so the product stays air-gapped and ships no font
payload.

| Token | Stack | Use |
|---|---|---|
| `--typeface-display` | Didot, Bodoni 72, Bodoni 72 Oldstyle, Playfair Display, Times New Roman, serif | Editorial headings, 20px and up only |
| `--typeface-sans` | system-ui, SF Pro Text, Helvetica Neue, Segoe UI, Roboto, Arial | Interface and body |
| `--typeface-mono` | ui-monospace, SF Mono, SFMono-Regular, JetBrains Mono, Menlo, Consolas | Measured data only |

**Why Didot.** The previous display face was a Palatino/Iowan stack, which
reads as a wedding invitation rather than an instrument. Didot and Bodoni 72
are Didones — the high-contrast serif of luxury editorial. Both ship with
macOS, so the air-gapped guarantee holds. At 20px and above its hairlines
hold; below that it goes spindly, which is why it is restricted.

**Why system sans for the interface.** SF Pro is Apple's own typeface, built
for legibility at small sizes, with optical sizing. Nothing beats it for
interface work, and it is already installed.

**Why system mono for data.** SF Mono is the measurement face. Hashes,
timings, counts, identifiers, document references.

### The scale

| Token | Size | Leading | Tracking | Use |
|---|---|---|---|---|
| `--size-display` | `clamp(2.75rem, 6vw, 5.25rem)` | 1.02 | -0.03em | The landing headline |
| `--size-display-sm` | `clamp(2rem, 4vw, 3.25rem)` | 1.06 | -0.025em | The closing CTA |
| `--size-h1` | `clamp(1.75rem, 3vw, 2.5rem)` | 1.14 | -0.02em | A screen's title |
| `--size-h2` | `clamp(1.375rem, 2vw, 1.875rem)` | 1.2 | -0.015em | A section heading |
| `--size-h3` | `1.25rem` | 1.3 | -0.01em | A panel heading |
| `--size-lede` | `1.125rem` | 1.62 | 0 | Standfirst, intro paragraph |
| `--size-body` | `1rem` | 1.65 | 0 | Body copy |
| `--size-body-sm` | `0.875rem` | 1.6 | 0 | Secondary copy, table cells |
| `--size-label` | `0.8125rem` | 1.45 | +0.005em | Form labels, buttons, tabs |
| `--size-micro` | `0.75rem` | 1.45 | +0.01em | Mono metadata, captions |

### The rules

- **Weights are 400 and 500.** Hierarchy comes from size and colour, not
  from bold. `font-extrabold` is not in the system.
- **Tracking is size-specific.** Display wants negative tracking; body
  wants none; small labels want a touch positive. Negative tracking never
  goes on small text.
- **Leading runs inverse to size.** 1.02 on display, 1.65 on body.
- **The measure is capped** at `--measure-prose` (68ch) for body copy and
  `--measure-narrow` (52ch) for standfirsts.
- **Mono is for data.** A sentence in mono is a sentence that should not be
  in mono.
- **Sentence case everywhere.** No uppercase, no tracked-out labels.
- **Numbers are `tabular-nums`** and use one format across the screen. If
  one figure is `$48,210`, the next is not `$124,860.40`.
- **No italic** for emphasis.
- **Never gradient text.** It made text invisible whenever the gradient
  failed to resolve.

---

## 3. Space

A 4px grid, in `rem` so it scales with the user's text size.

| Token | Value | Token | Value |
|---|---|---|---|
| `--step-1` | 0.25rem (4px) | `--step-10` | 2.5rem (40px) |
| `--step-2` | 0.5rem (8px) | `--step-12` | 3rem (48px) |
| `--step-3` | 0.75rem (12px) | `--step-16` | 4rem (64px) |
| `--step-4` | 1rem (16px) | `--step-20` | 5rem (80px) |
| `--step-5` | 1.25rem (20px) | `--step-24` | 6rem (96px) |
| `--step-6` | 1.5rem (24px) | `--step-32` | 8rem (128px) |
| `--step-7` | 1.75rem (28px) | | |
| `--step-8` | 2rem (32px) | | |

### Rhythm

| Token | Value | Use |
|---|---|---|
| `--section-space` | 6rem (96px) | Between sections |
| `--chapter-space` | 8rem (128px) | Between major movements |
| `--gutter` | 1.5rem (24px) | Page edge, desktop |
| `--measure-page` | 82.5rem (1320px) | Content cap |

The gutter steps down to 1.25rem at 768px and 1rem below 400px.

### The principles

- **Same thing, same size.** Every row of a list shares one height and one
  gap. Every card in a row shares one padding.
- **Space shows grouping.** Space inside a group is smaller than space
  between groups, so a list reads as one block.
- **Things line up.** Icons in one column, labels on one line, numbers
  right-aligned in one column.
- **More room above a heading than below it.** A heading belongs to what
  follows it.
- **Density follows the surface.** Compact panels and sidebars around 16px,
  cards 20–24px, page edges 24–32px.

---

## 4. Radius

| Token | Value | Use |
|---|---|---|
| `--radius-control` | 6px | Buttons, inputs, tabs |
| `--radius-card` | 10px | Cards |
| `--radius-panel` | 14px | Panels, records, drawers |
| `--radius-large` | 20px | The hero's product preview |
| `--radius-pill` | 9999px | Status pills only |

Not everything is a pill. Nested radii subtract: an inner radius is the
outer radius minus the padding between them, never less than 4.

---

## 5. Depth

On a dark theme, depth comes from **surface steps and hairlines**, not from
shadows.

Elevation is declared **once**: a 1px rule *or* a shadow, never both. A
1px border under a wide soft shadow is a ghost card.

```css
/* The default */
background: var(--surface-card);
border: 1px solid var(--rule);

/* Raised — one step up, still a rule */
background: var(--surface-panel);
border: 1px solid var(--rule-strong);
```

The system contains exactly one shadow, and it belongs to the one element
that genuinely floats above the page:

```css
--shadow-preview:
  0 32px 64px -32px rgba(0, 0, 0, 0.9),
  0 8px 24px -16px rgba(0, 0, 0, 0.6);
```

It is used by `.lx-preview`, the landing page's product preview, and by
nothing else.

---

## 6. Motion

One easing curve, a few durations. Motion explains something; it never
loops for decoration.

| Token | Value | Use |
|---|---|---|
| `--motion-duration-instant` | 80ms | Press feedback |
| `--motion-duration-fast` | 150ms | Hover, colour changes |
| `--motion-duration-base` | 220ms | Enters, state changes |
| `--motion-duration-slow` | 320ms | Larger transitions |
| `--motion-ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | The house curve |
| `--motion-ease-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | Two-way state changes |

### What moves

| Motion | Trigger | Duration |
|---|---|---|
| Entrance | Page load — the hero fades and rises with a 70ms stagger | 620ms |
| Scroll reveal | A section enters the viewport — a 16px rise, once | 320ms |
| The sweep | The pipeline diagram enters view — a highlight travels the chain once, then holds | 1400ms |
| Hover | A colour or border change | 150ms |
| Press | A scale to 0.985 | 80ms |

Springs, where Motion is used, are critically damped: `bounce: 0`,
`duration: 0.35`. Bounce is reserved for momentum-driven physical
interaction, which this product does not have.

### What does not move

Loops with no purpose — a pulsing heading, a breathing glow, a floating
card, a rotating beam, a cursor spotlight. The cursor spotlight that used
to follow the pointer around the application shell is removed.

Loops on **live** elements are permitted, because they report something
true: a connected provider, a running analysis, a live telemetry stream.
Those use `.lx-live-dot` and the Tailwind `animate-pulse`.

### The scroll reveal is fail-safe

Only elements **below the fold at mount** are ever hidden. Anything already
in view is visible immediately, so content can never be stranded by a
failed observer, a print, or an unusual layout. The `lx-js` class on
`<html>` is the second guard: without JavaScript the hidden state does not
exist at all.

`prefers-reduced-motion: reduce` collapses every duration to 1ms and
turns the reveal into a cross-fade.
