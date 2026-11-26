"""Cross-platform process control for the resilience harness.

``validate_resilience.py`` induces outages by stopping local services and then
repairing them. These tests pin the platform branches so a future edit cannot
reintroduce a hardcoded ``/usr/bin/pgrep`` or ``/bin/bash`` path.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
MODULE = API_DIR / "scripts" / "verify" / "validate_resilience.py"

_spec = importlib.util.spec_from_file_location("validate_resilience", MODULE)
assert _spec is not None and _spec.loader is not None
resilience = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resilience)


def test_posix_stop_resolves_pgrep_and_signals_pid(monkeypatch) -> None:
    commands = []
    signals = []
    monkeypatch.setattr(resilience.os, "name", "posix")
    monkeypatch.setattr(resilience.shutil, "which", lambda name: "/opt/bin/pgrep")
    monkeypatch.setattr(resilience, "_run", lambda cmd: commands.append(cmd) or "4242\n")
    monkeypatch.setattr(resilience.os, "kill", lambda pid, sig: signals.append((pid, sig)))

    assert resilience._stop("ollama serve") is True
    assert commands == [["/opt/bin/pgrep", "-f", "ollama serve"]]
    assert signals == [(4242, resilience.signal.SIGTERM)]


def test_posix_stop_without_pgrep_is_a_clean_noop(monkeypatch) -> None:
    monkeypatch.setattr(resilience.os, "name", "posix")
    monkeypatch.setattr(resilience.shutil, "which", lambda _name: None)
    assert resilience._stop("mongod --dbpath") is False


def test_windows_stop_uses_graceful_taskkill(monkeypatch) -> None:
    launches = []
    monkeypatch.setattr(resilience.os, "name", "nt")
    monkeypatch.setattr(
        resilience.shutil,
        "which",
        lambda name: f"C:\\Windows\\System32\\{name}.exe",
    )
    monkeypatch.setattr(
        resilience,
        "_run",
        lambda cmd: '"mongod.exe","1234","Console","1","100 K"\n',
    )

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        resilience.subprocess,
        "run",
        lambda cmd, **_kwargs: launches.append(cmd) or _Result(),
    )

    assert resilience._stop("mongod --dbpath") is True
    assert launches == [["C:\\Windows\\System32\\taskkill.exe", "/PID", "1234"]]
    assert all("/F" not in part for part in launches[0])


def test_windows_repair_invokes_the_python_launcher(monkeypatch, tmp_path: Path) -> None:
    launches = []
    monkeypatch.setattr(resilience.os, "name", "nt")
    monkeypatch.setattr(resilience, "REPO", tmp_path)
    monkeypatch.setattr(resilience.shutil, "which", lambda name: f"C:\\Tools\\{name}.exe")

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        resilience.subprocess,
        "run",
        lambda cmd, **_kwargs: launches.append(cmd) or _Result(),
    )

    resilience._repair()
    command = launches[0]
    assert command[0].endswith("powershell.exe")
    assert str(tmp_path / "scripts" / "serve.ps1") in command
    assert command[-2:] == ["serve", "--detach"]


def test_posix_repair_uses_resolved_bash(monkeypatch, tmp_path: Path) -> None:
    launches = []
    monkeypatch.setattr(resilience.os, "name", "posix")
    monkeypatch.setattr(resilience, "REPO", tmp_path)
    monkeypatch.setattr(resilience.shutil, "which", lambda name: "/usr/local/bin/bash")

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        resilience.subprocess,
        "run",
        lambda cmd, **_kwargs: launches.append(cmd) or _Result(),
    )

    resilience._repair()
    assert launches[0] == ["/usr/local/bin/bash", str(resilience.START_SCRIPT)]
