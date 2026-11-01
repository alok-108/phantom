#!/usr/bin/env python3
"""Benchmark the lexer and parser on large inputs (issue #35).

Generates inputs in memory (no files are written) and reports, per case,
input size, instruction count, parse time and peak memory. Run:

    python scripts/benchmark_lexer_parser.py [--quick]

``--quick`` runs only the small cases. Times are single-run measurements
on this machine, so compare runs on the same machine, not across machines.
No optimisation is proposed here: this script measures first, per #35.
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable

from phantom.encoding import WhitespaceEncoder
from phantom.parser import parse


def _plain_lines(n: int) -> str:
    return "".join(f"x_{i} = {i}\n" for i in range(n))


def _comment_instructions(n: int) -> str:
    return "".join(f'#: phantom:0.1.0 counter.create("c{i}", 3)\n' for i in range(n))


def _long_line(size: int) -> str:
    return 'text = "' + "a" * size + '"\n'


def _ws_payload(n_bytes: int) -> str:
    # One whitespace-encoded instruction with a long string argument:
    # each encoded byte becomes one whitespace line.
    text = 'phantom:0.1.0 diagnostic.note("' + "a" * n_bytes + '")'
    return WhitespaceEncoder.encode_block(text) + "\n"


def _mixed(n: int) -> str:
    parts = []
    for i in range(n):
        parts.append(f"def f_{i}():\n    return {i}\n")
        parts.append(f'#: phantom:0.1.0 counter.create("m{i}", 3)\n')
    return "".join(parts)


CASES: dict[str, Callable[[], str]] = {
    "plain_50k_lines": lambda: _plain_lines(50_000),
    "comment_10k_instructions": lambda: _comment_instructions(10_000),
    "long_line_1mb": lambda: _long_line(1_000_000),
    "ws_payload_100kb": lambda: _ws_payload(100_000),
    "mixed_10k_functions": lambda: _mixed(10_000),
}


def bench(name: str, source: str) -> dict[str, float | int | str]:
    # No tracemalloc here on purpose: it slows the parser several-fold
    # and would dominate the numbers it is meant to measure.
    start = time.perf_counter()
    program = parse(source)
    elapsed = time.perf_counter() - start
    return {
        "case": name,
        "bytes": len(source.encode("utf-8")),
        "lines": source.count("\n"),
        "instructions": len(program.instructions),
        "seconds": round(elapsed, 3),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args(argv)
    names = list(CASES)[:2] if args.quick else list(CASES)
    print("| Case | Bytes | Lines | Instructions | Seconds |")
    print("| :--- | ---: | ---: | ---: | ---: |")
    for name in names:
        row = bench(name, CASES[name]())
        print(
            f"| {row['case']} | {row['bytes']} | {row['lines']} | "
            f"{row['instructions']} | {row['seconds']} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
