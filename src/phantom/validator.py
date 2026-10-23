"""Phantom Validator.

Static checks on a parsed PhantomProgram: spec version, argument count and
types, and cross-instruction invariants (events, counters, metadata).
"""

from __future__ import annotations

import re

from phantom.grammar import INSTRUCTION_REGISTRY, SUPPORTED_VERSIONS
from phantom.ir import (
    InstructionType,
    PhantomInstruction,
    PhantomProgram,
    Severity,
    ValidationError,
)
from phantom.lines import split_physical_lines

BUILTIN_EVENTS = frozenset({"phantom.pre_execute", "phantom.post_execute", "phantom.shutdown"})
_HANDLER_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$")


def validate(program: PhantomProgram) -> list[ValidationError]:
    """Validate a program and return all findings (errors and warnings)."""
    findings: list[ValidationError] = []

    def add(
        message: str,
        inst: PhantomInstruction,
        severity: Severity = Severity.ERROR,
    ) -> None:
        findings.append(ValidationError(message, inst, inst.source, severity))

    events: set[str] = set(BUILTIN_EVENTS)
    counters: dict[str, int] = {}
    increments: dict[str, int] = {}
    metas: dict[InstructionType, PhantomInstruction] = {}

    for inst in program.instructions:
        if inst.spec_version not in SUPPORTED_VERSIONS:
            add(f"Unsupported spec version '{inst.spec_version}'", inst)

        spec = INSTRUCTION_REGISTRY.get(inst.identifier)
        if spec is None:
            add(f"Instruction '{inst.identifier}' is not in specification", inst)
            continue

        if len(inst.arguments) < spec.required_count or len(inst.arguments) > spec.total_count:
            add(
                f"Instruction '{inst.identifier}' takes {spec.total_count} argument(s), "
                f"got {len(inst.arguments)}",
                inst,
            )
            continue

        type_ok = True
        for idx, (arg, arg_spec) in enumerate(zip(inst.arguments, spec.arguments, strict=True)):
            if arg.type != arg_spec.type:
                add(
                    f"Argument {idx + 1} ('{arg_spec.name}') of '{inst.identifier}' must be "
                    f"{arg_spec.type.value}, got {arg.type.value}",
                    inst,
                )
                type_ok = False
        if not type_ok:
            continue

        if inst.type == InstructionType.EVENT_DECLARE:
            name = inst.get_string_arg(0) or ""
            if not name.strip():
                add("Event name must not be empty", inst)
            elif name in events:
                add(f"Event '{name}' is already declared", inst, Severity.WARNING)
            events.add(name)

        elif inst.type == InstructionType.EVENT_ON:
            name = inst.get_string_arg(0) or ""
            handler = inst.get_string_arg(1) or ""
            if name not in events:
                add(f"Handler registered for undeclared event '{name}'", inst)
            if not _HANDLER_PATH.match(handler):
                add(f"Handler '{handler}' is not a dotted module path", inst)

        elif inst.type == InstructionType.COUNTER_CREATE:
            name = inst.get_string_arg(0) or ""
            limit = inst.get_int_arg(1)
            if not name.strip():
                add("Counter name must not be empty", inst)
            elif name in counters:
                add(f"Counter '{name}' is already created", inst)
            if limit is not None and limit <= 0:
                add(f"Counter limit must be > 0, got {limit}", inst)
            elif name not in counters:
                counters[name] = limit if limit is not None else 0

        elif inst.type == InstructionType.COUNTER_INCREMENT:
            name = inst.get_string_arg(0) or ""
            if name not in counters:
                add(f"Counter '{name}' incremented before it is created", inst)
            else:
                increments[name] = increments.get(name, 0) + 1
                if increments[name] > counters[name]:
                    add(
                        f"Counter '{name}' exceeds its limit of {counters[name]}",
                        inst,
                        Severity.WARNING,
                    )

        elif inst.type in (InstructionType.META_AUTHOR, InstructionType.META_VERSION, InstructionType.META_LICENSE):
            prior: PhantomInstruction | None = metas.get(inst.type)
            if prior is not None:
                add(
                    f"Duplicate '{inst.identifier}' (first at line {prior.source.line})",
                    inst,
                    Severity.WARNING,
                )
            else:
                metas[inst.type] = inst

    return findings


# Bidirectional controls enable "Trojan Source" style display tricks.
_BIDI_CONTROLS = frozenset(
    "‪‫‬‭‮⁦⁧⁨⁩‎‏"
)


def audit_source(source: str, filename: str = "<string>") -> list[ValidationError]:
    """Strict-mode scan for invisible characters that are not legitimate payload.

    Reports (as errors): bidirectional controls and rejected invisible code
    points anywhere, and zero-width payload characters outside a `#:zw:` block.
    Reads text only; never executes or rewrites it.
    """
    from phantom.grammar import (
        ZW_BEGIN_MARKER,
        ZW_END_MARKER,
        ZW_PERMITTED_CODEPOINTS,
        ZW_REJECTED_CODEPOINTS,
    )
    from phantom.ir import EncodingMode, SourceLocation

    findings: list[ValidationError] = []
    in_zw = False
    audited_separators = "\x85\u2028\u2029"
    for lineno, line in enumerate(split_physical_lines(source), start=1):
        stripped = line.strip()
        if stripped == ZW_BEGIN_MARKER:
            in_zw = True
            continue
        if stripped == ZW_END_MARKER:
            in_zw = False
            continue
        for col, ch in enumerate(line):
            if ch in audited_separators:
                findings.append(
                    ValidationError(
                        f"Unexpected Unicode line separator U+{ord(ch):04X}",
                        source=SourceLocation(filename, lineno, col, EncodingMode.UNICODE),
                    )
                )
                continue
            if ch in ZW_PERMITTED_CODEPOINTS and in_zw:
                continue
            if ch in ZW_PERMITTED_CODEPOINTS or ch in ZW_REJECTED_CODEPOINTS or ch in _BIDI_CONTROLS:
                where = "inside a zero-width block" if in_zw else "outside a zero-width block"
                findings.append(
                    ValidationError(
                        f"Unexpected invisible code point U+{ord(ch):04X} {where}",
                        source=SourceLocation(filename, lineno, col, EncodingMode.UNICODE),
                    )
                )
    return findings
