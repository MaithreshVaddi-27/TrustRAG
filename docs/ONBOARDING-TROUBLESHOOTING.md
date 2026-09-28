# TrustRAG — Onboarding & Troubleshooting (Mac / Windows / Linux)

> New-user field guide: what the installer chain does, what each OS needs,
> and every known first-run failure with its fix. Code references are
> `file:line` from the repo root unless noted (`apps/api/` prefix kept).

---

## 1. What runs, in order

```
1. cp .env.example .env  (+ set JWT_SECRET to 64 hex chars)
2. backend venv:  cd apps/api && python3 -m venv .venv && pip install -e ".[dev,local-models]"
3. python scripts/bootstrap.py        # ONNX weights + LLM discovery snapshot
4. ./scripts/start_local_llm.sh       # llama-server router on :8080 (bash/WSL only)
5. ./scripts/setup.sh                 # verifier: prints copy-paste fixes (bash/WSL only)
6. backend:  cd apps/api && .venv/bin/uvicorn app.main:app --port 8000
7. frontend: cd apps/web && npm install && npm run dev   # :5173
```

`bootstrap.py` delegates to `scripts/ensure_onnx_models.py`, which guarantees
two files in `apps/api/.model_cache/`:

| File | Source | Size | Needed by |
|---|---|---|---|
| `bge-small-en-v1.5.onnx` | exported from `BAAI/bge-small-en-v1.5` via `scripts/export_bge_onnx.py` | ~130 MB | default `embedding.provider: onnx` |
| `reranker-ms-marco-MiniLM-L-6-v2_int8.onnx` | exported from `cross-encoder/ms-marco-MiniLM-L-6-v2` via `app/core/onnx_reranker.py` | ~90 MB | `reranker.use_onnx: true` |

Both exports need the torch stack (`pip install -e ".[local-models]"`:
`sentence-transformers` pulls torch, plus `onnx`/`onnxscript`). The export is
**CPU-only** (`model.to("cpu")` — MPS is unsupported by `torch.export`) and
needs **network once** (Hugging Face snapshot + tokenizer). The Docker runtime
image is torch-free **by design** — export on the host, then
`docker cp apps/api/.model_cache/. trustrag_api:/app/.model_cache/`.

Verify any time without downloading: `python scripts/bootstrap.py --verify`
(exit 0 = ready). Re-export: `--force`. Changing the embedding model in
`apps/api/config/models.yaml` is detected automatically (old cache file stops
matching) since 2026-09-23 — `export_bge_to_onnx()` takes the configured
model instead of a hardcoded id.

---

## 2. Per-OS prerequisites

### macOS (Apple Silicon recommended)

```bash
brew tap mongodb/brew   # required once for the mongodb-community formula
brew install python@3.11 node@22 mongodb-community ollama
brew services start mongodb-community
```

- Use Python **3.11–3.12** (`./scripts/setup.sh` enforces this). 3.13+ breaks
  `torch`/`onnxscript` export. `python@3.11` is keg-only — use
  `$(brew --prefix python@3.11)/bin/python3.11 -m venv`.
- MLX is **Apple-Silicon-only** (`pipx install mlx-lm`, needs `pipx` first).
  Intel Macs: skip MLX, use Ollama/llama.cpp (CPU flags are automatic).
- The MLX model id in the start command must match `model_mlx` in
  `apps/api/config/models.yaml` and `MLX_BASE_URL` port `:8090`.
- 8 GB Macs: export the `OLLAMA_*` vars from `.env.example:164-168` before
  `ollama serve`.

### Linux (Ubuntu/Debian)

```bash
# Stock Ubuntu ≤22.04 ships Python ≤3.10 — add deadsnakes first:
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3.11-dev \
  python3-pip build-essential curl git
```

- The MongoDB repo line in the README targets **`jammy`** — on 24.04 (noble),
  Debian, Fedora, or Arch adjust to your distro (or use Docker MongoDB).
- No systemd (WSL2/Docker): `sudo service mongod start` instead of
  `sudo systemctl enable --now mongod`.
