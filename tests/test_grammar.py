"""Public grammar helpers follow the canonical instruction registry contract."""

from __future__ import annotations

import pytest

from phantom.grammar import (
    INSTRUCTION_REGISTRY,
    get_instruction_spec,
    get_required_arg_count,
    get_total_arg_count,
    is_known_instruction,
    list_instruction_ids,
)


@pytest.mark.parametrize("identifier", sorted(INSTRUCTION_REGISTRY))
def test_known_instruction_helpers(identifier: str) -> None:
    spec = INSTRUCTION_REGISTRY[identifier]
    assert is_known_instruction(identifier) is True
    assert get_instruction_spec(identifier) is spec
    assert get_required_arg_count(identifier) == sum(arg.required for arg in spec.arguments)
    assert get_total_arg_count(identifier) == len(spec.arguments)


@pytest.mark.parametrize("identifier", ["", "not.an.instruction", "diagnostic.Note"])
def test_unknown_instruction_helpers(identifier: str) -> None:
    assert is_known_instruction(identifier) is False
    assert get_instruction_spec(identifier) is None
    assert get_required_arg_count(identifier) == -1
    assert get_total_arg_count(identifier) == -1


def test_list_instruction_ids_is_sorted_complete_and_detached() -> None:
    identifiers = list_instruction_ids()
    assert identifiers == sorted(INSTRUCTION_REGISTRY)
    assert len(identifiers) == len(set(identifiers))
    identifiers.clear()
    assert list_instruction_ids() == sorted(INSTRUCTION_REGISTRY)


def test_known_argument_counts() -> None:
    assert get_required_arg_count("event.declare") == 1
    assert get_total_arg_count("event.declare") == 1
    assert get_required_arg_count("counter.create") == 2
    assert get_total_arg_count("counter.create") == 2
