"""verify must not share Phantom's real stdin between the two programs (#82)."""

from __future__ import annotations

import subprocess
import sys

from phantom.generator.equivalence import compare_behavior
from phantom.generator.models import ComparisonVerdict, VerificationCase

ASK = 'print(input("name? "))\n'


def _phantom(*args: str, stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "phantom", *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_verify_identical_stdin_readers_with_piped_input_are_not_different(tmp_path):
    ask = tmp_path / "ask.py"
    ask.write_text(ASK, encoding="utf-8")
    proc = _phantom("verify", str(ask), str(ask), stdin="alice\n")
    assert "Behavior difference" not in proc.stdout
    assert proc.returncode == 3, proc.stdout + proc.stderr  # both see EOF: inconclusive


def test_verify_case_without_stdin_file_ignores_piped_input(tmp_path):
    ask = tmp_path / "ask.py"
    ask.write_text(ASK, encoding="utf-8")
    data = tmp_path / "in.txt"
    data.write_text("bob\n", encoding="utf-8")
    # Second case has no stdin file: it must get an empty stdin, not the piped "alice".
    proc = _phantom(
        "verify", str(ask), str(ask), "--stdin-file", str(data), "--args", "x", "--args", "y",
        stdin="alice\n",
    )
    assert "Behavior difference" not in proc.stdout
    assert proc.returncode == 3, proc.stdout + proc.stderr


def test_compare_behavior_default_case_gets_empty_stdin():
    res = compare_behavior(ASK, ASK)
    assert res.verdict == ComparisonVerdict.INCONCLUSIVE
    assert "EOFError" in res.original_stderr
    assert "EOFError" in res.candidate_stderr


def test_compare_behavior_stdin_text_still_fed_to_both():
    res = compare_behavior(ASK, "# c\n" + ASK, cases=[VerificationCase(stdin_text="alice\n")])
    assert res.verdict == ComparisonVerdict.EQUIVALENT
    assert "alice" in res.original_stdout and "alice" in res.candidate_stdout


def test_run_still_passes_stdin_through(tmp_path):
    ask = tmp_path / "ask.py"
    ask.write_text(ASK, encoding="utf-8")
    proc = _phantom("run", str(ask), stdin="carol\n")
    assert proc.returncode == 0, proc.stderr
    assert "carol" in proc.stdout