- No GPU needed for ONNX export/runtime (`onnxruntime` CPU). `nvidia-smi` is
  only probed for llama-server flags.

### Windows (PowerShell)

```powershell
winget install Python.Python.3.11 OpenJS.NodeJS.LTS MongoDB.Server Ollama.Ollama Git.Git
# reopen the shell so PATH refreshes
net start MongoDB
```

- Python must be **3.11–3.12** (winget may offer newer — pin 3.11).
- Venv lives at `.venv\Scripts\python.exe` (not `.venv/bin/python`):
  `cd apps\api; python -m venv .venv; .\.venv\Scripts\Activate.ps1`.
- `scripts/*.sh` are **bash-only** — run them under **Git Bash**
  (`bash scripts/setup.sh`) or **WSL** (`wsl ./scripts/start_local_llm.sh`).
  Native `setup.sh` probes use `/dev/tcp`, which PowerShell/`cmd` lack.
- `start_local_llm.sh` resolves the HF cache via `$HOME`/`HF_HUB_CACHE`;
  native Windows has neither — prefer WSL for the llama-server path.
- Avoid cloning into deep/OneDrive-synced paths (260-char limit bites the
  `.model_cache` + HF hub paths); SQLite WAL + OneDrive file locking can
  silently disable the embedding disk cache.

---

## 3. Failure table (symptom → cause → fix)

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `ConfigurationError: ONNX embedding model not found in …` on first query / boot ERROR log names the path | Skipped `bootstrap.py` (weights are never committed: `.gitignore`) | `python scripts/bootstrap.py` (needs network once), restart backend |
| 2 | `Service configuration error.` (old builds) with no detail | Pre-2026-09-23 handler redacted the message | Upgrade; the handler now returns the actionable message |
| 3 | Backend exits: `Settings validation failed — fresh clone? …` | No `.env` (`JWT_SECRET`/`MONGODB_URI` missing) | `cp .env.example .env`, set `JWT_SECRET` to `secrets.token_hex(64)` |
| 4 | `No module named 'sentence_transformers'` / `'torch'` during bootstrap export | Installed `.[dev]` without `local-models` | `cd apps/api && pip install -e ".[local-models]"` (CONTRIBUTING fixed 2026-09-23) |
| 5 | Reranker export warns, backend falls back to RRF order | Reranker `.onnx` missing (non-fatal by design) | Same `local-models` install, re-run bootstrap (no `optimum` needed — warning text fixed) |
| 6 | `tokenizers` / HF download blocked (`OfflineError`) on fresh clone | Pre-2026-09-23 boot forced `HF_HUB_OFFLINE=1` even with no bake | Upgrade; offline is now forced only when weights are cached |
| 7 | `curl: command not found` gaps / `setup.sh` errors about missing venv python | Ran checks before creating the venv | Create venv first; `setup.sh` now skips venv-gated checks with a pointer |
| 8 | `./scripts/setup.sh: /dev/tcp: No such file` / syntax errors | Ran under `sh`/`dash`/PowerShell instead of bash | `bash scripts/setup.sh` (or WSL on Windows) |
| 9 | `llama-server: command not found` | llama.cpp never installed (README had no step) | macOS: `brew install llama.cpp`; Linux: GitHub release binary; Windows: WSL |
| 10 | `ERROR: Models directory not found: ~/.cache/huggingface/hub` (old builds) | Hard fail on first run | Upgrade; script creates the dir and prints fetch commands |
| 11 | Backend 404s from MLX / model mismatch | Started `mlx_lm.server` with a different `--model` than `model_mlx` | Match the exact id; port must be `:8090` (`apply_ports.py` now syncs it) |
| 12 | `ollama pull` model 404 / backend talks to a model that isn't served | Requested id not in `ollama list` / router cache | `ollama pull gemma3:1b`; llama.cpp: `hf download … --include '*Q4_K_M*'` into the hub dir |
| 13 | MongoDB unreachable (`DatabaseError`, boot blocks ~minutes of retries) | `mongod` not running / wrong `MONGODB_URI` | Start per OS table above; boot is fail-hard by design (no degraded mode) |
| 14 | Qdrant errors only on first KB op, never at boot | Qdrant client is lazy (good for boot, confusing in logs) | Start Qdrant (compose includes it) or use `:memory:`/path `QDRANT_URL` for dev |
| 15 | `setup.sh` warns `:8080/:8090 already in use` while LLM checks above say healthy | False alarm: occupied LLM ports **are** the healthy state | Ignore if the LLM lines above report the servers |
| 16 | `python3.11: command not found` on Ubuntu | Stock Ubuntu ships 3.10 | deadsnakes PPA (see Linux section) |
| 17 | MongoDB apt 404 on Ubuntu 24.04 | README repo line hardcodes `jammy` | Use the `noble` repo path or Docker MongoDB |
| 18 | `pip install mlx-lm` fails on Intel Mac / Linux | MLX is Apple-Silicon-only | Skip MLX; use Ollama or llama.cpp |
| 19 | First query slow (~minutes), then fast | Cold ONNX load + hardware probe + disk cache warmup (by design, non-blocking) | Wait for `Embedding model pre-warmed` in logs |
| 20 | `Large diff` / OOM during export on 8 GB hosts | torch export + `/tmp` spikes on top of the ~8 GB note | Close browsers/IDEs, ensure ~4 GB free beyond the README figure |
| 21 | `Invalid QDRANT_URL` at first KB op | URL without scheme (e.g. `localhost:6333`) — rejected instead of being mkdir'd | Use `http://localhost:6333`, `local`, `:memory:`, or a path |
| 22 | `pip install -e .` fails on Python 3.13+ | `requires-python` now caps at `<3.13` (torch/onnxscript export incompatible) | Use Python 3.11 or 3.12 |
| 23 | `mlx_lm.server not applicable here` from `setup.sh` | Host is not Apple Silicon (check is now platform-gated) | Expected — use Ollama or llama.cpp instead |

