# 09 — Pages

The page-by-page redesign. One page at a time, each one audited, planned,
implemented and verified before the next begins.

---

## The order

| Phase | Surface | Depends on | State |
|---|---|---|---|
| P4.1 | Application shell | — | Done |
| P4.2 | Dashboard | shell | Done |
| P4.3 | Knowledge bases | shell | Done |
| P4.4 | Documents | shell | Done |
| P4.5 | Playground | shell | Done |
| P4.6 | Evidence, claims, conflicts | shell | Done |
| P4.8 | Execution trace | shell | Done |
| P4.9 | Settings | shell | Done |
| P4.10 | Authentication | shell | Done |
| P4.11 | Layout stability, programme close | all | Done |
| P4.12 | Landing page — content truth | — | Done |
| P4.13 | Frontend audit | all | Done |
| P4.3 | Knowledge bases | shell |
| P4.4 | Documents | knowledge bases |
| P4.5 | Playground | shell, knowledge bases |
| P4.6 | Evidence and verification | shell, playground |
| P4.7 | Experiments and evaluation | shell, playground |
| P4.8 | Traces | shell, playground |
| P4.9 | Settings | shell |
| P4.10 | Authentication | — |

---

## P4.1 — Application shell

The shell is the frame every other page sits in, so it was done first.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | The top bar overflowed at 1024px. The API status was clipped by the collapse control and the sign-out button was cut off by the viewport edge. | High |
| 2 | The sidebar footer read "Self-healing loop · StateGraph v1.0 active" — a hardcoded string that claimed the pipeline was running whether or not anything was listening. | High |
| 3 | The mobile drawer covered the entire viewport. It was a takeover, not a drawer, and it hid the page the user was navigating away from. | Medium |
| 4 | The sidebar and the drawer each carried their own copy of the navigation array. Two sources of truth, and they had already drifted. | Medium |
| 5 | The navigation was divided by bare rules. A separator says "something changes here"; it does not say what. | Medium |
| 6 | The account avatar rendered the first two characters of the email address — "AU" for audit@example.com. | Medium |
| 7 | Clicking the avatar signed you out. One stray click ended the session, with no confirmation and no indication of who you were. | Medium |
| 8 | The mobile drawer moved focus to its close button but neither trapped focus inside it nor restored focus when it closed. | Medium |
| 9 | The brand block did not respond to width — the wordmark and the subtitle stayed at full size down to 320px. | Low |
| 10 | The collapse control appeared twice with the same accessible name. | Low |

### What changed

**One navigation.** `components/layout/navigation.js` is the single source for
the eight routes, in three named groups — **Workbench**, **Corpus** and
**System**. The sidebar and the drawer are two renderings of the same list.
The group labels say what the rows below them are for.

**A real status.** `components/layout/EngineStatus.jsx` reports what the
health probe and the provider registry actually say: *Engine unreachable*
when the API does not answer, *Checking engine* while the probe is in
flight, and *Engine online* with the provider and model once it does. The
hardcoded claim is gone.

**A header that fits.** The telemetry sheds items as the bar narrows: the
engine and the embedding model step down at 1024px and 1280px, the
accelerator at 1440px. The API status is the last to go, because it is the
one that has to be present. The brand drops its subtitle at 1280px and
keeps only the mark at 640px.

**An account menu.** `components/layout/AccountMenu.jsx` replaces the
sign-out-on-click avatar. It shows who you are, offers Settings, and makes
signing out an explicit item. Escape closes it, a click outside closes it,
and focus returns to the trigger.

**A drawer, not a takeover.** The drawer is anchored to the left edge at
288px with a scrim behind it, so the page stays visible. Focus is trapped
inside it while it is open and returns to the trigger when it closes.

**Real initials.** `accountInitials()` reads the display name first and
falls back to the local part of the email — "AR" for "Audit Reviewer",
"AI" for "audit.jones@example.com", never "AU" for "audit@example.com".

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 8 files, 34 tests, all pass |
| `npm run build` | Succeeds in ~2.1s |
| Lighthouse — desktop | Accessibility 100 on all ten routes |
| Lighthouse — mobile | Accessibility 100 on all ten routes |
| Responsive | No page overflow and no top-bar overflow at 1440 / 1280 / 1024 / 768 / 390 / 320 |
| Landmarks | Exactly one `<main>` and one `<h1>` per route |
| Console | 0 errors and 0 warnings across all ten routes |
| Interactions | Drawer opens, traps focus, closes on Escape and restores focus; account menu opens, closes on Escape and on an outside click, and restores focus; sign-out clears the session and routes to `/login` |

### Open issues

- `GET /api/v1/evidence` returns **HTTP 500** from the backend. The
  frontend renders the error state correctly, but Lighthouse's Best
  Practices score on `/evidence` is 96 because of the failed request, and
  the evidence vault cannot show populated records until the endpoint
  works. This is a backend defect and was not changed.
- Lighthouse reports SEO 63 on the authenticated routes because
  `robots.txt` disallows them. That is deliberate — the workbench requires
  a session and is not useful in an index — so the score is expected. The
  public landing page scores 100.

---

## P4.2 — Dashboard

The operator's overview. Four questions, in the order they matter.

