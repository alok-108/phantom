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


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
@pytest.mark.parametrize("handler_kind", ["no_args", "named", "var_kw"])
def test_runtime_handler_error_is_not_retried(error_type, handler_kind):
    runtime = PhantomRuntime()
    calls = []

    def fail(value):
        calls.append(value)
        raise error_type("error inside handler")

    def no_args():
        fail(None)

    def named(value):
        fail(value)

    def var_kw(**kwargs):
        fail(kwargs["value"])

    handler = {"no_args": no_args, "named": named, "var_kw": var_kw}[handler_kind]
    runtime.register_handler("phantom.pre_execute", handler)
    runtime.register_handler("phantom.pre_execute", lambda: "next handler")

    assert runtime.fire_event("phantom.pre_execute", value=42, extra=True) == ["next handler"]
    assert calls == [None if handler_kind == "no_args" else 42]
    diagnostics = runtime.get_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == Severity.ERROR
    assert "error inside handler" in diagnostics[0].message


def test_runtime_callback_keyword_selection():
    runtime = PhantomRuntime()

    def named(value, *, optional=7):
        return value, optional

    def optional_only(optional=7):
        return optional

    def positional_default(value=7, /):
        return value

    class Handler:
        def __call__(self, value):
            return value

        def method(self, *, value):
            return value

    handler = Handler()
    callbacks = [
        lambda: "no args",
        named,
        optional_only,
        positional_default,
        lambda **kwargs: kwargs,
        handler,
        handler.method,
    ]
    for callback in callbacks:
        runtime.register_handler("phantom.pre_execute", callback)

    assert runtime.fire_event("phantom.pre_execute", value=42, extra=True) == [
        "no args", (42, 7), 7, 7, {"value": 42, "extra": True}, 42, 42,
    ]
    assert runtime.get_diagnostics() == []


@pytest.mark.parametrize("positional_only", [False, True])
def test_runtime_callback_invalid_signature_does_not_run(positional_only):
    runtime = PhantomRuntime()
    calls = []

    def named(required):
        calls.append(required)

    def positional(required, /):
        calls.append(required)

    runtime.register_handler("phantom.pre_execute", positional if positional_only else named)
    kwargs = {"required": 42} if positional_only else {"extra": True}
    assert runtime.fire_event("phantom.pre_execute", **kwargs) == []
    assert calls == []
    assert len(runtime.get_diagnostics()) == 1
    assert runtime.get_diagnostics()[0].severity == Severity.ERROR


@pytest.mark.parametrize("signature_error", [TypeError, ValueError])
@pytest.mark.parametrize("handler_error", [None, TypeError, ValueError])
def test_runtime_uninspectable_callback_runs_once(monkeypatch, signature_error, handler_error):
    runtime = PhantomRuntime()
    calls = []

    def unavailable_signature(fn):
        raise signature_error("signature unavailable")

    def handler(**kwargs):
        calls.append(kwargs)
        if handler_error is not None:
            raise handler_error("error inside handler")
        return "called"

    monkeypatch.setattr("phantom.runtime.inspect.signature", unavailable_signature)
    runtime.register_handler("phantom.pre_execute", handler)
    assert runtime.fire_event("phantom.pre_execute", value=42) == (
        ["called"] if handler_error is None else []
    )
    assert calls == [{"value": 42}]
    diagnostics = runtime.get_diagnostics()
    assert len(diagnostics) == (0 if handler_error is None else 1)
    if handler_error is not None:
        assert diagnostics[0].severity == Severity.ERROR
        assert "error inside handler" in diagnostics[0].message


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


def test_runtime_execute_host_timeout(tmp_path):
    script = tmp_path / "sleep_script.py"
    script.write_text("import time; time.sleep(5)\n")
    runtime = PhantomRuntime()
    res = runtime.execute_host(str(script), timeout=0.2)
    assert res.exit_code == 124
    assert "timed out" in res.stderr.lower()
