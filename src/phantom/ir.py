"""Phantom Intermediate Representation.

Typed data structures for representing parsed Phantom instructions.
This module is the core data model used by all other Phantom components.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InstructionType(Enum):
    """Supported Phantom instruction types."""

    EVENT_DECLARE = "event.declare"
    EVENT_ON = "event.on"
    DIAGNOSTIC_NOTE = "diagnostic.note"
    COUNTER_CREATE = "counter.create"
    COUNTER_INCREMENT = "counter.increment"
    COUNTER_RESET = "counter.reset"
    META_AUTHOR = "meta.author"
    META_VERSION = "meta.version"
    META_LICENSE = "meta.license"
    META_TAGS = "meta.tags"


class ArgumentType(Enum):
    """Supported argument types for Phantom instructions."""

    STRING = "string"
    INTEGER = "integer"
    IDENTIFIER = "identifier"


class EncodingMode(Enum):
    """Supported encoding modes for Phantom instructions."""

    COMMENT = "comment"
    WHITESPACE = "whitespace"
    UNICODE = "unicode"
    HYBRID = "hybrid"


class Severity(Enum):
    """Diagnostic severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class SourceLocation:
    """Source location for a parsed element."""

    file: str
    line: int
    column: int = 0
    encoding: EncodingMode = EncodingMode.COMMENT

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column} [{self.encoding.value}]"


@dataclass(frozen=True)
class Argument:
    """A typed argument to a Phantom instruction."""

    type: ArgumentType
    value: str | int

    def __str__(self) -> str:
        if self.type == ArgumentType.STRING:
            return f'"{self.value}"'
        return str(self.value)


@dataclass(frozen=True)
class PhantomInstruction:
    """A single parsed and validated Phantom instruction.

    Frozen to ensure instructions are immutable after parsing.
    """

    type: InstructionType
    arguments: tuple[Argument, ...]
    source: SourceLocation
    spec_version: str = "0.1.0"

    @property
    def identifier(self) -> str:
        """The dotted instruction identifier, e.g. 'event.declare'."""
        return self.type.value

    def get_argument(self, index: int) -> Argument | None:
        """Get argument by index, or None if out of range."""
        if 0 <= index < len(self.arguments):
            return self.arguments[index]
        return None

    def get_string_arg(self, index: int) -> str | None:
        """Get a string argument value by index."""
        arg = self.get_argument(index)
        if arg is not None and arg.type == ArgumentType.STRING:
            return str(arg.value)
        return None

    def get_int_arg(self, index: int) -> int | None:
        """Get an integer argument value by index."""
        arg = self.get_argument(index)
        if arg is not None and arg.type == ArgumentType.INTEGER:
            return int(arg.value)
        return None

    def __str__(self) -> str:
        args = ", ".join(str(a) for a in self.arguments)
        return f"phantom:{self.spec_version} {self.identifier}({args})"


@dataclass
class ParseError:
    """An error encountered during parsing."""

    message: str
    source: SourceLocation
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.source}: {self.message}"


@dataclass
class ValidationError:
    """An error encountered during validation."""

    message: str
    instruction: PhantomInstruction | None = None
    source: SourceLocation | None = None
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        loc = self.source or (
            self.instruction.source if self.instruction else "unknown"
        )
        return f"[{self.severity.value.upper()}] {loc}: {self.message}"


@dataclass
class PhantomProgram:
    """A complete parsed Phantom program.

    Contains the list of parsed instructions and any parse errors.
    This is the primary output of the parser and input to the validator.
    """

    instructions: list[PhantomInstruction] = field(default_factory=list)
    source_file: str = ""
    spec_version: str = "0.1.0"
    errors: list[ParseError] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """True if any ERROR-severity parse errors exist."""
        return any(e.severity == Severity.ERROR for e in self.errors)

    @property
    def instruction_count(self) -> int:
        """Number of successfully parsed instructions."""
        return len(self.instructions)

    def instructions_by_type(
        self, itype: InstructionType
    ) -> list[PhantomInstruction]:
        """Filter instructions by type."""
        return [i for i in self.instructions if i.type == itype]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for inspection and diagnostics."""
        return {
            "source_file": self.source_file,
            "spec_version": self.spec_version,
            "instruction_count": self.instruction_count,
            "has_errors": self.has_errors,
            "instructions": [
                {
                    "type": inst.type.value,
                    "arguments": [
                        {"type": a.type.value, "value": a.value}
                        for a in inst.arguments
                    ],
                    "source": {
                        "file": inst.source.file,
                        "line": inst.source.line,
                        "column": inst.source.column,
                        "encoding": inst.source.encoding.value,
                    },
                    "spec_version": inst.spec_version,
                }
                for inst in self.instructions
            ],
            "errors": [
                {
                    "severity": e.severity.value,
                    "message": e.message,
                    "source": {
                        "file": e.source.file,
                        "line": e.source.line,
                        "column": e.source.column,
                        "encoding": e.source.encoding.value,
                    },
                }
                for e in self.errors
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
