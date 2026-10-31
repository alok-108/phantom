"""Phantom Host Program Execution.

Executes host Python programs in isolated subprocesses with timeout
and resource management.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

# How long to wait for the pipes to close after the process tree was killed.
_DRAIN_SECONDS = 5.0

# Default per-stream capture cap: a chatty host must not exhaust memory by
# filling stdout/stderr without limit. Beyond the cap, bytes are drained
# and discarded so the host is not blocked on a full pipe, the returned
# text is truncated, and HostResult.truncated is set.
DEFAULT_MAX_OUTPUT_BYTES = 16 * 1024 * 1024


@dataclass
class HostResult:
    """Result of executing a host program."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    exception: str | None = None
    truncated: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class _CappedReader(threading.Thread):
    """Drain one pipe, keeping at most ``cap`` bytes."""

    def __init__(self, stream, cap: int) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._cap = cap
        self.data = bytearray()
        self.truncated = False

    def run(self) -> None:
        try:
            while True:
                chunk = self._stream.read(8192)
                if not chunk:
                    break
                if len(self.data) < self._cap:
                    keep = self._cap - len(self.data)
                    self.data.extend(chunk[:keep])
                    if len(chunk) > keep:
                        self.truncated = True
                else:
                    self.truncated = True
                # Continue reading (and discarding) past the cap so a
                # chatty host is not blocked on a full pipe.
        except (OSError, ValueError):
            pass
        finally:
            with contextlib.suppress(OSError, ValueError):
                self._stream.close()


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
    max_output_bytes: int | None = None,
) -> HostResult:
    """Execute a Python program in a subprocess.

    Uses sys.executable to run the same Python.
    Captures stdout, stderr, exit code.
    Applies timeout; on expiry the host *and every process it started* are killed,
    so a child that keeps the output pipes open cannot stretch the timeout.
    Never modifies the host file.
    Each of stdout and stderr is captured up to ``max_output_bytes``
    (default 16 MiB); beyond that the stream is drained and discarded,
    the returned text is truncated, and the result is marked truncated.
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
        cap = DEFAULT_MAX_OUTPUT_BYTES if max_output_bytes is None else max_output_bytes
        if cap < 0:
            raise ValueError("max_output_bytes must not be negative")
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=merged_env,
            **group,
        )
        if sys.platform == "win32":
            job = _WindowsJob(proc.pid)
        readers = [
            _CappedReader(proc.stdout, cap),
            _CappedReader(proc.stderr, cap),
        ]
        for reader in readers:
            reader.start()

        def _feed_stdin() -> None:
            try:
                assert proc.stdin is not None
                proc.stdin.write(stdin_text.encode("utf-8"))
                proc.stdin.close()
            except (BrokenPipeError, OSError, ValueError):
                pass

        stdin_thread = None
        if stdin_text is not None:
            stdin_thread = threading.Thread(target=_feed_stdin, daemon=True)
            stdin_thread.start()
        timed_out = False
        try:
            remaining = timeout - (time.perf_counter() - start_time)
            proc.wait(timeout=max(remaining, 0))
        except subprocess.TimeoutExpired:
            timed_out = True
        if not timed_out:
            # The process exited, but a descendant may still hold the
            # pipes open; do not wait past the deadline for it.
            remaining = timeout - (time.perf_counter() - start_time)
            for reader in readers:
                reader.join(timeout=max(remaining, 0))
            if any(reader.is_alive() for reader in readers):
                timed_out = True
        if timed_out:
            _kill_tree(proc, job)
            for reader in readers:
                reader.join(timeout=_DRAIN_SECONDS)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            timeout_msg = f"\n[HostExecution] Process timed out after {timeout} seconds."
            stdout = _as_text(bytes(readers[0].data))
            stderr = _as_text(bytes(readers[1].data)) + timeout_msg
            return HostResult(
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                exception=f"TimeoutExpired: Process timed out after {timeout} seconds",
                truncated=readers[0].truncated or readers[1].truncated,
                stdout_truncated=readers[0].truncated,
                stderr_truncated=readers[1].truncated,
            )
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return HostResult(
            exit_code=proc.returncode,
            stdout=_as_text(bytes(readers[0].data)),
            stderr=_as_text(bytes(readers[1].data)),
            duration_ms=duration_ms,
            truncated=readers[0].truncated or readers[1].truncated,
            stdout_truncated=readers[0].truncated,
            stderr_truncated=readers[1].truncated,
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
