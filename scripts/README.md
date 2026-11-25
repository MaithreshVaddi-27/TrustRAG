# TRUSTRAG — repository tooling

Every script that operates on the repository as a whole lives here, grouped
by what it does.

| File / folder | What it does | Entry point |
|---|---|---|
| [`serve.py`](serve.py) | Start the whole local stack on macOS, Linux or Windows | `python scripts/serve.py serve` |
| [`serve.ps1`](serve.ps1) | Windows wrapper that finds Python and forwards to `serve.py` | `powershell -File scripts\serve.ps1 serve` |
| [`setup/`](setup/) | Prepare a machine: the ONNX bake, the export tools, the prerequisite check | `python scripts/setup/bootstrap.py` |
| [`servers/`](servers/) | Start the local inference servers | `bash scripts/servers/start_local_llm.sh` |
| [`checks/`](checks/) | Verify the repository itself: the port registry, the type ratchet, the end-to-end smoke | `python scripts/checks/apply_ports.py --check` |
| [`eval/`](eval/) | Score the models against a ground truth | `bash scripts/eval/eval_provider.sh llama_cpp` |

The backend's own harnesses — the API benchmark, the accuracy evaluation and
the integration/resilience checks — live next to the code they measure, in
[`apps/api/scripts/`](../apps/api/scripts/).

## The order a new machine goes in

```bash
python scripts/setup/bootstrap.py          # ONNX weights + local-model snapshot
python scripts/serve.py doctor             # verify prerequisites and service health
python scripts/serve.py serve              # Mongo + Ollama + API + Vite
```

`serve.py` reads all ports from `config/ports.yaml` and uses only the standard
library. On Windows use `powershell -ExecutionPolicy Bypass -File scripts\serve.ps1`
with the same arguments. The optional local LLM on :9931 still has its own
bash launcher: `bash scripts/servers/start_local_llm.sh`.

## The order CI goes in

```bash
python scripts/checks/apply_ports.py --check   # no port drift
bash scripts/checks/typecheck_ratchet.sh       # no new type errors
bash scripts/checks/e2e_manual_verify.sh       # browser-driven smoke
```
