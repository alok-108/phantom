"""Phantom Grammar Definitions.

Contains the instruction registry, argument signatures, regex patterns,
and encoding-specific grammar rules for the Phantom language v0.1.0.

This module is the authoritative contract for the Phantom language.
The parser, validator, generator, and runtime all reference these definitions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from phantom.ir import ArgumentType, InstructionType

# ──────────────────────────────────────────────────────────────────────
# Specification version
# ──────────────────────────────────────────────────────────────────────

SPEC_VERSION = "0.1.0"
SUPPORTED_VERSIONS = frozenset({"0.1.0"})


# ──────────────────────────────────────────────────────────────────────
# Argument and Instruction specifications
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ArgumentSpec:
    """Specification for a single instruction argument."""

    name: str
    type: ArgumentType
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class InstructionSpec:
    """Full specification for an instruction type."""

    type: InstructionType
    arguments: tuple[ArgumentSpec, ...]
    description: str = ""
    since_version: str = "0.1.0"

    @property
    def identifier(self) -> str:
        return self.type.value

    @property
    def required_count(self) -> int:
        return sum(1 for a in self.arguments if a.required)

    @property
    def total_count(self) -> int:
        return len(self.arguments)


# ──────────────────────────────────────────────────────────────────────
# Instruction registry — the canonical set of supported instructions
# ──────────────────────────────────────────────────────────────────────

INSTRUCTION_REGISTRY: dict[str, InstructionSpec] = {
    "event.declare": InstructionSpec(
        type=InstructionType.EVENT_DECLARE,
        arguments=(
            ArgumentSpec(
                "name",
                ArgumentType.STRING,
                description="Unique event name",
            ),
        ),
        description="Declare a named event in the Phantom runtime.",
    ),
    "event.on": InstructionSpec(
        type=InstructionType.EVENT_ON,
        arguments=(
            ArgumentSpec(
                "event",
                ArgumentType.STRING,
                description="Event name to listen to",
            ),
            ArgumentSpec(
                "handler",
                ArgumentType.STRING,
                description="Dotted path to a callback function",
            ),
        ),
        description="Register a callback for a declared event.",
    ),
    "diagnostic.note": InstructionSpec(
        type=InstructionType.DIAGNOSTIC_NOTE,
        arguments=(
            ArgumentSpec(
                "message",
                ArgumentType.STRING,
                description="Diagnostic message text",
            ),
        ),
        description="Attach a structured diagnostic note at this source location.",
    ),
    "counter.create": InstructionSpec(
        type=InstructionType.COUNTER_CREATE,
        arguments=(
            ArgumentSpec(
                "name",
                ArgumentType.STRING,
                description="Counter identifier",
            ),
            ArgumentSpec(
                "limit",
                ArgumentType.INTEGER,
                description="Upper bound for the counter (must be > 0)",
            ),
        ),
        description="Create a bounded counter in the Phantom runtime.",
    ),
    "counter.increment": InstructionSpec(
        type=InstructionType.COUNTER_INCREMENT,
        arguments=(
            ArgumentSpec(
                "name",
                ArgumentType.STRING,
                description="Counter identifier to increment",
            ),
        ),
        description="Increment a bounded counter by one.",
    ),
    "meta.author": InstructionSpec(
        type=InstructionType.META_AUTHOR,
        arguments=(
            ArgumentSpec(
                "name",
                ArgumentType.STRING,
                description="Author name",
            ),
        ),
        description="Declare the author of the Phantom instructions in this file.",
    ),
    "meta.version": InstructionSpec(
        type=InstructionType.META_VERSION,
        arguments=(
            ArgumentSpec(
                "version",
                ArgumentType.STRING,
                description="Version label for the Phantom instructions",
            ),
        ),
        description="Declare the version label for the Phantom instructions in this file.",
    ),
    "meta.license": InstructionSpec(
        type=InstructionType.META_LICENSE,
        arguments=(
            ArgumentSpec(
                "spdx",
                ArgumentType.STRING,
                description="SPDX license id",
            ),
        ),
        description="Declare the license of the instruction layer.",
    ),
}


# ──────────────────────────────────────────────────────────────────────
# Comment encoding patterns
# ──────────────────────────────────────────────────────────────────────
# Full syntax:  #: phantom:0.1.0 event.declare("on_start")

COMMENT_MARKER = "#:"

class LineMatch:
    """The result of an `InstructionLinePattern`: `group(n)` like `re.Match`, with the
    last group (the raw argument text) already stripped of surrounding whitespace."""

    __slots__ = ("_match", "_args_group")

    def __init__(self, match: re.Match[str], args_group: int) -> None:
        self._match = match
        self._args_group = args_group

    def group(self, index: int = 0) -> str:
        if index == self._args_group:
            return self._match.group(index).strip()
        return self._match.group(index)


class InstructionLinePattern:
    r"""Matches ``<head>(<arguments>)`` lines in linear time.

    The earlier single regular expression ended in ``\(\s*(.*?)\s*\)\s*$``. Its three
    overlapping whitespace-capable parts backtrack cubically, so a line such as
    ``#: phantom:0.1.0 a.b(`` followed by a few thousand spaces took minutes to reject. Here
    trailing whitespace is removed first (``str.rstrip`` is linear), the arguments are
    captured greedily up to the final ``)`` and stripped afterwards; the accepted language
    is the same.
    """

    def __init__(self, head: str) -> None:
        self._regex = re.compile(head + r"\((.*)\)$")
        self._args_group = self._regex.groups

    def match(self, line: str) -> LineMatch | None:
        found = self._regex.match(line.rstrip())
        return LineMatch(found, self._args_group) if found else None

    fullmatch = match


# Matches a full Phantom comment-encoded instruction line.
# Groups: (1) leading whitespace  (2) version  (3) instruction id  (4) raw args
COMMENT_LINE_PATTERN = InstructionLinePattern(
    r'^(\s*)#:\s*phantom:([0-9]+\.[0-9]+\.[0-9]+)\s+'
    r'([a-z][a-z0-9]*\.[a-z][a-z0-9_]*)'
)

# Recognize malformed versions for diagnostics without accepting them as syntax.
# The rest of the line must still have the full instruction shape.
COMMENT_VERSION_CANDIDATE_PATTERN = InstructionLinePattern(
    r'^(\s*)#:\s*phantom:(\S+)\s+'
    r'([a-z][a-z0-9]*\.[a-z][a-z0-9_]*)'
)

# Decoded (whitespace / zero-width) instruction text: no comment marker, no indentation.
INSTRUCTION_TEXT_PATTERN = InstructionLinePattern(
    r'^phantom:([0-9]+\.[0-9]+\.[0-9]+)\s+'
    r'([a-z][a-z0-9]*\.[a-z][a-z0-9_]*)'
)

# A line that starts like an instruction but fails the full grammar is almost
# certainly a typo (missing parenthesis, no arguments list, ...). The lexer
# reports it instead of silently treating it as ordinary source.
COMMENT_ATTEMPT_PATTERN = re.compile(r'^(\s*)#:\s*phantom:')

# A complete instruction followed by a trailing comment. The specification makes
# such a line ordinary source, so it is only worth a warning, not an error.
COMMENT_TRAILING_PATTERN = re.compile(
    r'^(\s*)#:\s*phantom:\S+\s+[a-z][a-z0-9]*\.[a-z][a-z0-9_]*\(.*\)\s*#.*$'
)

# Validates an instruction identifier like "event.declare"
INSTRUCTION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*\.[a-z][a-z0-9_]*$")

# Argument tokenization patterns
STRING_ARG_PATTERN = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
INTEGER_ARG_PATTERN = re.compile(r"-?[0-9]+")
IDENTIFIER_ARG_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_.]*")


# ──────────────────────────────────────────────────────────────────────
# Whitespace encoding
# ──────────────────────────────────────────────────────────────────────
# Between #:ws:begin and #:ws:end markers, whitespace-only lines encode
# binary data.  Each line is exactly 8 characters: space=0, tab=1.
# The 8 bits form one byte.  Consecutive bytes decode as UTF-8 text
# containing standard Phantom instruction syntax.
#
# Example (spaces shown as · , tabs as →):
#   #:ws:begin
#   ·→→·····         ← byte 0x60 = '`' (hypothetical)
#   ·→→·····         ← ...
#   #:ws:end

WS_BEGIN_MARKER = "#:ws:begin"
WS_END_MARKER = "#:ws:end"
WS_BIT_SPACE = " "   # represents binary 0
WS_BIT_TAB = "\t"    # represents binary 1
WS_BITS_PER_BYTE = 8


# ──────────────────────────────────────────────────────────────────────
# Zero-width Unicode encoding
# ──────────────────────────────────────────────────────────────────────
# Between #:zw:begin and #:zw:end markers, lines contain zero-width
# characters after optional visible content.  Each zero-width char
# encodes 2 bits; 4 chars encode one byte.  Decoded bytes form UTF-8
# text containing standard Phantom instruction syntax.
#
# Code-point mapping:
#   U+200B  ZERO WIDTH SPACE           → 00
#   U+200C  ZERO WIDTH NON-JOINER      → 01
#   U+200D  ZERO WIDTH JOINER          → 10
#   U+FEFF  ZERO WIDTH NO-BREAK SPACE  → 11

ZW_BEGIN_MARKER = "#:zw:begin"
ZW_END_MARKER = "#:zw:end"

ZW_CHARS: dict[str, int] = {
    "\u200B": 0b00,  # ZERO WIDTH SPACE
    "\u200C": 0b01,  # ZERO WIDTH NON-JOINER
    "\u200D": 0b10,  # ZERO WIDTH JOINER
    "\uFEFF": 0b11,  # ZERO WIDTH NO-BREAK SPACE (BOM)
}
ZW_CHARS_REVERSE: dict[int, str] = {v: k for k, v in ZW_CHARS.items()}

ZW_BITS_PER_CHAR = 2
ZW_CHARS_PER_BYTE = 4  # 4 zero-width chars = 8 bits = 1 byte

# Regex matching one or more zero-width characters
ZW_CHAR_PATTERN = re.compile(r"[\u200B\u200C\u200D\uFEFF]+")

# Set of all permitted zero-width code points (for strict-mode checks)
ZW_PERMITTED_CODEPOINTS = frozenset(ZW_CHARS.keys())

# Additional invisible Unicode code points that are NOT permitted and
# should produce diagnostics in strict mode.
ZW_REJECTED_CODEPOINTS = frozenset(
    {
        "\u00AD",   # SOFT HYPHEN
        "\u034F",   # COMBINING GRAPHEME JOINER
        "\u061C",   # ARABIC LETTER MARK
        "\u115F",   # HANGUL CHOSEONG FILLER
        "\u1160",   # HANGUL JUNGSEONG FILLER
        "\u17B4",   # KHMER VOWEL INHERENT AQ
        "\u17B5",   # KHMER VOWEL INHERENT AA
        "\u180E",   # MONGOLIAN VOWEL SEPARATOR
        "\u2060",   # WORD JOINER
        "\u2061",   # FUNCTION APPLICATION
        "\u2062",   # INVISIBLE TIMES
        "\u2063",   # INVISIBLE SEPARATOR
        "\u2064",   # INVISIBLE PLUS
        "\u206A",   # INHIBIT SYMMETRIC SWAPPING
        "\u206B",   # ACTIVATE SYMMETRIC SWAPPING
        "\u206C",   # INHIBIT ARABIC FORM SHAPING
        "\u206D",   # ACTIVATE ARABIC FORM SHAPING
        "\u206E",   # NATIONAL DIGIT SHAPES
        "\u206F",   # NOMINAL DIGIT SHAPES
    }
)


# ──────────────────────────────────────────────────────────────────────
# Hybrid encoding
# ──────────────────────────────────────────────────────────────────────
# A file may mix comment, whitespace, and Unicode encodings.
# An optional header #:phantom:hybrid enables hybrid-mode validation.
# Precedence: comment > whitespace > Unicode (first occurrence wins
# if the same logical instruction appears in multiple encodings).

HYBRID_HEADER = "#:phantom:hybrid"


# ──────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────


def is_known_instruction(identifier: str) -> bool:
    """Return True if the identifier is in the instruction registry."""
    return identifier in INSTRUCTION_REGISTRY


def get_instruction_spec(identifier: str) -> InstructionSpec | None:
    """Return the InstructionSpec for an identifier, or None."""
    return INSTRUCTION_REGISTRY.get(identifier)


def get_required_arg_count(identifier: str) -> int:
    """Return the number of required arguments, or -1 if unknown."""
    spec = INSTRUCTION_REGISTRY.get(identifier)
    return spec.required_count if spec else -1


def get_total_arg_count(identifier: str) -> int:
    """Return the total argument count, or -1 if unknown."""
    spec = INSTRUCTION_REGISTRY.get(identifier)
    return spec.total_count if spec else -1


def list_instruction_ids() -> list[str]:
    """Return a sorted list of all known instruction identifiers."""
    return sorted(INSTRUCTION_REGISTRY.keys())
