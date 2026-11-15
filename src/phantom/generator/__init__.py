"""Phantom LLM-assisted generator."""

from phantom.generator.equivalence import compare_behavior, host_ast_equal
from phantom.generator.models import (
    CaseComparison,
    ComparisonResult,
    ComparisonVerdict,
    GenerationConstraints,
    GenerationRequest,
    GenerationResult,
    PlannedInstruction,
    TransformationPlan,
    VerificationCase,
)
from phantom.generator.provider import GeminiProvider, LLMProvider, ProviderError, StaticProvider
from phantom.generator.workflow import generate

__all__ = [
    "CaseComparison",
    "ComparisonResult",
    "ComparisonVerdict",
    "GeminiProvider",
    "GenerationConstraints",
    "GenerationRequest",
    "GenerationResult",
    "LLMProvider",
    "PlannedInstruction",
    "ProviderError",
    "StaticProvider",
    "TransformationPlan",
    "VerificationCase",
    "compare_behavior",
    "generate",
    "host_ast_equal",
]
