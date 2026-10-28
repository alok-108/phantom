"""Phantom Command-Line Interface.

Provides check, inspect, run, generate, diff, and verify commands
for Phantom dual-layer Python programs.
"""

from __future__ import annotations

import argparse
import codecs
import difflib
import json
import math
import os
import sys
from typing import Any

from phantom import diagnostics
from phantom.capabilities import (
    INSTRUCTION_CAPABILITIES,
    Capability,
    CapabilityGrant,
    build_policy,
    parse_capability,
)
from phantom.generator import (
    ComparisonVerdict,
    GenerationRequest,
    VerificationCase,
    compare_behavior,
    generate,
)
from phantom.generator.diff import format_diff_colored, host_layer_diff
from phantom.generator.provider import (
    LLMProvider,
    ProviderError,
    RetryingProvider,
    StaticProvider,
    get_provider,
    redact,
)
from phantom.generator.workflow import source_digest
from phantom.handler_policy import HandlerPolicy
from phantom.ir import EncodingMode, PhantomProgram, Severity, ValidationError
from phantom.lines import split_physical_lines
from phantom.parser import parse_file
from phantom.runtime import PhantomRuntime
from phantom.validator import audit_source, check_policy, validate
from phantom.version import __version__


def read_source(path: str) -> str | None:
    """Read a source file as UTF-8 (a leading BOM is dropped) with universal newlines.

    On undecodable bytes, print one clear error and return ``None`` so every command
    fails the same way (exit code 1) instead of crashing or silently replacing bytes.
    """
    with open(path, "rb") as f:
        data = f.read()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        pos = exc.start + (len(codecs.BOM_UTF8) if data.startswith(codecs.BOM_UTF8) else 0)
        print(
            f"Error: '{path}' is not valid UTF-8 (byte 0x{data[pos]:02x} at position {pos})",
            file=sys.stderr,
        )
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n")