The panel that answers the first question carries the registration seal: silver
when the instrument has nothing to report, crimson when it catches a conflict
or contradiction. It is the same mark used on verified records — no new colour,
no second accent.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | The page opened with a marketing panel — the product's own name and a pitch. A dashboard is not a landing page, and the hero repeated what the top bar already said. | High |
| 2 | **The mean reliability averaged abstentions in.** A run that abstained scores zero because there was no answer, not because the answer was unreliable. Averaging those in reported an unreliable answer where the system reported none. | High |
| 3 | Nothing on the screen said what had gone wrong. Conflicts were fetched, counted, and folded into a subtitle — the one number that mattered was the one that was least visible. | High |
| 4 | "Synced less than a minute ago" was updated by a timer every 30 seconds. It measured the clock, not the data. | High |
| 5 | "Analyses executed · Evidence-linked" was a label restating the label above it. The run had actually abstained. | Medium |
| 6 | "Claims decomposed · 0 verified · 2 flagged" mixed two different populations — verified claims and source conflicts — into one figure's subtitle, and never showed contradicted claims at all. | Medium |
| 7 | "Inspect" on every run linked to the playground, which starts a *new* run. There was no way to reach a specific run's trace from the list. | Medium |
| 8 | The same pipeline primer was on the dashboard and in the playground's empty state, for every user, on every visit. | Medium |
| 9 | The knowledge bases were a bare count. Nothing said whether a collection was queryable. | Medium |
| 10 | "Run analysis" appeared twice — in the top bar and in the page header — 60px apart. | Low |

### What changed

**The page answers four questions, in order.**

1. **What needs my attention?** — `AttentionPanel` leads the page. It lists
   contradicted claims, source conflicts and runs that produced no verified
   answer, each with what it means and where to go. When there is nothing,
   it says so in one line: silence would be ambiguous.
2. **How is the corpus doing?** — `StatStrip` (four figures, one ruled strip)
   and `WorkspacePanel` (the collections, their document counts, their
   pinned vector space and when they were last queried).
3. **Is reliability holding?** — the reliability progression and the claim
   distribution.
4. **What has happened lately?** — `ActivityFeed`, every run and what the
   verifier concluded.

**The metrics are honest.**

- Mean reliability is computed over **delivered answers only**. Runs that
  abstained or failed are counted separately, and the figure says how many
  answers it covers.
- The reliability curve plots delivered answers only, and the panel's
  footnote says how many runs were left off it.
- Every figure's second line is a real measurement. "Evidence-linked" was
  decoration; it is now "1 answered · 1 without an answer".
- "Synced X ago" comes from the least fresh feed's own fetch timestamp, so
  it moves when the data moves.

**The activity feed reads the run.** Each row carries the query, the
verdict, the collection it ran against, the time and a link to that run's
trace — `/traces/:id`, which is the only per-run view the product has. The
verdict badge appears only when there is a verdict: a run with no answer
shows its status, not a 0% score in crimson.

**The primer is a first-run guide.** The pipeline layer stack is shown
only while the workspace has never run anything. After the first run it
is noise, and it is already on the playground's empty state.

**The workspace is a specification, not a count.** A table: collection,
documents, vector space, last run.

### Files

| File | Change |
|---|---|
| `pages/DashboardPage.jsx` | Rewritten around the four questions |
| `components/dashboard/StatStrip.jsx` | New — replaces `MetricsGrid` |
| `components/dashboard/AttentionPanel.jsx` | New |
| `components/dashboard/WorkspacePanel.jsx` | New |
| `components/dashboard/ActivityFeed.jsx` | New — replaces `RecentAnalysesFeed` |
| `components/dashboard/ReliabilityChart.jsx` | Plots delivered answers only |
| `components/dashboard/HeroBanner.jsx` | Deleted — marketing copy on an app screen |
| `components/dashboard/MetricsGrid.jsx` | Deleted |
| `components/dashboard/ObservabilityBar.jsx` | Deleted — folded into the page header |
| `components/dashboard/RecentAnalysesFeed.jsx` | Deleted |
| `pages/DashboardPage.test.jsx` | New — 8 tests over the metric rules |

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 9 files, 43 tests, all pass |
| `npm run build` | Succeeds in ~2.2s |
| Lighthouse — dashboard | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Responsive | No page or top-bar overflow at 1440 / 1280 / 1024 / 768 / 390 / 320 |
| Landmarks | One `<main>`, one `<h1>`, headings in order |
| Console | 0 errors, 0 warnings |

---

## P4.3 — Knowledge bases

The corpus manager. Where the collections are, what is in them, and how
documents get into them.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | The page was a stack of identical panels — one per collection. Twenty collections made a wall, not a list, and the information in each one is tabular. | High |
| 2 | **Every collection carried a primary "Upload document" button.** N primary buttons on a page means no primary action. | High |
| 3 | **The documents were hidden.** The list collapsed by default behind a disclosure, and opening it issued a query per collection. The content you uploaded was one click away and invisible. | High |
| 4 | **A modal for a two-field form.** Creating a collection interrupted the work and hid the list it was about to change. | Medium |
| 5 | The document row said "Indexed chunks" as a placeholder — the API returns no chunk count, so the label was a lie. | Medium |
| 6 | The "Supported document formats" panel was permanent documentation at the bottom of every visit, duplicating the file input's own accept list. | Medium |
| 7 | The upload result flashed for 3.5 seconds and was gone. Navigating away mid-ingest lost the outcome. | Medium |
| 8 | Every collection had a 36px icon box before its name — decoration that added nothing. | Low |
| 9 | The filter had no way to clear it other than selecting all and deleting. | Low |
| 10 | The list had no sort, so the order was whatever the database returned. | Low |

### What changed

**The collections are a specification.** One table: collection and its
description, document count, vector space, when it was created. Every column
is a measurement the API actually returns. Below 768px the columns become
labelled rows, so the table is readable at 320px without a horizontal scroll.

**One collection opens at a time.** Opening it reveals the documents as a
ruled record list — file and format, size, content hash, when it was
indexed, its ingestion state — and the upload control moves inside it.
There is exactly one upload button on the screen, in the one place where
uploading makes sense.

