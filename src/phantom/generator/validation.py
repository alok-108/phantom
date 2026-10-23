"""Validation of generated candidate source."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from phantom.generator.equivalence import host_ast_equal
from phantom.ir import Severity
from phantom.parser import parse
from phantom.validator import validate


@dataclass
class CandidateReport:
    """Outcome of validating a candidate against its original."""

    host_syntax_valid: bool = False
    phantom_valid: bool = False
    host_preserved: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.host_syntax_valid and self.phantom_valid and self.host_preserved


def validate_candidate(
    original: str, candidate: str, expected_added: int | None = None
) -> CandidateReport:
    """Check that a candidate parses, validates, and leaves host code untouched.

    When `expected_added` is given, the candidate must also contain exactly that many
    more Phantom instructions than the original (an instruction that was written but
    cannot be read back is a failure, not a success).
    """
    report = CandidateReport()

    try:
        ast.parse(candidate)
        report.host_syntax_valid = True
    except SyntaxError as exc:
        report.errors.append(f"Candidate is not valid Python: {exc.msg} (line {exc.lineno})")

    program = parse(candidate, "<candidate>")
    findings = list(program.errors) + validate(program)
    for f in findings:
        (report.errors if f.severity == Severity.ERROR else report.warnings).append(str(f))
    report.phantom_valid = not any(f.severity == Severity.ERROR for f in findings)

    if expected_added is not None:
        before = len(parse(original, "<original>").instructions)
        found = len(program.instructions)
        if found != before + expected_added:
            report.phantom_valid = False
            report.errors.append(
                f"Candidate contains {found} Phantom instruction(s) but {before + expected_added} "
                f"were expected ({before} existing + {expected_added} planned); "
                "an inserted instruction could not be read back"
            )

    if report.host_syntax_valid:
        try:
            report.host_preserved = host_ast_equal(original, candidate)
        except SyntaxError as exc:
            report.errors.append(f"Original is not valid Python: {exc.msg}")
        else:
            if not report.host_preserved:
                report.errors.append("Host code differs between original and candidate")
    return report
