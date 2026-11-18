# 02 — Token reference

Every token, its value, and where it is used. The CSS files under
`apps/web/src/styles/tokens/` are the runtime source of truth;
`apps/web/tailwind.config.js` is the build-layer mirror. Change them
together.

---

## File layout

```
apps/web/src/styles/
├── index.css              ← entry; imports everything in order
├── tokens/
│   ├── index.css          ← the token layer, imported FIRST
│   ├── color.css          ← Obsidian / Chrome Silver / Laser Crimson
│   ├── typography.css     ← families, scale, weights, measures
│   ├── spacing.css        ← 4px grid, section rhythm, gutters
│   ├── radius.css         ← control / card / panel / large
│   ├── elevation.css      ← surfaces, the one shadow, the focus ring
│   ├── motion.css         ← durations, easing, springs
│   └── compat.css         ← legacy names → new palette (temporary)
├── base.css               ← element defaults, browser surfaces, preferences
├── utilities.css          ← the small shared vocabulary
├── legacy-components.css  ← classes the app surfaces still use
├── app/
│   ├── shell.css          ← the application shell
│   └── auth.css           ← authentication surfaces
└── components/            ← one stylesheet per component family
    ├── button.css  nav.css  section.css  hero.css  capabilities.css
    ├── ledger.css  pipeline.css  matrix.css  benchmarks.css  footer.css
```

### Import order

1. **Tokens.** Every `var(--…)` in the codebase resolves from here. If this
   is not first, nothing works and the failure is silent — which is exactly
   the bug that broke the previous build.
2. **Legacy application stylesheets.** Still on the old token names;
   `compat.css` re-points those names at the new palette.
3. **Base.** Element defaults and the browser surfaces nobody designed.
4. **Utilities.** The small shared vocabulary.
5. **Components.** The landing system.
6. **Tailwind's layers**, last, so utility classes win on a tie.

---

## Colour

### Obsidian — the substrate

| Token | Value | Use |
|---|---|---|
| `--color-obsidian-950` | `#080808` | Page |
| `--color-obsidian-900` | `#0c0c0d` | Raised chrome: top bar, sidebar |
| `--color-obsidian-850` | `#101012` | Panel |
| `--color-obsidian-800` | `#141416` | Card |

### Graphite — structure

| Token | Value | Use |
|---|---|---|
| `--color-graphite-300` | `#5a5957` | Strongest inactive stroke |
| `--color-graphite-400` | `#4a4a49` | |
| `--color-graphite-500` | `#3a3a3c` | Meter tracks, inactive fills |
| `--color-graphite-600` | `#2e2e33` | Scrollbar thumb |
| `--color-graphite-700` | `#232327` | Strong border on a raised surface |
| `--color-graphite-800` | `#1a1a1d` | Inset well |
| `--color-graphite-900` | `#141416` | |

### Chrome Silver — the voice

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--color-silver-050` | `#f7f7f6` | On-accent text, highest emphasis | 19.4:1 |
| `--color-silver-100` | `#e9e9e7` | Primary body text | 16.6:1 |
| `--color-silver-200` | `#d8d7d5` | Emphasis inside a block | 14.1:1 |
| `--color-silver-300` | `#cdcbcA` | Chrome Silver — the brand neutral | 12.0:1 |
| `--color-silver-400` | `#a3a2a0` | Secondary text | 7.6:1 |
| `--color-silver-500` | `#8a8987` | Muted text, mono metadata | 5.6:1 |
| `--color-silver-600` | `#5a5957` | Decorative only — never text | 2.9:1 |
| `--color-silver-700` | `#3d3d3c` | Hairlines on light fills | — |

### Laser Crimson — the alarm

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--color-crimson-300` | `#f26a68` | Light crimson text | 6.8:1 |
| `--color-crimson-400` | `#f04a48` | Focus ring, contradicted verdict | 5.5:1 |
| `--color-crimson-500` | `#d41514` | Laser Crimson — the brand mark | 3.7:1 |
| `--color-crimson-600` | `#a81010` | Pressed states | — |
| `--color-crimson-700` | `#7a0c0c` | Borders on crimson fills | — |
| `--color-crimson-950` | `#1a0707` | Crimson-tinted background | — |

