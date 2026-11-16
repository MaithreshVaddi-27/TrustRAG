"""
TRUSTRAG — frontend/backend integration contract check.

The frontend calls the API by string literal. Nothing in either codebase
cross-checks those literals against the backend's routes, so a renamed or
removed endpoint shows up as a broken page at runtime rather than as a
failed build.

This script closes that gap:

1. **Extract** every `/api/v1/...` path the frontend actually calls, from the
   source (``src/services/*.js``, ``src/lib/*.js``, ``src/hooks/*.js``,
   ``src/pages/*.jsx``, ``src/components/**/*.jsx``), including the
   templated ones (``/analyses/${id}/claims`` -> ``/analyses/{id}/claims``).
2. **Compare** them against the backend's live OpenAPI document.
3. **Exercise** the flow the user actually performs — login, list, create an
   analysis, read it back, read its claims/evidence/trace, mint a stream
   ticket — through the *frontend's* proxy when the Vite dev server is up, so
   the whole browser-facing path is covered.

Usage:
    python scripts/validate_integration.py
    python scripts/validate_integration.py --frontend-url http://localhost:5173
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

REPO = Path(__file__).resolve().parents[3]
API_DIR = REPO / "apps" / "api"
WEB_DIR = REPO / "apps" / "web"

# The shared benchmark account helper lives in this package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.bench_auth import register_or_login  # noqa: E402

# `api.get('/api/v1/knowledge-bases/${kbId}/documents')` and
# `api.get(`/api/v1/analyses/${id}/claims`)` — the template literal and the
# quoted-string forms are both in use.
_CALL = re.compile(
    r"""api\.(?:get|post|put|patch|delete)\(\s*[`'"]([^`'"]*?/api/v1/[^`'"]*)[`'"]""",
    re.MULTILINE,
)
# `${id}` / `${kbId}` / `${analysisId}` -> a path parameter placeholder.
_TEMPLATE = re.compile(r"\$\{[^}]+\}")

# The frontend's own service layer is the single place the API surface is
# described; these directories are where it lives.
_SOURCE_GLOBS = (
    "src/services/*.js",
    "src/lib/*.js",
    "src/hooks/*.js",
    "src/pages/*.jsx",
    "src/components/**/*.jsx",
)

# Endpoints the browser calls that are not part of the documented REST
# surface (an internal health probe the app polls, for instance).
_SKIP_PREFIXES = ("/api/v1/health",)


def _frontend_calls() -> dict[str, set[str]]:
    """Every (method, path) the frontend calls, extracted from the source."""
    calls: dict[str, set[str]] = {}

    patterns = [f"**/{g}" for g in _SOURCE_GLOBS]
    seen: set[Path] = set()
    for pattern in patterns:
        for path in WEB_DIR.glob(pattern):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            for method, raw_path in re.findall(
                r"api\.(get|post|put|patch|delete)\(\s*[`'\"]([^`'\"]*?/api/v1/[^`'\"]*)[`'\"]",
                text,
            ):
                calls.setdefault(method.upper(), set()).add(raw_path)

    return calls


def _normalise(path: str) -> str:
    """`/api/v1/analyses/${id}/claims` -> `/api/v1/analyses/{id}/claims`."""
    return _TEMPLATE.sub("{id}", path)


def _shape(path: str) -> str:
    """The path with every parameter name erased.

    The backend names its parameters (`{analysis_id}`, `{doc_id}`,
    `{kb_id}`); the frontend interpolates its own variable names. Only the
    *shape* of the path is the contract, so the names are erased on both
    sides before comparing.
    """
    return re.sub(r"\{[^}]+\}", "{}", path)


def _openapi_paths(spec: dict[str, Any]) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for path, operations in spec.get("paths", {}).items():
        for method in operations:
            if method.lower() in ("get", "post", "put", "patch", "delete"):
                routes.add((method.upper(), path))
    return routes


async def _check_routes(api_url: str, calls: dict[str, set[str]]) -> dict[str, Any]:
    """Compare the frontend's calls with the backend's routes."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(f"{api_url}/openapi.json")
        res.raise_for_status()
        spec = res.json()

    routes = _openapi_paths(spec)
    route_shapes = {(method, _shape(path)) for method, path in routes}
    missing: list[dict[str, str]] = []
    ok: list[dict[str, str]] = []

    for method, paths in sorted(calls.items()):
        for raw in sorted(paths):
            if raw.startswith(_SKIP_PREFIXES):
                continue
            normalised = _normalise(raw)
            if (method, _shape(normalised)) in route_shapes:
                ok.append({"method": method, "path": normalised})
            else:
                missing.append({"method": method, "path": normalised})

    return {
        "backend_routes": len(routes),
        "frontend_calls": len(ok) + len(missing),
        "matched": len(ok),
        "missing": missing,
        "ok": not missing,
    }


async def _check_flow(base_url: str, token: str, kb_id: str) -> dict[str, Any]:
    """Walk the flow the user actually performs, and check the shapes.

    The frontend's `unwrap()` returns the raw response body, and the pages
    index into it directly (`data.map(...)`, `data.id`). So the shape check
    is: a list endpoint must answer a JSON array whose items are objects,
    and an object endpoint must answer a JSON object.
    """
    headers = {"Authorization": f"Bearer {token}"}
    results: dict[str, Any] = {}
    problems: list[str] = []

    async def _get(path: str) -> Any:
        r = await client.get(f"{base_url}{path}", headers=headers)
        results[path] = r.status_code
        if r.status_code != 200:
            problems.append(f"{path} -> {r.status_code}")
            return None
        return r.json()

    async with httpx.AsyncClient(timeout=120.0) as client:
        kbs = await _get("/api/v1/knowledge-bases")
        if not isinstance(kbs, list):
            problems.append("GET /knowledge-bases did not answer a JSON array")
        elif kbs and not isinstance(kbs[0], dict):
            problems.append("GET /knowledge-bases items are not objects")

        analyses = await _get("/api/v1/analyses")
        if not isinstance(analyses, list):
            problems.append("GET /analyses did not answer a JSON array")

        for path in ("/api/v1/claims", "/api/v1/conflicts", "/api/v1/evidence"):
            payload = await _get(path)
            if payload is not None and not isinstance(payload, list):
                problems.append(f"GET {path} did not answer a JSON array")

        providers = await _get("/api/v1/models/providers")
        if providers is not None:
            if not isinstance(providers, dict) or "providers" not in providers:
                problems.append("GET /models/providers did not answer a provider registry object")
            else:
                for provider, info in providers.get("providers", {}).items():
                    models = info.get("models", []) if isinstance(info, dict) else []
                    if len(models) != len(set(models)):
                        problems.append(f"provider {provider} lists a model twice: {models}")

        # The analysis lifecycle: create, poll, read the artefacts back.
        created = await client.post(
            f"{base_url}/api/v1/analyses",
            headers=headers,
            json={"knowledge_base_id": kb_id, "query": "What is the default rate limit?"},
        )
        results["POST /api/v1/analyses"] = created.status_code
        if created.status_code not in (200, 201):
            problems.append(f"POST /analyses -> {created.status_code}")
        else:
            body = created.json()
            if "id" not in body:
                problems.append("POST /analyses did not answer an object with an id")
            else:
                analysis_id = body["id"]
                for suffix in ("", "/claims", "/evidence", "/trace", "/detail"):
                    await _get(f"/api/v1/analyses/{analysis_id}{suffix}")

                # The stream ticket is how the browser opens its SSE stream
                # without putting the JWT in the URL.
                ticket_res = await client.post(
                    f"{base_url}/api/v1/analyses/{analysis_id}/stream-ticket",
                    headers=headers,
                )
                results["POST /api/v1/analyses/{id}/stream-ticket"] = ticket_res.status_code
                if not 200 <= ticket_res.status_code < 300:
                    problems.append(f"stream-ticket -> {ticket_res.status_code}")
                elif not ticket_res.json().get("ticket"):
                    problems.append("stream-ticket did not answer a ticket")

    return {"statuses": results, "problems": problems, "ok": not problems}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-url", default="http://127.0.0.1:8000")
    ap.add_argument(
        "--frontend-url",
        default=None,
        help="the Vite dev server; when given, the flow is exercised through "
        "the frontend's own /api proxy instead of against the API directly",
    )
    ap.add_argument("--out", default="integration_results.json")
    args = ap.parse_args()

    calls = _frontend_calls()
    report: dict[str, Any] = {"routes": await _check_routes(args.api_url, calls)}

    async with httpx.AsyncClient(timeout=60.0) as client:
        # The shared benchmark account, the same one the other harnesses use:
        # it logs in when it exists and registers a fresh one when it does not.
        # Hardcoding a credential here made this script fail the moment that
        # account was gone.
        token, _email = await register_or_login(client, args.api_url)

        kb_res = await client.get(
            f"{args.api_url}/api/v1/knowledge-bases",
            headers={"Authorization": f"Bearer {token}"},
        )
        kbs = kb_res.json() if kb_res.status_code == 200 else []
        if kbs:
            kb_id = kbs[0]["id"]
        else:
            # A fresh benchmark account has no knowledge base, and an analysis
            # cannot run without one. Create a throwaway collection so the
            # flow can be exercised on a clean machine.
            created = await client.post(
                f"{args.api_url}/api/v1/knowledge-bases",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": "integration-check",
                    "description": "validate_integration.py",
                },
            )
            if created.status_code not in (200, 201):
                print(
                    "could not create a knowledge base: "
                    f"{created.status_code} {created.text[:200]}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            kb_id = created.json()["id"]

    report["flow_direct"] = await _check_flow(args.api_url, token, kb_id)

    if args.frontend_url:
        try:
            report["flow_through_frontend_proxy"] = await _check_flow(
                args.frontend_url, token, kb_id
            )
        except httpx.ConnectError as exc:
            report["flow_through_frontend_proxy"] = {
                "ok": False,
                "problems": [f"the frontend proxy is unreachable: {exc}"],
            }

    report["ok"] = (
        report["routes"]["ok"]
        and report["flow_direct"]["ok"]
        and report.get("flow_through_frontend_proxy", {"ok": True})["ok"]
    )

    print(json.dumps(report, indent=2))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"[integration] wrote {args.out}")
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
