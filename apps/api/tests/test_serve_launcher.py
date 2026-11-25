"""Tests for the cross-platform local stack launcher (scripts/serve.py).

The launcher lives at the repository root because it owns both apps. It is
tested here because this is the repository's pytest root; keeping the test
beside the backend suite means a change to port handling or service probes is
caught by the normal `pytest` run.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LAUNCHER = REPO / "scripts" / "serve.py"

_spec = importlib.util.spec_from_file_location("trustrag_serve", LAUNCHER)
assert _spec is not None and _spec.loader is not None
serve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve)


def test_load_ports_reads_canonical_registry() -> None:
    ports = serve.load_ports()
    assert ports["backend"] == 8000
    assert ports["frontend"] == 5173
    assert ports["mongodb"] == 27017
    assert ports["ollama"] == 11434


def test_load_ports_honours_a_modified_registry(tmp_path: Path, monkeypatch) -> None:
    custom = tmp_path / "ports.yaml"
    custom.write_text(
        "version: 1\nports:\n  backend: 9123\n  frontend: 9124\nhosts:\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(serve, "PORTS_YAML", custom)
    ports = serve.load_ports()
    assert ports["backend"] == 9123
    assert ports["frontend"] == 9124
    # Unspecified services keep their documented defaults.
    assert ports["mongodb"] == 27017


def test_load_ports_falls_back_when_registry_is_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(serve, "PORTS_YAML", tmp_path / "absent.yaml")
    assert serve.load_ports() == serve.DEFAULT_PORTS


def test_mongodb_probe_uses_tcp_not_http(monkeypatch) -> None:
    calls = []

    class _Socket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_connect(address, timeout):
        calls.append((address, timeout))
        return _Socket()

    monkeypatch.setattr(serve.socket, "create_connection", fake_connect)
    assert serve.probe("mongodb", serve.DEFAULT_PORTS) is True
    assert calls == [(("127.0.0.1", 27017), 5.0)]


def test_backend_probe_uses_http_health(monkeypatch) -> None:
    seen = []

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_open(url, timeout):
        seen.append((url, timeout))
        return _Response()

    monkeypatch.setattr(serve.urllib.request, "urlopen", fake_open)
    assert serve.probe("backend", serve.DEFAULT_PORTS) is True
    assert seen[0][0] == "http://127.0.0.1:8000/api/v1/health"


def test_probe_returns_false_on_connection_error(monkeypatch) -> None:
    def fake_open(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(serve.urllib.request, "urlopen", fake_open)
    assert serve.probe("frontend", serve.DEFAULT_PORTS) is False


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("VITE_API_URL=\n", False),
        ("VITE_API_URL=http://localhost:8000\n", True),
        ("# comment\nVITE_API_BASE_URL = https://api.example.com\n", True),
        ("VITE_BACKEND_PORT=8000\n", False),
    ],
)
def test_remote_api_override_detects_proxy_bypass(
    tmp_path: Path, monkeypatch, content: str, expected: bool
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    monkeypatch.setattr(serve, "WEB_DIR", tmp_path)
    assert serve.remote_api_override() is expected


def test_state_dir_is_scoped_per_repository(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRUSTRAG_STATE_DIR", str(tmp_path))
    first = serve.state_dir()
    second = serve.state_dir()
    assert first == second
    assert first.parent == tmp_path
    assert (first / "state.json").name == "state.json"


def test_state_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRUSTRAG_STATE_DIR", str(tmp_path))
    assert serve.read_state() == {}
    serve.write_state({"backend": {"pid": 1234}})
    assert serve.read_state() == {"backend": {"pid": 1234}}
    assert json.loads(serve.state_file().read_text(encoding="utf-8"))["backend"]["pid"] == 1234


def test_status_reports_down_services(capsys, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRUSTRAG_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(serve, "probe", lambda *_args, **_kwargs: False)
    assert serve.cmd_status(serve.DEFAULT_PORTS) == 0
    out = capsys.readouterr().out
    assert "backend" in out and "DOWN" in out
    assert "frontend" in out


def test_cli_help_is_cross_platform() -> None:
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "doctor" in result.stdout
    assert "serve" in result.stdout


@pytest.mark.parametrize("command", ["doctor", "status", "stop"])
def test_subcommands_exist(command: str) -> None:
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), command, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
