# TrustRAG — Frontend Design System

> **Canonical documentation:** [`docs/design/dark-luxury/`](../../docs/design/dark-luxury/)
> — the complete system, split by concern: foundations, tokens, components,
> patterns, accessibility, voice, migration and verification. This file is the
> short version for working in the app.

**Direction:** Obsidian Black × Chrome Silver × Laser Crimson.
Luxury editorial × Apple precision × Linear simplicity × enterprise sophistication.
**Strictly dark.** There is no light theme and the tokens expose no light values.

---

## 1. The palette

Three colours and a graphite substrate. The system is deliberately
near-monochrome: Chrome Silver carries the interface, and Laser Crimson is a
signal, not a decoration.

| Token | Value | Role |
|---|---|---|
| `--color-obsidian-950` | `#080808` | Page substrate |
| `--color-obsidian-900` | `#0c0c0d` | Raised chrome: nav, sidebar, panels |
| `--color-obsidian-850` | `#101012` | Panel |
| `--color-obsidian-800` | `#141416` | Card |
| `--color-graphite-500…800` | `#3a3a3c` → `#1a1a1d` | Rules, dividers, inactive strokes |
| `--color-silver-050` | `#f7f7f6` | On-accent text, highest emphasis |
| `--color-silver-300` | `#cdcbcA` | **Chrome Silver** — primary text, the accent |
| `--color-silver-400` | `#a3a2a0` | Secondary text — 7.6:1 on obsidian |
| `--color-silver-500` | `#8a8987` | Muted text — 5.6:1 on obsidian |
| `--color-silver-600` | `#5a5957` | Decorative only. Never text |
| `--color-crimson-400` | `#f04a48` | Focus ring — 5.5:1 on obsidian |
| `--color-crimson-500` | `#d41514` | **Laser Crimson** — the signal |

### Where crimson is allowed

Crimson marks exactly five things. Used anywhere else it stops meaning
anything.

1. A caught contradiction — the verdict, its record edge, its seal.
2. The active selection — the sidebar's left rule, the active tab, the
   active scenario, the TrustRAG column in the comparison matrix.
3. A live status — the engine dot, the "unrecoverable" outcome.
4. Keyboard focus.
5. The focal action of a view — one per surface: **Sign in**, **Create
   account**, **Get started**. Two crimson actions on one screen means there
   is no attention at all.

Crimson also carries the **alarm** register: failures and destructive
actions. Same hue, different depth — a destructive confirmation never reads
as an entry point.

| Register | Fill | Use |
|---|---|---|
| `--color-attention` | `crimson-500` | The focal action's filled button |
| `--color-attention-quiet` | `crimson-400` text + hairline | A second placement of the same action |
| `--color-alarm` | `crimson-600` | A destructive action's filled button |
| `--color-alarm-text` | `crimson-300` | Error text on a dark surface |

### Buttons

The default button is a **silver plate** (`--color-accent`), not a coloured
one. Crimson is entered only through the two registers above:

| Class | Treatment | Use |
|---|---|---|
| `.lx-btn--primary` | Silver plate, obsidian text | The ordinary action — the default |
| `.lx-btn--attention` | Crimson fill | The focal action of a view |
| `.lx-btn--attention-quiet` | Crimson hairline + text | A second placement of the focal action |
| `.lx-btn--secondary` | Hairline outline, silver text | Everything else |
| `.lx-btn--quiet` | Text only | Tertiary, inline |
| `.lx-btn--alarm` | Deep crimson fill | A destructive action |

A filled crimson button carries a **silver** focus ring (a crimson ring on a
crimson fill is 1.2:1). Every other focusable element keeps the crimson ring.

### Verdict family

Verdicts are a monochrome ramp plus one alarm, so a failed claim is the only
thing on screen that gets colour.

| Verdict | Colour | Icon |
|---|---|---|
| Supported | `--color-silver-200` | `Check` |
| Unsupported | `--color-silver-400` | `CircleDashed` |
| Unknown | `--color-silver-500` | `Circle` |
| Contradicted | `--color-crimson-400` | `X` |

Colour never travels alone: every verdict carries an icon shape and a word.

### Legacy palette mapping

`tailwind.config.js` remaps the older colour families into this one, so the
application surfaces inherited the new palette without a per-component edit.

