"""Prompt construction for the Phantom generator."""

from __future__ import annotations

from phantom.generator.models import GenerationRequest
from phantom.grammar import INSTRUCTION_REGISTRY
from phantom.lines import split_physical_lines

SYSTEM_PROMPT = """\
You annotate Python source with Phantom instructions. You NEVER rewrite, \
reformat, or reorder the Python code. You only propose instructions to insert \
as separate lines. Respond with a single JSON object and nothing else."""

RESPONSE_SCHEMA = """\
{
  "request_summary": "<one sentence>",
  "encoding": "comment" | "whitespace" | "unicode",
  "instructions": [
    {
      "instruction_type": "<identifier from the list above>",
      "arguments": [{"type": "string" | "integer", "value": <value>}],
      "placement_line": <1-based line; the instruction is inserted before it>,
      "rationale": "<why>",
      "anchor": "<exact text of the source line the instruction is inserted before; optional>"
    }
  ],
  "expected_behavior": "<host behavior is unchanged>",
  "limitations": ["<optional notes>"]
}"""


def describe_instructions() -> str:
    lines = []
    for ident, spec in sorted(INSTRUCTION_REGISTRY.items()):
        sig = ", ".join(f"{a.name}: {a.type.value}" for a in spec.arguments)
        lines.append(f"- {ident}({sig}) - {spec.description}")
    return "\n".join(lines)


def _numbered(source: str) -> str:
    return "\n".join(f"{i:4d} | {line}" for i, line in enumerate(split_physical_lines(source), start=1))


def build_prompt(request: GenerationRequest, target_line: int = 1) -> str:
    """Build the full prompt for a generation request."""
    intent = request.intent or "Annotate the key lifecycle points of this program."
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Available instructions:\n{describe_instructions()}\n\n"
        f"Rules:\n"
        f"- Use at most 20 instructions. Declare an event before event.on, create a counter "
        f"before incrementing it.\n"
        f"- Preferred encoding: {request.encoding.value}.\n"
        f"- All instructions will be inserted before line {target_line}; use it as placement_line.\n"
        f"- Program output and behavior must remain identical.\n\n"
        f"Goal: {intent}\n\n"
        f"Response schema:\n{RESPONSE_SCHEMA}\n\n"
        f"Source file{f' ({request.source_file})' if request.source_file else ''}:\n"
        f"{_numbered(request.source_code)}\n"
    )
