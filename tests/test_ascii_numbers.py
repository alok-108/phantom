"""ASCII numeric syntax must be consistent across instruction encodings."""

from __future__ import annotations

import pytest

from phantom.cli import main
from phantom.encoding import UnicodeEncoder, WhitespaceEncoder
from phantom.grammar import COMMENT_LINE_PATTERN, INTEGER_ARG_PATTERN
from phantom.ir import ArgumentType, EncodingMode
from phantom.parser import parse, parse_arguments


@pytest.fixture(params=[EncodingMode.COMMENT, EncodingMode.WHITESPACE, EncodingMode.UNICODE])
def encode_text(request):
    mode = request.param
    if mode == EncodingMode.COMMENT:
        return lambda text: f"#: {text}\n"
    if mode == EncodingMode.WHITESPACE:
        return WhitespaceEncoder.encode_block
    return UnicodeEncoder.encode_block


@pytest.mark.parametrize("literal", ["٣", "１０", "-٣", "-１０", "1٣", "１0"])
def test_non_ascii_integer_arguments_are_rejected(literal):
    with pytest.raises(ValueError, match="Cannot parse argument|Expected ','"):
        parse_arguments(literal)
    assert INTEGER_ARG_PATTERN.fullmatch(literal) is None


@pytest.mark.parametrize("literal", ["٣", "１０", "-٣", "-１０"])
def test_non_ascii_integers_are_errors_in_every_encoding(encode_text, literal):
    program = parse(encode_text(f'phantom:0.1.0 counter.create("n", {literal})'))
    assert program.instructions == []
    assert len(program.errors) == 1
    assert "Cannot parse argument" in program.errors[0].message
    assert literal in program.errors[0].message


@pytest.mark.parametrize("literal, expected", [("0", 0), ("10", 10), ("-10", -10)])
def test_ascii_integers_still_parse_in_every_encoding(encode_text, literal, expected):
    (argument,) = parse_arguments(literal)
    assert argument.type == ArgumentType.INTEGER
    assert argument.value == expected
    assert INTEGER_ARG_PATTERN.fullmatch(literal) is not None
    program = parse(encode_text(f'phantom:0.1.0 counter.create("n", {literal})'))
    assert program.errors == []
    (instruction,) = program.instructions
    assert instruction.get_int_arg(1) == expected


@pytest.mark.parametrize("version", ["٠.١.٠", "０.１.０", "0.١.0"])
def test_non_ascii_versions_are_errors_not_ignored(encode_text, version):
    text = f'phantom:{version} meta.author("Alice")'
    assert COMMENT_LINE_PATTERN.fullmatch(f"#: {text}") is None
    program = parse(encode_text(text))
    assert program.instructions == []
    assert len(program.errors) == 1
    assert "Malformed" in program.errors[0].message
    assert program.errors[0].source.line == 1


def test_unicode_digits_are_still_allowed_in_strings(encode_text):
    program = parse(encode_text('phantom:0.1.0 meta.author("٣１０")'))
    assert program.errors == []
    (instruction,) = program.instructions
    assert instruction.get_string_arg(0) == "٣１０"


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("literal", ["٣", "１０"])
def test_check_reports_non_ascii_integer_parse_error(tmp_path, capsys, strict, literal):
    path = tmp_path / "digits.py"
    path.write_text(f'#: phantom:0.1.0 counter.create("n", {literal})\n', encoding="utf-8")
    args = ["check", str(path)] + (["--strict"] if strict else [])
    assert main(args) == 2
    captured = capsys.readouterr()
    assert "Cannot parse argument" in captured.out + captured.err


def test_invalid_version_does_not_hide_following_valid_instruction():
    program = parse(
        '#: phantom:٠.١.٠ meta.author("bad")\n'
        '#: phantom:0.1.0 meta.author("good")\n'
    )
    assert len(program.errors) == 1
    (instruction,) = program.instructions
    assert instruction.get_string_arg(0) == "good"
    assert instruction.source.line == 2


@pytest.mark.parametrize("version", ["0.1", "latest"])
def test_other_malformed_versions_are_also_diagnosed(encode_text, version):
    program = parse(encode_text(f'phantom:{version} meta.author("Alice")'))
    assert program.instructions == []
    assert len(program.errors) == 1
    assert "Malformed" in program.errors[0].message


@pytest.mark.parametrize("source", [
    '# ordinary comment mentioning phantom:٠.١.٠ meta.author("Alice")',
    'text = '#: phantom:٠.١.٠ meta.author("Alice")'',
])
def test_incomplete_instruction_shapes_remain_ordinary_source(source):
    program = parse(source)
    assert program.instructions == []
    assert program.errors == []


def test_trailing_comment_after_instruction_is_ignored_with_a_warning():
    program = parse('#: phantom:٠.١.٠ meta.author("Alice") # trailing comment')
    assert program.instructions == []
    assert [e.severity.value for e in program.errors] == ["warning"]


def test_unterminated_instruction_is_an_error():
    program = parse('#: phantom:٠.١.٠ meta.author("Alice"')
    assert program.instructions == []
    assert [e.severity.value for e in program.errors] == ["error"]
