"""Tests for Phantom instruction kind classification."""
from __future__ import annotations

from phantom.capabilities import INSTRUCTION_KINDS, InstructionKind
from phantom.ir import InstructionType


def test_instruction_kind_enum_values():
    assert InstructionKind.EXECUTABLE.value == "executable"
    assert InstructionKind.METADATA_ONLY.value == "metadata-only"
    assert InstructionKind.UNSUPPORTED.value == "unsupported"


def test_instruction_kinds_mapping():
    assert INSTRUCTION_KINDS[InstructionType.EVENT_DECLARE] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.EVENT_ON] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.DIAGNOSTIC_NOTE] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.DIAGNOSTIC_WARN] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.COUNTER_CREATE] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.COUNTER_INCREMENT] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.COUNTER_DECREMENT] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.COUNTER_RESET] == InstructionKind.EXECUTABLE
    assert INSTRUCTION_KINDS[InstructionType.META_AUTHOR] == InstructionKind.METADATA_ONLY
    assert INSTRUCTION_KINDS[InstructionType.META_VERSION] == InstructionKind.METADATA_ONLY
    assert INSTRUCTION_KINDS[InstructionType.META_LICENSE] == InstructionKind.METADATA_ONLY
    assert INSTRUCTION_KINDS[InstructionType.META_TAGS] == InstructionKind.METADATA_ONLY

def test_every_instruction_has_mapping():
    assert set(INSTRUCTION_KINDS) == set(InstructionType)

def test_valid_kind_mapping():
    assert all(
        kind in (InstructionKind.EXECUTABLE, InstructionKind.METADATA_ONLY)
        for kind in INSTRUCTION_KINDS.values()
    )
