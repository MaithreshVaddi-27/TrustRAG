# TRUSTRAG — repository tooling

Every script that operates on the repository as a whole lives here, grouped
by what it does.

| Folder | What it does | Entry point |
|---|---|---|
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
bash scripts/servers/start_local_llm.sh    # llama-server on :9931 (optional)
bash apps/api/scripts/start_local_services.sh   # Mongo + Ollama + API
```

## The order CI goes in

```bash
python scripts/checks/apply_ports.py --check   # no port drift
bash scripts/checks/typecheck_ratchet.sh       # no new type errors
bash scripts/checks/e2e_manual_verify.sh       # browser-driven smoke
```
