# TRUSTRAG — backend harnesses

Everything that measures the backend lives here, grouped by what it
measures.

| Package | Question it answers | Entry point |
|---|---|---|
| [`bench/`](bench/) | *How fast and how well does it retrieve?* | `python scripts/bench/bench_api.py` |
| [`eval/`](eval/) | *Are the answers right?* | `bash scripts/eval/run_matrix.sh` |
| [`verify/`](verify/) | *Do the parts agree, and does it survive failure?* | `python scripts/verify/validate_integration.py` |

Plus one operation script at the top level:

| Script | What it does |
|---|---|
| `start_local_services.sh` | Starts MongoDB, Ollama and the API, and waits until the API answers. Discovers the interpreter itself, so it runs on macOS, Linux and Windows (Git Bash / WSL). |

## Which harness do I want?

| I want to know… | Run |
|---|---|
| how fast the API is | `bench/bench_api.py` |
| how fast each pipeline stage is | `bench/bench_pipeline.py` |
| how good the retrieval is over a run | `bench/analyze_quality.py` |
| whether the answers are correct | `eval/run_matrix.sh` |
| whether the frontend and the backend agree | `verify/validate_integration.py` |
| whether it survives an outage | `verify/validate_resilience.py` |

The harnesses that talk to a live API need the stack up:

```bash
bash scripts/start_local_services.sh
```

## The shared benchmark account

`bench/bench_auth.py` owns the one account the harnesses use. The register
endpoint allows only three registrations per hour per client, so a shared
account (cached on disk, re-registered when it is gone) is what makes
repeated runs possible. Nothing else should register an account.
