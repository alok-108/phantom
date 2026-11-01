"""Phantom Lexer.

Line-oriented lexical analyzer for Phantom source files.
Tokenizes source code to detect Phantom instructions embedded in comments,
whitespace blocks, zero-width Unicode blocks, and hybrid headers.
"""

from __future__ import annotations

import io
import tokenize as _py_tokenize
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum

from phantom.grammar import (
    COMMENT_ATTEMPT_PATTERN,
    COMMENT_LINE_PATTERN,
    COMMENT_VERSION_CANDIDATE_PATTERN,
    HYBRID_HEADER,
    WS_BEGIN_MARKER,
    WS_END_MARKER,
    ZW_BEGIN_MARKER,
    ZW_END_MARKER,
    ZW_PERMITTED_CODEPOINTS,
    ZW_REJECTED_CODEPOINTS,
)
from phantom.lines import split_physical_lines


class TokenType(Enum):
    """Token types emitted by the Phantom lexer."""

    COMMENT_INSTRUCTION = "COMMENT_INSTRUCTION"
    MALFORMED_INSTRUCTION = "MALFORMED_INSTRUCTION"
    WS_BEGIN = "WS_BEGIN"
    WS_END = "WS_END"
    WS_DATA_LINE = "WS_DATA_LINE"
    ZW_BEGIN = "ZW_BEGIN"
    ZW_END = "ZW_END"
    ZW_DATA_LINE = "ZW_DATA_LINE"
    HYBRID_HEADER = "HYBRID_HEADER"
    SOURCE_LINE = "SOURCE_LINE"
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    """A lexical token representing a line or block element in a Phantom source file."""

    type: TokenType
    value: str
    line: int
    column: int = 0

    def __str__(self) -> str:
        return f"Token({self.type.name}, line={self.line}, col={self.column}, value={self.value!r})"


# Combined set of zero-width and invisible code points for line classification
_ALL_ZW_CODEPOINTS = ZW_PERMITTED_CODEPOINTS | ZW_REJECTED_CODEPOINTS


def _contains_zero_width_chars(line: str) -> bool:
    """Return True if line contains any permitted or rejected zero-width code point."""
    return any(c in _ALL_ZW_CODEPOINTS for c in line)


class LexerState(Enum):
    """Internal lexer state."""

    NORMAL = "NORMAL"
    IN_WS_BLOCK = "IN_WS_BLOCK"
    IN_ZW_BLOCK = "IN_ZW_BLOCK"


class PhantomLexer:
    """Line-oriented lexer that tokenizes Python source files for Phantom instructions."""

    def __init__(self, source: str, filename: str = "<string>") -> None:
        self.source = source
        self.filename = filename

    def tokenize(self) -> list[Token]:
        """Tokenize entire source and return list of tokens ending with EOF."""
        return list(self.iter_tokens())

    def iter_tokens(self) -> Iterator[Token]:
        """Yield tokens line by line from source, followed by EOF.

        Lines that Python's tokenizer places inside a string literal are
        ordinary source, even if they start with an instruction-looking
        marker: a docstring that merely documents the syntax must not
        become executable. If the source cannot be tokenized (for example
        a syntax error), fall back to the previous line-based behaviour
        so a broken file is still reported the same way as before.
        """
        lines = split_physical_lines(self.source)
        string_lines = _string_literal_lines(self.source)
        state = LexerState.NORMAL

        for line_idx, raw_line in enumerate(lines):
            lineno = line_idx + 1
            line = raw_line.rstrip("\r")
            stripped = line.strip()

            if string_lines is not None and lineno in string_lines:
                # Inside a string literal: never start an instruction block,
                # and never treat the line as block payload either.
                if state == LexerState.NORMAL:
                    yield Token(TokenType.SOURCE_LINE, line, lineno, 0)
                else:
                    yield Token(TokenType.SOURCE_LINE, line, lineno, 0)
                continue

            if state == LexerState.NORMAL:
                if stripped == HYBRID_HEADER:
                    col = line.find(HYBRID_HEADER)
                    yield Token(TokenType.HYBRID_HEADER, line, lineno, col)
                elif stripped == WS_BEGIN_MARKER:
                    col = line.find(WS_BEGIN_MARKER)
                    state = LexerState.IN_WS_BLOCK
                    yield Token(TokenType.WS_BEGIN, line, lineno, col)
                elif stripped == ZW_BEGIN_MARKER:
                    col = line.find(ZW_BEGIN_MARKER)
                    state = LexerState.IN_ZW_BLOCK
                    yield Token(TokenType.ZW_BEGIN, line, lineno, col)
                else:
                    match = COMMENT_LINE_PATTERN.match(line) or COMMENT_VERSION_CANDIDATE_PATTERN.match(line)
                    attempt = COMMENT_ATTEMPT_PATTERN.match(line)
                    if match:
                        leading_ws = match.group(1)
                        col = len(leading_ws)
                        yield Token(TokenType.COMMENT_INSTRUCTION, line, lineno, col)
                    elif attempt:
                        yield Token(TokenType.MALFORMED_INSTRUCTION, line, lineno, len(attempt.group(1)))
                    else:
                        yield Token(TokenType.SOURCE_LINE, line, lineno, 0)

            elif state == LexerState.IN_WS_BLOCK:
                if stripped == WS_END_MARKER:
                    col = line.find(WS_END_MARKER)
                    state = LexerState.NORMAL
                    yield Token(TokenType.WS_END, line, lineno, col)
                elif all(c in " \t" for c in line):
                    # Whitespace-only line inside ws block
                    yield Token(TokenType.WS_DATA_LINE, line, lineno, 0)
                else:
                    # Non-whitespace line inside ws block
                    yield Token(TokenType.SOURCE_LINE, line, lineno, 0)

            elif state == LexerState.IN_ZW_BLOCK:
                if stripped == ZW_END_MARKER:
                    col = line.find(ZW_END_MARKER)
                    state = LexerState.NORMAL
                    yield Token(TokenType.ZW_END, line, lineno, col)
                elif _contains_zero_width_chars(line):
                    # Line containing zero-width chars inside zw block
                    yield Token(TokenType.ZW_DATA_LINE, line, lineno, 0)
                else:
                    yield Token(TokenType.SOURCE_LINE, line, lineno, 0)

        # Emit EOF token at the end
        eof_line = len(lines) + 1
        yield Token(TokenType.EOF, "", eof_line, 0)


def _string_literal_lines(source: str) -> set[int] | None:
    """Return line numbers covered by string literals, or None on failure.

    A line that also carries a real COMMENT token is not treated as a
    string line, so ``x = "hi"  #: phantom:...`` still works: the
    instruction is in the comment after the string, not inside it.
    """
    try:
        tokens = list(
            _py_tokenize.generate_tokens(io.StringIO(source).readline)
        )
    except (_py_tokenize.TokenError, IndentationError, SyntaxError):
        return None
    comment_lines = {
        tok.start[0] for tok in tokens if tok.type == _py_tokenize.COMMENT
    }
    string_lines: set[int] = set()
    for tok in tokens:
        if tok.type == _py_tokenize.STRING:
            string_lines.update(range(tok.start[0], tok.end[0] + 1))
    return string_lines - comment_lines


def tokenize(source: str, filename: str = "<string>") -> list[Token]:
    """Convenience function to tokenize source text."""
    return PhantomLexer(source, filename).tokenize()
