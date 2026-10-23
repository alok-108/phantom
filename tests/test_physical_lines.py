from __future__ import annotations

import ast
import io
import tokenize

import pytest

from phantom.generator.models import PlannedInstruction, TransformationPlan
from phantom.generator.prompts import _numbered
from phantom.generator.transformer import apply_plan, resolve_placement, unsafe_insertion_lines
from phantom.lexer import TokenType
from phantom.lexer import tokenize as phantom_tokenize
from phantom.parser import parse
from phantom.validator import audit_source

NON_PYTHON_SEPARATORS = ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]


@pytest.mark.parametrize(
    ("source", "without_endings", "with_endings"),
    [
        ("", [], []),
        ("x", ["x"], ["x"]),
        ("x\n", ["x"], ["x\n"]),
        ("\n", [""], ["\n"]),
        ("\n\n", ["", ""], ["\n", "\n"]),
        ("a\r\nb\rc\n", ["a", "b", "c"], ["a\r\n", "b\r", "c\n"]),
        ("a\rb\r\nc\n\nz", ["a", "b", "c", "", "z"], ["a\r", "b\r\n", "c\n", "\n", "z"]),
    ],
)
def test_split_physical_lines(source: str, without_endings: list[str], with_endings: list[str]) -> None:
    from phantom.lines import split_physical_lines

    assert split_physical_lines(source) == without_endings
    assert split_physical_lines(source, keepends=True) == with_endings


@pytest.mark.parametrize("separator", NON_PYTHON_SEPARATORS)
def test_non_python_separator_does_not_create_instruction_line(separator: str) -> None:
    instruction = '#: phantom:0.1.0 meta.author("later")'
    source = f"x = 1  # ordinary{separator}{instruction}\n{instruction}\nprint(x)\n"
    tokens = phantom_tokenize(source)
    real_instruction = [t for t in tokens if t.type == TokenType.COMMENT_INSTRUCTION]
    assert len(real_instruction) == 1
    assert real_instruction[0].line == 2
    assert [inst.source.line for inst in parse(source).instructions] == [2]
    python_comments = [t for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type == tokenize.COMMENT]
    assert len(python_comments) == 2
    assert ast.parse(source).body[-1].lineno == 3


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
def test_strict_audit_flags_non_python_separator_with_physical_coordinates(separator: str) -> None:
    findings = audit_source(f"x = 1{separator}y = 2\n", "physical.py")
    found = [item for item in findings if f"U+{ord(separator):04X}" in item.message]
    assert len(found) == 1
    assert (found[0].source.line, found[0].source.column) == (1, 5)


def test_mixed_physical_newlines_and_trailing_blank_line_are_counted_consistently() -> None:
    source = "x = 1\r\ny = 2\rz = 3\n\n"
    assert resolve_placement(source, "end") == 5
    assert ast.parse(source).body[-1].lineno == 3
    assert _numbered(source).splitlines() == ["   1 | x = 1", "   2 | y = 2", "   3 | z = 3", "   4 | "]


def test_numbered_generator_prompt_preserves_unicode_separator_inside_source_line() -> None:
    source = "x = 1\u2028y = 2\n"
    assert _numbered(source).startswith("   1 | x = 1\u2028y = 2")


@pytest.mark.parametrize("separator", NON_PYTHON_SEPARATORS)
def test_parse_roundtrip_unicode_separators_in_arguments_across_encodings(separator: str) -> None:
    from phantom.encoding import encode_instruction
    from phantom.ir import (
        Argument,
        ArgumentType,
        EncodingMode,
        InstructionType,
        PhantomInstruction,
        SourceLocation,
    )

    value = f"separator{separator}value"
    inst = PhantomInstruction(InstructionType.META_AUTHOR, (Argument(ArgumentType.STRING, value),), SourceLocation("t.py", 1))
    for mode in (EncodingMode.COMMENT, EncodingMode.WHITESPACE, EncodingMode.UNICODE):
        encoded = encode_instruction(inst, mode)
        parsed = parse(encoded)
        assert len(parsed.instructions) == 1
        assert parsed.instructions[0].get_string_arg(0) == value


@pytest.mark.parametrize(
    "source",
    [
        'value = """first\rsecond\rthird"""\rprint(value)\r',
        "value = (\r\n    1 +\r    2\n)\rprint(value)\n",
    ],
)
def test_transformer_rejects_insertions_inside_cr_multiline_constructs(source: str) -> None:
    before = ast.dump(ast.parse(source))
    assert 2 in unsafe_insertion_lines(source)
    plan = TransformationPlan(
        instructions=[PlannedInstruction("meta.author", [{"type": "string", "value": "A"}], placement_line=2)],
        valid=True,
    )
    with pytest.raises(ValueError, match="inside a multi-line construct"):
        apply_plan(source, plan)
    assert ast.dump(ast.parse(source)) == before


def test_transformer_preserves_unicode_separators_as_source_text() -> None:
    source = "x = 1  # retained\u2028y = 2\r\nz = 3\r"
    plan = TransformationPlan(
        instructions=[PlannedInstruction("meta.author", [{"type": "string", "value": "A"}], placement_line=2)],
        valid=True,
    )
    candidate = apply_plan(source, plan)
    assert "x = 1  # retained\u2028y = 2\r\n" in candidate
    assert candidate.endswith("z = 3\r")
