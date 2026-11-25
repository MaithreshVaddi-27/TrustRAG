# Remaining design changes — colour palette (25 Nov 2026)

**Status: proposal list only. No code changed.** Implement only after approval.

---

## Measured current state

Computed from the tokens in `tokens/color.css`:

| Pair | Ratio | Verdict |
|---|---|---|
| silver-050 `#f7f7f6` on obsidian-950 `#080808` | 18.68:1 | excellent |
| silver-500 `#8a8987` on obsidian | 5.73:1 | good |
| crimson-400 `#f04a48` on obsidian | 5.51:1 | good |
| crimson-300 `#f26a68` on obsidian (error text) | 6.71:1 | good |
| crimson-400 on the silver-050 plate (focus ring) | **3.39:1** | passes 3:1 only, marginal |
| crimson-500 `#d41514` on silver plate | 5.00:1 | good |
| crimson-600 `#a81010` on silver plate | 7.13:1 | strong |
| Disabled button text (silver-050 at 40% opacity on obsidian → `#686867`) | **3.59:1** | **fails 4.5:1 text** |
| Surface steps (card `#141416` vs panel `#101012`) | `#040404` apart | very subtle |

After Option A the palette is coherent and the semantic split is correct. The
remaining work is edge-case contrast, token consolidation and hygiene — not a
new brand direction.

---

## P0 — fix before anything else

**1. Disabled state fails text contrast.**
`.lx-btn:disabled { opacity: 0.4 }` (button.css:38) makes the label ~3.59:1 on
obsidian; WCAG AA needs 4.5:1. Replace opacity with a token pair:
`--color-disabled-surface` (graphite-600 `#2e2e33`) and
`--color-disabled-text` (silver-300 `#cdcbcA`, ~5.6:1 on that fill). Keep
`cursor: not-allowed`; add the same treatment to disabled inputs.

**2. Give the focus ring a context token.**
The global crimson-400 ring is 5.51:1 on dark but only 3.39:1 on the new
silver plate. Add `--focus-ring-on-plate: #d41514` (5.00:1) and apply it to
`.lx-btn--primary:focus-visible` and `.lx-btn--secondary` when filled. Keep
crimson-400 on dark chrome. Audit high-contrast mode too: `--focus-ring` is
currently crimson-300 there.

**3. Check the 404 and auth focus paths with the new silver plate.**
Smoke-test keyboard focus on every filled control after items 1–2; the silver
button is new and its focus behaviour changed with the palette.

---

## P1 — palette hygiene (reduces arbitrary choices)

**4. Consolidate the crimson alpha ladder.**
`color.css` now has 13 crimson wash/rule steps (0.045, 0.07, 0.08, 0.1, 0.12,
0.14, 0.24, 0.28, 0.32, 0.38, 0.42, 0.5, 0.55). Replace with four semantic
roles:

| Token | Value | Job |
|---|---|---|
| `--signal-wash-quiet` | `rgba(212,21,20,0.07)` | hover / quiet row |
| `--signal-wash` | `rgba(212,21,20,0.14)` | active surface |
| `--signal-rule` | `rgba(212,21,20,0.42)` | record edge, column rule |
| `--signal-fill` | `#d41514` | seal, alarm |

This is why focus-on-silver drifted: one ramp was doing several jobs.

**5. Name crimson by job, not by step.**
Add aliases `--signal-text` (`#f04a48`, on dark), `--signal-mark` (`#d41514`,
seals/fills), `--signal-on-plate` (`#a81010`, marks on silver). Components use
the alias; the hex stays in `color.css`.

**6. Chart theme has a second source of truth.**
`src/lib/chartTheme.js` hand-mirrors palette hex values (it says so in its
comment). Add a build-time drift check against `tokens/color.css`, or derive the
chart theme from computed CSS variables at runtime. No colour changes — just
palette integrity.

**7. Document the surface ladder explicitly.**
Four obsidian steps only four hex values apart read as one flat colour on some
displays. Decide and document: either widen the card step to ~`#18181b`, or
commit to hairlines as the only depth cue (currently the case). Do not do both
at once — depth must be declared once per the design system.

---

## P2 — optional, not recommended yet

- **No positive/success hue.** Supported verdicts stay silver. Adding green
  would break the single-accent rule; use weight and position instead.
- **Warm Ivory / Cool Platinum variants** from the approved proposal remain on
  the table only if the brand character changes. Not needed now.
- **Remove the deprecated `--attention*` aliases** in a future cleanup release,
  once no external consumers exist.
- **Automate the one-primary-per-view rule** with a test that fails if a route
  renders more than one `.lx-btn--primary`; the rule is currently verified by
  hand.
- **Re-run Lighthouse** after the palette change (Accessibility / Best
  Practices / SEO were 100 before).

---

## What I would do first

Items **1 + 2** together — they are the only actual accessibility defects and
they touch one file each. Then **4 + 5** as a single token refactor. Items 6–7
and P2 are discretionary.
