# TrustRAG — Dark Luxury Design System

**Direction:** Obsidian Black × Chrome Silver × Laser Crimson
**Character:** Luxury editorial × Apple precision × Linear simplicity ×
enterprise sophistication
**Mode:** Strictly dark. There is no light theme and the tokens expose no
light values.

This folder is the canonical documentation for the TrustRAG interface
system. The token values here mirror
`apps/web/src/styles/tokens/` — the CSS is the runtime source of truth,
`apps/web/tailwind.config.js` is the build-layer mirror, and this folder
explains what they mean and when to use them.

---

## The one-line idea

> **Obsidian is the room. Chrome Silver is the instrument. Laser Crimson is
> the alarm.**

Most interfaces are made of many colours fighting for attention. This one
is made of a near-monochrome ramp that carries the interface, plus exactly
one colour that means *something needs your attention*. A failed claim, the
active selection, a live status, keyboard focus. Nowhere else.

That discipline is the whole system. Every rule below exists to protect it.

---

## Documents

| # | Document | What it covers |
|---|---|---|
| 01 | [Foundations](./01-foundations.md) | Colour, typography, space, radius, depth — the raw material |
| 02 | [Tokens](./02-tokens.md) | The complete token reference, with values and usage |
| 03 | [Components](./03-components.md) | The component vocabulary and how to compose it |
| 04 | [Patterns](./04-patterns.md) | Page and section layouts, states, data display |
| 05 | [Accessibility](./05-accessibility.md) | The measurable standard every surface must meet |
| 06 | [Voice and copy](./06-voice-and-copy.md) | How the product talks |
| 07 | [Migration](./07-migration.md) | How the old surfaces map onto the new system |
| 08 | [Verification](./08-verification.md) | The gate, the commands, the browser checklist |
| 09 | [Pages](./09-pages.md) | The page-by-page redesign, and what each phase changed |

---

## Quick reference

```css
/* Type */
font-family: var(--typeface-display);   /* Didot — headings ≥ 20px only */
font-family: var(--typeface-sans);      /* system-ui — interface and body */
font-family: var(--typeface-mono);      /* SF Mono — measured data only */

/* Surfaces */
background: var(--surface-page);        /* #080808 */
background: var(--surface-raised);      /* #0c0c0d — nav, sidebar */
background: var(--surface-panel);       /* #101012 */
background: var(--surface-card);        /* #141416 */
background: var(--surface-inset);       /* inset wells, code blocks */

/* Rules */
border-color: var(--rule);             /* the only structural device */

/* The accent */
background: var(--color-accent);        /* #f7f7f6 — off-white plate */
color: var(--color-on-accent);          /* #080808 — obsidian text */

/* The alarm */
color: var(--color-crimson-500);        /* #d41514 */
outline: 2px solid var(--focus-ring);   /* #f04a48 */
```

---

## What is deliberately absent

These are not oversights. Each one was removed on purpose, and
reintroducing any of them breaks the system.

| Absent | Why |
|---|---|
| A light theme | The brief is strict dark. A half-built light theme is worse than none. |
| Purple / blue / indigo gradients | Generic AI aesthetics. The palette is obsidian, silver, crimson. |
| Gradient text | It made text invisible whenever the gradient failed to resolve. Emphasis comes from weight and size. |
| Coloured glows and neon shadows | A zero-offset coloured halo is decoration, not depth. |
| Glassmorphism as a default | On a dark theme, depth comes from surface steps and hairlines. |
| Bokeh / ambient blobs / particle fields | Filler. They say nothing about a reliability instrument. |
| Cursor spotlights | Chrome is chrome. It should not follow the pointer around. |
| Looping motion | A pulsing heading or a breathing glow tells the user nothing. |
| Emoji as icons | One icon set, one size, one stroke. |
| Uppercase tracked labels | Sentence case everywhere. |
| Kicker / eyebrow labels above headings | The heading carries its own weight. |
| Equal-size card grids of icon + heading + text | The lazy container. Use a specification instead. |
| Sparklines and progress rings standing in for content | If the chart is placeholder noise, replace it with data that says something. |

---

## Related

- [`apps/web/DESIGN.md`](../../../apps/web/DESIGN.md) — the short version, for
  developers working in the app.
- `docs/evaluation/` — the measurement methodology behind the numbers quoted
  in the product.