def load_and_parse(filepath: str) -> PhantomProgram:
    """Parse a file into a PhantomProgram. Never executes the file."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: '{filepath}'")
    return parse_file(filepath)


def load_and_validate(program: PhantomProgram) -> list[ValidationError]:
    """Validate a PhantomProgram."""
    return validate(program)


def _capability_arg(value: str) -> Capability:
    try:
        return parse_capability(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _add_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--deny",
        action="append",
        type=_capability_arg,
        metavar="CAP",
        help="Deny a capability (for example cap.events); repeatable. "
        "An instruction that needs it is a validation error",
    )
    parser.add_argument(
        "--allow-only",
        action="append",
        type=_capability_arg,
        metavar="CAP",
        help="Grant only these capabilities (repeatable); --deny is applied on top",
    )


def _grant_from_args(args: argparse.Namespace) -> CapabilityGrant | None:
    """The capability policy requested on the command line, or None for the default."""
    deny = getattr(args, "deny", None)
    allow_only = getattr(args, "allow_only", None)
    if not deny and not allow_only:
        return None
    return build_policy(deny or (), allow_only)


def _handler_policy_from_args(args: argparse.Namespace) -> HandlerPolicy:
    return HandlerPolicy.create(
        getattr(args, "handlers_from", None) or (),
        getattr(args, "allow_handler", None) or (),
    )


# ──────────────────────────────────────────────────────────────────────
# CLI Subcommands
# ──────────────────────────────────────────────────────────────────────


def cmd_check(args: argparse.Namespace) -> int:
    """Check and validate Phantom instructions in one or more files."""
    filepaths = args.file
    if isinstance(filepaths, str):
        filepaths = [filepaths]

    sources: dict[str, str] = {}
    all_diagnostics: list[Any] = []
    # 1 when any file could not be read or parsed, like a single-file hard failure.
    hard_failure = 0
    for filepath in filepaths:
        if not os.path.isfile(filepath):
            print(f"Error: File not found: '{filepath}'", file=sys.stderr)
            hard_failure = 1
            continue
        source_text = read_source(filepath)
        if source_text is None:
            hard_failure = 1
            continue

        try:
            program = load_and_parse(filepath)
        except Exception as exc:
            print(f"Error: Failed to parse '{filepath}': {exc}", file=sys.stderr)
            hard_failure = 1
            continue

        sources[filepath] = source_text
        if program.source_file:
            sources[program.source_file] = source_text

        val_errors = load_and_validate(program)
        grant = _grant_from_args(args)
        if grant is not None:
            val_errors += check_policy(program, grant)
        all_diagnostics += list(program.errors) + list(val_errors)
        if args.strict:
            all_diagnostics += audit_source(source_text, filepath)

    error_count = sum(
        1 for d in all_diagnostics if getattr(d, "severity", None) == Severity.ERROR
    )

    def _sort_key(diag: Any) -> tuple[str, int]:
        loc = diagnostics.finding_location(diag)
        return (loc.file, loc.line) if loc else ("", 0)

    all_diagnostics.sort(key=_sort_key)

    if args.format == "sarif":
        print(diagnostics.to_sarif_json(all_diagnostics))
        return 2 if error_count > 0 else hard_failure

    for diag in all_diagnostics:
        if (
            getattr(args, "quiet", False)
            and getattr(diag, "severity", None) != Severity.ERROR
        ):
            continue
        loc = diagnostics.finding_location(diag)
        source_text = sources.get(loc.file) if loc else None
        out = (
            sys.stderr
            if getattr(diag, "severity", None) == Severity.ERROR
            else sys.stdout
        )
        print(diagnostics.render(diag, source_text), file=out)

    if not getattr(args, "quiet", False):
        print(diagnostics.summary(all_diagnostics))

    if error_count > 0:
        return 2
    return hard_failure


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect Phantom instructions without executing the host program."""
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"Error: File not found: '{filepath}'", file=sys.stderr)
        return 1
    source_text = read_source(filepath)
    if source_text is None:
        return 1

    try:
        program = load_and_parse(filepath)
    except Exception as exc:
        print(f"Error: Failed to parse '{filepath}': {exc}", file=sys.stderr)
        return 1

    strict_findings: list[Any] = []
    if args.strict:
        strict_findings = audit_source(source_text, filepath)

    grant = _grant_from_args(args)
    # Parse errors make inspect fail like check, in both output modes.
    has_parse_errors = any(e.severity == Severity.ERROR for e in program.errors)
    exit_code = 2 if strict_findings or has_parse_errors else 0

    def blocked_by(inst: Any) -> list[str]:
        if grant is None:
            return []
        needed = INSTRUCTION_CAPABILITIES.get(inst.type, frozenset())
        return sorted(c.value for c in needed - grant.granted)

    if args.json:
        data = {
            "schema": "phantom.inspect",
            "schema_version": "1.0",
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
                    **({"blocked_by_policy": blocked_by(inst)} if grant is not None else {}),
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
        return exit_code

    # Human-readable output
    print(f"File: {program.source_file or filepath}")
    print(f"Spec Version: {program.spec_version}")
    print(f"Total Instructions: {program.instruction_count}")
    for f in strict_findings:
        print(f"  strict: {f}", file=sys.stderr)
    if program.errors:
        for err in program.errors:
            out = sys.stderr if err.severity == Severity.ERROR else sys.stdout
            print(diagnostics.render(err, source_text), file=out)
    if program.instruction_count == 0:
        print("  (no Phantom instructions found)")
        return exit_code

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
        denied = blocked_by(inst)
        if denied:
            print(f"      Policy:       BLOCKED (denied: {', '.join(denied)})")

    return exit_code


def cmd_run(args: argparse.Namespace) -> int:
    """Validate first, initialize runtime, execute host, and shutdown."""
    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"Error: File not found: '{filepath}'", file=sys.stderr)
        return 1

    timeout = getattr(args, "timeout", 30.0)
    if not math.isfinite(timeout) or timeout <= 0:
        print("Error: --timeout must be positive", file=sys.stderr)
        return 1

    if read_source(filepath) is None:
        return 1

    # Extract extra arguments for host program
    host_args = list(args.host_args or [])
    if host_args and host_args[0] == "--":
        host_args = host_args[1:]

    if not getattr(args, "quiet", False):
        print(f"=== Phantom Runtime v{__version__} ===")

    try:
        program = load_and_parse(filepath)
    except Exception as exc:
        print(f"Error: Failed to parse '{filepath}': {exc}", file=sys.stderr)
        return 1

    val_errors = load_and_validate(program)
    grant = _grant_from_args(args)
    if grant is not None:
        val_errors += check_policy(program, grant)
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

    if not getattr(args, "quiet", False):
        print(
            f"[OK] Validation passed ({program.instruction_count} instruction(s), {warning_count} warning(s))"
        )

    if grant is not None and Capability.STDIO not in grant:
        print(
            "Error: cap.stdio is denied by the capability policy, so the host program "
            "will not be started",
            file=sys.stderr,
        )
        return 2

    # Initialize runtime
    runtime = PhantomRuntime(grant, _handler_policy_from_args(args))
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
    records = runtime.get_diagnostics()
    if records and not getattr(args, "quiet", False):
        print("\n--- Phantom Diagnostics ---")
        for record in records:
            print(str(record))

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
        file_source = read_source(args.file)
        if file_source is None:
            return 1
        source = file_source
        name = args.file

    interactive = sys.stdin.isatty() and not args.stdin
    if args.placement is None:
        args.placement = "beginning"
        if interactive:
            args.placement = _ask(
                "Where should Phantom be added? [beginning|end|line:N|near:NAME|near:Class.method|main-guard] (beginning) ",
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
        current = read_source(name)
        if current is None:
            return 1
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


def _colors_enabled(args: argparse.Namespace) -> bool:
    """Whether ANSI color output is allowed for this invocation.

    Color is off when ``--no-color`` was passed or when the ``NO_COLOR``
    environment variable is present with any value, per https://no-color.org.
    """
    return not getattr(args, "no_color", False) and os.environ.get("NO_COLOR") is None


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
        orig_text = read_source(orig_path)
        cand_text = read_source(cand_path)
    except OSError as exc:
        print(f"Error reading files: {exc}", file=sys.stderr)
        return 1
    if orig_text is None or cand_text is None:
        return 1
    orig_lines = split_physical_lines(orig_text, keepends=True)
    cand_lines = split_physical_lines(cand_text, keepends=True)

    if args.host_only:
        sys.stdout.write(
            format_diff_colored(
                host_layer_diff("".join(orig_lines), "".join(cand_lines)),
                colored=_colors_enabled(args),
            )
        )
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
        sys.stdout.write(format_diff_colored("".join(diff), colored=_colors_enabled(args)))
    return 0


_VERDICT_LABELS = {
    ComparisonVerdict.EQUIVALENT: ("Tested equivalence for the single tested run", 0),
    ComparisonVerdict.DIFFERENT: ("Behavior difference detected", 1),
    ComparisonVerdict.VALIDATION_FAILED: ("Validation failed", 2),
    ComparisonVerdict.INCONCLUSIVE: ("Not verified (inconclusive)", 3),
    ComparisonVerdict.NOT_TESTED: ("Not verified", 3),
}


def _build_verify_cases(args: argparse.Namespace) -> list[VerificationCase] | None:
    """Build one case per argument group or stdin file, paired by position.

    Returns None when no case option was given, which keeps the single
    default run. A case with no partner on one side gets no arguments or
    no stdin file on that side; a case with no stdin file inherits the
    caller's stdin, as a single run always has.
    """
    arg_groups: list[list[str]] = list(getattr(args, "args", None) or [])
    stdin_files: list[str] = list(getattr(args, "stdin_file", None) or [])
    if not arg_groups and not stdin_files:
        return None
    stdin_texts: list[str | None] = []
    for path in stdin_files:
        if not os.path.isfile(path):
            print(f"Error: Stdin file not found: '{path}'", file=sys.stderr)
            return None
        text = read_source(path)
        if text is None:
            return None
        stdin_texts.append(text)
    count = max(len(arg_groups), len(stdin_files))
    cases = []
    for index in range(count):
        cases.append(
            VerificationCase(
                args=list(arg_groups[index]) if index < len(arg_groups) else [],
                stdin_text=stdin_texts[index] if index < len(stdin_texts) else None,
                stdin_label=stdin_files[index] if index < len(stdin_files) else None,
            )
        )
    return cases


def _describe_verify_case(case: VerificationCase) -> str:
    stdin = case.stdin_label if case.stdin_label is not None else "inherited"
    return f"args={case.args!r} stdin-file={stdin}"


def cmd_verify(args: argparse.Namespace) -> int:
    """Run both programs and compare stdout, stderr and exit code.

    This executes both files. Only verify programs you trust.
    """
    for label, path in (("Original", args.original), ("Candidate", args.candidate)):
        if not os.path.isfile(path):
            print(f"Error: {label} file not found: '{path}'", file=sys.stderr)
            return 1
    original = read_source(args.original)
    if original is None:
        return 1
    candidate = read_source(args.candidate)
    if candidate is None:
        return 1

    cases = _build_verify_cases(args)
    # _build_verify_cases returns None both for "no case options" and for a
    # failed stdin file read; the latter already printed an error, and the
    # two are told apart by whether any case option was given.
    if cases is None and (getattr(args, "args", None) or getattr(args, "stdin_file", None)):
        return 1

    result = compare_behavior(original, candidate, timeout=args.timeout, cases=cases)
    label, code = _VERDICT_LABELS[result.verdict]
    if len(result.case_results) > 1 and result.verdict == ComparisonVerdict.EQUIVALENT:
        label = f"Tested equivalence for {len(result.case_results)} cases"
    print(f"Result: {label}")
    if len(result.case_results) > 1:
        for index, compared in enumerate(result.case_results, start=1):
            print(f"Case {index}: {_describe_verify_case(compared.case)}")
            for d in compared.differences:
                print(f"  case {index} difference: {d}", file=sys.stderr)
        for index, compared in enumerate(result.case_results, start=1):
            if compared.differences:
                for tag, x, y in (
                    ("stdout", compared.original_stdout, compared.candidate_stdout),
                    ("stderr", compared.original_stderr, compared.candidate_stderr),
                ):
                    if x != y:
                        sys.stderr.writelines(
                            difflib.unified_diff(
                                split_physical_lines(x, keepends=True),
                                split_physical_lines(y, keepends=True),
                                f"case {index} original {tag}",
                                f"case {index} candidate {tag}",
                            )
                        )
    else:
        for d in result.differences:
            print(f"  difference: {d}", file=sys.stderr)
        if result.differences:
            for tag, x, y in (
                ("stdout", result.original_stdout, result.candidate_stdout),
                ("stderr", result.original_stderr, result.candidate_stderr),
            ):
                if x != y:
                    sys.stderr.writelines(
                        difflib.unified_diff(
                            split_physical_lines(x, keepends=True),
                            split_physical_lines(y, keepends=True),
                            f"original {tag}",
                            f"candidate {tag}",
                        )
                    )
    for n in result.notes:
        print(f"  note: {n}")
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
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Omit ANSI color escapes from output (same as setting NO_COLOR)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # check
    check_p = subparsers.add_parser(
        "check", help="Check and validate Phantom instructions in one or more files"
    )
    check_p.add_argument("file", nargs="+", help="Source file(s) to check")
    check_p.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error output")
    check_p.add_argument(
        "--strict",
        action="store_true",
        help="Also report invisible/bidirectional code points outside zero-width blocks",
    )
    check_p.add_argument(
        "--format", choices=("text", "sarif"), default="text", help="Output format"
    )
    _add_policy_args(check_p)

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
    _add_policy_args(inspect_p)

    # run
    run_p = subparsers.add_parser(
        "run", help="Validate and run host program with Phantom runtime"
    )
    run_p.add_argument("file", help="Source file to run")
    run_p.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error output")
    run_p.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Host program timeout in seconds (default: 30.0)",
    )
    _add_policy_args(run_p)
    run_p.add_argument(
        "--handlers-from",
        action="append",
        metavar="DIR",
        help="Only import event handlers whose top-level module lives inside DIR "
        "(repeatable). Without --handlers-from/--allow-handler any importable module is allowed",
    )
    run_p.add_argument(
        "--allow-handler",
        action="append",
        metavar="PATTERN",
        help="Also allow handlers whose dotted path matches PATTERN (fnmatch, e.g. 'myapp.hooks.*')",
    )
    run_p.add_argument(
        "host_args",
        nargs="*",
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
        help="beginning | end | line:N | near:NAME | near:Class.method | main-guard (asked interactively if omitted on a terminal; default: beginning)",
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
    diff_p.add_argument(
        "--no-color",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Omit ANSI color escapes from the diff (same as setting NO_COLOR)",
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
    verify_p.add_argument(
        "--args",
        action="append",
        nargs="*",
        metavar="ARG",
        default=None,
        help="Arguments for one case (repeatable; each use starts a new case)",
    )
    verify_p.add_argument(
        "--stdin-file",
        action="append",
        metavar="FILE",
        default=None,
        help="File whose contents are fed as stdin for one case "
        "(repeatable; cases are paired with argument groups by position, "
        "and a case with no stdin file inherits the caller's stdin)",
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

    if "--" in argv:
        dash_idx = argv.index("--")
        parse_argv = argv[:dash_idx]
        dash_args = argv[dash_idx + 1 :]
    else:
        parse_argv = argv
        dash_args = None

    try:
        args = parser.parse_args(parse_argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    if dash_args is not None and getattr(args, "command", None) == "run":
        args.host_args = (getattr(args, "host_args", None) or []) + dash_args

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
