"""Phantom Command-Line Interface.

Provides check, inspect, run, generate, diff, and verify commands
for Phantom dual-layer Python programs.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from typing import Any

from phantom import diagnostics
from phantom.capabilities import INSTRUCTION_CAPABILITIES
from phantom.generator import (
    ComparisonVerdict,
    GenerationRequest,
    compare_behavior,
    generate,
)
from phantom.generator.diff import host_layer_diff
from phantom.generator.provider import (
    LLMProvider,
    ProviderError,
    RetryingProvider,
    StaticProvider,
    get_provider,
    redact,
)
from phantom.generator.workflow import source_digest
from phantom.ir import EncodingMode, PhantomProgram, Severity, ValidationError
from phantom.parser import parse_file
from phantom.runtime import PhantomRuntime
from phantom.validator import audit_source, validate
from phantom.version import __version__


def load_and_parse(filepath: str) -> PhantomProgram:
    """Parse a file into a PhantomProgram. Never executes the file."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: '{filepath}'")
    return parse_file(filepath)


def load_and_validate(program: PhantomProgram) -> list[ValidationError]:
    """Validate a PhantomProgram."""
    return validate(program)


# ──────────────────────────────────────────────────────────────────────
# CLI Subcommands
# ──────────────────────────────────────────────────────────────────────


