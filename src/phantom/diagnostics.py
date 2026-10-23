"""Phantom diagnostics rendering.

Formats parse/validation findings with source context and exports SARIF 2.1.0
for CI systems.
"""

from __future__ import annotations

import json
from typing import Any

from phantom.ir import ParseError, Severity, SourceLocation, ValidationError
from phantom.lines import split_physical_lines
from phantom.version import __version__

Finding = ParseError | ValidationError

_SARIF_LEVEL = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "note"}
_ANSI = {Severity.ERROR: "\033[31m", Severity.WARNING: "\033[33m", Severity.INFO: "\033[36m"}
_RESET = "\033[0m"


def finding_location(finding: Finding) -> SourceLocation | None:
    if isinstance(finding, ParseError):
        return finding.source
    return finding.source or (finding.instruction.source if finding.instruction else None)


def render(finding: Finding, source: str | None = None, color: bool = False) -> str:
    """Render one finding; with `source`, include the line and a caret marker."""
    loc = finding_location(finding)
    sev = finding.severity
    label = sev.value
    if color:
        label = f"{_ANSI[sev]}{label}{_RESET}"
    head = f"{label}: {finding.message}"
    if loc is None:
        return head

    out = [head, f"  --> {loc.file}:{loc.line}:{loc.column + 1}"]
    if source is not None:
        lines = split_physical_lines(source)
        if 1 <= loc.line <= len(lines):
            text = lines[loc.line - 1]
            gutter = f"{loc.line:>4} | "
            out.append(f"{gutter}{text}")
            out.append(f"{' ' * (len(gutter) - 2)}| {' ' * loc.column}^")
    return "\n".join(out)


def summary(findings: list[Finding]) -> str:
    errors = sum(1 for f in findings if f.severity == Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity == Severity.WARNING)
    return f"{errors} error(s), {warnings} warning(s)"


def to_sarif(findings: list[Finding]) -> dict[str, Any]:
    """Build a SARIF 2.1.0 log for the findings."""
    results = []
    for f in findings:
        loc = finding_location(f)
        item: dict[str, Any] = {
            "ruleId": "phantom",
            "level": _SARIF_LEVEL[f.severity],
            "message": {"text": f.message},
        }
        if loc is not None:
            item["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": loc.file.replace("\\", "/")},
                        "region": {"startLine": loc.line, "startColumn": loc.column + 1},
                    }
                }
            ]
        results.append(item)
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {"driver": {"name": "phantom", "version": __version__}},
                "results": results,
            }
        ],
    }


def to_sarif_json(findings: list[Finding], indent: int = 2) -> str:
    return json.dumps(to_sarif(findings), indent=indent)
