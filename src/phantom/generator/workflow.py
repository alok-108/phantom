"""End-to-end generation workflow: prompt -> plan -> transform -> validate."""

from __future__ import annotations

import ast
import hashlib

from phantom.generator.diff import unified_diff
from phantom.generator.models import GenerationRequest, GenerationResult
from phantom.generator.planner import parse_plan
from phantom.generator.prompts import build_prompt
from phantom.generator.provider import LLMProvider, ProviderError
from phantom.generator.transformer import TransformError, apply_plan, resolve_placement
from phantom.generator.validation import validate_candidate

MAX_SOURCE_CHARS = 100_000


def source_digest(source: str) -> str:
    """SHA-256 of the source text, used to detect a changed input (stale candidate)."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def generate(request: GenerationRequest, provider: LLMProvider) -> GenerationResult:
    """Run the full workflow. Never raises for model or plan problems.

    The candidate is returned as text; nothing is written or executed here.
    """
    result = GenerationResult(success=False, source_sha256=source_digest(request.source_code))

    if len(request.source_code) > MAX_SOURCE_CHARS:
        result.errors.append(f"Source exceeds the {MAX_SOURCE_CHARS}-character request limit")
        return result
    try:
        ast.parse(request.source_code)
    except SyntaxError as exc:
        result.errors.append(f"Input is not valid Python: {exc.msg} (line {exc.lineno})")
        return result
    try:
        target_line = resolve_placement(request.source_code, request.placement)
    except TransformError as exc:
        result.errors.append(str(exc))
        return result

    try:
        response = provider.complete(build_prompt(request, target_line))
    except ProviderError as exc:
        result.errors.append(str(exc))
        return result

    try:
        plan = parse_plan(response)
    except ValueError as exc:
        result.errors.append(f"Unusable model response: {exc}")
        return result
    # Placement is decided locally; the model's line numbers are not trusted.
    for planned in plan.instructions:
        planned.placement_line = target_line
    result.plan = plan
    if not plan.valid:
        result.errors.extend(plan.validation_errors)
        return result

    try:
        candidate = apply_plan(request.source_code, plan)
    except TransformError as exc:
        result.errors.append(str(exc))
        return result

    report = validate_candidate(
        request.source_code, candidate, expected_added=len(plan.instructions)
    )
    result.candidate_source = candidate
    result.diff = unified_diff(
        request.source_code,
        candidate,
        request.source_file or "original",
        "candidate",
    )
    result.host_syntax_valid = report.host_syntax_valid
    result.phantom_valid = report.phantom_valid
    result.validation_passed = report.passed
    result.errors.extend(report.errors)
    result.warnings.extend(report.warnings)
    result.success = report.passed
    return result
