"""Capability policy (--deny / --allow-only) and handler allow-list (--handlers-from)."""

from __future__ import annotations

import json

import pytest

from phantom.capabilities import Capability, build_policy, parse_capability
from phantom.cli import create_parser, main
from phantom.handler_policy import HandlerPolicy
from phantom.parser import parse
from phantom.runtime import PhantomRuntime
from phantom.validator import check_policy

COUNTER_PROGRAM = (
    '#: phantom:0.1.0 counter.create("n", 3)\n'
    '#: phantom:0.1.0 meta.author("a")\n'
    'print("host ran")\n'
)


class TestCapabilityNames:
    @pytest.mark.parametrize("name", ["cap.events", "events", "EVENTS", " cap.events "])
    def test_accepted_spellings(self, name):
        assert parse_capability(name) is Capability.EVENTS

    def test_unknown_name_lists_the_known_ones(self):
        with pytest.raises(ValueError, match="cap.counters"):
            parse_capability("cap.nope")

    def test_argparse_rejects_an_unknown_capability(self, capsys):
        with pytest.raises(SystemExit):
            create_parser().parse_args(["check", "x.py", "--deny", "cap.nope"])
        assert "unknown capability" in capsys.readouterr().err


class TestBuildPolicy:
    def test_default_grants_everything(self):
        assert set(build_policy().granted) == set(Capability)

    def test_deny_subtracts(self):
        grant = build_policy(deny=[Capability.COUNTERS])
        assert Capability.COUNTERS not in grant
        assert Capability.EVENTS in grant

    def test_allow_only_replaces_the_default(self):
        grant = build_policy(allow_only=[Capability.STDIO])
        assert set(grant.granted) == {Capability.STDIO}

    def test_deny_wins_over_allow_only(self):
        grant = build_policy(deny=[Capability.STDIO], allow_only=[Capability.STDIO, Capability.EVENTS])
        assert set(grant.granted) == {Capability.EVENTS}


def test_check_policy_names_the_instruction_and_capability():
    program = parse(COUNTER_PROGRAM)
    findings = check_policy(program, build_policy(deny=[Capability.COUNTERS]))
    (finding,) = findings
    assert "counter.create" in finding.message
    assert "cap.counters" in finding.message
    assert finding.source.line == 1


def test_check_policy_is_quiet_when_everything_is_granted():
    assert check_policy(parse(COUNTER_PROGRAM), build_policy()) == []


class TestCliCapabilityPolicy:
    @pytest.fixture
    def program(self, tmp_path):
        path = tmp_path / "prog.py"
        path.write_text(COUNTER_PROGRAM, encoding="utf-8")
        return str(path)

    def test_check_passes_without_a_policy(self, program):
        assert main(["check", program]) == 0

    def test_check_fails_when_a_denied_capability_is_used(self, program, capsys):
        assert main(["check", program, "--deny", "cap.counters"]) == 2
        captured = capsys.readouterr()
        assert "counter.create" in captured.out + captured.err

    def test_a_denied_capability_stops_run_before_the_host_starts(self, program, capsys):
        assert main(["run", program, "--deny", "counters"]) == 2
        captured = capsys.readouterr()
        assert "host ran" not in captured.out
        assert "cap.counters" in captured.err

    def test_allow_only_blocks_everything_else(self, program, capsys):
        assert main(["run", program, "--allow-only", "cap.stdio"]) == 2
        assert "host ran" not in capsys.readouterr().out

    def test_run_without_stdio_never_starts_the_host(self, tmp_path, capsys):
        path = tmp_path / "plain.py"
        path.write_text('print("host ran")\n', encoding="utf-8")
        assert main(["run", str(path), "--deny", "cap.stdio"]) == 2
        captured = capsys.readouterr()
        assert "host ran" not in captured.out
        assert "cap.stdio" in captured.err

    def test_an_unaffected_program_still_runs_under_a_policy(self, tmp_path, capsys):
        path = tmp_path / "meta.py"
        path.write_text('#: phantom:0.1.0 meta.author("a")\nprint("host ran")\n', encoding="utf-8")
        assert main(["run", str(path), "--deny", "cap.counters"]) == 0
        assert "host ran" in capsys.readouterr().out

    def test_inspect_marks_blocked_instructions(self, program, capsys):
        assert main(["inspect", program, "--deny", "cap.counters"]) == 0
        out = capsys.readouterr().out
        assert "BLOCKED (denied: cap.counters)" in out

    def test_inspect_json_reports_blocked_by_policy(self, program, capsys):
        assert main(["inspect", program, "--json", "--deny", "cap.counters"]) == 0
        data = json.loads(capsys.readouterr().out)
        blocked = {i["type"]: i["blocked_by_policy"] for i in data["instructions"]}
        assert blocked == {"counter.create": ["cap.counters"], "meta.author": []}

    def test_inspect_json_has_no_policy_field_without_a_policy(self, program, capsys):
        main(["inspect", program, "--json"])
        data = json.loads(capsys.readouterr().out)
        assert all("blocked_by_policy" not in i for i in data["instructions"])


# ---------------------------------------------------------------------------
# Handler allow-list
# ---------------------------------------------------------------------------

MARKER_MODULE = (
    "from pathlib import Path\n"
    "Path(__file__).with_name('{name}.marker').write_text('imported')\n"
    "def run(**kw):\n"
    "    return '{name} ran'\n"
)


