"""Tests for the Phantom parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from phantom.encoding import encode_instruction
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    Severity,
    SourceLocation,
)
from phantom.parser import parse, parse_arguments, parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def _inst(itype: InstructionType, *args: object) -> PhantomInstruction:
    built = tuple(
        Argument(ArgumentType.INTEGER if isinstance(a, int) else ArgumentType.STRING, a)
        for a in args
    )
    return PhantomInstruction(itype, built, SourceLocation("t.py", 1))


def _errors(findings):
    return [f for f in findings if f.severity == Severity.ERROR]


class TestArguments:
    def test_mixed(self):
        args = parse_arguments('"a", 5')
        assert [(a.type, a.value) for a in args] == [
            (ArgumentType.STRING, "a"),
            (ArgumentType.INTEGER, 5),
        ]

    def test_escapes_and_commas_in_strings(self):
        (arg,) = parse_arguments(r'"say \"hi\", ok\n"')
        assert arg.value == 'say "hi", ok\n'

    def test_hex_escapes_decode_control_characters(self):
        (arg,) = parse_arguments(r'"a\x00b\x1bc"')
        assert arg.value == "a\x00b\x1bc"

    def test_hex_escape_without_two_hex_digits_raises_value_error(self):
        with pytest.raises(ValueError, match=r"Invalid \\x"):
            parse_arguments(r'"a\xzzb"')

    def test_unrecognized_escape_character_raises_value_error(self):
        with pytest.raises(ValueError, match=r"Invalid escape sequence '\\z'"):
            parse_arguments(r'"a\zb"')

    @pytest.mark.parametrize("bad", ['"a" "b"', '"a",', "foo", '"unterminated'])
    def test_malformed(self, bad):
        with pytest.raises(ValueError):
            parse_arguments(bad)


class TestParser:
    def test_comment_instructions(self):
        prog = parse('x = 1\n#: phantom:0.1.0 counter.create("n", 3)\n')
        assert not prog.errors
        (inst,) = prog.instructions
        assert inst.type == InstructionType.COUNTER_CREATE
        assert inst.get_int_arg(1) == 3
        assert inst.source.line == 2

    def test_diagnostic_warn_instruction(self):
        prog = parse('#: phantom:0.1.0 diagnostic.warn("deprecated API")\n')
        assert not prog.errors
        (inst,) = prog.instructions
        assert inst.type == InstructionType.DIAGNOSTIC_WARN
        assert inst.get_string_arg(0) == "deprecated API"

    def test_unknown_instruction_is_parse_error(self):
        prog = parse('#: phantom:0.1.0 foo.bar("x")\n')
        assert prog.has_errors and not prog.instructions

    def test_plain_python_has_no_instructions(self):
        prog = parse_file(str(FIXTURES / "valid_plain.py"))
        assert prog.instruction_count == 0 and not prog.errors

    def test_fixture_file(self):
        prog = parse_file(str(FIXTURES / "hello_phantom.py"))
        assert [i.identifier for i in prog.instructions] == ["event.declare", "diagnostic.note"]

    @pytest.mark.parametrize("mode", [EncodingMode.WHITESPACE, EncodingMode.UNICODE])
    def test_steganographic_roundtrip(self, mode):
        original = _inst(InstructionType.META_AUTHOR, "Alice")
        source = "print('hi')\n" + encode_instruction(original, mode) + "\n"
        prog = parse(source)
        assert not prog.errors, prog.errors
        (inst,) = prog.instructions
        assert inst.type == original.type
        assert inst.get_string_arg(0) == "Alice"
        assert inst.source.encoding == mode

    def test_source_order_across_encodings(self):
        ws = encode_instruction(_inst(InstructionType.META_AUTHOR, "Bob"), EncodingMode.WHITESPACE)
        source = (
            '#: phantom:0.1.0 meta.version("1")\n' + ws + '\n#: phantom:0.1.0 event.declare("e")\n'
        )
        prog = parse(source)
        assert [i.identifier for i in prog.instructions] == [
            "meta.version",
            "meta.author",
            "event.declare",
        ]

    def test_hybrid_dedupes_repeated_instruction(self):
        line = '#: phantom:0.1.0 meta.author("Bob")\n'
        assert parse(line * 2).instruction_count == 2
        assert parse("#:phantom:hybrid\n" + line * 2).instruction_count == 1

    @pytest.mark.parametrize("marker", ["ws", "zw"])
    def test_empty_block_is_error(self, marker):
        prog = parse(f"#:{marker}:begin\n#:{marker}:end\n")
        assert prog.has_errors and "Empty" in prog.errors[0].message

    def test_unterminated_block(self):
        prog = parse("#:ws:begin\n \t \t \t \t\n")
        assert prog.has_errors

    def test_invalid_string_escape_reports_parse_error(self):
        prog = parse('#: phantom:0.1.0 diagnostic.note("test\\zval")\n')
        assert prog.has_errors
        assert any("Invalid escape sequence" in e.message for e in prog.errors)

    def test_invalid_hex_escape_reports_parse_error(self):
        prog = parse('#: phantom:0.1.0 diagnostic.note("test\\xzzval")\n')
        assert prog.has_errors
        assert any("Invalid \\x" in e.message for e in prog.errors)
