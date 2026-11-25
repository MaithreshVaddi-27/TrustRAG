# 03 — Components

The component vocabulary. Each entry names the class, what it is for, and
when **not** to use it.

---

## The rules that apply to everything

1. **One container.** A card is a surface with a hairline. It is not a
   layout device, and it does not nest.
2. **One accent.** Chrome Silver is the accent. The primary action is an
   off-white plate with obsidian text.
3. **One alarm.** Laser Crimson is a signal: a caught contradiction, the
   registration seal, a live status, focus, or a destructive action. It is
   never an action colour and never decoration.
4. **One icon set.** Lucide. One size. 1.5px stroke. Icons take the
   colour of their text role and never get a colour of their own.
5. **One focus ring.** 2px Laser Crimson at 3px offset.
6. **One rhythm.** Everything on the 4px grid.

---

## Buttons — `.lx-btn`

```jsx
<button className="lx-btn lx-btn--primary">Sign in</button>
<button className="lx-btn lx-btn--secondary">Read the methodology</button>
<a className="lx-btn lx-btn--quiet">Back to overview</a>
```

| Variant | Treatment | Use |
|---|---|---|
| `--primary` | Chrome Silver plate, obsidian text, bottom registration hairline | The one focal action per view |
| `--secondary` | Hairline outline, silver text | Everything else |
| `--quiet` | Text only, no border | Tertiary, inline, navigational |
| `--alarm` | Deep crimson fill | A destructive action |
| `--attention`, `--attention-quiet` | Deprecated silver aliases | Do not use in new code |

| Modifier | Effect |
|---|---|
| `.lx-btn--large` | 52px tall, 16px type |
| `.lx-btn--block` | Full width |

Minimum target: 44×44px. Press feedback scales to 0.985 in 80ms.

**Do not** use a gradient button, a glow, or a second primary action on the
same surface. If two actions matter, one is primary and one is secondary.

Only a filled crimson (alarm) button carries a silver focus ring: a crimson ring on a
crimson fill is 1.2:1 against the button it outlines. Every other focusable
element keeps the crimson ring.

The React primitive is `components/ui/Button.jsx`.

---

## Surfaces

| Class | Use |
|---|---|
| `.lx-panel` | The one translucent surface. Used only where content genuinely overlaps other content. |
| `.lx-surface` | A flat surface with a hairline. |
| `.lx-record` | A verification record: a claim, its evidence, its verdict. |
| `.lx-ledger` | A document-like panel with a ruled header. |

**Depth is declared once.** A surface has a 1px rule *or* a shadow, never
both. The only shadow in the system is `--shadow-preview`, used by
`.lx-preview`.

---

## Typography utilities

| Class | Size | Use |
|---|---|---|
| `.lx-display` | `--size-display` | The landing headline |
| `.lx-display-sm` | `--size-display-sm` | The closing CTA |
| `.lx-h1` | `--size-h1` | A screen's title |
| `.lx-h2` | `--size-h2` | A section heading |
| `.lx-h3` | `--size-h3` | A panel heading |
| `.lx-lede` | `--size-lede` | Standfirst |
| `.lx-body` | `--size-body` | Body copy |
| `.lx-body-sm` | `--size-body-sm` | Secondary copy |
| `.lx-label` | `--size-label` | Form labels, tabs, buttons |
| `.lx-micro` | `--size-micro` | Mono metadata |

`.lx-measure` caps prose at 68ch. `.lx-measure--narrow` caps a standfirst
at 52ch.

**Do not** combine a display face with a size under 20px. Didot's hairlines
go spindly below that.

---

## Layout utilities

| Class | Use |
|---|---|
| `.lx-container` | Page content cap, 1320px, with the gutter |
| `.lx-section` | Section rhythm, 6rem block padding |
| `.lx-band` | A section with a rule at the top and a heading 40px below |
| `.lx-rule` | A hairline; `--faint` and `--strong` modifiers |

---

## The signature — `.lx-seal`

The registration seal: two opposing corner brackets, borrowed from the
registration targets printers use to check that two impressions land in the
same place. That is exactly what this product does with a claim and its
evidence — it checks that they align.

```jsx
import VerificationSeal from '@/components/landing/VerificationSeal'

<VerificationSeal />              {/* crimson — the default */}
<VerificationSeal tone="silver" />
```

It is the only place Laser Crimson appears as a mark rather than as a
verdict. It appears on every verified record.

