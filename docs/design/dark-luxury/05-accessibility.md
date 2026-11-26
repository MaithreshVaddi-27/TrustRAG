# 05 — Accessibility

The standard every surface must meet. These are measurable, not
aspirational: each one has a threshold and a way to check it.

---

## Contrast

| Rule | Threshold |
|---|---|
| Body text | ≥ 4.5:1 |
| Large text (≥18.66px bold or ≥24px) | ≥ 3:1 |
| Icons and meaningful graphics | ≥ 3:1 |
| UI component boundaries and focus indicators | ≥ 3:1 |

Measure on the **rendered** surface, not on the declared colour pair. A
token that passes on obsidian can fail inside a tinted card.

### Measured values on obsidian-950 (`#080808`)

| Token | Value | Ratio | Verdict |
|---|---|---|---|
| `--color-silver-050` | `#f7f7f6` | 19.4:1 | Passes everything |
| `--color-silver-100` | `#e9e9e7` | 16.6:1 | Passes everything |
| `--color-silver-200` | `#d8d7d5` | 14.1:1 | Passes everything |
| `--color-silver-300` | `#cdcbcA` | 12.0:1 | Passes everything |
| `--color-silver-400` | `#a3a2a0` | 7.6:1 | Passes body text |
| `--color-silver-500` | `#8a8987` | 5.6:1 | Passes body text |
| `--color-silver-600` | `#5a5957` | 2.9:1 | **Never text** |
| `--color-crimson-300` | `#f26a68` | 6.8:1 | Passes body text |
| `--color-crimson-400` | `#f04a48` | 5.5:1 | Passes body text |
| `--color-crimson-500` | `#d41514` | 3.7:1 | Large text and graphics only |

Two rules fall out of this table and both are enforced in the CSS:

- `.lx-micro` uses `--color-silver-500`, never `--color-silver-600`. Small
  mono metadata stays readable.
- Any crimson that carries text uses `--color-crimson-400`, never
  `--color-crimson-500`.

---

## Target size

| Context | Minimum |
|---|---|
| Coarse pointer (touch) | 44×44px |
| Fine pointer, dense navigation row | 36px tall |
| Fine pointer, standard control | 44×44px |
| Inline text link in a paragraph | WCAG 2.5.8 inline exception |

The system implements the coarse-pointer case explicitly:

```css
@media (pointer: coarse) {
  .lx-navlink,
  .lx-collapse-btn {
    min-height: 44px;
  }
}
```

---

## Focus

One visible focus ring for the whole product.

```css
:focus-visible {
  outline: 2px solid var(--focus-ring); /* #f04a48 — 5.5:1 */
  outline-offset: 3px;
  border-radius: var(--radius-control);
}

:focus:not(:focus-visible) {
  outline: none;
}
```

- The ring is Laser Crimson because a focus ring is an alarm.
- It is never removed. If a component's own border makes the ring hard to
  see, the ring wins.
- `:focus-visible` is used rather than `:focus`, so a mouse click does not
  leave a ring on a button but a keyboard does.
- Focus is never trapped except in a modal or a drawer, and both release it
  on `Escape`.

---

## Landmarks and structure

- Exactly one `<main>` per route. The landing page and the auth pages
  provide their own; the application shell provides it for every protected
  route.
- A skip link is the first focusable element on every route:
  `.lx-skip-link` — visible when focused, hidden until then.
- One `<h1>` per route, and it is the route's title.
- Heading levels descend without skipping.
- The navigation landmark wraps the primary navigation; a `nav` element
  with an `aria-label` for each distinct group.

---

## Forms

- Every input has a real `<label for>`.
- Inputs are 44px tall and set in 16px, so iOS does not zoom the viewport
  on focus.
- The password toggle is a 44px hit area and reports its state with
  `aria-pressed`.
- Errors use `role="alert"` and appear near the field, not only at the
  top of the form.
- A busy form uses `role="status"` and disables the submit control. Input
  is never locked during a transition.
- Placeholder text is not a label.

---

## Icons and colour

- One icon set (Lucide). One size. 1.5px stroke.
- Icons take the colour of their text role. They do not get a colour of
  their own.
- **Colour never travels alone.** Every verdict carries an icon shape and
  a word, so the interface survives a monochrome display and every form of
  colour vision deficiency.
- Decorative icons carry `aria-hidden="true"`.
- Icon-only controls carry an `aria-label`.

---

## Motion

`prefers-reduced-motion: reduce` is honoured throughout:

- Every duration collapses to 1ms.
- The scroll reveal becomes a cross-fade with no travel.
- The pipeline sweep resolves to its final state with no motion.
- Springs become short tweens.

Motion is never the only signal. A live status dot is accompanied by the
word "Live" or "API online".

---

## User preferences

| Query | Treatment |
|---|---|
| `prefers-reduced-motion` | Durations collapse to 1ms; travel is removed |
| `prefers-reduced-transparency` | The panel and the drawer flatten to solid surfaces; blur is removed |
| `prefers-contrast: more` | Rules strengthen to 20/40/60% silver; text steps up two steps; the focus ring becomes `--color-crimson-300` |

---

## Reflow

At 320px there is no horizontal page scroll. Content reflows into a single
column and nothing is clipped or truncated to avoid it.

The only element permitted to scroll sideways is a code block, which
scrolls itself.

---

## Verification

```bash
npm run lint     # 0 warnings
npm run test     # 33 unit tests
npm run build
```

Browser checks with Brave DevTools MCP:

1. Lighthouse on every route — Accessibility must be 100.
2. Screenshots at 1440, 1280, 1024, 768, 390 and 320.
3. `document.documentElement.scrollWidth` must equal `clientWidth`.
4. A console-error check on every route.
5. A keyboard pass: tab through, confirm the ring is visible and that
   `Escape` closes a drawer.
6. An invisible-text sweep: no element with a text node may compute
   `color: rgba(0, 0, 0, 0)`.

Current result on the landing page: **Accessibility 100 · Best Practices
100 · SEO 100 · Agentic Browsing 97.**