| Legacy | Now |
|---|---|
| `primary`, `cyan`, `slate` | the silver ramp |
| `cyber` | the graphite ramp |
| `surface` | the obsidian ramp |
| `emerald` | silver ramp (supported) |
| `amber` | silver ramp, dimmer (unsupported) |
| `red` | crimson ramp (contradicted) |
| `gold` | retired → silver steps |

---

## 2. Typography

Three system faces, so the product stays air-gapped and ships no font
payload.

| Token | Family | Use |
|---|---|---|
| `--typeface-display` | Didot, Bodoni 72, Playfair Display, Times | Editorial headings ≥ 20px only |
| `--typeface-sans` | `system-ui`, SF Pro Text, Helvetica Neue | Interface and body |
| `--typeface-mono` | `ui-monospace`, SF Mono, JetBrains Mono | Measured data only — hashes, timings, counts, identifiers |

**Rules**

- Weights are 400 and 500. Hierarchy comes from size and colour, not bold.
- Tracking is size-specific: display `-0.03em`, body `0`, small labels
  `+0.005em`. Negative tracking never goes on small text.
- Leading runs inverse to size: 1.02 on display, 1.65 on body.
- Body copy is capped at `--measure-prose` (68ch).
- Mono is for data, never as a costume for "technical". A sentence in mono
  is a sentence that should not be in mono.
- Sentence case everywhere. No uppercase tracked labels.

### The scale

`--size-display` · `--size-display-sm` · `--size-h1` · `--size-h2` ·
`--size-h3` · `--size-lede` · `--size-body` · `--size-body-sm` ·
`--size-label` · `--size-micro`

---

## 3. Space, radius, depth

**Space** — a 4px grid, `--step-1` … `--step-32`, in `rem` so it scales with
the user's text size. Section rhythm is `--section-space` (6rem) and
`--chapter-space` (8rem); a band's rule sits at the top and its heading 40px
below. More room above a heading than below it.

**Radius** — controls 6px, cards 10px, panels 14px, large surfaces 20px.
Nested radii subtract: an inner radius is the outer radius minus the padding
between them. Not everything is a pill.

**Depth** — on a dark theme, depth comes from surface steps and hairlines,
not from shadows. Elevation is declared **once**: a 1px rule *or* a shadow,
never both. The only shadow in the system belongs to the one element that
genuinely floats above the page — the hero's product preview.

---

## 4. Motion

One easing curve, a few durations.

| Token | Value | Use |
|---|---|---|
| `--motion-duration-instant` | 80ms | press feedback |
| `--motion-duration-fast` | 150ms | hover, colour changes |
| `--motion-duration-base` | 220ms | enters, state changes |
| `--motion-duration-slow` | 320ms | larger transitions |
| `--motion-ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | the house curve |

**What moves**

- One entrance on load: the hero fades and rises with a small stagger.
- One scroll reveal per section: a 16px rise as it enters the viewport,
  once. Only elements below the fold at mount are ever hidden, so content
  can never be stranded by a failed observer.
- One authored moment: the pipeline sweep, which travels the chain once when
  the diagram enters view and holds its final state.
- Hover: a colour or border change in 150ms.
- Press: a scale to 0.985 in 80ms.

**What does not move**

Loops with no purpose — a pulsing heading, a breathing glow, a floating card,
a rotating beam, a cursor spotlight. The cursor spotlight that used to
follow the pointer around the app shell is removed: chrome is chrome.

`prefers-reduced-motion: reduce` collapses every duration to 1ms and turns
the reveal into a cross-fade.

---

## 5. The signature: the registration seal

`VerificationSeal.jsx` — two opposing corner brackets, borrowed from the
registration targets printers use to check that two impressions land in the
same place. That is exactly what this product does with a claim and its
evidence: it checks that they align.

It is the only place Laser Crimson appears as a mark rather than as a
verdict, and it appears on every verified record.

---

## 6. File layout

```
src/styles/
├── index.css              ← entry; imports everything in order
├── tokens/
│   ├── index.css          ← the token layer, imported FIRST
│   ├── color.css          ← Obsidian / Chrome Silver / Laser Crimson
│   │                        + the accent, attention and alarm aliases
│   ├── typography.css     ← families, scale, weights, measures
│   ├── spacing.css        ← 4px grid, section rhythm, gutters
│   ├── radius.css         ← control / card / panel / large
│   ├── elevation.css      ← surfaces, the one shadow, the focus ring
│   └── motion.css         ← durations, easing, springs
├── animations.css         ← the global keyframes
├── materials.css          ← browser surfaces nobody designed
├── landing.css            ← the landing-page scope
├── loaders.css            ← the loading states
├── base.css               ← element defaults, preferences
├── utilities.css          ← the small shared vocabulary
├── components/            ← one stylesheet per component family
│   ├── index.css          ← the family index
│   ├── button.css  nav.css  section.css  hero.css  capabilities.css
│   ├── ledger.css  pipeline.css  matrix.css  benchmarks.css  footer.css
└── app/                   ← the application shell
    ├── shell.css          ← navbar, sidebar, drawer, chrome
    ├── auth.css           ← authentication surfaces
    ├── surfaces.css       ← cards, panels, messages, the workbench
    ├── layers.css         ← stacking and scroll layers
    └── markdown.css       ← the rendered-answer typography
