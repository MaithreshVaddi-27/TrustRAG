# 08 — Verification

The gate. What is checked, how, and what the current result is.

---

## The gate

Nothing ships until all of these pass.

```bash
cd apps/web
npm run lint     # 0 warnings, 0 errors
npm run test     # all unit tests pass
npm run build    # production build succeeds
```

Then the browser pass, with Brave DevTools MCP.

### 1. Lighthouse, every route

Accessibility must be **100**. Best Practices and SEO must not regress.

### 2. Responsive sweep

Screenshots and a measurement at **1440, 1280, 1024, 768, 390 and 320**.

At every width:

```js
document.documentElement.scrollWidth === document.documentElement.clientWidth
```

No horizontal page scroll. The only element permitted to scroll sideways
is a code block, which scrolls itself.

### 3. Console

Zero errors and zero warnings on every route.

### 4. Invisible text

No element with a text node may compute to `color: rgba(0, 0, 0, 0)`.

```js
[...document.querySelectorAll('h1,h2,h3,p,span,button,a')]
  .filter(el => el.children.length === 0
    && el.textContent.trim()
    && getComputedStyle(el).color === 'rgba(0, 0, 0, 0)')
```

This check exists because of the token bug. A text-fill gradient that
fails to resolve makes its text invisible while leaving it in the
document.

### 5. Target size

```js
[...document.querySelectorAll('a,button,[role="button"],input')]
  .filter(el => {
    const cs = getComputedStyle(el)
    if (cs.display === 'none' || cs.visibility === 'hidden') return false
    const r = el.getBoundingClientRect()
    return r.width > 0 && r.height > 0 && r.height < 44
  })
```

Every remaining entry must be either a coarse-pointer target (44px via
the `pointer: coarse` rule), an inline text link (the WCAG 2.5.8 inline
exception), or a dense navigation row on a fine pointer.

### 6. Focus

Tab through the route. The ring must be visible on every control:
2px `#f04a48` at 3px offset.

```js
el.focus()
getComputedStyle(el).outlineWidth   // "2px"
getComputedStyle(el).outlineColor   // "rgb(240, 74, 72)"
```

`Escape` must close the mobile drawer.

### 7. Landmarks

Exactly one `<main>` per route, one `<h1>` per route, and a skip link as
the first focusable element.

---

## Current result

| Check | Result |
|---|---|
| `npm run lint` | Clean — 0 warnings, 0 errors |
| `npm run test` | 8 files, 34 tests, all pass |
| `npm run build` | Succeeds in ~2.1s |
| Lighthouse — landing | Accessibility 100 · Best Practices 100 · SEO 100 · Agentic Browsing 100 |
| Lighthouse — all ten routes | Accessibility 100 · Best Practices 100 · Agentic Browsing 100 |
| Lighthouse — SEO on app routes | 63 — `robots.txt` disallows the authenticated routes on purpose |
| Lighthouse — Best Practices on `/evidence` | 96 — the backend's `GET /api/v1/evidence` returns HTTP 500 |
| Responsive | No page overflow and no top-bar overflow at 1440 / 1280 / 1024 / 768 / 390 / 320 |
| Landmarks | Exactly one `<main>` and one `<h1>` per route, including the auth routes |
| Target size | No interactive target below 24px, except inline text links covered by WCAG 2.5.8 |
| Focus | 2px Laser Crimson, 5.5:1 on obsidian |
| Console | 0 errors and 0 warnings across landing and all nine app routes |
| Route coverage | `/`, `/login`, `/register`, `/dashboard`, `/playground`, `/knowledge-bases`, `/claims`, `/evidence`, `/conflicts`, `/settings` |

### Bundle

| Chunk | Raw | Gzipped |
|---|---|---|
| LandingPage | 35.1 kB | 10.7 kB |
| PlaygroundPage | 37.8 kB | 10.7 kB |
| AppLayout | 22.0 kB | 6.8 kB |
| DashboardPage | 20.3 kB | 6.8 kB |
| SettingsPage | 16.8 kB | 4.5 kB |
| KnowledgeBasesPage | 15.2 kB | 4.6 kB |
| FormattedAnswer (lazy) | 158.7 kB | 48.1 kB |
| query-vendor | 41.7 kB | 12.6 kB |
| http-vendor | 51.4 kB | 19.5 kB |
| ui-vendor | 52.7 kB | 12.5 kB |
| react-vendor | 179.9 kB | 59.2 kB |

Two vendor chunks are gone. `chart-vendor` (386 kB) was replaced by two
purpose-built SVG charts, and `motion-vendor` (131 kB) by CSS transitions
plus a `prefers-reduced-motion` hook. The playground chunk fell from
215.9 kB to 37.8 kB, and the Markdown renderer moved into an on-demand
chunk that loads only when an answer is rendered.

---

## Verifying against the real app

The system runs locally without Docker.

```bash
# 1. MongoDB must be listening on 27017
mongod --dbpath <path> --fork --logpath <path>

# 2. The vector store runs in embedded local mode — no container needed
cd apps/api
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. The local LLM, if the playground is to execute a real analysis
ollama serve

# 4. The frontend
cd apps/web
npm run dev
```

Then open `http://localhost:5173/`.

---

## A note on the token bug

The single most expensive defect in this codebase's history was a file
that existed, was correct, and was never loaded.

It produced invisible text, borders with no width, radii with no radius,
and transitions with no duration — and every one of those failures looked
like a design decision rather than a defect. The reduced-motion path
accidentally restored the invisible headline, which made it look
intermittent.

Two structural guards now prevent a repeat:

1. The token layer is a directory of small files imported **first**, so a
   missing import takes one small file down instead of the whole system.
2. The invisible-text sweep in step 4 above catches the exact symptom.