**The content hash replaced the fake chunk count.** The API returns the
document's SHA-256 and no chunk count, so the hash is what the row shows.
It is the value that pins the content, which is the point of showing a
document at all.

**Creation is inline.** The form opens above the ledger, takes the name
first, and reports its error next to the field. No dialog, no focus trap,
no interrupted list.

**The ingestion state is honest.** The upload returns when the file is
queued, not when it is embedded, so the confirmation says "uploaded —
chunking and embedding it now" and the row's own chip says "Indexing" until
the backend says otherwise.

**Sorting and a clearable filter.** Newest, name, or document count, and
an × that clears the filter.

### Files

| File | Change |
|---|---|
| `pages/KnowledgeBasesPage.jsx` | Rewritten around the ledger |
| `components/kb/CollectionLedger.jsx` | New — the specification table |
| `components/kb/DocumentTable.jsx` | New — the upload surface and document list |
| `components/kb/DocumentRow.jsx` | Rewritten as a record row |
| `components/kb/CreateCollectionForm.jsx` | New — the inline form |
| `components/kb/CreateKnowledgeBaseDialog.jsx` | Deleted — replaced by the inline form |
| `components/kb/KnowledgeBaseCard.jsx` | Deleted — replaced by the ledger |
| `pages/KnowledgeBasesPage.test.jsx` | New — 5 tests over the ledger and the form |

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 10 files, 48 tests, all pass |
| `npm run build` | Succeeds in ~2.4s |
| Lighthouse — desktop and mobile | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Responsive | No page or top-bar overflow at 1440 / 1280 / 1024 / 768 / 390 / 320 |
| Landmarks | One `<main>`, one `<h1>` per route |
| Console | 0 errors, 0 warnings |
| Behaviour | Creating a collection, uploading a document, expanding a row, filtering, sorting and deleting all verified in the browser |

---

## P4.4 — Documents

The record for one indexed document. The API has always exposed
`GET /api/v1/documents/{id}`; nothing in the frontend called it, and a
document's temporal-validity window was never shown anywhere.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **A document had no record of its own.** It existed only as a row in a collection ledger — a filename, a size and a state. Nothing answered "what is this document, and when does it apply?" | High |
| 2 | **The effective window was invisible.** `effective_from` and `effective_until` — the interval in which retrieval may treat a document as authoritative — were stored on every document and shown for no document. | High |
| 3 | **The ingestion error was unreachable.** A failed ingestion stores the backend's own `error_message`. Nothing in the UI could show it; the row's chip just said "Failed". | High |
| 4 | The hash was truncated to twelve characters in the ledger. Twelve characters do not identify a document. | Medium |
| 5 | There was no way to reach a document from its own identifier. | Medium |

### What changed

**A document is a record with a route.** `/documents/:id` — reachable from the
filename in the ledger row, and addressable on its own.

**Three questions, three panels.** *Content* — size, format, the full
SHA-256 and the document identifier, the hash with a copy button beside it.
*Ingestion* — the state, the backend's error message when there is one, the
vector space the document was embedded into, the collection it lives in and
the moment it was uploaded. *Applicability* — the two bounds of the
effective window, named, with the rule stated: a document with no window
is always in force.

**The whole hash, not twelve characters.** The hash scrolls sideways inside
its own box when it is wider than the column, and the copy button copies
the whole thing.

**The page holds its shape while it loads.** The frame is rendered before
the record arrives and the values fill in. Every value in it is exactly one
line tall whether it is loaded or not, so the panels below never move when
the record lands. This took four separate fixes to get right — a skeleton
of a different shape is a layout shift waiting to happen, and the shifts
came from the row's baseline alignment, the key wrapping, the value
overflowing its column, and the scrollbar taking height from the box.

### Files

| File | Change |
|---|---|
| `pages/DocumentPage.jsx` | New — the document record |
| `pages/DocumentPage.test.jsx` | New — 8 tests over the record |
| `services/api.js` | Added `kbService.getDocument` and `kbService.get` |
| `App.jsx` | Added the `/documents/:id` route |
| `components/kb/DocumentRow.jsx` | The filename is now a link to the record |
| `components/layout/EngineStatus.jsx` | Fixed a misreport — see below |
| `styles/app/surfaces.css` | `.lx-value-line`, `.lx-deflist--measured`, `.lx-deflist__value--grow` |

### Also fixed

**The sidebar reported the wrong model.** The engine status said
"Ollama · qwen3:1.7b" while queries were actually running on `gemma3:1b`.
The status read the provider's `default_model` — the first entry in the
registry — rather than the *active* model, and `qwen3:1.7b` is not even
enabled for that provider. A status surface that names a model the system
is not running is worse than no status at all. It now reports
`active_model`.

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 11 files, 56 tests, all pass (8 new) |
| `npm run build` | Succeeds in ~2.1s |
| Lighthouse — desktop and mobile | Accessibility 100 · Best Practices 100 · SEO 100 · Agentic Browsing 100 |
| Layout stability | Zero layout shifts at 1440 / 1280 / 1024 / 768 / 390 / 320 — measured, not assumed |
| Responsive | No page or top-bar overflow at any width; the full route sweep is clean |
| Console | 0 errors, 0 warnings |

---

## P4.5 — Playground

