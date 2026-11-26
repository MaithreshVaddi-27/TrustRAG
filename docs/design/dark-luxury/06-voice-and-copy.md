# 06 — Voice and copy

The product's own language. A reliability tool that writes like a
marketing deck has failed its own test.

---

## Voice

**Precise, forensic, unhurried.** The voice of a document prepared for
audit: it states what was checked, what the result was, and what follows
from it.

| We are | We are not |
|---|---|
| A document prepared for audit | A brochure |
| Reporting a result | Announcing a breakthrough |
| Saying what was measured | Saying what was achieved |
| Calm under a contradiction | Excited that something failed |

The brand does not need to shout. Chrome Silver on Obsidian Black, with
one crimson alarm, is already a deliberate and confident surface.

---

## The rules

### Say what was checked

Headlines name the mechanism.

- ✓ "Every claim, checked against its evidence."
- ✓ "One loop, six stages, one verdict."
- ✓ "Watch a claim fail its check."
- ✗ "Verify everything. Instantly. Forever."
- ✗ "AI-powered trust for the enterprise."

The first says what the product does. The second says nothing that another
product could not say.

### Never invent a claim

A figure without its provenance is a marketing claim, not a measurement.
Every number on the marketing page names its source.

- ✓ "Retrieval recall@8 of 0.889 on the internal 27-query reliability
  fixture." — and a link to the methodology.
- ✗ "99.4% accuracy."

If a figure cannot be traced to a run in `docs/evaluation/`, it does not
go on the page. If a competitor figure is used, it is labelled as a
published literature value rather than presented as our own measurement.

### No hype words

Not: supercharge, seamless, unlock, magic, revolutionize, game-changing,
effortless, powerful, blazing fast, cutting-edge, next-generation.

Not "AI-powered" on everything. The product is a verification tool; it does
not need to announce that it involves a model.

### No exclamation marks

In interface text, and never `!!`.

### Short labels

- "Search", not "Search anything…"
- "Email", not "Enter your email address"
- "Retry", not "Retry connection"

### Changes compare

A change says what it compares to.

- ✓ "+12% vs last month"
- ✓ "3 fewer vs last week"
- ✗ "Improved"

### Sentence case, everywhere

`NAVIGATION` becomes "Navigation". `PAID THIS MONTH` becomes "Paid this
month". `REAL-TIME PIPELINE EXECUTION` becomes "Real-time pipeline
execution". An acronym stays an acronym — MCP, API, SHA-256, NLI, RRF.

### No periods on short strings

Headings, subheads, labels, buttons and captions end without a period.
Only paragraphs of several sentences keep theirs.

### No greeting headlines

"Welcome back, Damir" is a template. The title names the context:
"Settings", "Evidence vault", "Atomic claims".

### Mock data looks real

Plausible numbers and names, never `[X]` or `123,456`.

---

## Error messages

An error names the problem and the recovery.

| Situation | Message |
|---|---|
| Backend down | "Backend unreachable — start the API server to enable analysis." |
| Claims unverified | "Some claims could not be verified against the citation corpus. Inspect the Claims tab for proposition-level breakdown." |
| Password too short | "Password must be at least 12 characters." |
| Email taken | "This email is already registered. Sign in to continue." |

Never:

- "Something went wrong."
- "Error 500."
- "Invalid input." — invalid *what*?

---

## Interface vocabulary

| Instead of | Write |
|---|---|
| "Workspace" | "Knowledge bases" |
| "Entity" | "Knowledge base" / "Document" |
| "Agent" | "Playground" / "Run analysis" |
| "Config" | "Settings" |
| "Telemetry" | "Engine" / "Live status" |
| "Utilisation" | "Usage" |
| "Ascertain" | "Check" / "Verify" |
| "Leverage" | "Use" |
| "Orchestrate" | "Run" |

The product domain already has good, precise words. Use them:
*claim*, *evidence*, *verdict*, *entailment*, *provenance*, *abstain*,
*threshold*, *chunk*, *retrieval*.

---

## Writing for the console

The product is local-first and developer-facing. The empty state of the
playground says:

> Enter a prompt and execute the reliability pipeline to inspect real-time
> claim decomposition, NLI verification, and self-healing recovery.

It explains what will happen and what will come back. It does not say
"Get started" and it does not show a decorative illustration.

---

## Buttons

One primary action and at most one secondary beside it. Anything else
moves out of the hero.

| Good | Bad |
|---|---|
| "Start auditing" | "Start your free trial today!" |
| "Retry" | "Retry connection" |
| "Sign in" | "Sign in to your account" |
| "Run analysis" | "Run analysis" (as a coloured gradient with a glow) |

---

## The brand name

**TRUSTRAG**, always in caps as a wordmark. In prose, "TrustRAG". The
`RAG` is not a separate colour and the wordmark is not a gradient.