@pytest.fixture
def modules(tmp_path, monkeypatch):
    """Two importable modules in different directories; importing either leaves a marker."""
    allowed = tmp_path / "allowed"
    other = tmp_path / "other"
    allowed.mkdir()
    other.mkdir()
    (allowed / "good_hook.py").write_text(MARKER_MODULE.format(name="good_hook"), encoding="utf-8")
    (other / "evil_hook.py").write_text(MARKER_MODULE.format(name="evil_hook"), encoding="utf-8")
    monkeypatch.syspath_prepend(str(allowed))
    monkeypatch.syspath_prepend(str(other))
    for name in ("good_hook", "evil_hook"):
        monkeypatch.delitem(__import__("sys").modules, name, raising=False)
    return allowed, other


def _fire(policy):
    runtime = PhantomRuntime(handler_policy=policy)
    runtime.register_handler("phantom.pre_execute", "good_hook.run")
    runtime.register_handler("phantom.pre_execute", "evil_hook.run")
    return runtime, runtime.fire_event("phantom.pre_execute")


class TestHandlerPolicy:
    def test_disabled_by_default(self, modules):
        allowed, other = modules
        _, results = _fire(HandlerPolicy())
        assert results == ["good_hook ran", "evil_hook ran"]
        assert (allowed / "good_hook.marker").exists() and (other / "evil_hook.marker").exists()

    def test_a_disallowed_module_is_never_imported(self, modules):
        allowed, other = modules
        runtime, results = _fire(HandlerPolicy.create(directories=[allowed]))
        assert results == ["good_hook ran"]
        assert (allowed / "good_hook.marker").exists()
        assert not (other / "evil_hook.marker").exists(), "disallowed module was imported"
        assert "evil_hook" not in __import__("sys").modules
        (diag,) = runtime.get_diagnostics()
        assert diag.severity.value == "error"
        assert "not allowed by the handler policy" in diag.message
        assert "evil_hook.run" in diag.message

    def test_patterns_allow_by_dotted_path(self, modules):
        allowed, other = modules
        _, results = _fire(HandlerPolicy.create(patterns=["good_hook.*"]))
        assert results == ["good_hook ran"]
        assert not (other / "evil_hook.marker").exists()

    def test_directories_and_patterns_combine(self, modules):
        _, results = _fire(HandlerPolicy.create(directories=[modules[0]], patterns=["evil_hook.run"]))
        assert results == ["good_hook ran", "evil_hook ran"]

    def test_standard_library_handlers_are_denied_under_a_policy(self, modules, tmp_path):
        runtime = PhantomRuntime(handler_policy=HandlerPolicy.create(directories=[modules[0]]))
        runtime.register_handler("phantom.pre_execute", "os.getcwd")
        assert runtime.fire_event("phantom.pre_execute") == []
        assert "not allowed" in runtime.get_diagnostics()[0].message

    def test_missing_modules_still_fail_as_import_errors(self, modules):
        runtime = PhantomRuntime(handler_policy=HandlerPolicy.create(directories=[modules[0]]))
        runtime.register_handler("phantom.pre_execute", "no_such_module_zz.run")
        assert runtime.fire_event("phantom.pre_execute") == []
        assert "Could not resolve" in runtime.get_diagnostics()[0].message

    def test_callable_handlers_are_not_restricted(self, modules):
        runtime = PhantomRuntime(handler_policy=HandlerPolicy.create(directories=[modules[0]]))
        runtime.register_handler("phantom.pre_execute", lambda: "python callable")
        assert runtime.fire_event("phantom.pre_execute") == ["python callable"]

    def test_a_module_in_the_working_directory_is_checked_too(self, tmp_path, monkeypatch):
        """The cwd is added to sys.path during resolution; the check must see it."""
        (tmp_path / "cwd_hook.py").write_text(MARKER_MODULE.format(name="cwd_hook"), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delitem(__import__("sys").modules, "cwd_hook", raising=False)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        runtime = PhantomRuntime(handler_policy=HandlerPolicy.create(directories=[elsewhere]))
        runtime.register_handler("phantom.pre_execute", "cwd_hook.run")
        assert runtime.fire_event("phantom.pre_execute") == []
        assert not (tmp_path / "cwd_hook.marker").exists()


def test_cli_handlers_from_blocks_other_modules(tmp_path, capsys):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (tmp_path / "hook.py").write_text(MARKER_MODULE.format(name="hook"), encoding="utf-8")
    program = tmp_path / "prog.py"
    program.write_text(
        '#: phantom:0.1.0 event.on("phantom.pre_execute", "hook.run")\nprint("host ran")\n',
        encoding="utf-8",
    )
    assert main(["run", str(program), "--handlers-from", str(allowed)]) == 0
    out = capsys.readouterr().out
    assert "host ran" in out
    assert "not allowed by the handler policy" in out
    assert not (tmp_path / "hook.marker").exists()


def test_cli_allow_handler_pattern(tmp_path, capsys):
    (tmp_path / "hook.py").write_text(MARKER_MODULE.format(name="hook"), encoding="utf-8")
    program = tmp_path / "prog.py"
    program.write_text(
        '#: phantom:0.1.0 event.on("phantom.pre_execute", "hook.run")\nprint("host ran")\n',
        encoding="utf-8",
    )
    assert main(["run", str(program), "--allow-handler", "hook.*"]) == 0
    assert "not allowed" not in capsys.readouterr().out
    assert (tmp_path / "hook.marker").exists()
