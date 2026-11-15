"""Property-based tests (hypothesis) for the parser, the encodings and the validator."""

from __future__ import annotations

import string

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from phantom.encoding import encode_instruction
from phantom.grammar import INSTRUCTION_REGISTRY
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    SourceLocation,
)
from phantom.lexer import TokenType, tokenize
from phantom.parser import parse
from phantom.validator import audit_source, validate

PROPERTY_SETTINGS = settings(
    max_examples=150,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# All Unicode scalar values, including Python line separators, must round-trip.
# The property that builds Python source excludes NUL separately (see #75).
strings = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # lone surrogates cannot be encoded as UTF-8
    ),
    max_size=40,
)
integers = st.integers(min_value=-(10**12), max_value=10**12)
modes = st.sampled_from([EncodingMode.COMMENT, EncodingMode.WHITESPACE, EncodingMode.UNICODE])
LOCATION = SourceLocation("<property>", 1, 0, EncodingMode.COMMENT)


@st.composite
def instructions(draw):
    """A syntactically valid instruction for any identifier in the registry."""
    spec = draw(st.sampled_from(sorted(INSTRUCTION_REGISTRY.values(), key=lambda s: s.identifier)))
    args = tuple(
        Argument(a.type, draw(strings if a.type is ArgumentType.STRING else integers))
        for a in spec.arguments
    )
    return PhantomInstruction(InstructionType(spec.identifier), args, LOCATION)


@PROPERTY_SETTINGS
@given(inst=instructions(), mode=modes)
def test_every_instruction_round_trips_through_every_encoding(inst, mode):
    program = parse(encode_instruction(inst, mode) + "\n", "<property>")
    assert program.errors == []
    (parsed,) = program.instructions
    assert parsed.type == inst.type
    assert [(a.type, a.value) for a in parsed.arguments] == [(a.type, a.value) for a in inst.arguments]


@PROPERTY_SETTINGS
@given(insts=st.lists(instructions(), min_size=1, max_size=5), mode=modes)
def test_instruction_order_is_preserved(insts, mode):
    source = "".join(encode_instruction(i, mode) + "\n" for i in insts)
    program = parse(source, "<property>")
    assert program.errors == []
    assert [i.type for i in program.instructions] == [i.type for i in insts]


@PROPERTY_SETTINGS
@given(inst=instructions(), mode=modes, before=st.text(string.ascii_letters + " =()\n", max_size=30))
def test_host_code_around_an_instruction_does_not_change_it(inst, mode, before):
    # Ordinary source lines before the instruction must not alter how it parses.
    safe = "".join(f"# {line}\n" for line in before.splitlines())
    program = parse(safe + encode_instruction(inst, mode) + "\n", "<property>")
    assert [i.type for i in program.instructions] == [inst.type]


@PROPERTY_SETTINGS
@given(text=st.text(max_size=300))
def test_the_parser_never_raises_on_arbitrary_text(text):
    program = parse(text, "<property>")
    assert program.instruction_count >= 0
    for finding in program.errors:
        assert finding.source.line >= 1


@PROPERTY_SETTINGS
@given(
    text=st.text(
        alphabet=st.sampled_from(
            list("#:phantom0.1 meta.author() ") + [chr(c) for c in (0x22, 0x5C, 0x0A, 0x09, 0x200B, 0x200C, 0x200D, 0xFEFF)]
        ),
        max_size=200,
    )
)
def test_the_whole_pipeline_survives_instruction_shaped_noise(text):
    program = parse(text, "<property>")
    validate(program)
    audit_source(text, "<property>")


@PROPERTY_SETTINGS
@given(text=st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=200))
def test_lexer_line_numbers_increase_and_end_with_eof(text):
    tokens = tokenize(text)
    assert tokens[-1].type == TokenType.EOF
    lines = [t.line for t in tokens]
    assert lines == sorted(lines)
    assert all(line >= 1 for line in lines)


@PROPERTY_SETTINGS
@given(inst=instructions())
def test_instructions_survive_surrounding_python_code(inst):
    """A Phantom file is still valid Python, and the instruction is found at its own line."""
    import ast

    source = "def f():\n    return 1\n\n" + encode_instruction(inst, EncodingMode.COMMENT) + "\nf()\n"
    ast.parse(source)
    program = parse(source, "<property>")
    (parsed,) = program.instructions
    assert parsed.source.line == 4


@pytest.mark.parametrize("mode", [EncodingMode.WHITESPACE, EncodingMode.UNICODE])
@PROPERTY_SETTINGS
@given(inst=instructions())
def test_invisible_encodings_keep_the_host_ast_unchanged(mode, inst):
    import ast

    host = "x = 1\nprint(x)\n"
    candidate = encode_instruction(inst, mode) + "\n" + host
    assert ast.dump(ast.parse(host)) == ast.dump(ast.parse(candidate))


@pytest.mark.parametrize("codepoint", [0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85, 0x2028, 0x2029])
@pytest.mark.parametrize("mode", [EncodingMode.COMMENT, EncodingMode.WHITESPACE, EncodingMode.UNICODE])
def test_line_separators_round_trip(codepoint, mode):
    value = "before" + chr(codepoint) + "after"
    inst = PhantomInstruction(
        InstructionType.META_AUTHOR,
        (Argument(ArgumentType.STRING, value),),
        LOCATION,
    )
    program = parse(encode_instruction(inst, mode) + "\n", "<line-separator>")
    assert program.errors == []
    (parsed,) = program.instructions
    assert parsed.type == inst.type
    assert parsed.arguments[0].value == value