### Rules

| Token | Value | Use |
|---|---|---|
| `--rule-faint` | `rgba(205, 203, 202, 0.08)` | Dividers inside a block |
| `--rule` | `rgba(205, 203, 202, 0.16)` | Default card and panel border |
| `--rule-strong` | `rgba(205, 203, 202, 0.28)` | Raised or hovered border |

### Verdict, accent and alarm aliases

| Token | Resolves to | Use |
|---|---|---|
| `--verdict-supported` | `--color-silver-200` | |
| `--verdict-unsupported` | `--color-silver-400` | |
| `--verdict-contradicted` | `--color-crimson-400` | |
| `--verdict-unknown` | `--color-silver-500` | |
| `--color-accent` | `--color-silver-050` | The primary action's plate |
| `--color-accent-hover` | `--color-silver-100` | |
| `--color-on-accent` | `--color-obsidian-950` | The primary action's text |
| `--color-attention` | `--color-crimson-500` | The focal action's crimson fill |
| `--color-attention-hover` | `--color-crimson-400` | |
| `--color-on-attention` | `--color-silver-050` | Text on the crimson fill |
| `--color-attention-quiet` | `--color-crimson-400` | Crimson text and hairline, no fill |
| `--color-alarm` | `--color-crimson-600` | A destructive action's fill |
| `--color-alarm-hover` | `--color-crimson-700` | |
| `--color-on-alarm` | `--color-silver-050` | Text on the alarm fill |
| `--color-alarm-text` | `--color-crimson-300` | Error text |
| `--color-alarm-wash` | `rgba(212, 21, 20, 0.09)` | An error surface's background |
| `--color-alarm-rule` | `rgba(212, 21, 20, 0.34)` | An error surface's hairline |

---

## Typography

### Families

| Token | Stack |
|---|---|
| `--typeface-display` | `'Didot', 'Bodoni 72', 'Bodoni 72 Oldstyle', 'Playfair Display', 'Times New Roman', serif` |
| `--typeface-sans` | `system-ui, -apple-system, 'SF Pro Text', 'Helvetica Neue', 'Segoe UI', Roboto, Arial, sans-serif` |
| `--typeface-mono` | `ui-monospace, 'SF Mono', SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, monospace` |

### Scale

| Token | Size | Leading | Tracking |
|---|---|---|---|
| `--size-display` | `clamp(2.75rem, 6vw, 5.25rem)` | `--leading-display` 1.02 | `--tracking-display` -0.03em |
| `--size-display-sm` | `clamp(2rem, 4vw, 3.25rem)` | 1.06 | -0.025em |
| `--size-h1` | `clamp(1.75rem, 3vw, 2.5rem)` | 1.14 | -0.02em |
| `--size-h2` | `clamp(1.375rem, 2vw, 1.875rem)` | 1.2 | -0.015em |
| `--size-h3` | `1.25rem` | 1.3 | -0.01em |
| `--size-lede` | `1.125rem` | 1.62 | 0 |
| `--size-body` | `1rem` | 1.65 | 0 |
| `--size-body-sm` | `0.875rem` | 1.6 | 0 |
| `--size-label` | `0.8125rem` | 1.45 | 0.005em |
| `--size-micro` | `0.75rem` | 1.45 | 0.01em |

### Weights and measures

| Token | Value |
|---|---|
| `--weight-regular` | 400 |
| `--weight-medium` | 500 |
| `--measure-prose` | 68ch |
| `--measure-narrow` | 52ch |

---

## Space