---

## 4. Environment knobs that matter on day one

- `HF_HUB_OFFLINE=1` — set automatically at boot **only when weights are
  cached**; unset it (or just run bootstrap) for the one-time download.
- `HF_TOKEN` — only for rate-limited/private HF repos.
- `MODEL_CACHE_DIR` — overrides `apps/api/.model_cache` location.
- `SKIP_ONNX_EXPORT=1` — verify-only escape hatch for air-gapped CI.
- `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_FLASH_ATTENTION=1`,
  `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`,
  `MALLOC_ARENA_MAX=1`, `TOKENIZERS_PARALLELISM=false` — 8 GB survival kit
  (`.env.example:139-168`).
- `config/ports.yaml` is the port source of truth; after editing run
  `python3 scripts/apply_ports.py` (now also syncs the MLX `:8090` consumers;
  `--check` is the CI gate).

---

## 5. Live verification backlog (carried over from the retired `UPGRADE.md`)

Mocked tests are green, but these need a running stack + human judgment:

- **Providers never live-tested:** Gemini, NVIDIA NIM, MLX (`mlx_lm.server --port 8090`).
- **qwen3:1.7b** hallucinated unrelated claims in manual testing — retry with
  `temperature=0` before trusting it for verification.
- **LFM2.5-1.2B** verification fixated on SHA-256 and missed NLI context —
  may need a larger `max_output_tokens` cap.
- **k6 smoke:** `k6 run load-test/smoke.js` against a live backend with seeded auth.
- **Playwright e2e:** needs Mongo + Qdrant + LLM + web all running.

## 6. Sanity checklist (should all be green)

```bash
bash scripts/setup.sh                                        # prereqs + ports
python scripts/bootstrap.py --verify                        # ONNX bake present
curl localhost:8000/api/v1/health                           # {"status": ...}
curl localhost:8000/api/v1/health/detailed                  # services + models
cd apps/web && npm run lint && npm test                     # frontend gate
```
