"""Tests for Phantom host execution."""

from __future__ import annotations

import time
from pathlib import Path

from phantom.host import HostResult, execute_host_program

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_execute_host_program_success():
    target = FIXTURES_DIR / "valid_plain.py"
    res = execute_host_program(str(target))

    assert isinstance(res, HostResult)
    assert res.exit_code == 0
    assert "Hello, World!" in res.stdout
    assert res.stderr == ""
    assert res.duration_ms >= 0


def test_execute_host_program_with_args(tmp_path):
    script = tmp_path / "args_test.py"
    script.write_text("import sys; print(' '.join(sys.argv[1:]))")

    res = execute_host_program(str(script), args=["alpha", "beta", "gamma"])
    assert res.exit_code == 0
    assert res.stdout.strip() == "alpha beta gamma"


def test_execute_host_program_not_found():
    res = execute_host_program("non_existent_file_xyz.py")
    assert res.exit_code == 1
    assert "not found" in res.stderr.lower()
    assert res.exception is not None


def test_execute_host_program_timeout(tmp_path):
    script = tmp_path / "hang.py"
    script.write_text("import time; time.sleep(5)")

    res = execute_host_program(str(script), timeout=0.2)
    assert res.exit_code == 124
    assert "timed out" in res.stderr.lower()


_GRANDCHILD = (
    "import subprocess, sys, time\n"
    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
    "print('started', flush=True)\n"
)


def test_timeout_kills_children_that_hold_the_pipes(tmp_path):
    script = tmp_path / "parent_sleeps.py"
    script.write_text(_GRANDCHILD + "time.sleep(60)\n")

    started = time.perf_counter()
    res = execute_host_program(str(script), timeout=1.5)
    elapsed = time.perf_counter() - started

    assert res.exit_code == 124
    assert "timed out" in res.stderr.lower()
    assert "started" in res.stdout
    assert elapsed < 15, f"timeout was not enforced: returned after {elapsed:.1f}s"


def test_timeout_kills_orphans_after_the_parent_exited(tmp_path):
    script = tmp_path / "parent_exits.py"
    script.write_text(_GRANDCHILD)

    started = time.perf_counter()
    res = execute_host_program(str(script), timeout=1.5)
    elapsed = time.perf_counter() - started

    assert "started" in res.stdout
    assert elapsed < 15, f"timeout was not enforced: returned after {elapsed:.1f}s"


def test_partial_output_is_kept_on_timeout(tmp_path):
    script = tmp_path / "partial.py"
    script.write_text("import time\nprint('before', flush=True)\ntime.sleep(30)\n")

    res = execute_host_program(str(script), timeout=1.0)
    assert res.exit_code == 124
    assert "before" in res.stdout


def test_execute_host_program_with_stdin_text(tmp_path):
    script = tmp_path / "stdin_test.py"
    script.write_text("print(input())\n")

    res = execute_host_program(str(script), stdin_text="hello\n")
    assert res.exit_code == 0
    assert res.stdout.strip() == "hello"
