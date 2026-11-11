# 09 — Pages

The page-by-page redesign. One page at a time, each one audited, planned,
implemented and verified before the next begins.

---

## The order

| Phase | Surface | Depends on |
|---|---|---|
| P4.1 | Application shell | — |
| P4.2 | Dashboard | shell |
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
