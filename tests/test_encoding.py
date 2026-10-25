"""Tests for the encoding subsystem."""

from __future__ import annotations

import ast

import pytest

from phantom.encoding import (
    CommentDecoder,
    HybridCodec,
    UnicodeDecoder,
    UnicodeEncoder,
    WhitespaceDecoder,
    WhitespaceEncoder,
    decode_source,
    encode_instruction,
)
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    SourceLocation,
)
from phantom.parser import parse

TEXT = 'phantom:0.1.0 diagnostic.note("héllo ✓")'


def _note(msg="héllo ✓"):
    return PhantomInstruction(
        InstructionType.DIAGNOSTIC_NOTE,
        (Argument(ArgumentType.STRING, msg),),
        SourceLocation("t", 1),
    )


def test_comment_roundtrip():
    line = encode_instruction(_note(), EncodingMode.COMMENT)
    assert line == "#: " + TEXT
    assert CommentDecoder.decode(line) == TEXT


def test_comment_decoder_rejects_non_instruction():
    with pytest.raises(ValueError):
        CommentDecoder.decode("# just a comment")


@pytest.mark.parametrize("mode", [EncodingMode.COMMENT, EncodingMode.WHITESPACE, EncodingMode.UNICODE])
@pytest.mark.parametrize("message", ["a\nb", "a\rb", "a\tb", "a\r\nb\tc", r'literal \n \r \t and "quotes"', 'héllo\n"\\\t\r✓'])
def test_string_escapes_roundtrip_through_parser(mode, message):
    encoded = encode_instruction(_note(message), mode)
    ast.parse(encoded)
    decoded = decode_source(encoded, mode)
    assert len(decoded) == 1
    assert "\n" not in decoded[0] and "\r" not in decoded[0] and "\t" not in decoded[0]
    program = parse(encoded)
    assert not program.errors
    assert len(program.instructions) == 1
    assert program.instructions[0].get_string_arg(0) == message


def test_whitespace_roundtrip_is_utf8_exact():
    lines = WhitespaceEncoder.encode(TEXT)
    assert len(lines) == len(TEXT.encode("utf-8"))
    assert all(len(line) == 8 and set(line) <= {" ", "\t"} for line in lines)
    assert WhitespaceDecoder.decode(lines) == TEXT


@pytest.mark.parametrize(
    "lines",
    [[], [" " * 7], [" " * 9], ["x" * 8], ["\t" * 8, " " * 7]],
)
def test_whitespace_decoder_rejects_malformed(lines):
    with pytest.raises(ValueError):
        WhitespaceDecoder.decode(lines)


def test_whitespace_block_roundtrip():
    block = WhitespaceEncoder.encode_block(TEXT)
    assert WhitespaceDecoder.decode_block(block) == TEXT


def test_unicode_roundtrip_and_alphabet():
    encoded = UnicodeEncoder.encode(TEXT)
    assert len(encoded) == 4 * len(TEXT.encode("utf-8"))
    assert set(encoded) <= set("​‌‍﻿")
    assert UnicodeDecoder.decode(encoded, strict=True) == TEXT


def test_unicode_strict_rejects_foreign_invisible():
    with pytest.raises(ValueError):
        UnicodeDecoder.decode(UnicodeEncoder.encode(TEXT) + "⁠", strict=True)


def test_unicode_block_is_valid_python_comment():
    import ast

    block = UnicodeEncoder.encode_block(TEXT)
    ast.parse(block)
    assert UnicodeDecoder.decode_block(block, strict=True) == TEXT


def test_whitespace_block_survives_python_parse():
    import ast

    ast.parse("def f():\n    return 1\n" + WhitespaceEncoder.encode_block(TEXT) + "\n")


def test_decode_source_by_mode():
    ws = encode_instruction(_note("a"), EncodingMode.WHITESPACE)
    zw = encode_instruction(_note("b"), EncodingMode.UNICODE)
    cm = encode_instruction(_note("c"), EncodingMode.COMMENT)
    src = "\n".join([cm, ws, zw]) + "\n"
    assert decode_source(src, EncodingMode.COMMENT) == ['phantom:0.1.0 diagnostic.note("c")']
    assert decode_source(src, EncodingMode.WHITESPACE) == ['phantom:0.1.0 diagnostic.note("a")']
    assert decode_source(src, EncodingMode.UNICODE) == ['phantom:0.1.0 diagnostic.note("b")']
    assert len(decode_source(src)) == 3


def test_hybrid_precedence_dedupes_with_comment_first():
    same = _note("same")
    src = HybridCodec.encode_instructions(
        [same, same, same],
        mode_map={0: EncodingMode.WHITESPACE, 1: EncodingMode.COMMENT, 2: EncodingMode.UNICODE},
    )
    decoded = HybridCodec.decode_instructions(src)
    assert decoded == ['phantom:0.1.0 diagnostic.note("same")']

def test_hybrid_precedence_dedupes_with_comment_second():
    same = _note("same")
    src = HybridCodec.encode_instructions(
        [same, same],
        mode_map={0: EncodingMode.HYBRID},
    )
    decoded = HybridCodec.decode_instructions(src)
    assert decoded == ['phantom:0.1.0 diagnostic.note("same")']

def test_trailing_whitespace_on_source_does_not_create_instructions():
    assert decode_source("x = 1   \n\t\n   \n") == []
