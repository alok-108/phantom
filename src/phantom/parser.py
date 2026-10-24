"""Phantom Parser.

Turns a Python source file into a PhantomProgram by running the lexer and
decoding every instruction found in comment, whitespace, and zero-width
Unicode encodings. Instructions are returned in source order.
"""

from __future__ import annotations

import re

from phantom.encoding import UnicodeDecoder, WhitespaceDecoder
from phantom.grammar import (
    COMMENT_LINE_PATTERN,
    COMMENT_TRAILING_PATTERN,
    INSTRUCTION_ID_PATTERN,
    SPEC_VERSION,
    ZW_PERMITTED_CODEPOINTS,
    ZW_REJECTED_CODEPOINTS,
)
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    ParseError,
    PhantomInstruction,
    PhantomProgram,
    Severity,
    SourceLocation,
)
from phantom.lexer import Token, TokenType, tokenize
from phantom.lines import split_physical_lines

_INSTRUCTION_TEXT_PATTERN = re.compile(
    r"^phantom:([0-9]+\.[0-9]+\.[0-9]+)\s+([a-z][a-z0-9]*\.[a-z][a-z0-9_]*)\(\s*(.*?)\s*\)$"
)
_INVISIBLE = ZW_PERMITTED_CODEPOINTS | ZW_REJECTED_CODEPOINTS
_STRING_TOKEN =re.compile(r'"((?:[^"\\]|\\.)*)"')
_INTEGER_TOKEN = re.compile(r"-?[0-9]+")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}


