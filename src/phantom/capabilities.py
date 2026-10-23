"""Phantom Capability Model.

Defines fine-grained capabilities required for runtime operations,
such as stdio, event dispatch, diagnostics, counters, and metadata.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from phantom.ir import InstructionType


class Capability(Enum):
    """Runtime capabilities required by instructions and runtime operations."""

    STDIO = "cap.stdio"  # Read/write to stdout/stderr
    EVENTS = "cap.events"  # Event declaration and dispatch
    DIAGNOSTICS = "cap.diagnostics"  # Diagnostic collection
    COUNTERS = "cap.counters"  # Counter operations
    METADATA = "cap.metadata"  # Metadata declarations


DEFAULT_CAPABILITIES = frozenset(
    {
        Capability.STDIO,
        Capability.EVENTS,
        Capability.DIAGNOSTICS,
        Capability.COUNTERS,
        Capability.METADATA,
    }
)


# Map instruction types to required capabilities
INSTRUCTION_CAPABILITIES: dict[InstructionType, frozenset[Capability]] = {
    InstructionType.EVENT_DECLARE: frozenset({Capability.EVENTS}),
    InstructionType.EVENT_ON: frozenset({Capability.EVENTS}),
    InstructionType.DIAGNOSTIC_NOTE: frozenset({Capability.DIAGNOSTICS}),
    InstructionType.COUNTER_CREATE: frozenset({Capability.COUNTERS}),
    InstructionType.COUNTER_INCREMENT: frozenset({Capability.COUNTERS}),
    InstructionType.META_AUTHOR: frozenset({Capability.METADATA}),
    InstructionType.META_VERSION: frozenset({Capability.METADATA}),
    InstructionType.META_LICENSE: frozenset({Capability.METADATA}),
}


def get_required_capabilities(instruction_type: InstructionType) -> frozenset[Capability]:
    """Return the set of capabilities required for an instruction type."""
    return INSTRUCTION_CAPABILITIES.get(instruction_type, frozenset())


class PhantomError(Exception):
    """Base exception for all Phantom language runtime and capability errors."""


class CapabilityError(PhantomError):
    """Raised when an operation is attempted without the required capability."""

    def __init__(
        self,
        capability: Capability | None,
        message: str | None = None,
    ) -> None:
        self.capability = capability
        if message is None:
            if capability is None:
                message = "A required capability is missing."
            else:
                message = f"Capability '{capability.value}' is required but not granted."
        super().__init__(message)


class CapabilityGrant:
    """Represents a set of capabilities granted to a Phantom runtime execution context."""

    def __init__(self, granted: Iterable[Capability] | None = None) -> None:
        if granted is None:
            self.granted: frozenset[Capability] = DEFAULT_CAPABILITIES
        else:
            self.granted = frozenset(granted)

    def check(self, capability: Capability) -> bool:
        """Check whether a specific capability is granted."""
        return capability in self.granted

    def require(self, capability: Capability) -> None:
        """Assert that a capability is granted, raising CapabilityError if not."""
        if not self.check(capability):
            raise CapabilityError(
                capability=capability,
                message=f"Missing required capability: {capability.value}",
            )

    def check_instruction(self, instruction_type: InstructionType) -> bool:
        """Check whether all capabilities required for an instruction type are granted."""
        required = get_required_capabilities(instruction_type)
        return required.issubset(self.granted)

    def require_instruction(self, instruction_type: InstructionType) -> None:
        """Assert that all capabilities for an instruction type are granted."""
        required = get_required_capabilities(instruction_type)
        missing = required - self.granted
        if missing:
            missing_str = ", ".join(sorted(c.value for c in missing))
            capability = next(iter(missing)) if len(missing) == 1 else None
            raise CapabilityError(
                capability=capability,
                message=f"Instruction '{instruction_type.value}' requires capabilities [{missing_str}], which are not granted.",
            )

    def __contains__(self, item: Capability) -> bool:
        return item in self.granted

    def __repr__(self) -> str:
        caps = ", ".join(sorted(c.name for c in self.granted))
        return f"CapabilityGrant({caps})"