`--step-1` 0.25rem · `--step-2` 0.5rem · `--step-3` 0.75rem · `--step-4` 1rem ·
`--step-5` 1.25rem · `--step-6` 1.5rem · `--step-7` 1.75rem · `--step-8` 2rem ·
`--step-10` 2.5rem · `--step-12` 3rem · `--step-16` 4rem · `--step-20` 5rem ·
`--step-24` 6rem · `--step-32` 8rem

| Token | Value | Use |
|---|---|---|
| `--section-space` | 6rem | Between sections (4rem at 768px, 3.25rem below 400px) |
| `--chapter-space` | 8rem | Between major movements (5rem / 4rem) |
| `--gutter` | 1.5rem | Page edge (1.25rem at 768px, 1rem below 400px) |
| `--measure-page` | 82.5rem | Content cap, 1320px |

---

## Radius

| Token | Value | Use |
|---|---|---|
| `--radius-control` | 6px | Buttons, inputs, tabs |
| `--radius-card` | 10px | Cards |
| `--radius-panel` | 14px | Panels, records, drawers |
| `--radius-large` | 20px | The hero's product preview |
| `--radius-pill` | 9999px | Status pills only |

---

## Elevation

| Token | Value | Use |
|---|---|---|
| `--surface-page` | `--color-obsidian-950` | The page |
| `--surface-raised` | `--color-obsidian-900` | Top bar, sidebar |
| `--surface-panel` | `--color-obsidian-850` | A panel |
| `--surface-card` | `--color-obsidian-800` | A card |
| `--surface-inset` | `--color-graphite-800` | Inset wells, code blocks |
| `--shadow-preview` | two-layer soft black | The hero's product preview, only |
| `--focus-ring` | `--color-crimson-400` | The one focus ring |

---

## Motion

| Token | Value | Use |
|---|---|---|
| `--motion-duration-instant` | 80ms | Press feedback |
| `--motion-duration-fast` | 150ms | Hover, colour changes |
| `--motion-duration-base` | 220ms | Enters, state changes |
| `--motion-duration-slow` | 320ms | Larger transitions |
| `--motion-ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | The house curve |
| `--motion-ease-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | Two-way state changes |
| `--stagger-step` | 60ms | Stagger between siblings |

Spring presets, mirrored in `lib/motionConfig.js` for Motion's JS API:

| Name | Value | Use |
|---|---|---|
| `SPRING_SNAPPY` | `{ type: 'spring', bounce: 0, duration: 0.25 }` | Micro-interactions |
| `SPRING_GENTLE` | `{ type: 'spring', bounce: 0, duration: 0.5 }` | Entrances |

---

## Tailwind mapping

`tailwind.config.js` exposes the new families directly:

| Family | Steps | Note |
|---|---|---|
| `silver` | 50–950 | The brand neutral and the accent |
| `graphite` | 300–900 | Structure |
| `obsidian` | 800–950 | The substrate |
| `crimson` | 300–950 | The alarm |

### Legacy families remapped

The older colour names now resolve into the same three voices, so the
application surfaces inherited the new palette without a per-component
edit.

| Legacy family | Now resolves to |
|---|---|
| `primary` | the silver ramp |
| `cyan` | the silver ramp |
| `cyber` | the graphite ramp |
| `surface` | the obsidian ramp |
| `slate` | the silver ramp |
| `emerald` | the silver ramp — supported |
| `amber` | the silver ramp, dimmer — unsupported |
| `red` | the crimson ramp — contradicted |
| `gold` | retired → silver steps |

### Compatibility layer

`tokens/compat.css` re-points the old *CSS custom property* names at the
new tokens. It holds no raw values of its own; every declaration resolves
in one direction, so there is no cycle.

```css
--color-primary-400: var(--color-silver-300);
--color-surface-950: var(--color-obsidian-950);
--font-display: var(--typeface-display);
--space-4: var(--step-4);
--radius-md: var(--radius-card);
--duration-fast: var(--motion-duration-fast);
```

Delete `compat.css` when the application surfaces are migrated, and rename
the remaining references to their semantic equivalents.
