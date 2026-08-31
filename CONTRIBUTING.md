# Contributing to TRUSTRAG

## Development Loop

```
READ → PLAN → BUILD → VERIFY → FIX → DOCUMENT → NEXT
```

Never continue with known failures. Do not generate the whole project blindly.

## Before Contributing

1. Read `TRUSTRAG_specs.md` — it is the source of truth
2. Review open ADRs in `docs/architecture/decision-log.md`
3. Check the threat model before touching security-sensitive code

## Rules

- **No model IDs in code.** All model identifiers go in `config/models.yaml`
- **No secrets in code or YAML.** Secrets in `.env` only
- **No invented requirements.** Only implement what the spec mandates
- **No scope creep.** See spec §34 for explicit out-of-scope items

## Setup

```bash
# Backend
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd apps/web
npm install
```

## Running Tests

```bash
# Backend unit tests (86 unit tests across 14 test suites, no live services required)
cd apps/api
pytest -v

# Frontend lint and build check
cd apps/web
npm run lint
npm run build
```

## Code Style

- Python: `ruff` for linting and formatting (`ruff check app/` and `ruff format app/`)
- JavaScript: ESLint (`npm run lint`)
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)

## Security

- All security issues → see [SECURITY.md](SECURITY.md)
- Never commit `.env`
- Run `pip-audit` before adding new Python dependencies
