#!/usr/bin/env python3
"""
TRUSTRAG — Pre-backend local model discovery.

Queries the locally installed GENERATIVE models from the CLI tooling:
    ollama       -> `ollama list`
    llama.cpp    -> `llama-server --cache-list`

Seeds the shared in-process discovery cache (app.core.local_llm) AND persists a
JSON snapshot that the backend reads at startup (see main.py lifespan), so every
model installed locally is selectable from the very first request — no need to
first hit /models/providers.

Run BEFORE starting the backend:

    apps/api/.venv/bin/python scripts/discover_local_models.py
    # or, with the repo venv active:
    python scripts/discover_local_models.py

Embedding models (nomic-embed, bge, etc.) are intentionally filtered out — Ollama
and llama.cpp are LLM-only in TrustRAG.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from app.core.local_llm import (
    seed_local_model_discovery,
)


def _fmt(models: list[str]) -> str:
    return "\n".join(f"    - {m}" for m in models) or "    (none found — is the service installed?)"


async def main() -> int:
    print("TRUSTRAG — discovering locally installed models\n")
    result = await seed_local_model_discovery()

    ollama = result["ollama"]
    llamacpp = result["llama_cpp"]

    print("[ollama]     `ollama list`")
    print(_fmt(ollama))
    print()
    print("[llama.cpp]  `llama-server --cache-list`")
    print(_fmt(llamacpp))
    print()

    total = len(ollama) + len(llamacpp)
    print(f"Discovered {total} local generative model(s) — snapshot cached for the backend.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))