The workbench. The product's primary interaction, and the surface that had
been taken furthest apart from the ground up.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The answer could never be displayed.** The answer is rendered through a lazy import, and the module exports the component by name rather than by default. `React.lazy` resolved to nothing and the view crashed the moment a run finished — with "Cannot convert object to primitive value". The product's one output was unreachable. | Critical |
| 2 | **The run button was below the fold.** The query panel claimed to anchor the query and the run control at its foot. The pane was a plain block, so the form grew to its content and the button sat 259px below the viewport on a 900px screen. | Critical |
| 3 | **A finished run stayed on "Pipeline running…".** The completion path waited on the evidence endpoint, which can take minutes to fail. Nothing bounded the wait, so the run never appeared to finish. | High |
| 4 | **The engine panel called itself offline before it had asked.** The hook treated "the registry has not arrived" as "the registry could not be read", so a crimson alarm appeared on every cold load — before a single request had failed. | High |
| 5 | **The empty state was unstyled.** `styles/app/layers.css` — the vocabulary of the five pipeline stages — was never imported. The stages rendered as bare stacked text. | High |
| 6 | **The embedding panel was hardcoded.** It said "ONNX runtime" and "384d · offline" in fixed strings, whatever the registry actually said. | Medium |
| 7 | **The compose bar was transparent.** It asked Tailwind for `bg-surface-raised`, a colour the theme does not define. On a phone the configuration scrolled through the run control. | Medium |
| 8 | **The stacked layout squeezed both panes into the viewport.** The configuration was clipped away and the query control covered the results. | Medium |
| 9 | "1 docs" — a plural on a count of one. | Low |

### What changed

**The answer renders.** The lazy chunk is mapped onto the shape React.lazy
expects. A test now renders the answer tab and asserts the prose appears.

**The run control is anchored, on every width.** The pane is a flex column
beside the results, so the query and the run button sit at its foot. Below
the breakpoint the page scrolls instead of the pane, and the compose bar —
moved out of the form so it has a containing block tall enough to stick —
follows the reader down the window.

**A finished run finishes.** No request may hang: the client has a
30-second timeout, and the completion path races the detail bundle against
a deadline. The run reaches its result whether or not the evidence
endpoint ever answers.

**Three engine states, not two.** *Detecting* while the registry is still
coming back, *Connected* or *Standby* once it has, and the alarm only when
the request has actually failed.

**The embedding panel reads the registry.** The provider, the model and the
dimension come from the registry; nothing about the vector engine is
written down in the interface.

**An empty list and an unreadable list are different facts.** The evidence
tab says which one it is.

**The pipeline stages are styled again** — the dead stylesheet is
imported, and the five stages read as the ordered plates they were meant
to be.

### Files

| File | Change |
|---|---|
| `components/results/AnswerTab.jsx` | Fixed the lazy import — the answer renders |
| `components/results/AnswerTab.test.jsx` | New — 2 tests, one of them the crash regression |
| `components/results/EvidenceTab.jsx` | Passes the load-failure state through |
| `components/workbench/EvidenceViewer.jsx` | "Could not be loaded" is not "nothing was retrieved" |
| `components/playground/QueryPanel.jsx` | The compose bar left the form so it can stick |
| `components/playground/AIEngineSelector.jsx` | Three honest engine states |
| `components/playground/EmbeddingModelDisplay.jsx` | Reads the registry instead of fixed strings |
| `components/playground/KnowledgeBaseSelector.jsx` | "1 doc", not "1 docs" |
| `hooks/useModelSelection.js` | Removed the state that guessed "offline" and the dead refetch trigger |
| `hooks/useAnalysisStream.js` | The completion path is bounded |
| `lib/api.js` | A 30-second request timeout |
| `styles/index.css` | Imported the orphaned `app/layers.css` |
| `styles/app/surfaces.css` | The pane is a flex column; the stacked layout scrolls the page; the compose bar is solid and sticky |
| `pages/PlaygroundPage.test.jsx` | 2 new tests — no false alarm, no hardcoded embedding |

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 12 files, 60 tests, all pass (4 new) |
| `npm run build` | Succeeds in ~2.0s |
| Lighthouse — desktop and mobile | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Responsive | No overflow on any of the nine routes at 1440 / 1280 / 1024 / 768 / 390 / 320 |
| Run control | Visible without scrolling at 1440, 1280, 1024, 390 and 320 |
| Behaviour | A full analysis run exercised end to end — the answer renders, the four tabs open, the trace streams, the export is offered |
| Console | 0 errors, 0 warnings |

---

## P4.6 — Evidence, claims and conflicts

The audit vault. What the system retrieved, what it concluded, and where
two sources disagree.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The vault never finished loading.** The evidence and claim endpoints can take minutes to fail. The page showed a spinner for all of it, and the count said "0 records" while the request was still in flight. | High |
| 2 | **A failed load was reported as a count of zero.** "0 records" is a claim about the corpus. When the request failed, the interface knew nothing about the corpus. | High |
| 3 | **The evidence card inverted its own hierarchy.** A passage is the subject of the card, but its five score rows took more vertical space than the passage itself — five rows of metadata above and below one line of text. | Medium |
| 4 | Three slow failures were retried three times over. A local read that takes a minute to fail is broken, not transient. | Medium |

### What changed

**The wait is bounded, and the failure is fast.** The client times out at ten
seconds and the vault reads make one attempt. The error state carries a
Retry button for the reader who wants to try again.

**An unknown count is not a count of zero.** The header chip reads
"unavailable" when the load failed, and nothing at all while it is still in
flight.

**The passage leads.** The scores, the retrieval method and the validity
window are a strip of figures under the passage — label above, number
below — instead of five key/value rows that outweighed the text they
describe. The evidence card is roughly half the height it was, and what
it is about is legible first.

### Files

