"""Phantom Host Program Execution.

Executes host Python programs in isolated subprocesses with timeout
and resource management.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

# How long to wait for the pipes to close after the process tree was killed.
_DRAIN_SECONDS = 5.0


@dataclass
class HostResult:
    """Result of executing a host program."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    exception: str | None = None


class _WindowsJob:
    """A Windows job object, so the host's descendants can be terminated together.

    `taskkill /T` cannot reach processes whose parent already exited; a job
    object tracks descendants regardless. Everything here is best effort: if the
    job cannot be created or assigned (for example when Phantom itself runs in a
    restrictive job), `kill_tree` falls back to `taskkill`.
    """

    _PROCESS_SET_QUOTA = 0x0100
    _PROCESS_TERMINATE = 0x0001

    def __init__(self, pid: int) -> None:
        self._job: int | None = None
        try:
            import ctypes
            from ctypes import wintypes

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
            k32.CreateJobObjectW.restype = wintypes.HANDLE
            k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
            k32.CloseHandle.argtypes = [wintypes.HANDLE]
            self._k32 = k32
            job = k32.CreateJobObjectW(None, None)
            if not job:
                return
            proc = k32.OpenProcess(self._PROCESS_SET_QUOTA | self._PROCESS_TERMINATE, False, pid)
            if not proc:
                k32.CloseHandle(job)
                return
            try:
                if k32.AssignProcessToJobObject(job, proc):
                    self._job = job
                else:
                    k32.CloseHandle(job)
            finally:
                k32.CloseHandle(proc)
        except (OSError, AttributeError, ImportError):
            self._job = None

    def terminate(self) -> bool:
        if self._job is None:
            return False
        return bool(self._k32.TerminateJobObject(self._job, 1))

    def close(self) -> None:
        if self._job is not None:
            self._k32.CloseHandle(self._job)
            self._job = None


def _kill_tree(proc: subprocess.Popen[str], job: _WindowsJob | None) -> None:
    """Kill the host and everything it started."""
    if sys.platform == "win32":
        if job is not None and job.terminate():
            return
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.kill()


def _as_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def execute_host_program(
    filepath: str,
    args: list[str] | None = None,
    timeout: float = 30.0,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> HostResult:
    """Execute a Python program in a subprocess.

    Uses sys.executable to run the same Python.
    Captures stdout, stderr, exit code.
    Applies timeout; on expiry the host *and every process it started* are killed,
    so a child that keeps the output pipes open cannot stretch the timeout.
    Never modifies the host file.
    When stdin_text is None the program inherits the caller's stdin, as before;
    when it is given, exactly those bytes are fed to the program instead.
    """
    if not os.path.isfile(filepath):
        return HostResult(
            exit_code=1,
            stdout="",
            stderr=f"Error: Host file not found: '{filepath}'",
            duration_ms=0.0,
            exception=f"FileNotFoundError: '{filepath}'",
        )

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    # Ensure unbuffered and UTF-8 output
    merged_env["PYTHONUNBUFFERED"] = "1"
    merged_env["PYTHONIOENCODING"] = "utf-8"

    cmd = [sys.executable, filepath]
    if args:
        cmd.extend(args)

    start_time = time.perf_counter()
    job: _WindowsJob | None = None
    try:
        # The host gets its own process group (POSIX session) so the whole tree can be killed.
        group: dict[str, Any] = (
            {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
            if sys.platform == "win32"
            else {"start_new_session": True}
        )
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=merged_env,
            encoding="utf-8",
            errors="replace",
            **group,
        )
        if sys.platform == "win32":
            job = _WindowsJob(proc.pid)
        try:
            stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _kill_tree(proc, job)
            try:
                stdout, stderr = proc.communicate(timeout=_DRAIN_SECONDS)
            except subprocess.TimeoutExpired as drain:
                # Something outside the tree still holds the pipes: report what we have.
                stdout = _as_text(drain.stdout or exc.stdout)
                stderr = _as_text(drain.stderr or exc.stderr)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            timeout_msg = f"\n[HostExecution] Process timed out after {timeout} seconds."
            return HostResult(
                exit_code=124,
                stdout=stdout,
                stderr=stderr + timeout_msg,
                duration_ms=duration_ms,
                exception=f"TimeoutExpired: Process timed out after {timeout} seconds",
            )
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return HostResult(
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return HostResult(
            exit_code=1,
            stdout="",
            stderr=f"Execution error: {exc}",
            duration_ms=duration_ms,
            exception=str(exc),
        )
    finally:
        if job is not None:
            job.close()
