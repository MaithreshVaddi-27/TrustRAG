"""
TRUSTRAG — Port propagator (single source of truth: config/ports.yaml).

Usage:
  python3 scripts/apply_ports.py          # rewrite all consumers in place
  python3 scripts/apply_ports.py --check  # exit 1 with diff if anything drifts (CI gate)

Propagates the canonical ports to:
  docker-compose.yml, apps/api/Dockerfile, apps/api/config/models.yaml,
  .env, apps/web/vite.config.js, apps/web/.env.example,
  apps/web/playwright.config.js, apps/web/e2e/auth.spec.js,
  load-test/smoke.js, .github/workflows/ci.yml, README.md

NOTE: .env.example carries no URLs (secrets/endpoints only) — nothing to sync
there. The live .env keeps its explicit OLLAMA/LLAMACPP_BASE_URL lines synced.

Stdlib only. Idempotent — running twice changes nothing the second time.
Model IDs are NOT touched here (apps/api/config/models.yaml + .env own those).
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTS_YAML = ROOT / "config" / "ports.yaml"


def load_ports(path: Path = PORTS_YAML) -> dict[str, int]:
    """Parse the flat `ports:` mapping without third-party deps."""
    text = path.read_text(encoding="utf-8")
    ports: dict[str, int] = {}
    in_ports = False
    for line in text.splitlines():
        if re.match(r"^ports\s*:\s*$", line):
            in_ports = True
            continue
        if in_ports:
            if re.match(r"^\S", line):  # next top-level key ends the block
                break
            m = re.match(r"^\s+([a-z_]+)\s*:\s*(\d+)\s*(?:#.*)?$", line)
            if m:
                ports[m.group(1)] = int(m.group(2))
    required = {
        "backend",
        "frontend",
        "ollama",
        "llamacpp",
        "mongodb",
        "qdrant_http_host",
        "qdrant_http_container",
        "qdrant_grpc_host",
        "qdrant_grpc_container",
    }
    missing = required - ports.keys()
    if missing:
        raise ValueError(f"config/ports.yaml missing keys: {sorted(missing)}")
    return ports


def build_rules(p: dict[str, int]) -> dict[str, list[tuple[str, str]]]:
    """Map of relative path -> [(regex, replacement)] applied in order."""
    b = p["backend"]
    f = p["frontend"]
    ol = p["ollama"]
    ll = p["llamacpp"]
    mg = p["mongodb"]
    rules: dict[str, list[tuple[str, str]]] = {
        "apps/api/Dockerfile": [
            (r"ENV PORT=\d+", f"ENV PORT={b}"),
            (r"EXPOSE \d+", f"EXPOSE {b}"),
            (r"\$\{PORT:-\d+\}", f"${{PORT:-{b}}}"),
        ],
        "apps/api/config/models.yaml": [
            (r'(ollama_base_url:\s*"http://)[^":]+:\d+(")', rf"\1localhost:{ol}\2"),
            (r'(llamacpp_base_url:\s*"http://)[^":]+:\d+(/v1")', rf"\g<1>127.0.0.1:{ll}\2"),
        ],
        ".env": [
            (r"(OLLAMA_BASE_URL=http://)[^:]+:\d+", rf"\g<1>localhost:{ol}"),
            (r"(LLAMACPP_BASE_URL=http://)[^:]+:\d+(/v1)", rf"\g<1>127.0.0.1:{ll}\2"),
        ],
        "apps/web/vite.config.js": [
            (r"port: \d+,", f"port: {f},"),
            (r"\(default: \d+\)", f"(default: {b})"),
            (r"\|\| '\d+'\}\);", f"|| '{b}');"),
        ],
        "apps/web/.env.example": [
            (r"VITE_BACKEND_PORT=\d+", f"VITE_BACKEND_PORT={b}"),
            (r"\(default is \d+\)", f"(default is {b})"),
        ],
        "apps/web/playwright.config.js": [
            (r"http://localhost:\d+/api/v1", f"http://localhost:{b}/api/v1"),
            (r"http://localhost:\d+'", f"http://localhost:{b}'"),
            (r"--port \d+", f"--port {b}"),
            (r"Vite preview on :\d+", f"Vite preview on :{f}"),
            (r"const PORT = \d+", f"const PORT = {f}"),
        ],
        "apps/web/e2e/auth.spec.js": [
            (r"http://localhost:\d+'", f"http://localhost:{b}'"),
            (r'http://localhost:\d+"', f'http://localhost:{b}"'),
        ],
        "load-test/smoke.js": [
            (r"http://localhost:\d+", f"http://localhost:{b}"),
        ],
        ".github/workflows/ci.yml": [
            (r"--port \d+", f"--port {b}"),
            (r"http://127\.0\.0\.1:\d+/api/v1/health", f"http://127.0.0.1:{b}/api/v1/health"),
            (r"E2E_API_URL: http://localhost:\d+", f"E2E_API_URL: http://localhost:{b}"),
            (r"API_BASE_URL: http://localhost:\d+", f"API_BASE_URL: http://localhost:{b}"),
        ],
        "README.md": [
            # Backend-origin URLs only — frontend (:5173), Qdrant (:6335/:6333),
            # MongoDB (:27017) and llama-server (:8080) prose must NOT change.
            (r"http://localhost:\d+/api/v1", f"http://localhost:{b}/api/v1"),
            (r"http://localhost:\d+/docs", f"http://localhost:{b}/docs"),
            (r"http://localhost:\d+/openapi\.json", f"http://localhost:{b}/openapi.json"),
            (r"BASE=http://localhost:\d+", f"BASE=http://localhost:{b}"),
            (r"uvicorn app\.main:app --host [0-9.]+ --port \d+", f"uvicorn app.main:app --host 0.0.0.0 --port {b}"),
            (r"requires backend on :\d+", f"requires backend on :{b}"),
            (r"API_BASE_URL=http://localhost:\d+", f"API_BASE_URL=http://localhost:{b}"),
            (r"E2E_API_URL: http://localhost:\d+", f"E2E_API_URL: http://localhost:{b}"),
        ],
    }
    _ = mg  # mongodb stays 27017 in URIs (default); documented here for completeness
    return rules


def apply(check: bool = False) -> int:
    ports = load_ports()
    rules = build_rules(ports)
    failed: list[str] = []
    for rel, subs in rules.items():
        path = ROOT / rel
        if not path.exists():
            print(f"SKIP (missing): {rel}")
            continue
        original = path.read_text(encoding="utf-8")
        updated = original
        for pat, repl in subs:
            updated = re.sub(pat, repl, updated)
        if updated != original:
            if check:
                failed.append(rel)
                diff = "".join(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        updated.splitlines(keepends=True),
                        fromfile=f"a/{rel}",
                        tofile=f"b/{rel}",
                    )
                )
                print(diff)
            else:
                path.write_text(updated, encoding="utf-8")
                print(f"UPDATED: {rel}")
    # docker-compose needs structural port-map handling on top of regex rules
    compose = ROOT / "docker-compose.yml"
    if compose.exists():
        _sync_compose(compose, ports, check, failed)
    if check and failed:
        print(f"\nDRIFT in: {', '.join(failed)} — run `python3 scripts/apply_ports.py`")
        return 1
    if not check:
        print("ports in sync.")
    return 0


def _sync_compose(path: Path, p: dict[str, int], check: bool, failed: list[str]) -> None:
    b, f, ll = p["backend"], p["frontend"], p["llamacpp"]
    qhh, qhc, qgh, qgc = (
        p["qdrant_http_host"],
        p["qdrant_http_container"],
        p["qdrant_grpc_host"],
        p["qdrant_grpc_container"],
    )
    t = path.read_text(encoding="utf-8")
    orig = t
    t = re.sub(r"FastAPI backend \(Port \d+,", f"FastAPI backend (Port {b},", t)
    t = re.sub(r"llama-server \(:\d+\)", f"llama-server (:{ll})", t)
    t = re.sub(r"--port \d+", f"--port {b}", t)
    t = re.sub(r"http://localhost:\d+/api/v1/health", f"http://localhost:{b}/api/v1/health", t)
    t = re.sub(r"VITE_API_BASE_URL: http://localhost:\d+", f"VITE_API_BASE_URL: http://localhost:{b}", t)
    t = re.sub(
        r"LLAMACPP_BASE_URL: http://host\.docker\.internal:\d+/v1",
        f"LLAMACPP_BASE_URL: http://host.docker.internal:{ll}/v1",
        t,
    )
    # Structural port mappings (order-sensitive, service-aware)
    lines = t.splitlines(keepends=True)
    out: list[str] = []
    in_service = ""
    in_ports = False
    qdrant_seen = 0
    for line in lines:
        if re.match(r"^  [A-Za-z][\w-]*:\s*$", line):
            in_service = line.strip()[:-1]
            in_ports = False
            if in_service == "qdrant":
                qdrant_seen = 0
        elif re.match(r"^    ports:\s*$", line):
            in_ports = True
        elif re.match(r"^    \S", line):
            in_ports = False
        m = re.match(r'^(\s+- ")(\d+):(\d+)(".*)$', line)
        if m and in_ports:
            if in_service == "qdrant":
                if qdrant_seen == 0:
                    line = f'{m.group(1)}{qhh}:{qhc}{m.group(4)}\n'
                else:
                    line = f'{m.group(1)}{qgh}:{qgc}{m.group(4)}\n'
                qdrant_seen += 1
            elif in_service == "api":
                line = f'{m.group(1)}{b}:{b}{m.group(4)}\n'
            elif in_service == "web":
                line = f'{m.group(1)}{f}:{f}{m.group(4)}\n'
        out.append(line)
    t = "".join(out)
    if t != orig:
        if check:
            failed.append("docker-compose.yml")
            print("".join(difflib.unified_diff(orig.splitlines(keepends=True), t.splitlines(keepends=True), fromfile="a/docker-compose.yml", tofile="b/docker-compose.yml")))
        else:
            path.write_text(t, encoding="utf-8")
            print("UPDATED: docker-compose.yml")


def main() -> int:
    ap = argparse.ArgumentParser(description="Propagate config/ports.yaml to all consumers.")
    ap.add_argument("--check", action="store_true", help="fail (exit 1) if any file drifts")
    args = ap.parse_args()
    try:
        return apply(check=args.check)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
