"""Tests for the Phantom validator."""

from __future__ import annotations

from pathlib import Path

from phantom.ir import (
    Argument,
    ArgumentType,
    InstructionType,
    PhantomInstruction,
    Severity,
    SourceLocation,
)
from phantom.parser import parse, parse_file
from phantom.validator import validate

FIXTURES = Path(__file__).parent / "fixtures"


def _inst(itype: InstructionType, *args: object) -> PhantomInstruction:
    built = tuple(
        Argument(ArgumentType.INTEGER if isinstance(a, int) else ArgumentType.STRING, a)
        for a in args
    )
    return PhantomInstruction(itype, built, SourceLocation("t.py", 1))


def _errors(findings):
    return [f for f in findings if f.severity == Severity.ERROR]


class TestValidator:
    def test_valid_program(self):
        prog = parse(
            '#: phantom:0.1.0 event.declare("e")\n'
            '#: phantom:0.1.0 event.on("e", "pkg.mod.handler")\n'
            '#: phantom:0.1.0 counter.create("c", 2)\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
        )
        assert validate(prog) == []

    def test_fixture_invalid(self):
        prog = parse_file(str(FIXTURES / "invalid_instructions.py"))
        assert prog.has_errors or _errors(validate(prog))

    def test_undeclared_event_and_builtin_event(self):
        bad = parse('#: phantom:0.1.0 event.on("nope", "a.b")\n')
        assert any("undeclared" in e.message for e in validate(bad))
        ok = parse('#: phantom:0.1.0 event.on("phantom.shutdown", "a.b")\n')
        assert validate(ok) == []

    def test_handler_must_be_dotted(self):
        prog = parse(
            '#: phantom:0.1.0 event.declare("e")\n#: phantom:0.1.0 event.on("e", "handler")\n'
        )
        assert any("dotted" in e.message for e in validate(prog))

    def test_type_mismatch(self):
        prog = parse('#: phantom:0.1.0 counter.create("c", "ten")\n')
        assert any("must be integer" in e.message for e in validate(prog))

    def test_argument_count(self):
        prog = parse('#: phantom:0.1.0 meta.author("a", "b")\n')
        assert any("argument" in e.message for e in _errors(validate(prog)))

    def test_counter_rules(self):
        prog = parse(
            '#: phantom:0.1.0 counter.create("c", 0)\n#: phantom:0.1.0 counter.increment("ghost")\n'
        )
        messages = [e.message for e in validate(prog)]
        assert any("> 0" in m for m in messages)
        assert any("before it is created" in m for m in messages)

    def test_counter_invalid_limit_does_not_cascade_before_create_error(self):
        prog = parse(
            '#: phantom:0.1.0 counter.create("c", 0)\n'
            '#: phantom:0.1.0 counter.decrement("c")\n'
            '#: phantom:0.1.0 counter.reset("c")\n'
        )
        messages = [e.message for e in validate(prog)]
        assert messages == ["Counter limit must be > 0, got 0"]

        # Counter is registered, so increment warns about exceeding 0 limit rather than 'before create'
        prog_inc = parse(
            '#: phantom:0.1.0 counter.create("c", 0)\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
        )
        errors = [e.message for e in validate(prog_inc) if e.severity == Severity.ERROR]
        assert errors == ["Counter limit must be > 0, got 0"]

    def test_counter_overflow_is_warning(self):
        prog = parse(
            '#: phantom:0.1.0 counter.create("c", 1)\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
        )
        (finding,) = validate(prog)
        assert finding.severity == Severity.WARNING

    def test_counter_reset_valid(self):
        prog = parse(
            '#: phantom:0.1.0 counter.create("c", 2)\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
            '#: phantom:0.1.0 counter.reset("c")\n'
        )
        # The reset must parse as an instruction, not be dropped as unknown.
        assert not prog.has_errors
        assert len(prog.instructions) == 3
        assert validate(prog) == []

    def test_counter_reset_before_create_is_error(self):
        prog = parse('#: phantom:0.1.0 counter.reset("ghost")\n')
        assert any("reset before it is created" in e.message for e in validate(prog))

    def test_counter_decrement_valid(self):
        prog = parse(
            '#: phantom:0.1.0 counter.create("c", 2)\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
            '#: phantom:0.1.0 counter.decrement("c")\n'
        )
        assert not prog.has_errors
        assert len(prog.instructions) == 3
        assert validate(prog) == []

    def test_counter_decrement_before_create_is_error(self):
        prog = parse('#: phantom:0.1.0 counter.decrement("ghost")\n')
        assert any("decremented before it is created" in e.message for e in validate(prog))

    def test_counter_reset_restarts_limit_count(self):
        # After a reset the counter is back at 0, so one more increment
        # against a limit of 1 must not warn as an overflow.
        prog = parse(
            '#: phantom:0.1.0 counter.create("c", 1)\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
            '#: phantom:0.1.0 counter.reset("c")\n'
            '#: phantom:0.1.0 counter.increment("c")\n'
        )
        assert validate(prog) == []

    def test_unsupported_version(self):
        prog = parse('#: phantom:9.9.9 meta.author("a")\n')
        assert any("Unsupported spec version" in e.message for e in validate(prog))

    def test_duplicate_meta_is_warning(self):
        prog = parse('#: phantom:0.1.0 meta.author("a")\n#: phantom:0.1.0 meta.author("b")\n')
        (finding,) = validate(prog)
        assert finding.severity == Severity.WARNING

    def test_duplicate_meta_license_is_warning(self):
        prog = parse('#: phantom:0.1.0 meta.license("MIT")\n#: phantom:0.1.0 meta.license("Apache-2.0")\n')
        (finding,) = validate(prog)
        assert finding.severity == Severity.WARNING

    def test_single_meta_tags_is_clean(self):
        prog = parse('#: phantom:0.1.0 meta.tags("telemetry,audit,compliance")\n')
        assert prog.errors == []
        assert validate(prog) == []

    def test_duplicate_meta_tags_is_warning(self):
        prog = parse('#: phantom:0.1.0 meta.tags("telemetry")\n#: phantom:0.1.0 meta.tags("audit")\n')
        (finding,) = validate(prog)
        assert finding.severity == Severity.WARNING
        assert "meta.tags" in finding.message