| File | Change |
|---|---|
| `pages/EvidencePage.jsx` | The count chip is honest about an unreadable vault |
| `pages/ClaimsPage.jsx` | The same |
| `pages/ConflictsPage.jsx` | The same |
| `components/workbench/EvidenceChunk.jsx` | The score breakdown is a figure strip, not a list of rows |
| `components/workbench/EvidenceViewer.jsx` | "Could not be loaded" is not "nothing was retrieved" |
| `styles/app/surfaces.css` | The `.lx-figures` strip |
| `lib/api.js` | The timeout is ten seconds, not thirty |
| `services/api.js` | The vault reads make one attempt |

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 12 files, 60 tests, all pass |
| `npm run build` | Succeeds |
| Lighthouse — desktop and mobile, all three pages | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Design review | The populated evidence vault and the populated claims list were both reviewed with real-shaped records, since the backend cannot currently serve them |

---

## P4.8 — Execution trace

The record of one run, recovered from the trace API when the live stream
is gone.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The trace had no subject.** The page listed events and the raw analysis id. It never said which question was asked, which collection answered it, what the verifier concluded, or which model produced it. A log without its run is a log without meaning. | High |
| 2 | **The page ended with implementation notes.** "Persisted in MongoDB. The SSE stream is recovered from the trace API if it disconnected" is documentation about the implementation, printed on the user's surface on every visit. | Medium |
| 3 | A trace that does not exist was requested three times. | Low |

### What changed

**The run comes before the events.** A summary strip names the collection,
the model that answered, the number of events and the stage time the
pipeline measured — the sum of the durations it reported for its own
stages, labelled as exactly that. The heading carries the question.

**The verdict is stated.** A run that abstained says so on the trace page,
not only on the dashboard.

**The implementation note is gone**, replaced by a sentence about what the
durations mean — a fact about the numbers on the page.

**A missing trace is asked for once.** A 404 will not become a 404 on the
third attempt.

### Files

| File | Change |
|---|---|
| `pages/TracePage.jsx` | Rebuilt around the run: summary strip, the question, the verdict |
| `pages/TracePage.test.jsx` | New — 3 tests over the run's context |

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 13 files, 63 tests, all pass (3 new) |
| `npm run build` | Succeeds |
| Lighthouse — desktop and mobile | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Responsive | No overflow at 1440 or 390; no target under 24px |

---

## P4.9 — Settings

The diagnostics screen: what the machine is, what the engines are doing,
and what the platform is configured to run.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The hardware panel reported zeros.** "Host memory 0 / 8 GB · 0%", "Process RSS 0 MB" — these were the fallback for a registry that had not answered yet. A reading of zero is a measurement; printing one for a machine nobody had measured yet is a claim the page cannot support. | High |
| 2 | **Ollama was reported as "Not running" while it was running.** The panel read the engine state before the registry arrived and reported the absence as fact. | High |
| 3 | **The engine and machine were guessed.** "CPU · arm64" was a hardcoded guess about the host, printed as a reading. | High |
| 4 | **The embedding panel described one deployment as if it were a reading.** "384d · offline", "ONNX Runtime / CPU", "Zero API cost · torch-free" — all fixed strings, none of them read from the registry. | Medium |
| 5 | **The model registry printed two rows it could not source.** It claims to report `config/models.yaml` and nothing else, but it also printed a fusion constant and a recovery ceiling that the registry never reported. | Medium |

### What changed

**Nothing is measured until it is measured.** The hardware readings, the
engine states and the embedding facts now read "Detecting…" until the
registry answers, and every one of them is a live value afterwards.

**The registry reports the registry.** The model registry's rows are the
identifiers the registry reports. The two it could not source — a fusion
constant and a recovery ceiling — are gone, because a panel that claims
to report the configuration should not print configuration it does not
have.

### Files

| File | Change |
|---|---|
| `components/settings/HardwarePanel.jsx` | Real readings, or "Detecting…" |
| `components/settings/LocalLLMPanel.jsx` | An engine that is unknown is not an engine that is stopped |
| `components/settings/EmbeddingPanel.jsx` | Provider, dimension, execution and cost read from the registry |
| `components/settings/ModelRegistryPanel.jsx` | Only rows the registry can source |
| `pages/SettingsPage.jsx` | Passes the loading state and the embedding record |

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 13 files, 63 tests, all pass |
| `npm run build` | Succeeds |
| Lighthouse — desktop and mobile | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Responsive | No overflow at 1440 or 390; no target under 24px |
| Readings | Host memory 6 / 8 GB · 75%, process RSS 578.31 MB, Ollama Online, provider ONNX, dimension 384d — all live values, verified in the browser |

---

## P4.10 — Authentication

The sign-in and account-creation surfaces.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The password's rules were checked only after the form was submitted.** A sentence described five requirements; a reader who missed one learned about it by failing. | High |
| 2 | **A password was never confirmed.** A typo in twelve characters with five classes of rule is a failed registration and no way to find the typo. | High |
| 3 | **The page had no `<h1>`.** Every other route in the product opens with one; the auth surface opened with an `<h2>` and had none. | Medium |
| 4 | **`?registered=1` was a dead flag.** The register page sent the reader to the login screen carrying it; nothing read it. | Medium |

### What changed

**The requirements report themselves.** The five rules are a list under
the field, and each one is marked as it is met. An unmet rule is a
requirement, not an alarm, so it is written in the same quiet silver as
the rest of the screen — only a met rule is marked.

**A failure names what is still missing.** Submitting with an unmet rule
says which ones, and focuses the password field. Submitting with two
different passwords says so, and focuses the confirmation.

**The password is confirmed**, so a typo is visible while it can still be
corrected.

**A new account is acknowledged.** The login page reads the flag the
register page has always been sending.

**The card is another record in the instrument.** A mono `credential check`
strip with a hairline and the registration seal puts the form in the same
visual language as the evidence ledger. The brand and card share one finite
entrance; reduced motion makes both static.

### Files

