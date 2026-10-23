"""Phantom LLM-assisted generator."""

from phantom.generator.equivalence import compare_behavior, host_ast_equal
from phantom.generator.models import (
    ComparisonResult,
    ComparisonVerdict,
    GenerationConstraints,
    GenerationRequest,
    GenerationResult,
    PlannedInstruction,
    TransformationPlan,
)
from phantom.generator.provider import (
    GeminiProvider,
    LLMProvider,
    OpenAICompatibleProvider,
    ProviderError,
    StaticProvider,
)
from phantom.generator.workflow import generate

__all__ = [
    "ComparisonResult",
    "ComparisonVerdict",
    "GeminiProvider",
    "GenerationConstraints",
    "GenerationRequest",
    "GenerationResult",
    "LLMProvider",
    "OpenAICompatibleProvider",
    "PlannedInstruction",
    "ProviderError",
    "StaticProvider",
    "TransformationPlan",
    "compare_behavior",
    "generate",
    "host_ast_equal",
]
