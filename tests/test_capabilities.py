"""Tests for Phantom capability system."""

from __future__ import annotations

import pytest

from phantom.capabilities import (
    DEFAULT_CAPABILITIES,
    INSTRUCTION_CAPABILITIES,
    Capability,
    CapabilityError,
    CapabilityGrant,
    PhantomError,
)
from phantom.ir import InstructionType


def test_capability_enum_values():
    assert Capability.STDIO.value == "cap.stdio"
    assert Capability.EVENTS.value == "cap.events"
    assert Capability.DIAGNOSTICS.value == "cap.diagnostics"
    assert Capability.COUNTERS.value == "cap.counters"
    assert Capability.METADATA.value == "cap.metadata"


def test_default_capabilities():
    assert Capability.STDIO in DEFAULT_CAPABILITIES
    assert Capability.EVENTS in DEFAULT_CAPABILITIES
    assert Capability.DIAGNOSTICS in DEFAULT_CAPABILITIES
    assert Capability.COUNTERS in DEFAULT_CAPABILITIES
    assert Capability.METADATA in DEFAULT_CAPABILITIES
    assert len(DEFAULT_CAPABILITIES) == 5


def test_instruction_capabilities_mapping():
    assert INSTRUCTION_CAPABILITIES[InstructionType.EVENT_DECLARE] == frozenset({Capability.EVENTS})
    assert INSTRUCTION_CAPABILITIES[InstructionType.EVENT_ON] == frozenset({Capability.EVENTS})
    assert INSTRUCTION_CAPABILITIES[InstructionType.DIAGNOSTIC_NOTE] == frozenset({Capability.DIAGNOSTICS})
    assert INSTRUCTION_CAPABILITIES[InstructionType.DIAGNOSTIC_WARN] == frozenset({Capability.DIAGNOSTICS})
    assert INSTRUCTION_CAPABILITIES[InstructionType.COUNTER_CREATE] == frozenset({Capability.COUNTERS})
    assert INSTRUCTION_CAPABILITIES[InstructionType.COUNTER_INCREMENT] == frozenset({Capability.COUNTERS})
    assert INSTRUCTION_CAPABILITIES[InstructionType.META_AUTHOR] == frozenset({Capability.METADATA})
    assert INSTRUCTION_CAPABILITIES[InstructionType.META_VERSION] == frozenset({Capability.METADATA})


def test_capability_grant_default():
    grant = CapabilityGrant()
    for cap in Capability:
        assert grant.check(cap)
        grant.require(cap)  # Should not raise


def test_capability_grant_restricted():
    grant = CapabilityGrant([Capability.STDIO, Capability.DIAGNOSTICS])
    assert grant.check(Capability.STDIO)
    assert grant.check(Capability.DIAGNOSTICS)
    assert not grant.check(Capability.EVENTS)
    assert not grant.check(Capability.COUNTERS)

    with pytest.raises(CapabilityError) as exc_info:
        grant.require(Capability.EVENTS)
    assert "cap.events" in str(exc_info.value)
    assert issubclass(CapabilityError, PhantomError)


def test_capability_grant_instruction():
    grant = CapabilityGrant([Capability.EVENTS])
    assert grant.check_instruction(InstructionType.EVENT_DECLARE)
    assert grant.check_instruction(InstructionType.EVENT_ON)
    assert not grant.check_instruction(InstructionType.COUNTER_CREATE)

    grant.require_instruction(InstructionType.EVENT_DECLARE)
    with pytest.raises(CapabilityError):
        grant.require_instruction(InstructionType.COUNTER_CREATE)