```

**Import order matters.** Tokens come first, so every `var(--…)` resolves.
Tailwind's layers come last, so utility classes win on a tie — the
convention the rest of the codebase already assumes.

The rule that keeps the folder structure professional: **a raw colour value
lives in `tokens/color.css` and nowhere else.** A component stylesheet may
only reference a token. That is what makes "change the alarm shade" a
one-line change instead of a search across fifteen files.

---

## 7. Component vocabulary

| Class | Purpose |
|---|---|
| `.lx-btn` + `--primary` / `--attention` / `--secondary` / `--quiet` | The one button |
| `.lx-panel` | The one translucent surface (used sparingly) |
| `.lx-surface` | A flat surface with a hairline |
| `.lx-display` … `.lx-micro` | The type scale |
| `.lx-measure` | Prose measure cap |
| `.lx-container` | Page content cap, 1320px |
| `.lx-section` / `.lx-band` | Section rhythm and the rule between bands |
| `.lx-signal` | Laser Crimson inline text |
| `.lx-live-dot` | A live status dot |
| `.lx-tab` | Segmented control |
| `.lx-rule` | A hairline |
| `.lx-sr-only` | Screen-reader only text |

---

## 8. Accessibility standard

- Body text ≥ 4.5:1, large text ≥ 3:1. Measured on the rendered surface,
  not declared in the token.
- Every interactive target ≥ 44×44px on coarse pointers, 36px on fine
  pointers for dense navigation rows.
- One visible focus ring for the whole product: 2px Laser Crimson at 3px
  offset.
- Exactly one `<main>` landmark per route.
- Icons come from one set (lucide), one size, one stroke (1.5).
- Colour never travels alone — verdicts carry an icon shape and a word.
- `prefers-reduced-motion`, `prefers-reduced-transparency` and
  `prefers-contrast` are all honoured.

---

## 9. Verification

```bash
npm run lint     # 0 warnings
npm run test     # 33 tests
npm run build
```

Browser verification uses Brave DevTools MCP: DOM and computed-style
inspection, screenshots at 1440 / 1280 / 1024 / 768 / 390 / 320, console
error checks, and Lighthouse.

Current Lighthouse on the landing page: **Accessibility 100 · Best Practices
100 · SEO 100 · Agentic Browsing 97.**

---

## 10. The brand mark — Overlap

The mark is **Overlap**: a solid Chrome Silver disc (the claim) half-grounded in a Chrome
Silver ring (the corpus). The single Laser Crimson point sits at the centre of the supported
half — support is the overlap; everything outside it is unsupported. Flat linework, one
accent, drawn from the same palette as the interface.

- Master: `brand/trustrag-symbol.svg` · usage board: `brand/brand-board.png` · docs: `brand/README.md`
- Rendered in the app by `src/components/common/TrustRagLogo.jsx` (`TrustRagEmblem`)
- Web/app icons: `public/icons/`, wired through `index.html` and `public/manifest.json`

Rules: clear space = the crimson point's diameter; minimum 20 px for the mark, 16 px for the
app-tile/favicon; obsidian/graphite grounds only (black or mono variant on light); never
rotate, outline, recolour, or move the crimson point.
