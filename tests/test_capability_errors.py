"""Regression tests for capability denial messages."""

from __future__ import annotations

import pytest

from phantom.capabilities import (
    INSTRUCTION_CAPABILITIES,
    Capability,
    CapabilityError,
    CapabilityGrant,
)
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    PhantomProgram,
    SourceLocation,
)
from phantom.runtime import PhantomRuntime


def test_require_preserves_capability_and_custom_message():
    with pytest.raises(CapabilityError) as exc_info:
        CapabilityGrant([]).require(Capability.COUNTERS)

    assert exc_info.value.capability is Capability.COUNTERS
    assert str(exc_info.value) == "Missing required capability: cap.counters"


def test_require_instruction_preserves_specific_message():
    with pytest.raises(CapabilityError) as exc_info:
        CapabilityGrant([]).require_instruction(InstructionType.COUNTER_CREATE)

    assert exc_info.value.capability is Capability.COUNTERS
    assert str(exc_info.value) == (
        "Instruction 'counter.create' requires capabilities [cap.counters], "
        "which are not granted."
    )


def test_require_instruction_lists_all_missing_capabilities(monkeypatch):
    monkeypatch.setitem(
        INSTRUCTION_CAPABILITIES,
        InstructionType.EVENT_DECLARE,
        frozenset({Capability.EVENTS, Capability.COUNTERS}),
    )

    with pytest.raises(CapabilityError) as exc_info:
        CapabilityGrant([]).require_instruction(InstructionType.EVENT_DECLARE)

    assert exc_info.value.capability is None
    assert str(exc_info.value) == (
        "Instruction 'event.declare' requires capabilities "
        "[cap.counters, cap.events], which are not granted."
    )


def test_initialize_returns_instruction_specific_capability_error():
    instruction = PhantomInstruction(
        type=InstructionType.COUNTER_CREATE,
        arguments=(
            Argument(type=ArgumentType.STRING, value="requests"),
            Argument(type=ArgumentType.INTEGER, value=3),
        ),
        source=SourceLocation(
            file="test.py",
            line=1,
            column=0,
            encoding=EncodingMode.COMMENT,
        ),
    )
    program = PhantomProgram(instructions=[instruction], source_file="test.py")
    runtime = PhantomRuntime(CapabilityGrant([Capability.STDIO]))

    errors = runtime.initialize(program)

    assert len(errors) == 1
    assert str(errors[0]) == (
        "Instruction 'counter.create' requires capabilities [cap.counters], "
        "which are not granted."
    )
