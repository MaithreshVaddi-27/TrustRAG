"""
TRUSTRAG — B5 resilience validation.

Three things the happy-path benchmark cannot show:

1. **Concurrency** — several analyses at once must not corrupt each other
   (shared Qdrant collection, shared HTTP pool, shared settings cache).
2. **Provider down** — an unreachable inference server must produce a clear
   503 with an actionable message, not a hang and not a stack trace.
3. **Database down** — an unreachable MongoDB must produce the API's standard
   error envelope, not a leaked traceback.

Each outage is induced with a graceful SIGTERM and then repaired, so no data
is corrupted. The script is read-mostly: it creates analyses, it does not
delete anything.

Usage:
    python scripts/validate_resilience.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.bench_auth import register_or_login

REPO = Path(__file__).resolve().parents[3]
API_DIR = REPO / "apps" / "api"
START_SCRIPT = API_DIR / "scripts" / "start_local_services.sh"


def _run(cmd: list[str]) -> str:
    return subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, check=False
    ).stdout


def _stop(pattern: str) -> bool:
    """Graceful stop of a matching process (SIGTERM, never SIGKILL)."""
    out = _run(["/usr/bin/pgrep", "-f", pattern])
    pids = [line.strip() for line in out.splitlines() if line.strip().isdigit()]
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            continue
    return bool(pids)


def _repair() -> None:
    """Bring the local services back up."""
    subprocess.run(  # noqa: S603
        ["/bin/bash", str(START_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )


async def _concurrency_phase(client, base_url: str, token: str, kb_id: str, n: int) -> dict:
    """Run N analyses at once and check every one reaches a terminal state."""
    headers = {"Authorization": f"Bearer {token}"}

    async def _one(i: int) -> dict[str, Any]:
        r = await client.post(
            f"{base_url}/api/v1/analyses",
            headers=headers,
            json={
                "knowledge_base_id": kb_id,
                "query": f"How many handshakes per cycle? (probe {i})",
            },
        )
        if r.status_code not in (200, 201):
            return {"ok": False, "stage": "create", "status": r.status_code}
        analysis_id = r.json()["id"]
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            g = await client.get(f"{base_url}/api/v1/analyses/{analysis_id}", headers=headers)
            if g.status_code == 200:
                doc = g.json()
                if doc.get("status") in ("completed", "abstained", "failed"):
                    return {"ok": True, "status": doc["status"]}
            await asyncio.sleep(1)
        return {"ok": False, "stage": "poll", "status": "timeout"}

    started = time.perf_counter()
    results = await asyncio.gather(*(_one(i) for i in range(n)))
    elapsed = (time.perf_counter() - started) * 1000
    terminal = [r for r in results if r.get("ok")]
    return {
        "phase": "concurrency",
        "n": n,
        "terminal": len(terminal),
        "failures": [r for r in results if not r.get("ok")],
        "statuses": [r.get("status") for r in terminal],
        "elapsed_ms": round(elapsed),
        "ok": len(terminal) == n,
    }


async def _provider_down_phase(client, base_url: str, token: str, kb_id: str) -> dict:
    """With the inference server stopped, an analysis must fail fast and clearly."""
    headers = {"Authorization": f"Bearer {token}"}
    stopped = _stop("ollama serve")
    time.sleep(2)
    try:
        t0 = time.perf_counter()
        r = await client.post(
            f"{base_url}/api/v1/analyses",
            headers=headers,
            json={
                "knowledge_base_id": kb_id,
                "query": "What is the reciprocal rank fusion constant?",
            },
        )
        elapsed = (time.perf_counter() - t0) * 1000
        body = r.json() if r.content else {}
        message = ""
        if isinstance(body, dict):
            message = str(body.get("error", {}).get("message", ""))
        return {
            "phase": "provider_down",
            "stopped": stopped,
            "status": r.status_code,
            "elapsed_ms": round(elapsed),
            "message": message[:220],
            "mentions_provider": "ollama" in message.lower() or "llm" in message.lower(),
            "ok": r.status_code == 503 and bool(message),
        }
    finally:
        _repair()


async def _database_down_phase(client, base_url: str, token: str) -> dict:
    """With MongoDB stopped, the API must answer with its error envelope."""
    headers = {"Authorization": f"Bearer {token}"}
    stopped = _stop("mongod --dbpath")
    time.sleep(3)
    try:
        r = await client.get(f"{base_url}/api/v1/knowledge-bases", headers=headers)
        body = r.json() if r.content else {}
        message = ""
        if isinstance(body, dict):
            message = str(body.get("error", {}).get("message", ""))
        return {
            "phase": "database_down",
            "stopped": stopped,
            "status": r.status_code,
            "message": message[:220],
            "envelope": isinstance(body, dict) and "error" in body,
            "ok": r.status_code >= 500 and isinstance(body, dict) and "error" in body,
        }
    finally:
        _repair()


async def _rate_limit_phase(client, base_url: str, token: str) -> dict:
    """The global budget must fire and use the standard error envelope."""
    headers = {"Authorization": f"Bearer {token}"}
    codes: list[int] = []
    for _ in range(260):
        r = await client.get(f"{base_url}/api/v1/models/providers", headers=headers)
        codes.append(r.status_code)
        if r.status_code == 429:
            body = r.json()
            return {
                "phase": "rate_limit",
                "requests": len(codes),
                "status": 429,
                "code": body.get("error", {}).get("code"),
                "retry_after": r.headers.get("Retry-After"),
                "ok": body.get("error", {}).get("code") == "RATE_LIMITED",
            }
    return {"phase": "rate_limit", "requests": len(codes), "status": codes[-1], "ok": False}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="resilience_results.json")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    import httpx

    report: dict[str, Any] = {"phases": []}

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        token, _email = await register_or_login(client, args.base_url)
        headers = {"Authorization": f"Bearer {token}"}

        r = await client.get(f"{args.base_url}/api/v1/knowledge-bases", headers=headers)
        kb_id = r.json()[0]["id"] if r.status_code == 200 and r.json() else ""

        report["phases"].append(
            await _concurrency_phase(client, args.base_url, token, kb_id, args.concurrency)
        )
        report["phases"].append(await _rate_limit_phase(client, args.base_url, token))
        # The rate-limit phase spends the budget for this client; wait for the
        # window to roll over before the outage phases.
        await asyncio.sleep(62)
        report["phases"].append(await _provider_down_phase(client, args.base_url, token, kb_id))
        report["phases"].append(await _database_down_phase(client, args.base_url, token))

    report["ok"] = all(p.get("ok") for p in report["phases"])
    print(json.dumps(report, indent=2))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"[validate] wrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
