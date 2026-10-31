"""Phantom Code Generator Data Models.

Typed data structures representing requests, plans, results,
and comparison verdicts for the Phantom LLM code generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from phantom.ir import EncodingMode


@dataclass
class GenerationConstraints:
    """Constraints applied to candidate code generation."""

    preserve_output: bool = True
    minimal_changes: bool = True
    complete_file: bool = True  # vs fragment
    dry_run: bool = False


@dataclass
class GenerationRequest:
    """A request to generate or insert Phantom instructions into source code."""

    source_code: str
    source_file: str | None = None
    intent: str = ""  # What the user wants Phantom to do
    placement: str = "beginning"  # Where to add instructions ("beginning", "end", "near:function_name", etc.)
    encoding: EncodingMode = EncodingMode.COMMENT  # Preferred encoding
    constraints: GenerationConstraints = field(default_factory=GenerationConstraints)


@dataclass
class PlannedInstruction:
    """A single instruction planned for insertion by the LLM."""

    instruction_type: str  # e.g. "event.declare"
    arguments: list[dict[str, Any]] = field(default_factory=list)  # [{"type": "string", "value": "on_start"}]
    placement_line: int = 1  # Target line number
    encoding: str = "comment"  # "comment", "whitespace", "unicode"
    rationale: str = ""  # Why this instruction
    anchor: str | None = None  # Expected text of the line the instruction is inserted before

    def to_dict(self) -> dict[str, Any]:
        """Convert planned instruction to a dictionary."""
        return {
            "instruction_type": self.instruction_type,
            "arguments": self.arguments,
            "placement_line": self.placement_line,
            "encoding": self.encoding,
            "rationale": self.rationale,
            "anchor": self.anchor,
        }


@dataclass
class TransformationPlan:
    """A structured plan proposed by the LLM for transforming source code."""

    request_summary: str = ""
    instructions: list[PlannedInstruction] = field(default_factory=list)
    encoding: str = "comment"
    expected_behavior: str = ""
    limitations: list[str] = field(default_factory=list)
    valid: bool = False
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert transformation plan to a dictionary."""
        return {
            "request_summary": self.request_summary,
            "instructions": [inst.to_dict() for inst in self.instructions],
            "encoding": self.encoding,
            "expected_behavior": self.expected_behavior,
            "limitations": self.limitations,
            "valid": self.valid,
            "validation_errors": self.validation_errors,
        }


@dataclass
class GenerationResult:
    """Result of running the Phantom code generation workflow."""

    success: bool
    candidate_source: str | None = None
    diff: str | None = None
    plan: TransformationPlan | None = None
    validation_passed: bool = False
    phantom_valid: bool = False
    host_syntax_valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_sha256: str | None = None  # digest of the input the candidate was built from


class ComparisonVerdict(Enum):
    """Verdict of behavior comparison between original and candidate source."""

    EQUIVALENT = "equivalent"
    DIFFERENT = "different"
    INCONCLUSIVE = "inconclusive"
    NOT_TESTED = "not_tested"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class VerificationCase:
    """One run to compare: arguments plus optional stdin text.

    A stdin_text of None means the case gets an empty stdin (immediate EOF);
    it never inherits the caller's stdin, which only one of the two programs
    could read (#82).
    """

    args: list[str] = field(default_factory=list)
    stdin_text: str | None = None
    stdin_label: str | None = None


@dataclass
class CaseComparison:
    """The comparison outcome for one verification case."""

    case: VerificationCase
    verdict: ComparisonVerdict
    original_stdout: str = ""
    candidate_stdout: str = ""
    original_stderr: str = ""
    candidate_stderr: str = ""
    original_exit_code: int = 0
    candidate_exit_code: int = 0
    differences: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Detailed result of behavior comparison."""

    verdict: ComparisonVerdict
    original_stdout: str = ""
    candidate_stdout: str = ""
    original_stderr: str = ""
    candidate_stderr: str = ""
    original_exit_code: int = 0
    candidate_exit_code: int = 0
    differences: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    case_results: list[CaseComparison] = field(default_factory=list)