def cmd_check(args: argparse.Namespace) -> int:
    """Check and validate Phantom instructions in a file."""
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"Error: File not found: '{filepath}'", file=sys.stderr)
        return 1

    try:
        program = load_and_parse(filepath)
    except Exception as exc:
        print(f"Error: Failed to parse '{filepath}': {exc}", file=sys.stderr)
        return 1

    val_errors = load_and_validate(program)
    all_diagnostics: list[Any] = list(program.errors) + list(val_errors)
    if args.strict:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            all_diagnostics += audit_source(f.read(), filepath)

    error_count = sum(
        1 for d in all_diagnostics if getattr(d, "severity", None) == Severity.ERROR
    )
    all_diagnostics.sort(
        key=lambda d: (lambda loc: loc.line if loc else 0)(diagnostics.finding_location(d))
    )

    if args.format == "sarif":
        print(diagnostics.to_sarif_json(all_diagnostics))
        return 2 if error_count > 0 else 0

    with open(filepath, encoding="utf-8", errors="replace") as f:
        source_text = f.read()
    for diag in all_diagnostics:
        out = (
            sys.stderr
            if getattr(diag, "severity", None) == Severity.ERROR
            else sys.stdout
        )
        print(diagnostics.render(diag, source_text), file=out)

    print(diagnostics.summary(all_diagnostics))

    if error_count > 0:
        return 2
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect Phantom instructions without executing the host program."""
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"Error: File not found: '{filepath}'", file=sys.stderr)
        return 1

    try:
        program = load_and_parse(filepath)
    except Exception as exc:
        print(f"Error: Failed to parse '{filepath}': {exc}", file=sys.stderr)
        return 1

    strict_findings: list[Any] = []
    if args.strict:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            strict_findings = audit_source(f.read(), filepath)

    if args.json:
        data = {
            "source_file": program.source_file or filepath,
            "spec_version": program.spec_version,
            "instruction_count": program.instruction_count,
            "has_errors": program.has_errors,
            "instructions": [
                {
                    "type": inst.type.value,
                    "arguments": [
                        {"type": a.type.value, "value": a.value}
                        for a in inst.arguments
                    ],
                    "source": {
                        "file": inst.source.file,
                        "line": inst.source.line,
                        "column": inst.source.column,
                        "encoding": inst.source.encoding.value,
                    },
                    "encoding": inst.source.encoding.value,
                    "required_capabilities": sorted(
                        c.value
                        for c in INSTRUCTION_CAPABILITIES.get(
                            inst.type, frozenset()
                        )
                    ),
                }
                for inst in program.instructions
            ],
            "errors": [
                {
                    "severity": e.severity.value,
                    "message": e.message,
                    "source": str(e.source),
                }
                for e in program.errors
            ],
        }
        data["strict_findings"] = [str(f) for f in strict_findings]
        print(json.dumps(data, indent=2))
        return 2 if strict_findings else 0

    # Human-readable output
    print(f"File: {program.source_file or filepath}")
    print(f"Spec Version: {program.spec_version}")
    print(f"Total Instructions: {program.instruction_count}")
    for f in strict_findings:
        print(f"  strict: {f}", file=sys.stderr)
    if program.instruction_count == 0:
        print("  (no Phantom instructions found)")
        return 2 if strict_findings else 0

    print("\nInstructions:")
    for idx, inst in enumerate(program.instructions, start=1):
        args_str = ", ".join(f"{a.type.value}={a.value!r}" for a in inst.arguments)
        caps = sorted(
            c.value for c in INSTRUCTION_CAPABILITIES.get(inst.type, frozenset())
        )
        caps_str = ", ".join(caps) if caps else "(none)"
        print(f"  [{idx}] {inst.type.value}")
        print(f"      Arguments:    {args_str if args_str else '(none)'}")
        print(f"      Source:       {inst.source.file}:{inst.source.line}:{inst.source.column}")
        print(f"      Encoding:     {inst.source.encoding.value}")
        print(f"      Capabilities: {caps_str}")

    return 2 if strict_findings else 0


def cmd_run(args: argparse.Namespace) -> int:
    """Validate first, initialize runtime, execute host, and shutdown."""
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"Error: File not found: '{filepath}'", file=sys.stderr)
        return 1

    timeout = getattr(args, "timeout", 30.0)

    # Extract extra arguments for host program
    host_args: list[str] = []
    if args.host_args:
        raw_args = list(args.host_args)
        if "--" in raw_args:
            idx = raw_args.index("--")
            before_dash = raw_args[:idx]
            after_dash = raw_args[idx + 1:]
        else:
            before_dash = raw_args
            after_dash = []

        remaining_before: list[str] = []
        i = 0
        while i < len(before_dash):
            item = before_dash[i]
            if item == "--timeout":
                if i + 1 >= len(before_dash):
                    print("Error: --timeout requires an argument", file=sys.stderr)
                    return 1
                try:
                    timeout = float(before_dash[i + 1])
                except ValueError:
                    print(
                        f"Error: --timeout must be a valid number, got '{before_dash[i + 1]}'",
                        file=sys.stderr,
                    )
                    return 1
                i += 2
            elif item.startswith("--timeout="):
                val_str = item.split("=", 1)[1]
                try:
                    timeout = float(val_str)
                except ValueError:
                    print(
                        f"Error: --timeout must be a valid number, got '{val_str}'",
                        file=sys.stderr,
                    )
                    return 1
                i += 1
            else:
                remaining_before.append(item)
                i += 1

        if after_dash or "--" in raw_args:
            host_args = remaining_before + after_dash
        else:
            host_args = remaining_before

    if timeout <= 0:
        print("Error: --timeout must be positive", file=sys.stderr)
        return 1

    print(f"=== Phantom Runtime v{__version__} ===")

    try:
        program = load_and_parse(filepath)
    except Exception as exc:
        print(f"Error: Failed to parse '{filepath}': {exc}", file=sys.stderr)
        return 1

    val_errors = load_and_validate(program)
    all_diagnostics = list(program.errors) + list(val_errors)

    error_count = sum(
        1 for d in all_diagnostics if getattr(d, "severity", None) == Severity.ERROR
    )
    warning_count = sum(
        1 for d in all_diagnostics if getattr(d, "severity", None) == Severity.WARNING
    )

    if error_count > 0:
        for diag in all_diagnostics:
            print(str(diag), file=sys.stderr)
        print(
            f"Validation failed: {error_count} error(s), {warning_count} warning(s)",
            file=sys.stderr,
        )
        return 2

    print(
        f"[OK] Validation passed ({program.instruction_count} instruction(s), {warning_count} warning(s))"
    )

    # Initialize runtime
    runtime = PhantomRuntime()
    init_errors = runtime.initialize(program)
    if init_errors:
        for r_err in init_errors:
            print(f"[RuntimeWarning] {r_err}", file=sys.stderr)

    # Execute host program
    host_res = runtime.execute_host(filepath, args=host_args, timeout=timeout)

    # Shutdown runtime
    runtime.shutdown()

    # Host program output
    if host_res.stdout:
        sys.stdout.write(host_res.stdout)
        if not host_res.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if host_res.stderr:
        sys.stderr.write(host_res.stderr)
        if not host_res.stderr.endswith("\n"):
            sys.stderr.write("\n")

    # Diagnostics output
    diagnostics = runtime.get_diagnostics()
    if diagnostics:
        print("\n--- Phantom Diagnostics ---")
        for diag in diagnostics:
            print(str(diag))

    return host_res.exit_code


_ENCODING_ALIASES = {
    "comment": EncodingMode.COMMENT,
    "comments": EncodingMode.COMMENT,
    "whitespace": EncodingMode.WHITESPACE,
    "unicode": EncodingMode.UNICODE,
}


def _confirm_remote(provider_name: str) -> bool:
    print(
        f"The program source will be sent to the remote '{provider_name}' service, "
        "which processes whatever is submitted.",
        file=sys.stderr,
    )
    if not sys.stdin.isatty():
        return False
    return _ask("Continue? [y/N] ").lower() in ("y", "yes")


def _ask(prompt: str, default: str = "") -> str:
    """Ask a question on a terminal; fall back to `default` if input is unavailable."""
    try:
        return input(prompt).strip() or default
    except EOFError:
        return default


def cmd_generate(args: argparse.Namespace, provider: LLMProvider | None = None) -> int:
    """Propose a candidate with Phantom instructions. Never runs the candidate."""
    if args.stdin:
        source = sys.stdin.read()
        name: str | None = None
    else:
        if not args.file:
            print("Error: provide a file or --stdin", file=sys.stderr)
            return 1
        if not os.path.isfile(args.file):
            print(f"Error: File not found: '{args.file}'", file=sys.stderr)
            return 1
        with open(args.file, encoding="utf-8") as f:
            source = f.read()
        name = args.file

    interactive = sys.stdin.isatty() and not args.stdin
    if args.placement is None:
        args.placement = "beginning"
        if interactive:
            args.placement = _ask(
                "Where should Phantom be added? [beginning|end|line:N|near:NAME] (beginning) ",
                "beginning",
            )
    if args.encoding is None:
        args.encoding = "comment"
        if interactive:
            args.encoding = _ask("Encoding? [comment|whitespace|unicode] (comment) ", "comment")

    encoding = _ENCODING_ALIASES.get(args.encoding)
    if encoding is None:
        print(
            f"Error: unsupported generator encoding '{args.encoding}' "
            "(supported: comment, whitespace, unicode)",
            file=sys.stderr,
        )
        return 1
    if args.output and name and os.path.abspath(args.output) == os.path.abspath(name):
        print("Error: --output must differ from the input file", file=sys.stderr)
        return 1

    intent = args.intent
    if not intent:
        if sys.stdin.isatty() and not args.stdin:
            intent = _ask("What should Phantom do for this program? ")
        if not intent:
            print("Error: --intent is required in non-interactive mode", file=sys.stderr)
            return 1

    if provider is None and args.plan_file:
        try:
            with open(args.plan_file, encoding="utf-8") as f:
                provider = StaticProvider(f.read())
        except OSError as exc:
            print(f"Error: cannot read plan file: {exc}", file=sys.stderr)
            return 1
    if provider is None:
        if not args.allow_remote and not _confirm_remote(args.provider):
            print(
                "Error: remote generation not authorized (pass --allow-remote to consent)",
                file=sys.stderr,
            )
            return 1
        try:
            provider = RetryingProvider(get_provider(args.provider))
        except ProviderError as exc:
            print(f"Error: {redact(str(exc))}", file=sys.stderr)
            return 1

    request = GenerationRequest(
        source_code=source,
        source_file=name,
        intent=intent,
        placement=args.placement,
        encoding=encoding,
    )
    result = generate(request, provider)

    for w in result.warnings:
        print(f"warning: {redact(w)}", file=sys.stderr)
    if result.plan:
        print("Plan:")
        for pi in result.plan.instructions:
            print(f"  - {pi.instruction_type}  [{pi.encoding}]  {pi.rationale}")
        if result.plan.limitations:
            print("Limitations: " + "; ".join(result.plan.limitations))
    if not result.success:
        for e in result.errors:
            print(f"error: {redact(e)}", file=sys.stderr)
        return 2

    if name and os.path.isfile(name):
        with open(name, encoding="utf-8") as f:
            current = f.read()
        if source_digest(current) != result.source_sha256:
            print(
                f"error: {name} changed while the candidate was being generated; "
                "refusing to write a stale candidate",
                file=sys.stderr,
            )
            return 2

    print("\nDiff:")
    print(result.diff or "(no changes)")
    print("Checks: host syntax OK, Phantom instructions valid, host code unchanged (AST).")
    print("Behavior has NOT been executed; run 'phantom verify' to compare outputs.")
    if args.dry_run:
        print("Dry run: nothing written.")
    elif args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(result.candidate_source or "")
        print(f"Candidate written to {args.output} (original untouched).")
    else:
        print("No --output given: candidate not saved.")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    """Unified diff between two source files."""
    orig_path = args.original
    cand_path = args.candidate

    if not os.path.isfile(orig_path):
        print(f"Error: Original file not found: '{orig_path}'", file=sys.stderr)
        return 1
    if not os.path.isfile(cand_path):
        print(f"Error: Candidate file not found: '{cand_path}'", file=sys.stderr)
        return 1

    try:
        with open(orig_path, encoding="utf-8", errors="replace") as f:
            orig_lines = f.readlines()
        with open(cand_path, encoding="utf-8", errors="replace") as f:
            cand_lines = f.readlines()
    except Exception as exc:
        print(f"Error reading files: {exc}", file=sys.stderr)
        return 1

    if args.host_only:
        sys.stdout.write(host_layer_diff("".join(orig_lines), "".join(cand_lines)))
        return 0

    diff = list(
        difflib.unified_diff(
            orig_lines,
            cand_lines,
            fromfile=orig_path,
            tofile=cand_path,
        )
    )
    if diff:
        sys.stdout.writelines(diff)
    return 0


_VERDICT_LABELS = {
    ComparisonVerdict.EQUIVALENT: ("Tested equivalence for the single tested run", 0),
    ComparisonVerdict.DIFFERENT: ("Behavior difference detected", 1),
    ComparisonVerdict.VALIDATION_FAILED: ("Validation failed", 2),
    ComparisonVerdict.INCONCLUSIVE: ("Not verified (inconclusive)", 3),
    ComparisonVerdict.NOT_TESTED: ("Not verified", 3),
}


def cmd_verify(args: argparse.Namespace) -> int:
    """Run both programs and compare stdout, stderr and exit code.

    This executes both files. Only verify programs you trust.
    """
    for label, path in (("Original", args.original), ("Candidate", args.candidate)):
        if not os.path.isfile(path):
            print(f"Error: {label} file not found: '{path}'", file=sys.stderr)
            return 1
    with open(args.original, encoding="utf-8") as f:
        original = f.read()
    with open(args.candidate, encoding="utf-8") as f:
        candidate = f.read()

    result = compare_behavior(original, candidate, timeout=args.timeout)
    label, code = _VERDICT_LABELS[result.verdict]
    print(f"Result: {label}")
    for d in result.differences:
        print(f"  difference: {d}", file=sys.stderr)
    for n in result.notes:
        print(f"  note: {n}")
    if result.differences:
        for tag, x, y in (
            ("stdout", result.original_stdout, result.candidate_stdout),
            ("stderr", result.original_stderr, result.candidate_stderr),
        ):
            if x != y:
                sys.stderr.writelines(
                    difflib.unified_diff(
                        x.splitlines(keepends=True),
                        y.splitlines(keepends=True),
                        f"original {tag}",
                        f"candidate {tag}",
                    )
                )
    if result.verdict == ComparisonVerdict.EQUIVALENT:
        print("This is not a proof of equivalence for other inputs, state or environments.")
    return code


# ──────────────────────────────────────────────────────────────────────
# Main Parser & Entry Point
# ──────────────────────────────────────────────────────────────────────


def create_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="phantom",
        description="Phantom dual-layer programming language CLI",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"phantom {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # check
    check_p = subparsers.add_parser(
        "check", help="Check and validate Phantom instructions in a file"
    )
    check_p.add_argument("file", help="Source file to check")
    check_p.add_argument(
        "--strict",
        action="store_true",
        help="Also report invisible/bidirectional code points outside zero-width blocks",
    )
    check_p.add_argument(
        "--format", choices=("text", "sarif"), default="text", help="Output format"
    )

    # inspect
    inspect_p = subparsers.add_parser(
        "inspect", help="Inspect Phantom instructions without executing"
    )
    inspect_p.add_argument("file", help="Source file to inspect")
    inspect_p.add_argument(
        "--json", action="store_true", help="Output instructions in JSON format"
    )
    inspect_p.add_argument(
        "--strict",
        action="store_true",
        help="List suspicious invisible code points (exit 2 if any)",
    )

    # run
    run_p = subparsers.add_parser(
        "run", help="Validate and run host program with Phantom runtime"
    )
    run_p.add_argument("file", help="Source file to run")
    run_p.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Host program timeout in seconds (default: 30.0)",
    )
    run_p.add_argument(
        "host_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the host program (use '--' before args if needed)",
    )

    # generate
    gen_p = subparsers.add_parser(
        "generate", help="Generate Phantom instructions using LLM"
    )
    gen_p.add_argument("file", nargs="?", help="Source file to augment")
    gen_p.add_argument("--stdin", action="store_true", help="Read the program from stdin")
    gen_p.add_argument("--intent", help="What the Phantom layer should do")
    gen_p.add_argument(
        "--placement",
        default=None,
        help="beginning | end | line:N | near:NAME (asked interactively if omitted on a terminal; default: beginning)",
    )
    gen_p.add_argument(
        "--encoding", default=None, help="comment | whitespace | unicode (asked interactively if omitted on a terminal; default: comment)"
    )
    gen_p.add_argument("--output", "-o", help="Write the candidate here (never the input file)")
    gen_p.add_argument("--dry-run", action="store_true", help="Show the diff; write nothing")
    gen_p.add_argument("--provider", default="gemini", help="LLM provider (default: gemini)")
    gen_p.add_argument(
        "--plan-file",
        help="Use this local JSON plan instead of calling a provider (offline; nothing is sent)",
    )
    gen_p.add_argument(
        "--allow-remote",
        action="store_true",
        help="Consent to sending the source to the remote provider",
    )

    # diff
    diff_p = subparsers.add_parser(
        "diff", help="Unified diff between two source files"
    )
    diff_p.add_argument("original", help="Original file")
    diff_p.add_argument("candidate", help="Candidate file")
    diff_p.add_argument(
        "--host-only", action="store_true",
        help="Compare only the Python host layer, excluding Phantom instructions",
    )

    # verify
    verify_p = subparsers.add_parser(
        "verify", help="Compare runtime behavior of two programs"
    )
    verify_p.add_argument("original", help="Original program file")
    verify_p.add_argument("candidate", help="Candidate program file")
    verify_p.add_argument(
        "--timeout", type=float, default=30.0, help="Per-program timeout in seconds"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Phantom CLI main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = create_parser()
    if not argv:
        parser.print_help()
        return 0

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    if args.command == "check":
        return cmd_check(args)
    elif args.command == "inspect":
        return cmd_inspect(args)
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "generate":
        return cmd_generate(args)
    elif args.command == "diff":
        return cmd_diff(args)
    elif args.command == "verify":
        return cmd_verify(args)
    else:
        parser.print_help()
        return 0
