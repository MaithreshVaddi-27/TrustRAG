# 04 — Patterns

Layouts, section rhythms, and the state matrix. These are the arrangements
the components compose into.

---

## Page architecture

Every route follows the same frame.

```
┌──────────────────────────────────────────────────────────────┐
│  .lx-topbar    brand · engine telemetry · primary action     │  60px, raised, hairline
├───────────────┬──────────────────────────────────────────────┤
│               │                                              │
│  .lx-sidebar  │  .lx-main                                    │
│  240px        │  scrollable content                          │
│  (72px        │                                              │
│   collapsed)  │                                              │
│               │                                              │
│  .lx-sidebar  │                                              │
│  __footer     │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

- The shell is `100dvh`, not `100vh`, so mobile browser chrome does not
  clip the footer.
- The content area scrolls; the shell does not.
- The sidebar collapses to 72px and the preference persists in
  `localStorage` under `trustrag_sidebar_collapsed`.
- `⌘B` / `Ctrl+B` toggles it, and the shortcut is shown as a keycap.
- Below 768px the sidebar is replaced by `.lx-app-drawer`, a full-height
  sheet that slides from the left along a single path, traps focus on
  open, closes on `Escape` and locks the page behind it.

### Landing routes have no shell

`/`, `/login` and `/register` render standalone. The landing page is its
own composition; the auth pages use `.lx-auth`.

---

## Section rhythm

A band is a section with a rule at the top. The rule is what separates
sections — not whitespace alone.

```
────────────────────────────────────────────────  ← --rule
                                                 ← 40px (--step-10)
  Section heading                     Lede
  ────────────────────────────────────  ← 2-col at ≥1024px
                                                  
  Content
```

| Token | Value |
|---|---|
| Rule to heading | `--step-10` (40px) |
| Heading to content | `--step-10` (40px) |
| Section to section | `--section-space` (96px) |

At ≥1024px the heading and the lede sit side by side on one baseline
(`align-items: end`), heading left and lede right, capped at 52ch. Below
that they stack.

### The heading carries its own weight

There is no eyebrow label above it, and no section number. The heading
speaks.

```jsx
<SectionBand
  id="pipeline"
  title="One loop, six stages, one verdict."
  lede="Every stage below is in the path of every answer. The diagram follows your scroll through the loop."
>
  <PipelineDiagram />
</SectionBand>
```

---

## The landing page composition

| # | Section | Kind | Purpose |
|---|---|---|---|
| 1 | Hero | Asymmetric split | The promise, and the product itself |
| 2 | Pipeline | Diagram | The mechanism |
| 3 | Sandbox | Interactive ledger | Proof |
| 4 | Capabilities | Specification + code | How it is built |
| 5 | Benchmarks | Ranked table | Evidence |
| 6 | Comparison | Specification table | The decision |
| 7 | CTA | Statement | The close |
| 8 | Footer | Ruled index | The way out |

### The hero is a split, not a stack

The copy sits left; the right column carries a **real evidence record** from
the workbench, not an illustration of one. It is the only element on the
page that reads as an object, and it earns the single shadow.

The headline is set as three deliberate lines in the content file. It is
left-aligned and capped at 16ch so the lines never re-wrap.

Under the actions, a quiet footnote states where the number came from and
links to the methodology. A reliability product that publishes a figure
without its provenance has failed its own test.

### One record, two states

The hero preview shows one supported record and one contradicted record.
The contradicted record carries the crimson edge, the seal and the crimson
verdict — the only colour in the hero.

---

## The record

The system's core unit. A claim, the evidence it was checked against, and
the verdict.

```
┌──────────────────────────────────────────────────┐
│  Claim 03                             Registered  │  ← seal
├──────────────────────────────────────────────────┤
│  Every atomic claim is scored against the cited  │  ← the claim
│  corpus before the answer is emitted.            │
│                                                  │
│  chunk_18 · trustrag_sys_arch_v2.pdf · p. 29     │  ← mono
│  sha256 3f9a2c8e…c2e1                           │  ← mono
├──────────────────────────────────────────────────┤
│  ✓ Supported                    entailment 0.987│
└──────────────────────────────────────────────────┘
```

A contradicted record gets a crimson border and a crimson left edge. Its
conflict text sits in a crimson-ruled inset.

---

## The ledger

A document-like panel: a mono header carrying the document identity, the
query in the display face, then ruled claim rows, then the recovery band.

The mono header is how a record identifies itself — `trustrag_sys_arch_v2.pdf
· 3 claims`. A human reading a file header recognises it instantly.

---

## The layer stack

Ordered plates separated by hairlines, each with its own specification on
the right. This replaces a grid of equal cards with something that reads
like a document.

```
01  ─────────────────────────────────────────────
    LangGraph self-healing state machine         Recovery bound  2 iterations
    When a run's aggregation drops below…        Trigger         confidence < 0.70
    LangGraph · StateGraph · Conditional edge