| File | Change |
|---|---|
| `lib/passwordRules.js` | New — the five requirements in one place |
| `components/auth/PasswordRules.jsx` | New — the list, reporting itself |
| `pages/RegisterPage.jsx` | The rules, a confirmation field, and failures that name the field |
| `pages/LoginPage.jsx` | Acknowledges an account that was just created |
| `layouts/AuthLayout.jsx` | The heading is the page's `<h1>` |
| `styles/app/auth.css` | The requirement list |
| `pages/AuthPages.test.jsx` | New — 6 tests over both auth surfaces |

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean |
| `npm run test` | 14 files, 69 tests, all pass (6 new) |
| `npm run build` | Succeeds |
| Lighthouse — desktop and mobile, both pages | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Landmarks | One `<main>`, one `<h1>` on both pages |
| Behaviour | A full registration was exercised against the live backend — 201, automatic sign-in, and the dashboard with the new account |

---

## P4.11 — Programme close: layout stability

The last pass over every route, measuring what a reader actually
experiences rather than what the DOM says.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The diagnostics page moved its own panels.** A reading is longer or shorter than the placeholder it replaces, so every panel below the first one shifted when the registry answered. Mobile CLS 0.149. | High |
| 2 | **The dashboard's heading moved.** The sync time was inside the status chip, so the chip's width depended on how long ago the last sync was. It sometimes fitted beside the heading and sometimes did not, and the heading moved with it. Mobile CLS up to 0.118, and it varied between loads. | High |

### What changed

**The diagnostics stack waits for its readings.** The panels arrive as one
piece instead of arriving one panel at a time, so nothing below the first
one moves.

**The sync time moved next to the control that performs the sync.** It was
never a status; it was a timestamp about an action, and it belonged with
the button that does it. The chip now says one thing — Live or Paused —
and its width no longer depends on the clock.

---

## P4.12 — Landing page: content truth

The landing page is the one surface a visitor sees before any of the
workbench exists. Its job is to say what the product does, and the
standard for that is higher than for an internal screen: every figure
must have a source, and every demonstration must be a real run.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The demonstration runs were invented.** Three scenarios claimed to be "real runs from the fixture corpus" and cited three PDFs — `trustrag_sys_arch_v2.pdf`, `langgraph_agent_spec.pdf`, `vector_store_integrity.pdf` — that do not exist in this repository. The corpus is seven plain-text and Markdown files. | Critical |
| 2 | **The verifier was described as a cross-encoder.** Pipeline stage 4 said "a cross-encoder scores each claim"; a capability panel was titled "Batch cross-encoder entailment audit" and its code sample imported `EntailmentAuditor(model="bge-reranker-v2-m3")`. The verifier is natural-language inference served by the local `ollama/gemma3:1b`. The cross-encoder ships as a disabled reranker (`reranker_enabled: false`) and is not in the verification path. | Critical |
| 3 | **The abstention threshold was wrong.** The capabilities panel and one scenario claim used `0.70`. `models.yaml` sets `reliability.abstain_below: 0.50`. | High |
| 4 | **The code samples imported modules that do not exist.** `from trustrag.agent import RecoveryGraph`, `from trustrag.verification import Decomposer`, `from trustrag.retrieval import HybridRetriever`, `from trustrag.ingestion import IntegrityGuard`. | High |
| 5 | **The benchmark table was partly fabricated.** "TrustRAG hybrid RRF 114 ms" and "Dense RAG, no audit 98 ms" were labelled as measured on the fixture corpus; the measured p50 is 5,145 ms. The three competitor grounding figures were labelled "Published" with no publication. The memory tab's index sizes had no measurement behind them. | Critical |
| 6 | **Two links pointed nowhere.** The hero's "Read the methodology" went to `/docs/evaluation`, which is not a route. The footer's "Licence" and "Documentation" both went to `/settings`, which contains neither. | High |
| 7 | **The header's "Architecture" anchor was dead.** `#layers` had no section behind it; the page's sections are `pipeline`, `simulation`, `capabilities`, `benchmarks`, `compare`. | Medium |
| 8 | **The hero's record card had collapsed.** P4.4 introduced `.lx-record` for the knowledge-base document row, which silently overwrote the landing page's `.lx-record` grid. The claim column rendered one word per line. | High |
| 9 | **Five landing classes had no rule at all.** `lx-bench__head`, `lx-bench__desc`, `lx-hero__copy`, `lx-record__citation`, `lx-record__conflict`. The citation icon sat on a line of its own; the contradiction text had no crimson edge. | Medium |
| 10 | **The footer named the wrong licence.** The repository is MIT; the footer said Apache-2.0. | Medium |

### What changed

**The runs are real.** Four measured runs from the frozen 27-query
reliability fixture, each opened as a case file: the query, the answer as
the system emitted it, the atomic claims it was split into, the
verifier's verdict and its own reasoning on each claim, the run's
measured figures, and the provenance line naming the run.

| Run | Source | What it shows |
|---|---|---|
| Temporal audit | `baseline` 1.29, gemma3:1b, analysis `6aedce9e…` | Five claims, all supported, reliability 1.00, 17,117 ms |
| Superseded spec | `baseline` 1.29, gemma3:1b, analysis `6aedceb9…` | The expired 2025 specification was filtered out of retrieval on its effective window; the answer cites the current one |
| Abstention | `baseline` 1.29, gemma3:1b, analysis `6aedcee7…` | Zero claims, zero cited segments, reliability 0.00 — a refusal with its reason attached |
| Contradiction | `baseline` 1.28, mlx Qwen3-4B, analysis `6aec435e…` | One contradicted claim with the verifier's reasoning; the run withheld an answer, and the harness records that the outcome did not match |

