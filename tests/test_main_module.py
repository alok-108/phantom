"""Exercise the installed module entry point with real subprocesses and CLI dispatch."""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from phantom import __version__

FIXTURE = Path(__file__).parent / "fixtures" / "valid_plain.py"


def _module(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "phantom", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_module_version_from_another_working_directory(tmp_path: Path) -> None:
    result = _module("--version", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.strip() == f"phantom {__version__}"
    assert not result.stderr


def test_module_checks_a_plain_python_file(tmp_path: Path) -> None:
    result = _module("check", str(FIXTURE.resolve()), cwd=tmp_path)
    assert result.returncode == 0
    assert "Traceback" not in result.stdout + result.stderr


def test_module_missing_file_returns_cli_error_without_traceback(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"
    result = _module("check", str(missing), cwd=tmp_path)
    assert result.returncode == 1
    assert missing.name in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr


@pytest.mark.parametrize("missing", [False, True])
def test_module_dispatch_keeps_the_cli_exit_code(monkeypatch, tmp_path, missing) -> None:
    # Run the real module in this process too, so coverage records __main__.py.
    path = tmp_path / "missing.py" if missing else FIXTURE.resolve()
    monkeypatch.setattr(sys, "argv", ["phantom", "check", str(path)])
    with pytest.raises(SystemExit) as result:
        runpy.run_module("phantom", run_name="__main__")
    assert result.value.code == (1 if missing else 0)
