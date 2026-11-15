#!/usr/bin/env python3
"""Render a map of untested code from a coverage.py JSON report.

Usage:
    pytest -q --cov=phantom --cov-report=json
    python scripts/coverage_map.py [coverage.json] [--top N]

The input is the JSON report written by ``--cov-report=json`` (default
``coverage.json`` in the current directory). Output is Markdown, lowest
coverage first, with each file's missing lines compressed to ranges.
Files at 100% are listed only in the summary count. This script adds no
threshold of its own: the existing ``fail_under`` gate in pyproject.toml
is the only gate, per issue #25.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def compress(lines: list[int]) -> str:
    """Compress sorted line numbers to ranges, e.g. [1, 2, 3, 5] -> '1-3, 5'."""
    if not lines:
        return ""
    ranges = []
    start = prev = lines[0]
    for line in lines[1:]:
        if line == prev + 1:
            prev = line
        else:
            ranges.append(f"{start}-{prev}" if start != prev else str(start))
            start = prev = line
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(ranges)


def render(data: dict, top: int) -> str:
    files = data["files"]
    rows = []
    for path, info in files.items():
        summary = info["summary"]
        rows.append(
            (
                summary["percent_covered"],
                path,
                summary["num_statements"],
                summary["missing_lines"],
                summary["excluded_lines"],
            )
        )
    rows.sort()
    total = data["totals"]
    out = [
        "# Coverage map",
        "",
        f"Total: {total['percent_covered']:.1f}% "
        f"({total['covered_lines']}/{total['num_statements']} statements). "
        f"{sum(1 for r in rows if r[0] >= 100)} of {len(rows)} files fully covered. "
        "Lowest coverage first.",
        "",
        "| File | Cover | Miss | Missing lines |",
        "| :--- | ---: | ---: | :--- |",
    ]
    for percent, path, _stmts, missing, _excluded in rows[:top]:
        out.append(
            f"| `{path}` | {percent:.1f}% | {len(missing)} | {compress(missing)} |"
        )
    if len(rows) > top:
        out.append("")
        out.append(f"({len(rows) - top} further file(s) omitted; see the full report.)")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", default="coverage.json")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)
    path = Path(args.report)
    if not path.exists():
        print(
            f"coverage_map: no report at {path}; run "
            "`pytest -q --cov=phantom --cov-report=json` first",
            file=sys.stderr,
        )
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    sys.stdout.write(render(data, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
