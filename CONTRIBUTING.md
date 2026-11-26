# Contributing to TRUSTRAG

## Development Loop

```
READ → PLAN → BUILD → VERIFY → FIX → DOCUMENT → NEXT
```

Never continue with known failures. Do not generate the whole project blindly.

## Before Contributing

1. Read `docs/TRUSTRAG_specs.md` — it is the source of truth
2. Review open ADRs in `docs/architecture/decision-log.md`
3. Check the threat model before touching security-sensitive code

## Rules

- **No model IDs in code.** All model identifiers go in `apps/api/config/models.yaml`
- **No secrets in code or YAML.** Secrets go in the single repo-root `.env` only —
  do not create `apps/api/.env` or another env file: a second file shadows the
  first (pydantic-settings gives later files precedence) and empty duplicates
  silently erase real keys
- **No invented requirements.** Only implement what the spec mandates
- **No scope creep.** See spec §34 for explicit out-of-scope items

## Repository layout & naming

```
apps/api/     FastAPI backend, models.yaml, tests, bench/eval/verify scripts
apps/web/     React frontend, e2e tests, public assets
brand/        Brand kit and exported logo set (source of truth for icons)
config/       ports.yaml (single source of truth for ports)
docs/         Spec, ADRs, living engineering logs, design system
scripts/      Cross-cutting checks, setup, eval runners, server launchers
load-test/    k6 load profiles
```

- Python packages and modules: `snake_case`; React components: `PascalCase`
  filenames; everything else (scripts, docs, CSS, assets): `kebab-case`.
- One concern per directory. A test lives beside the module it covers
  (`*.test.jsx` / `test_*.py`), not in a separate top-level test tree.
- Generated output (`dist/`, `test-results/`, `__pycache__/`, caches) stays
  gitignored and out of the working tree; never commit a generated artefact.

## Setup

```bash
# Backend (macOS / Linux)
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,local-models]"   # local-models = torch export stack for ONNX bootstrap

# Backend (Windows PowerShell)
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,local-models]"

# Frontend
cd apps/web
npm install
```

Then check the machine before starting anything:

```bash
python scripts/serve.py doctor
```

`doctor` verifies the port registry, the single repo-root `.env`, the backend
interpreter, npm and frontend dependencies, the ONNX weights and the local
service binaries. It also fails when `apps/web/.env` sets `VITE_API_URL` to a
remote origin, which bypasses the Vite dev proxy and causes CORS errors.

## Running the stack

One command starts MongoDB, Ollama, the API and Vite on macOS, Linux or
Windows. Ports always come from `config/ports.yaml`.

```bash
python scripts/serve.py serve          # Ctrl+C stops every service
python scripts/serve.py serve --detach # background; use `stop` to clean up
python scripts/serve.py status
python scripts/serve.py stop

# Windows
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1 serve
```

## Running Tests

```bash
# Backend unit tests (no live services required). pytest reports the full count.
cd apps/api
pytest -v

# Frontend: unit, lint, palette drift, build
cd apps/web
npm test
npm run lint
npm run check:tokens
npm run build

# Browser E2E against the live stack (Playwright starts the preview itself)
npm run test:e2e
```

Launcher and resilience harness tests live under `apps/api/tests/` because
that is this repository's pytest root; they cover repository-root scripts that
cannot be collected from their own directory.

## Code Style

- Python: `ruff` for linting and formatting (`ruff check app/` and `ruff format app/`)
- JavaScript: ESLint (`npm run lint`)
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)

## Security

- All security issues → see [SECURITY.md](SECURITY.md)
- Never commit `.env`
- Run `pip-audit` before adding new Python dependencies