---

## Verdict — `.lx-verdict`

```jsx
<Verdict status="supported" />
<Verdict status="contradicted" />
<Verdict status="unsupported" />
<Verdict status="unknown" />
```

The icon carries the verdict colour; the label always uses the readable
text role. Colour never travels alone — the icon shape differs per verdict
so it survives a monochrome display, and the word is always there.

The React primitive is `components/ui/Badge.jsx`, with
`components/workbench/ReliabilityBadge.jsx` for the numeric band variant.

---

## The application shell

| Class | Use |
|---|---|
| `.lx-shell` | The frame: 100dvh, obsidian, overflow hidden |
| `.lx-topbar` | The top bar: 60px, raised surface, hairline bottom |
| `.lx-topbar__brand` | Emblem plus wordmark |
| `.lx-telemetry` | The engine readout |
| `.lx-telemetry__item` | One mono telemetry value |
| `.lx-dot` | A status dot; `--live` for crimson, `--alarm` for crimson light |
| `.lx-icon-btn` | A 40px square icon button |
| `.lx-userchip` | The account control |
| `.lx-sidebar` | 240px, or 72px collapsed |
| `.lx-navlink` | A navigation row, 36px (44px on coarse pointers) |
| `.lx-navlink--active` | Selected: silver text plus a 2px crimson rule |
| `.lx-navlink__meta` | Quiet mono counts, never a glowing pill |
| `.lx-sidebar__footer` | The pinned status widget and collapse control |
| `.lx-kbd` | A keyboard shortcut keycap |
| `.lx-alarm` | The backend-unreachable band |
| `.lx-main` | The content area |
| `.lx-app-drawer` | The mobile navigation sheet |

---

## Authentication

| Class | Use |
|---|---|
| `.lx-auth` | The centred column on obsidian |
| `.lx-auth__column` | 24rem max |
| `.lx-auth__back` | The back link |
| `.lx-auth__brand` | Emblem, wordmark, tagline |
| `.lx-auth__card` | The one hairline card |
| `.lx-field` | A labelled field |
| `.lx-field__label` | The label |
| `.lx-field__input` | 44px tall, 16px type so iOS does not zoom |
| `.lx-field__affix` | The password toggle, a 44px hit area |
| `.lx-alert` | A message; `--error` is crimson, `--info` is a neutral well |

---

## Landing sections

| Class | Use |
|---|---|
| `.lx-preview` | The hero's product preview — the one shadow in the system |
| `.lx-record` | A verification record |
| `.lx-record--contradicted` | A contradicted record, crimson edge |
| `.lx-claim` | A claim row in the sandbox ledger |
| `.lx-recovery` | The recovery band |
| `.lx-scenario` | A scenario switch; the active one has a crimson border |
| `.lx-capability` | A capability row in the left list |
| `.lx-capabilities__panel` | The panel that shows the selected capability |
| `.lx-code` | A code block |
| `.lx-pipeline` | The pipeline diagram |
| `.lx-stage` | One stage node |
| `.lx-matrix` | The comparison specification table |
| `.lx-bench` | The benchmark table |
| `.lx-cta` | The closing call to action |

---

## The app primitives

`components/ui/` holds four primitives. They are the shared vocabulary for
the application surfaces.

| Primitive | Purpose |
|---|---|
| `Button` | The one button. Handles loading, disabled and press feedback. |
| `Card` | A surface with a hairline. `elevation` is `flat`, `raised`, `panel` or `inset`. |
| `Badge` | The verdict marker. |
| `PageHeader` | The editorial rhythm for a screen: title, description, count, actions. |

`PageHeader` takes an optional `eyebrow`, but the house rule is that the
heading carries its own weight and no eyebrow is used above it.

---

## Composing, not collecting

The failure mode this system exists to prevent is a page made of
same-sized cards, each holding an icon, a heading and a paragraph. It
looks like a design system and says nothing.

**Instead, prefer a specification.** A specification reads like a document
a person wrote:

- A **record** — a claim, its evidence, its verdict.
- A **ledger** — a ruled document with a mono header.
- A **layer stack** — ordered plates separated by hairlines, each with its
  own specification on the right.
- A **table** — ranked rows with thin bars and a caption that says where
  the numbers came from.
- A **diagram** — linework that explains a mechanism.

Each of those is a different *kind* of thing, and a page built from them
reads as a document rather than a grid.