Each claim carries the document it was checked against, the real retrieval
score that document held in that run, and the SHA-256 root hash recorded
at ingestion. Nothing on the page is a reconstruction.

**The descriptions now match the implementation.** NLI, not a
cross-encoder. `abstain_below: 0.50`, not 0.70. Two recovery attempts,
not "two-iteration bound". The code samples import the modules the
system actually uses — `app.rag.verification.pipeline.nli`,
`app.rag.retrieval.retriever`, `app.rag.verification.integrity`,
`app.rag.agent.graph.build`, `app.mcp.server`.

**The benchmarks are one run, fully sourced.** Three tables — grounding,
latency, coverage — and every figure in them comes from the same
`trustrag_baseline_reliability_phase1_1.29` run. The competitor column
is gone, because there was no measurement behind it.

**Every link resolves.** The hero's methodology link and the footer's
licence, methodology and source links point at the repository, which is
public. The dead `#layers` anchor points at the runs section. The footer
names MIT.

**The class collision is gone.** The document row's vocabulary is
`.lx-docrow`, which it should have been from P4.4. The landing page's
`.lx-record` belongs to the landing page.

**Five missing rules were written**, and the two dead ones
(`.lx-recovery`, `.lx-claim__conflict`) were deleted.

### The same defect, elsewhere in the frontend

Auditing the landing page turned up the fabricated-threshold defect in
five more places in the application. These were copy corrections, not
redesigns, and each was checked against `models.yaml` and
`app/rag/verification/verdict.py` before it was changed.

| Where | Was | Now |
|---|---|---|
| `dashboard/PipelineArchitecture.jsx` | Stage 04 tagged "Cross-encoder", threshold `0.70` | Tagged "NLI", "Abstain below 0.50" |
| `dashboard/ReliabilityChart.jsx` | Threshold hairline and fallback status at 75 | At 50, the `abstain_below` boundary; the fallback no longer claims TRUSTED, which only the coverage and contradiction rates can establish |
| `pages/DashboardPage.jsx` | "Threshold 75%" | "Threshold 50%" |
| `pages/ConflictsPage.jsx` | "A refutation score above 0.70 triggers query reformulation" | A contradicted claim pushes the contradiction rate past the evidence gate, and the run enters query reformulation |
| `workbench/EmptyState.jsx` | "when reliability drops below 75%" | "when a run fails the evidence-coverage and contradiction gate" |
| `pages/ClaimsPage.jsx` | "with a confidence of 0.70 or above" | The NLI verdict names the segments that carry it, and the reasoning is stored |
| `playground/WebSearchToggle.jsx` | "invokes web retrieval when knowledge base confidence falls below 75%"; tool named `verify_claim` | Web search is a switch, not a confidence trigger; the tool is `trustrag_verify_claim` |

The real rules, from `compute_verdict` in
`app/rag/verification/verdict.py`: coverage `≥ 0.80` and contradiction
rate `≤ 0.20` to PASS; the reliability score is
`coverage × (1 − contradiction_rate)`; below `abstain_below` (0.50) the
run is FAILED rather than UNCERTAIN; and the recovery loop fires when the
verdict is not PASS, not when a score crosses a single line.

### The honest parts

The page states three things a marketing page would usually hide:

- The temporal audit's third and fourth claims carry verifier reasoning
  that misattributes a segment. It is shown verbatim, because the point
  of storing the reasoning is that it can be read.
- The contradiction run abstained on a query the dataset expected to be
  answered. The harness record says so.
- The abstention's diagnosis is cited from the Phase 1 abstention audit,
  which ran against a different baseline, and says which one.

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean — 0 warnings, 0 errors |
| `npm run test` | 14 files, 69 tests, all pass |
| `npm run build` | Succeeds in ~2.1 s |
| Lighthouse — landing, desktop | Performance 100 · Accessibility 100 · Best Practices 100 · SEO 100 · Agentic Browsing 100 |
| Lighthouse — landing, mobile | Performance 99 · Accessibility 100 · Best Practices 100 · SEO 100 · Agentic Browsing 100 |
| Layout stability | CLS 0 on the landing page |
| Responsive | No page overflow at 1440 / 1280 / 1024 / 768 / 390 / 320; only the code block scrolls, and it scrolls itself |
| Landmarks | One `<main>`, one `<h1>` |
| Focus | 2 px Laser Crimson on every visible control at 1440 and 390 |
| Invisible text | None |
| Target size | Only inline text links below 24 px, covered by the WCAG 2.5.8 inline exception |
| Console | 0 errors, 0 warnings |
| Knowledge-base document row | Six columns in the correct order after the `.lx-docrow` rename |
| Threshold corrections | Seven copy fixes across the dashboard, claims, conflicts and playground, each checked against `models.yaml` and `compute_verdict` |

---

## P4.13 — Frontend audit

A pass over the whole of `apps/web` with axe-core against every route,
looking for the same class of defect the landing page had been hiding:
a claim the interface makes that the code does not support.

### What was wrong

