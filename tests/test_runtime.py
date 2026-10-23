"""Tests for Phantom deterministic runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from phantom.capabilities import Capability, CapabilityError, CapabilityGrant
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    PhantomProgram,
    Severity,
    SourceLocation,
)
from phantom.runtime import PhantomRuntime

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def dummy_callback(*args, **kwargs):
    return "called"


def failing_callback(*args, **kwargs):
    raise ValueError("intentional error")


def test_runtime_builtin_events():
    runtime = PhantomRuntime()
    state = runtime.get_state()
    assert "phantom.pre_execute" in state["events"]
    assert "phantom.post_execute" in state["events"]
    assert "phantom.shutdown" in state["events"]


def test_runtime_event_lifecycle():
    runtime = PhantomRuntime()
    runtime.declare_event("my_event")

    # Duplicate declare raises RuntimeError
    with pytest.raises(RuntimeError):
        runtime.declare_event("my_event")

    # Undeclared event register raises RuntimeError
    with pytest.raises(RuntimeError):
        runtime.register_handler("unknown_event", "test_runtime.dummy_callback")

    # Register handler using a registered module in sys.modules
    import sys
    dummy_mod = type(sys)("phantom_test_dummy")
    dummy_mod.dummy_callback = dummy_callback
    sys.modules["phantom_test_dummy"] = dummy_mod

    runtime.register_handler("my_event", "phantom_test_dummy.dummy_callback")
    results = runtime.fire_event("my_event")
    assert results == ["called"]


def test_runtime_event_order_and_exception_handling():
    runtime = PhantomRuntime()
    runtime.declare_event("test_chain")

    order = []

    def cb1():
        order.append(1)
        return 1

    def cb2():
        order.append(2)
        raise RuntimeError("boom")

    def cb3():
        order.append(3)
        return 3

    runtime.register_handler("test_chain", cb1)
    runtime.register_handler("test_chain", cb2)
    runtime.register_handler("test_chain", cb3)

    results = runtime.fire_event("test_chain")
    assert order == [1, 2, 3]
    assert results == [1, 3]

    # Check diagnostic recorded for cb2 exception
    diagnostics = runtime.get_diagnostics()
    assert any("boom" in d.message for d in diagnostics)


def test_runtime_unresolvable_handler():
    runtime = PhantomRuntime()
    runtime.declare_event("missing_handler_ev")
    runtime.register_handler("missing_handler_ev", "non_existent_module.no_func")

    # Should not crash runtime, logs diagnostic
    results = runtime.fire_event("missing_handler_ev")
    assert results == []
    diags = runtime.get_diagnostics()
    assert any("Failed to resolve handler" in d.message for d in diags)


def test_runtime_counters():
    runtime = PhantomRuntime()
    runtime.create_counter("requests", 2)
    assert runtime.get_counter("requests") == (0, 2)

    # Invalid limits and duplicates
    with pytest.raises(RuntimeError):
        runtime.create_counter("invalid", 0)
    with pytest.raises(RuntimeError):
        runtime.create_counter("requests", 10)

    # Increment
    assert runtime.increment_counter("requests") == 1
    assert runtime.increment_counter("requests") == 2
    # Beyond limit: logged as diagnostic, stays at limit
    assert runtime.increment_counter("requests") == 2
    assert runtime.get_counter("requests") == (2, 2)

    diags = runtime.get_diagnostics()
    assert any("exceeded limit" in d.message for d in diags)


def test_runtime_metadata_and_diagnostics():
    runtime = PhantomRuntime()
    runtime.set_metadata("author", "Alice")
    assert runtime.get_metadata("author") == "Alice"
    assert runtime.get_metadata("non_existent") is None

    runtime.add_diagnostic("A test note", severity=Severity.INFO)
    diags = runtime.get_diagnostics()
    assert len(diags) == 1
    assert diags[0].message == "A test note"


def test_runtime_initialize_program():
    loc = SourceLocation(file="test.py", line=1, column=0, encoding=EncodingMode.COMMENT)
    instructions = [
        PhantomInstruction(
            type=InstructionType.META_AUTHOR,
            arguments=(Argument(type=ArgumentType.STRING, value="Phantom Team"),),
            source=loc,
        ),
        PhantomInstruction(
            type=InstructionType.EVENT_DECLARE,
            arguments=(Argument(type=ArgumentType.STRING, value="on_ready"),),
            source=loc,
        ),
        PhantomInstruction(
            type=InstructionType.COUNTER_CREATE,
            arguments=(
                Argument(type=ArgumentType.STRING, value="runs"),
                Argument(type=ArgumentType.INTEGER, value=5),
            ),
            source=loc,
        ),
        PhantomInstruction(
            type=InstructionType.COUNTER_INCREMENT,
            arguments=(Argument(type=ArgumentType.STRING, value="runs"),),
            source=loc,
        ),
    ]
    program = PhantomProgram(instructions=instructions, source_file="test.py")

    runtime = PhantomRuntime()
    errors = runtime.initialize(program)
    assert errors == []

    assert runtime.get_metadata("author") == "Phantom Team"
    assert "on_ready" in runtime.get_state()["events"]
    assert runtime.get_counter("runs") == (1, 5)


def test_runtime_license_metadata_after_initialize():
    loc = SourceLocation(file="test.py", line=1, column=0, encoding=EncodingMode.COMMENT)
    instructions = [
        PhantomInstruction(
            type=InstructionType.META_LICENSE,
            arguments=(Argument(type=ArgumentType.STRING, value="MIT"),),
            source=loc,
        ),
    ]
    program = PhantomProgram(instructions=instructions, source_file="test.py")

    runtime = PhantomRuntime()
    errors = runtime.initialize(program)
    assert errors == []

    assert runtime.get_metadata("license") == "MIT"


def test_runtime_capability_restriction():
    # Grant only STDIO (no EVENTS, COUNTERS, etc.)
    grant = CapabilityGrant([Capability.STDIO])
    runtime = PhantomRuntime(capabilities=grant)

    with pytest.raises(CapabilityError):
        runtime.declare_event("foo")

    with pytest.raises(CapabilityError):
        runtime.create_counter("bar", 10)


def test_runtime_execute_host_lifecycle():
    runtime = PhantomRuntime()
    pre_fired = []
    post_fired = []
    shutdown_fired = []

    runtime.register_handler("phantom.pre_execute", lambda **kw: pre_fired.append(kw))
    runtime.register_handler("phantom.post_execute", lambda **kw: post_fired.append(kw))
    runtime.register_handler("phantom.shutdown", lambda **kw: shutdown_fired.append(True))

    target = FIXTURES_DIR / "valid_plain.py"
    res = runtime.execute_host(str(target))
    assert res.exit_code == 0
    assert len(pre_fired) == 1
    assert len(post_fired) == 1

    runtime.shutdown()
    assert len(shutdown_fired) == 1