def _unescape(raw: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            out.append(_ESCAPES.get(raw[i + 1], raw[i + 1]))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_arguments(raw_args: str) -> list[Argument]:
    """Tokenize a comma-separated argument list.

    Raises:
        ValueError: On an unterminated string, a stray token, or a missing comma.
    """
    args: list[Argument] = []
    pos = 0
    text = raw_args.strip()
    while pos < len(text):
        m = _STRING_TOKEN.match(text, pos)
        if m:
            args.append(Argument(ArgumentType.STRING, _unescape(m.group(1))))
        else:
            m = _INTEGER_TOKEN.match(text, pos)
            if not m:
                raise ValueError(f"Cannot parse argument near {text[pos:pos + 20]!r}")
            args.append(Argument(ArgumentType.INTEGER, int(m.group(0))))
        pos = m.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos < len(text):
            if text[pos] != ",":
                raise ValueError(f"Expected ',' between arguments near {text[pos:pos + 20]!r}")
            pos += 1
            while pos < len(text) and text[pos].isspace():
                pos += 1
            if pos >= len(text):
                raise ValueError("Trailing comma in argument list")
    return args


def _build_instruction(
    version: str,
    ident: str,
    raw_args: str,
    loc: SourceLocation,
) -> PhantomInstruction:
    """Build one instruction; raises ValueError with a user-facing message."""
    if not INSTRUCTION_ID_PATTERN.match(ident):
        raise ValueError(f"Malformed instruction identifier: '{ident}'")
    try:
        itype = InstructionType(ident)
    except ValueError:
        raise ValueError(f"Unknown instruction identifier: '{ident}'") from None
    args = parse_arguments(raw_args)
    return PhantomInstruction(itype, tuple(args), loc, version)


def _parse_text(
    text: str, loc: SourceLocation, errors: list[ParseError]
) -> PhantomInstruction | None:
    m = _INSTRUCTION_TEXT_PATTERN.match(text.strip())
    if not m:
        errors.append(ParseError(f"Malformed decoded instruction: {text.strip()!r}", loc))
        return None
    try:
        return _build_instruction(m.group(1), m.group(2), m.group(3), loc)
    except ValueError as exc:
        errors.append(ParseError(str(exc), loc))
        return None


def parse(content: str, filepath: str = "<string>") -> PhantomProgram:
    """Parse source text into a PhantomProgram."""
    instructions: list[PhantomInstruction] = []
    errors: list[ParseError] = []
    hybrid = False
    seen_hybrid: set[str] = set()

    tokens = tokenize(content, filepath)
    block_mode: EncodingMode | None = None
    block_start: Token | None = None
    block_data: list[str] = []

    def emit(text: str, loc: SourceLocation) -> None:
        if hybrid:
            key = text.strip()
            if key in seen_hybrid:
                return
            seen_hybrid.add(key)
        inst = _parse_text(text, loc, errors)
        if inst is not None:
            instructions.append(inst)

    def flush_block() -> None:
        assert block_start is not None and block_mode is not None
        loc = SourceLocation(filepath, block_start.line, block_start.column, block_mode)
        if not block_data:
            errors.append(ParseError(f"Empty {block_mode.value} block (no payload)", loc))
            return
        try:
            if block_mode == EncodingMode.WHITESPACE:
                decoded = WhitespaceDecoder.decode(block_data)
            else:
                decoded = UnicodeDecoder.decode("".join(block_data), strict=True)
        except ValueError as exc:
            errors.append(ParseError(f"Cannot decode {block_mode.value} block: {exc}", loc))
            return
        for line in split_physical_lines(decoded):
            if line.strip():
                emit(line, loc)

    for tok in tokens:
        if tok.type == TokenType.HYBRID_HEADER:
            hybrid = True
        elif tok.type == TokenType.COMMENT_INSTRUCTION:
            m = COMMENT_LINE_PATTERN.match(tok.value)
            loc = SourceLocation(filepath, tok.line, tok.column, EncodingMode.COMMENT)
            if m is None:
                errors.append(ParseError(
                    "Malformed instruction version: expected ASCII digits in major.minor.patch",
                    loc,
                ))
                continue
            if hybrid:
                key = f"phantom:{m.group(2)} {m.group(3)}({m.group(4)})"
                if key in seen_hybrid:
                    continue
                seen_hybrid.add(key)
            try:
                instructions.append(_build_instruction(m.group(2), m.group(3), m.group(4), loc))
            except ValueError as exc:
                errors.append(ParseError(str(exc), loc))
        elif tok.type == TokenType.MALFORMED_INSTRUCTION:
            loc = SourceLocation(filepath, tok.line, tok.column, EncodingMode.COMMENT)
            if COMMENT_TRAILING_PATTERN.match(tok.value):
                errors.append(
                    ParseError(
                        "Instruction followed by a trailing comment is ordinary source and is "
                        "ignored; put the instruction on a line of its own",
                        loc,
                        Severity.WARNING,
                    )
                )
            else:
                errors.append(
                    ParseError(
                        "Malformed instruction: expected "
                        "'#: phantom:<major.minor.patch> <id>(<arguments>)' on a line of its own",
                        loc,
                    )
                )
        elif tok.type in (TokenType.WS_BEGIN, TokenType.ZW_BEGIN):
            block_mode = (
                EncodingMode.WHITESPACE if tok.type == TokenType.WS_BEGIN else EncodingMode.UNICODE
            )
            block_start = tok
            block_data = []
        elif tok.type == TokenType.WS_DATA_LINE:
            block_data.append(tok.value)
        elif tok.type == TokenType.ZW_DATA_LINE:
            # Only zero-width (or rejected invisible) code points are payload;
            # the visible '# ' prefix that keeps the line valid Python is not.
            block_data.extend(c for c in tok.value if c in _INVISIBLE)
        elif tok.type in (TokenType.WS_END, TokenType.ZW_END):
            flush_block()
            block_mode = block_start = None
            block_data = []
        elif tok.type == TokenType.EOF and block_mode is not None:
            assert block_start is not None
            errors.append(
                ParseError(
                    f"Unterminated {block_mode.value} block",
                    SourceLocation(filepath, block_start.line, block_start.column, block_mode),
                )
            )

    instructions.sort(key=lambda i: (i.source.line, i.source.column))
    return PhantomProgram(
        instructions=instructions,
        source_file=filepath,
        spec_version=SPEC_VERSION,
        errors=errors,
    )


def parse_file(filepath: str) -> PhantomProgram:
    """Parse a file from disk.

    A leading UTF-8 BOM is dropped (``utf-8-sig``), as Python itself does, so it
    cannot hide an instruction on the first line.
    """
    with open(filepath, encoding="utf-8-sig", errors="replace") as f:
        return parse(f.read(), filepath)