02  ─────────────────────────────────────────────
    Atomic claim decomposition                   Granularity     propositional
    …
```

The layer number carries information — the sequence *is* the information —
so it is not a decorative section number.

---

## The comparison table

Three columns separated by hairlines. The TrustRAG column is marked with
a **crimson** hairline, because it is the column that differs.

At <900px each row stacks and every column carries its own label, so the
comparison survives 320px without becoming a different design.

The filter above the table is a segmented control whose active tab is
marked with a 2px crimson rule.

---

## The benchmark table

Ranked rows with thin bars. One accent leads: the row that matters is
Chrome Silver; every other row sits in a quiet step of the ramp.

Each table carries a **caption** that names where the numbers came from.
A figure without its provenance is a marketing claim, not a measurement.

The latency table says explicitly that longer bars are slower, so the
metric direction is never ambiguous.

---

## The pipeline diagram

Linework. A hairline runs the whole chain behind the nodes, which are
opaque so the line reads as passing between them. This is how a real
diagram does it and it cannot drift out of alignment.

The final stage — "Ground" — carries a crimson ring, because it is where
the verdict is produced.

One authored motion: a highlight travels the chain with the reader's
**scroll**, lighting each stage as it is reached, then holds its final state.
It is finite and tied to input, never a loop. Under reduced motion the diagram
is shown complete with no movement.

---

## States

Every surface ships these.

| State | Treatment |
|---|---|
| **Loading** | A skeleton in the surface's own shape, or a spinner. Never a spinner in the middle of an empty page. |
| **Empty** | A heading, one sentence of guidance, and the action that fills it. No illustration. |
| **Error** | `role="alert"`, crimson, names the problem and the recovery. Never "Something went wrong." |
| **Busy** | The control is disabled and shows progress. Input is never locked during a transition. |
| **Disabled** | 40% opacity, `cursor: not-allowed`, still legible. |
| **Hover** | A colour or border change in 150ms. Never a scale. |
| **Focus** | 2px crimson at 3px offset, always visible. |
| **Selected** | A surface step plus a hairline, or a 2px crimson rule. |

### Error copy

An error names the problem and the recovery.

- ✗ "Backend unreachable — start the API server to enable analysis."
- ✗ "Some claims could not be verified against the citation corpus. Inspect
  the Claims tab for proposition-level breakdown."
- ✗ "Password must be at least 12 characters."

Not:

- ✗ "Something went wrong."
- ✗ "Error 500."

---

## Responsive behaviour

| Breakpoint | Behaviour |
|---|---|
| ≥1280px | Full layout. Sidebar 240px. Engine telemetry visible in the top bar. |
| 1024–1279px | Sidebar visible, telemetry collapses to the mobile strip below the top bar. |
| 768–1023px | Sidebar hidden, replaced by the drawer. Two-column content stacks. |
| 390–767px | Single column. The pipeline becomes a vertical chain. Capability list and panel stack. |
| ≤389px | Single column, tighter gutter, the landing nav drops its primary action (it is in the hero). |

Rules that hold at every width:

- No horizontal page scroll. The only thing that may scroll sideways is a
  code block, and it scrolls itself.
- No text below 11px.
- The table row heights do not change between breakpoints.
- Touch targets are ≥44px on coarse pointers, 36px for dense navigation
  rows on a mouse.
- The hero's headline uses `clamp()`, so it steps down rather than
  overflowing.

---

## Data display

- A trend is a line. A comparison is bars. A share is one stacked bar or a
  list with bars. A single goal is a progress bar.
- One accent per chart. The thing that matters gets Chrome Silver or
  crimson; everything else sits in neutral steps.
- No rainbow bars inside one series. No glowing bars. No uppercase day
  labels.
- Numbers use `tabular-nums` and one format across the screen.
- If a chart is placeholder noise, replace it with data that says
  something real.
- Stat cards are numbers: a label, a big figure, and a change that says
  what it compares to. No sparklines, mini bars or decorative icons.
