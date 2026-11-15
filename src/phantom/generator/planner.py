"""Parsing and validation of LLM transformation plans."""

from __future__ import annotations

import json
import re
from typing import Any

from phantom.generator.models import PlannedInstruction, TransformationPlan
from phantom.grammar import INSTRUCTION_REGISTRY

MAX_INSTRUCTIONS = 50
VALID_ENCODINGS = ("comment", "whitespace", "unicode")
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Extract a JSON value from model output, tolerating fences and prose."""
    candidates = [text.strip()]
    candidates += [m.strip() for m in _FENCE.findall(text)]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for cand in candidates:
        try:
            return json.loads(cand)
        except ValueError:
            continue
    raise ValueError("Model response does not contain valid JSON")


def parse_plan(text: str) -> TransformationPlan:
    """Parse model output into a TransformationPlan and validate it."""
    data = extract_json(text)
    if not isinstance(data, dict):
        raise ValueError("Plan must be a JSON object")

    default_enc = str(data.get("encoding", "comment"))

    raw_instructions = data.get("instructions")
    if raw_instructions is None:
        instructions_list: list[Any] = []
    elif not isinstance(raw_instructions, list):
        raise ValueError("'instructions' must be a list of instruction objects")
    else:
        instructions_list = raw_instructions

    planned: list[PlannedInstruction] = []
    for raw in instructions_list:
        if not isinstance(raw, dict):
            raise ValueError("Each instruction must be a JSON object")
        raw_args = raw.get("arguments")
        if raw_args is None:
            arguments_list: list[Any] = []
        elif not isinstance(raw_args, list):
            raise ValueError("Instruction 'arguments' must be a list")
        else:
            arguments_list = list(raw_args)

        planned.append(
            PlannedInstruction(
                instruction_type=str(raw.get("instruction_type", "")),
                arguments=arguments_list,
                placement_line=raw.get("placement_line", 1),
                encoding=str(raw.get("encoding", default_enc)),
                rationale=str(raw.get("rationale", "")),
                anchor=None if raw.get("anchor") is None else str(raw["anchor"]),
            )
        )

    raw_limitations = data.get("limitations")
    if raw_limitations is None:
        limitations_list = []
    elif not isinstance(raw_limitations, list):
        raise ValueError("'limitations' must be a list of strings")
    else:
        limitations_list = [str(x) for x in raw_limitations]

    plan = TransformationPlan(
        request_summary=str(data.get("request_summary", "")),
        instructions=planned,
        encoding=default_enc,
        expected_behavior=str(data.get("expected_behavior", "")),
        limitations=limitations_list,
    )
    validate_plan(plan)
    return plan


def validate_plan(plan: TransformationPlan) -> TransformationPlan:
    """Check a plan against the grammar; sets `valid` and `validation_errors`."""
    errors: list[str] = []
    if not plan.instructions:
        errors.append("Plan contains no instructions")
    if len(plan.instructions) > MAX_INSTRUCTIONS:
        errors.append(f"Plan has {len(plan.instructions)} instructions (max {MAX_INSTRUCTIONS})")

    for n, inst in enumerate(plan.instructions, start=1):
        tag = f"instruction {n} ({inst.instruction_type or '?'})"
        spec = INSTRUCTION_REGISTRY.get(inst.instruction_type)
        if spec is None:
            errors.append(f"{tag}: unknown instruction")
            continue
        if inst.encoding not in VALID_ENCODINGS:
            errors.append(f"{tag}: unsupported encoding '{inst.encoding}'")
        if not isinstance(inst.placement_line, int) or isinstance(inst.placement_line, bool):
            errors.append(f"{tag}: placement_line must be an integer")
        elif inst.placement_line < 1:
            errors.append(f"{tag}: placement_line must be >= 1")
        if len(inst.arguments) != spec.total_count:
            errors.append(f"{tag}: expected {spec.total_count} argument(s), got {len(inst.arguments)}")
            continue
        for idx, (arg, arg_spec) in enumerate(zip(inst.arguments, spec.arguments, strict=True), start=1):
            if not isinstance(arg, dict) or arg.get("type") != arg_spec.type.value:
                errors.append(f"{tag}: argument {idx} must be {arg_spec.type.value}")
                continue
            value = arg.get("value")
            ok = (
                isinstance(value, int) and not isinstance(value, bool)
                if arg_spec.type.value == "integer"
                else isinstance(value, str)
            )
            if not ok:
                errors.append(f"{tag}: argument {idx} has wrong value type")

    plan.validation_errors = errors
    plan.valid = not errors
    return plan
