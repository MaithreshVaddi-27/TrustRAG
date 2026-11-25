#!/usr/bin/env python3
"""Cross-platform local stack launcher for TRUSTRAG.

One entry point for macOS, Linux and Windows. Uses only the Python standard
library, reads every port from config/ports.yaml (the repository's single
source of truth), and never hardcodes an OS-specific binary path.

    python scripts/serve.py doctor
    python scripts/serve.py serve --detach
    python scripts/serve.py status
    python scripts/serve.py stop

Windows: powershell -ExecutionPolicy Bypass -File scripts\\serve.ps1 serve
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API_DIR = REPO / "apps" / "api"
WEB_DIR = REPO / "apps" / "web"
PORTS_YAML = REPO / "config" / "ports.yaml"

DEFAULT_PORTS = {
    "backend": 8000,
    "frontend": 5173,
    "ollama": 11434,
    "mongodb": 27017,
}

# Health probes. The backend's /api/v1/health is a real readiness signal;
# for the other services a successful TCP connect is enough.
PROBES = {
    "mongodb": ("/", None),
    "ollama": ("/api/tags", "ollama"),
    "backend": ("/api/v1/health", "backend"),
    "frontend": ("/", "frontend"),
}


def load_ports() -> dict[str, int]:
    """Read the canonical port registry without needing PyYAML installed."""
    ports = dict(DEFAULT_PORTS)
    try:
        lines = PORTS_YAML.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ports

    in_ports = False
    for line in lines:
        if line.startswith("ports:"):
            in_ports = True
            continue
        if in_ports and line.strip() and not line[0].isspace():
            break
        if not in_ports:
            continue
        match = re.match(r"^  ([a-z_]+):\s*(\d+)\s*(?:#.*)?$", line)
        if match:
            ports[match.group(1)] = int(match.group(2))
    return ports


def state_dir() -> Path:
    """Per-repository scratch dir under the OS temp folder."""
    override = os.environ.get("TRUSTRAG_STATE_DIR")
    base = Path(override) if override else Path(tempfile.gettempdir()) / "trustrag-serve"
    # Used only to namespace scratch files, never for security.
    key = hashlib.sha1(str(REPO).encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    path = base / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_file() -> Path:
    return state_dir() / "state.json"


def read_state() -> dict:
    try:
        data = json.loads(state_file().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state: dict) -> None:
    state_file().write_text(json.dumps(state, indent=2), encoding="utf-8")


def base_url(service: str, ports: dict[str, int]) -> str:
    key = ports.get(service, DEFAULT_PORTS.get(service, 0))
    return f"http://127.0.0.1:{key}"


def probe(service: str, ports: dict[str, int], timeout: float = 5.0) -> bool:
    path, port_key = PROBES[service]
    port = ports.get(port_key, DEFAULT_PORTS.get(port_key, 0)) if port_key else ports[service]
    if path == "/" and service == "mongodb":
        # MongoDB speaks its own wire protocol, not HTTP. A TCP connect is the
        # correct readiness signal; an HTTP probe could never succeed here.
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout):
                return True
        except OSError:
            return False
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_for(service: str, ports: dict[str, int], tries: int = 60, delay: float = 1.0) -> bool:
    for _ in range(tries):
        if probe(service, ports):
            return True
        time.sleep(delay)
    return False


def windows_tool(name: str) -> str:
    """Absolute path to a Windows system tool (avoid PATH hijacking)."""
    found = shutil.which(name)
    if found:
        return found
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return str(Path(windir) / "System32" / f"{name}.exe")


def alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(  # noqa: S603 — resolved binary path, fixed argv
            [windows_tool("tasklist"), "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def terminate(pid: int) -> None:
    if not alive(pid):
        return
    if os.name == "nt":
        subprocess.run(  # noqa: S603 — resolved binary path, fixed argv
            [windows_tool("taskkill"), "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def find_python() -> str | None:
    """Backend interpreter: explicit override, project venv, then PATH."""
    candidates = []
    override = os.environ.get("TRUSTRAG_PYTHON")
    if override:
        candidates.append(override)
    candidates += [
        str(API_DIR / ".venv" / "Scripts" / "python.exe"),
        str(API_DIR / ".venv" / "bin" / "python"),
        sys.executable,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        exe = shutil.which(candidate) or candidate
        if Path(exe).is_absolute() and not Path(exe).exists():
            continue
        try:
            check = subprocess.run(  # noqa: S603 — validated interpreter path, fixed argv
                [exe, "-c", "import sys, uvicorn; assert sys.version_info >= (3, 11)"],
                capture_output=True,
                timeout=20,
                check=False,
            )
            if check.returncode == 0:
                return exe
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def find_npm() -> str | None:
    return shutil.which("npm") or shutil.which("npm.cmd")


def start_daemon(name: str, command: list[str], cwd: Path) -> int:
    log = state_dir() / f"{name}.log"
    with log.open("ab", buffering=0) as handle:
        options = {
            "stdout": handle,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
            "cwd": str(cwd),
        }
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            options["creationflags"] = flags
        else:
            options["start_new_session"] = True
        process = subprocess.Popen(command, **options)  # noqa: S603 — argv built by this module
    return process.pid


def start_service(name: str, command: list[str], cwd: Path, state: dict) -> bool:
    pid = start_daemon(name, command, cwd)
    state[name] = {"pid": pid, "log": str(state_dir() / f"{name}.log")}
    write_state(state)
    print(f"[serve] started {name} (pid {pid})")
    return True


def remote_api_override() -> bool:
    """True when apps/web/.env points the frontend at a remote API origin.

    The Vite dev proxy is the supported local path: it keeps /api on the same
    origin, so no CORS header has to be configured. A non-empty VITE_API_URL
    silently bypasses it and produces an "API offline" dashboard.
    """
    env_file = WEB_DIR / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() in ("VITE_API_URL", "VITE_API_BASE_URL") and value.strip():
            return True
    return False


def cmd_doctor(ports: dict[str, int]) -> int:
    checks: list[tuple[str, bool, str]] = [
        ("ports registry", PORTS_YAML.exists(), str(PORTS_YAML)),
        ("root .env", (REPO / ".env").exists(), "copy .env.example to .env"),
        ("backend venv python", find_python() is not None, "pip install -e '.[dev]' in apps/api"),
        ("npm", find_npm() is not None, "install Node.js 20+"),
        ("frontend deps", (WEB_DIR / "node_modules").exists(), "npm install in apps/web"),
        # A local VITE_API_URL bypasses the Vite dev proxy and breaks CORS.
        # .env.example documents the empty value for exactly this reason.
        (
            "dev proxy unblocked",
            not remote_api_override(),
            "clear VITE_API_URL in apps/web/.env for local development",
        ),
        (
            "onnx models",
            len(list((API_DIR / ".model_cache").glob("*.onnx"))) >= 2,
            "python scripts/setup/bootstrap.py",
        ),
        (
            "mongod",
            shutil.which("mongod") is not None,
            "install MongoDB or use docker compose up mongodb",
        ),
        ("ollama", shutil.which("ollama") is not None, "optional: install Ollama for local LLM"),
    ]
    failed = 0
    for name, ok, hint in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name:22} {'' if ok else hint}")
        failed += 0 if ok else 1
    for service in ("mongodb", "ollama", "backend", "frontend"):
        state = "PASS" if probe(service, ports) else "DOWN"
        print(f"{state}  {service} ({base_url(service, ports)})")
    return 1 if failed else 0


def cmd_status(ports: dict[str, int]) -> int:
    state = read_state()
    for service in ("mongodb", "ollama", "backend", "frontend"):
        entry = state.get(service, {})
        pid = entry.get("pid", 0)
        url = base_url(service, ports)
        status = "UP" if probe(service, ports) else "DOWN"
        owner = f" pid={pid}" if alive(pid) else ""
        print(f"{service:10} {status:4} {url}{owner}")
    return 0


def cmd_stop(ports: dict[str, int]) -> int:
    state = read_state()
    if not state:
        print("[serve] no recorded services to stop")
        return 0
    for service, entry in state.items():
        pid = int(entry.get("pid", 0))
        if alive(pid):
            terminate(pid)
            print(f"[serve] stopped {service} (pid {pid})")
    write_state({})
    return 0


def cmd_serve(args: argparse.Namespace, ports: dict[str, int]) -> int:
    state = read_state()
    only = args.only
    py = find_python()
    npm = find_npm()

    if only in ("all", "backend") and py is None:
        print(
            "[serve] no Python 3.11+ with uvicorn found; run 'python scripts/serve.py doctor'",
            file=sys.stderr,
        )
        return 1
    if only in ("all", "frontend") and npm is None:
        print("[serve] npm not found; run 'python scripts/serve.py doctor'", file=sys.stderr)
        return 1
    if only in ("all", "frontend") and not (WEB_DIR / "node_modules").exists():
        print(
            f"[serve] frontend dependencies missing; run 'npm install' in {WEB_DIR}",
            file=sys.stderr,
        )
        return 1

    if only in ("all", "backend") and not args.skip_deps:
        if not probe("mongodb", ports) and shutil.which("mongod"):
            dbpath = state_dir() / "mongodata"
            dbpath.mkdir(parents=True, exist_ok=True)
            start_service(
                "mongodb",
                [
                    "mongod",
                    "--dbpath",
                    str(dbpath),
                    "--port",
                    str(ports["mongodb"]),
                    "--logpath",
                    str(state_dir() / "mongod.log"),
                ],
                REPO,
                state,
            )
        if not probe("ollama", ports) and shutil.which("ollama") and not args.skip_ollama:
            start_service("ollama", ["ollama", "serve"], REPO, state)

    if only in ("all", "backend") and not probe("backend", ports):
        start_service(
            "backend",
            [
                py,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(ports["backend"]),
                "--log-level",
                "info",
            ],
            API_DIR,
            state,
        )

    if only in ("all", "frontend") and not probe("frontend", ports):
        env = dict(os.environ, VITE_BACKEND_PORT=str(ports["backend"]))
        with EnvOverride(env):
            pid = start_daemon(
                "frontend",
                [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(ports["frontend"])],
                WEB_DIR,
            )
        state["frontend"] = {"pid": pid, "log": str(state_dir() / "frontend.log")}
        write_state(state)
        print(f"[serve] started frontend (pid {pid})")

    deadlines = []
    for service in ("mongodb", "backend", "frontend"):
        if only == "frontend" and service != "frontend":
            continue
        if only == "backend" and service == "frontend":
            continue
        if service == "mongodb" and args.skip_deps:
            continue
        if not probe(service, ports) and not wait_for(service, ports):
            deadlines.append(service)
    if deadlines:
        print(f"[serve] did not become healthy: {', '.join(deadlines)}", file=sys.stderr)
        for service in deadlines:
            log = state_dir() / f"{service}.log"
            if log.exists():
                print(
                    f"--- {log} ---\n{log.read_text(encoding='utf-8', errors='replace')[-3000:]}",
                    file=sys.stderr,
                )
        return 1

    print(f"[serve] frontend  {base_url('frontend', ports)}")
    print(f"[serve] backend   {base_url('backend', ports)}")
    print(f"[serve] API docs  {base_url('backend', ports)}/docs")
    if args.detach:
        print("[serve] running in background. Stop with: python scripts/serve.py stop")
        return 0

    print("[serve] press Ctrl+C to stop all services")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[serve] stopping services")
        return cmd_stop(ports)


class EnvOverride:
    """Temporarily set environment variables for a subprocess launch."""

    def __init__(self, values: dict[str, str]) -> None:
        self.values = values
        self.previous: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)
            os.environ[key] = value

    def __exit__(self, *_args: object) -> None:
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="check prerequisites and service health")
    sub.add_parser("status", help="show service health and recorded PIDs")
    sub.add_parser("stop", help="stop services started by this launcher")

    serve = sub.add_parser("serve", help="start the local stack")
    serve.add_argument("--only", choices=("all", "backend", "frontend"), default="all")
    serve.add_argument("--detach", action="store_true", help="start and exit (logs in temp dir)")
    serve.add_argument("--skip-deps", action="store_true", help="do not start Mongo/Ollama")
    serve.add_argument("--skip-ollama", action="store_true", help="do not start Ollama")

    args = parser.parse_args(argv)
    ports = load_ports()
    if args.command == "doctor":
        return cmd_doctor(ports)
    if args.command == "status":
        return cmd_status(ports)
    if args.command == "stop":
        return cmd_stop(ports)
    return cmd_serve(args, ports)


if __name__ == "__main__":
    raise SystemExit(main())
