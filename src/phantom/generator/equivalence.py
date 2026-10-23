"""Equivalence checks between an original program and a candidate.

Two levels: a static AST comparison (strong evidence the host code is
untouched) and a dynamic comparison of stdout, stderr and exit code.
"""

from __future__ import annotations

import ast
import os
import re
import tempfile

from phantom.generator.models import ComparisonResult, ComparisonVerdict
from phantom.host import execute_host_program

_SCRIPT_NAME = "program.py"


def host_ast_equal(original: str, candidate: str) -> bool:
    """True when both sources have identical ASTs (comments and blank lines ignored).

    Raises:
        SyntaxError: If either source is not valid Python.
    """
    return ast.dump(ast.parse(original)) == ast.dump(ast.parse(candidate))


def compare_behavior(
    original: str,
    candidate: str,
    timeout: float = 30.0,
) -> ComparisonResult:
    """Run both sources and compare their observable behavior."""
    try:
        host_ast_equal(original, candidate)
    except SyntaxError as exc:
        return ComparisonResult(
            ComparisonVerdict.VALIDATION_FAILED, notes=[f"Syntax error: {exc.msg}"]
        )

    with tempfile.TemporaryDirectory(prefix="phantom_verify_") as tmp:
        # Same file name in two directories: output that mentions the script's own
        # name (``__file__``, ``sys.argv[0]``, tracebacks) is identical for equal programs.
        dirs = []
        for sub, text in (("original", original), ("candidate", candidate)):
            directory = os.path.join(tmp, sub)
            os.makedirs(directory)
            with open(os.path.join(directory, _SCRIPT_NAME), "w", encoding="utf-8", newline="") as f:
                f.write(text)
            dirs.append(directory)
        orig = execute_host_program(os.path.join(dirs[0], _SCRIPT_NAME), timeout=timeout)
        cand = execute_host_program(os.path.join(dirs[1], _SCRIPT_NAME), timeout=timeout)

    result = ComparisonResult(
        verdict=ComparisonVerdict.EQUIVALENT,
        original_stdout=orig.stdout,
        candidate_stdout=cand.stdout,
        original_stderr=orig.stderr,
        candidate_stderr=cand.stderr,
        original_exit_code=orig.exit_code,
        candidate_exit_code=cand.exit_code,
    )
    if orig.exit_code != cand.exit_code:
        result.differences.append(f"exit code {orig.exit_code} != {cand.exit_code}")
    # The temporary directories differ between the two runs, so they are masked in
    # both streams before comparing.
    if _mask(orig.stdout, dirs[0]) != _mask(cand.stdout, dirs[1]):
        result.differences.append("stdout differs")
    if _mask_traceback(_mask(orig.stderr, dirs[0])) != _mask_traceback(_mask(cand.stderr, dirs[1])):
        result.differences.append("stderr differs")

    if result.differences:
        result.verdict = ComparisonVerdict.DIFFERENT
    elif orig.exception or cand.exception:
        result.verdict = ComparisonVerdict.INCONCLUSIVE
        result.notes.append("A program timed out or failed to start")
    elif orig.exit_code != 0:
        # Both programs fail in the same way. Typical cause: they depend on files or
        # modules next to the original, which are not in the temporary directory.
        result.verdict = ComparisonVerdict.INCONCLUSIVE
        result.notes.append(
            f"Both programs exited with status {orig.exit_code} and identical output, "
            "so this run does not show that they behave alike. Programs that import "
            "sibling modules or read files next to themselves cannot be verified here."
        )
    else:
        result.notes.append("Only one input (no arguments, no stdin) was exercised")
    return result


def _mask(text: str, directory: str) -> str:
    """Replace the temporary directory (in the spellings Python prints) with a placeholder."""
    spellings = {
        directory,
        directory.replace("\\", "\\\\"),  # repr() doubles backslashes
        directory.replace("\\", "/"),
    }
    for spelling in sorted(spellings, key=len, reverse=True):
        text = text.replace(spelling, "<dir>")
    return text


_CARET_LINE = re.compile(r"^\s*[\^~]+$")
_TRACEBACK_LINE = re.compile(r'(File "<dir>[^"]*", line )\d+')


def _mask_traceback(text: str) -> str:
    """Hide line numbers in tracebacks of the script itself.

    The candidate has extra lines, so the same failure is reported at a different
    line number; the failing source line and the exception message still have to match.
    """
    text = _TRACEBACK_LINE.sub(lambda m: m.group(1) + "<n>", text)
    # Before Python 3.13 a traceback echoes trailing whitespace of the failing source line;
    # whitespace is not significant to the program, so it is not a difference either.
    # Python 3.11+ underlines the failing expression (``~~~^^^``); where the underline
    # starts and ends depends on the exact source text, so it is cosmetic too.
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(line for line in lines if not _CARET_LINE.match(line))