| # | Problem | Severity |
|---|---|---|
| 1 | **The results panel showed the wrong status.** `ReliabilityBadge` was given `analysis.status` — the run lifecycle (`completed`, `abstained`) — instead of `analysis.reliability.status`, the verdict (`TRUSTED`, `UNCERTAIN`, `FAILED`, `ABSTAINED`), and no score at all. The badge rendered a generic question-mark icon, an em dash, and the word "completed". The two other call sites passed the reliability status correctly. | High |
| 2 | **The badge invented its own thresholds.** The band came from `pct >= 75 ? 'high' : pct >= 50 ? 'medium' : 'low'`. The real bands are the verdict's: TRUSTED is a coverage-and-contradiction judgement that a score cannot make, and an abstention scored zero, so it was rendered in Laser Crimson — which says the system produced a bad answer when it produced no answer at all. | High |
| 3 | **Mutations were retried.** `kbService.create`, `kbService.delete`, `kbService.uploadDocument`, `kbService.deleteDocument` and `analysisService.create` all went through the retry wrapper, which retries 500/502/503/504 — while the comment above them said "no retry for mutations". A create that answered 500 and then succeeded on the retry left two collections, two documents or two analysis runs behind, and the retry looked successful. | High |
| 4 | **Two landmarks shared a name.** The landing page wrapped `LandingCTA` in `<section aria-labelledby="cta-heading">` while `LandingCTA` rendered another `<section aria-labelledby="cta-heading">` containing `<h2 id="cta-heading">`. Two regions with one name, and a duplicated `id` in the document. | Medium |
| 5 | **The brand link broke Label in Name.** `aria-label="TrustRAG home"` on a link whose visible text is "TRUSTRAG Reliability workbench" on wide screens and "TRUSTRAG" below 1280px. No single fixed label can contain both, so the label was removed and the wordmark now supplies the name — visually hidden rather than removed below 640px, so the link is never left nameless. | Medium |
| 6 | **The collapse button broke Label in Name.** `aria-label="Collapse sidebar"` against a visible "Collapse ⌘B". The expanded button now takes its name from its content; the collapsed one, which is an icon with no visible text, keeps its short label. | Medium |
| 7 | **The quick prompts broke Label in Name.** Each chip's accessible name was the full prompt it sends, and its visible label was a shortened rewrite — "Explain key concepts" against "Explain the key concepts in this document". The visible words were not a contiguous run of the name's words. Each label is now the opening of its prompt. | Medium |
| 8 | **The playground's idle pane could not be scrolled.** The empty-state panel scrolls and holds nothing focusable, so a keyboard user had no way to reach the content below the fold. It now has a tab stop and a name. | Medium |
| 9 | **The code block could not be scrolled.** The capability code scrolls sideways on a phone and holds nothing focusable either. | Medium |
| 10 | **The narrow-screen engine readout was never rendered.** `EngineTelemetry` was written for exactly the case where the top bar sheds the engine, the embedding model and the accelerator — and never wired into the drawer. On a phone the application showed no API state, no model and no accelerator at all. | Medium |
| 11 | **Three components were dead.** `components/app/Dialog.jsx` (superseded by `ConfirmDialog`, which has its own focus management), `components/kb/KnowledgeBaseCard.jsx` (superseded by `CollectionLedger`) and `hooks/usePrefersReducedMotion.js` (the CSS handles the preference). | Low |
| 12 | **Three exports were dead.** `NAV_ITEMS`, `ClaimStateBadge`, and the recharts-era `tooltipStyle` / `tooltipLabelStyle` / `axisProps` in `lib/chartTheme.js`. | Low |
| 13 | **Two comments described code that was not there.** `useBackendHealth` said the first probe was deferred to the next interval tick; it fires on mount. `RequireAuth` said "Phase 4 will add server-side token validation"; the server validates on every request and the interceptor clears a 401. | Low |

### What changed

Three regression tests now hold the fixes in place: the quick-prompt
labels must stay a prefix of the prompts they send, the badge's band must
come from the verdict, and a write must make exactly one attempt while a
read may be retried.

### Verification

| Check | Result |
|---|---|
| `npm run lint` | Clean — 0 warnings, 0 errors |
| `npm run test` | 18 files, 85 tests, all pass |
| `npm run build` | Succeeds in ~2.1 s |
| axe-core, WCAG 2.0/2.1/2.2 A + AA + best practice | 0 violations on all ten routes at 1440 and 390 |
| Lighthouse — landing, desktop | Performance 100 · Accessibility 100 · Best Practices 100 · SEO 100 · Agentic Browsing 100 |
| Lighthouse — landing, mobile | Performance 99 · Accessibility 100 · Best Practices 100 · SEO 100 · Agentic Browsing 100 |
| Responsive | No page overflow on eight routes × six widths; only the code block and the drawer scroll, and they scroll themselves |
| Console | 0 errors, 0 warnings on every route |
| Landmarks | One `<main>` and one `<h1>` per route |
| Focus | 2 px Laser Crimson on every visible control at 1440 and 390 |

### A note on the colour-contrast readings

Sampling the landing page while its entrance animation is still running
reports a hundred-odd contrast failures. Every one of them is a blend
between the intended colour and the background — the text is mid-fade.
Re-running the same rule on the settled page reports none. The figures in
the table above are from the settled state.

---

## The rules for the remaining phases

1. **Audit before editing.** Read the page, its components, its API calls
   and its states first. The shell phase found a fabricated status string
   and a hardcoded overflow; neither was visible from the component list.
2. **One page at a time.** Each phase lands as its own commit with its own
   verification.
3. **No fabricated capability.** If a panel claims the system is doing
   something, that something has to be observable. The shell's status card
   was the clearest case: it now reads the health endpoint.
4. **Reuse the shared vocabulary.** `lx-page`, `lx-panel-block`,
   `lx-stack`, `lx-statstrip`, `lx-list`, `lx-table`, `lx-deflist`,
   `lx-workbench`, `PageHeader`, `AsyncState`, `ExplainerList`, `Dialog`.
   A page that needs a new primitive adds it to the system; it does not
   invent one locally.
5. **Every state is designed.** Loading, empty, error, success, and the
   partial states in between — a page that only renders its success state
   is not finished.
6. **Verify in the browser, not in the source.** The overflow at 1024px
   was in the rendered layout, not in the markup.
