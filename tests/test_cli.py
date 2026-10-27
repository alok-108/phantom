"""Tests for Phantom CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from phantom.cli import _ENCODING_ALIASES, ProviderError, main
from phantom.version import __version__

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_cli_version(capsys):
    ret = main(["--version"])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert __version__ in out


def test_cli_help(capsys):
    ret = main(["--help"])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "usage:" in out.lower() or "phantom" in out


def test_cli_no_args(capsys):
    ret = main([])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "usage:" in out.lower() or "phantom" in out


def test_cli_check_valid(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["check", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "0 error(s)" in out


def test_cli_check_invalid(capsys):
    target = FIXTURES_DIR / "invalid_instructions.py"
    ret = main(["check", str(target)])
    assert ret == 2
    out, err = capsys.readouterr()
    combined = out + err
    assert "error(s)" in combined


def test_cli_check_not_found(capsys):
    ret = main(["check", "not_real_file.py"])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "not found" in err.lower()


def test_cli_check_quiet_suppresses_summary(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["check", "-q", str(target)])

    assert ret == 0
    out, _ = capsys.readouterr()
    assert "0 error(s)" not in out


def test_cli_inspect_text(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["inspect", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "Instructions:" in out
    assert "event.declare" in out
    assert "Capabilities:" in out


def test_cli_inspect_json(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["inspect", str(target), "--json"])
    assert ret == 0
    out, _ = capsys.readouterr()
    parsed = json.loads(out)
    assert parsed["instruction_count"] > 0
    assert len(parsed["instructions"]) > 0
    first = parsed["instructions"][0]
    assert "type" in first
    assert "required_capabilities" in first


def test_cli_inspect_json_schema_fields(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["inspect", str(target), "--json"])
    assert ret == 0
    out, _ = capsys.readouterr()
    parsed = json.loads(out)
    assert parsed["schema"] == "phantom.inspect"
    assert parsed["schema_version"] == "1.0"
    # The top-level key set is fixed so later changes are deliberate.
    assert set(parsed) == {
        "schema",
        "schema_version",
        "source_file",
        "spec_version",
        "instruction_count",
        "has_errors",
        "instructions",
        "errors",
        "strict_findings",
    }


def test_cli_inspect_text_has_no_schema_fields(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["inspect", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "phantom.inspect" not in out
    assert "schema_version" not in out


_MALFORMED = 'x = 1\n#: phantom:0.1.0 meta.author("a"\nprint(x)\n'


def test_cli_inspect_text_shows_parse_errors(capsys, tmp_path):
    target = tmp_path / "bad.py"
    target.write_text(_MALFORMED, encoding="utf-8")
    ret = main(["inspect", str(target)])
    assert ret == 2
    out, err = capsys.readouterr()
    assert "Total Instructions: 0" in out
    assert "error: Malformed instruction" in err
    assert f"--> {target}:2:" in err
    assert '#: phantom:0.1.0 meta.author("a"' in err
    assert "^" in err


def test_cli_inspect_json_parse_errors_exit_2(capsys, tmp_path):
    target = tmp_path / "bad.py"
    target.write_text(_MALFORMED, encoding="utf-8")
    ret = main(["inspect", str(target), "--json"])
    assert ret == 2
    out, _ = capsys.readouterr()
    parsed = json.loads(out)
    assert parsed["has_errors"] is True
    assert parsed["errors"][0]["severity"] == "error"
    assert "Malformed instruction" in parsed["errors"][0]["message"]


def test_cli_inspect_clean_file_has_no_errors(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    assert main(["inspect", str(target)]) == 0
    out, err = capsys.readouterr()
    assert out.startswith("File: ")
    assert "Instructions:" in out
    assert "error" not in out + err
    assert main(["inspect", str(target), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["errors"] == []


def test_cli_run_valid(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["run", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "=== Phantom Runtime" in out
    assert "Hello, World!" in out


def test_cli_run_quiet_suppresses_banner(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["run", "-q", str(target)])

    assert ret == 0
    out, _ = capsys.readouterr()
    assert "=== Phantom Runtime" not in out
    assert "Hello, World!" in out


def test_cli_run_with_phantom_instructions(capsys):
    target = FIXTURES_DIR / "hello_phantom.py"
    ret = main(["run", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "=== Phantom Runtime" in out
    assert "Validation passed" in out
    assert "Hello, World!" in out


def test_cli_run_invalid(capsys):
    target = FIXTURES_DIR / "invalid_instructions.py"
    ret = main(["run", str(target)])
    assert ret == 2
    _, err = capsys.readouterr()
    assert "Validation failed" in err


def test_cli_run_timeout(capsys, tmp_path):
    script = tmp_path / "sleep_host.py"
    script.write_text("import time; time.sleep(5)\n")
    ret = main(["run", str(script), "--timeout", "0.5"])
    assert ret == 124
    _, err = capsys.readouterr()
    assert "timed out" in err.lower()


def test_cli_run_timeout_before_file(capsys, tmp_path):
    script = tmp_path / "sleep_host.py"
    script.write_text("import time; time.sleep(5)\n")
    ret = main(["run", "--timeout", "0.5", str(script)])
    assert ret == 124
    _, err = capsys.readouterr()
    assert "timed out" in err.lower()


def test_cli_run_invalid_timeout(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["run", str(target), "--timeout", "0"])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "--timeout" in err.lower()

    ret_neg = main(["run", str(target), "--timeout", "-1"])
    assert ret_neg == 1
    _, err_neg = capsys.readouterr()
    assert "--timeout" in err_neg.lower()

    ret_before = main(["run", "--timeout", "0", str(target)])
    assert ret_before == 1
    _, err_before = capsys.readouterr()
    assert "--timeout" in err_before.lower()

    ret_bad_val = main(["run", str(target), "--timeout", "invalid"])
    assert ret_bad_val == 2
    _, err_bad_val = capsys.readouterr()
    assert "--timeout" in err_bad_val.lower()


def test_cli_run_non_finite_timeout(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    for val in ("nan", "inf"):
        ret = main(["run", str(target), "--timeout", val])
        assert ret == 1
        _, err = capsys.readouterr()
        assert "--timeout must be positive" in err
        assert "Traceback" not in err

    for val in ("nan", "inf", "-inf"):
        ret_eq = main(["run", str(target), f"--timeout={val}"])
        assert ret_eq == 1
        _, err_eq = capsys.readouterr()
        assert "--timeout must be positive" in err_eq
        assert "Traceback" not in err_eq


def test_cli_run_timeout_equals_syntax(capsys, tmp_path):
    script = tmp_path / "sleep_host.py"
    script.write_text("import time; time.sleep(5)\n")
    ret = main(["run", str(script), "--timeout=0.5"])
    assert ret == 124
    _, err = capsys.readouterr()
    assert "timed out" in err.lower()


def test_cli_run_host_args_with_resembling_timeout(capsys, tmp_path):
    script = tmp_path / "echo_args.py"
    script.write_text("import sys; print(sys.argv[1:])\n")
    ret = main(["run", str(script), "--", "--timeout", "5"])
    assert ret == 0
    out, err = capsys.readouterr()
    assert "['--timeout', '5']" in out
    assert "Traceback" not in err


def test_cli_run_host_args_without_dash_dash(capsys, tmp_path):
    script = tmp_path / "echo_args.py"
    script.write_text("import sys; print(sys.argv[1:])\n")
    ret = main(["run", str(script), "a", "b"])
    assert ret == 0
    out, err = capsys.readouterr()
    assert "['a', 'b']" in out
    assert "Traceback" not in err


def test_cli_run_timeout_with_host_args(capsys, tmp_path):
    script = tmp_path / "args_host.py"
    script.write_text("import sys; print(','.join(sys.argv[1:]))\n")
    ret = main(["run", str(script), "--timeout", "10", "--", "alpha", "beta"])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "alpha,beta" in out


def test_cli_generate_requires_intent_noninteractive(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["generate", str(target)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "--intent is required" in err


def test_cli_generate_requires_remote_consent(capsys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["generate", "--intent", "note startup", str(target)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "not authorized" in err


def test_cli_diff(capsys, tmp_path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("print('hello')\n")
    f2.write_text("print('world')\n")

    ret = main(["diff", str(f1), str(f2)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "-print('hello')" in out
    assert "+print('world')" in out


def _diff_pair(tmp_path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("print('hello')\n")
    f2.write_text("print('world')\n")
    return f1, f2


def test_cli_diff_is_colored_by_default(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    f1, f2 = _diff_pair(tmp_path)
    assert main(["diff", str(f1), str(f2)]) == 0
    out, _ = capsys.readouterr()
    assert "\033[31m-print('hello')\033[0m" in out
    assert "\033[32m+print('world')\033[0m" in out


def test_cli_diff_no_color_env(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    f1, f2 = _diff_pair(tmp_path)
    assert main(["diff", str(f1), str(f2)]) == 0
    out, _ = capsys.readouterr()
    assert "\033[" not in out
    assert "-print('hello')" in out
    assert "+print('world')" in out


def test_cli_diff_no_color_env_empty_value_still_disables_color(
    capsys, tmp_path, monkeypatch
):
    # NO_COLOR suppresses color when present, regardless of its value.
    monkeypatch.setenv("NO_COLOR", "")
    f1, f2 = _diff_pair(tmp_path)
    assert main(["diff", str(f1), str(f2)]) == 0
    out, _ = capsys.readouterr()
    assert "\033[" not in out


def test_cli_diff_no_color_flag(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    f1, f2 = _diff_pair(tmp_path)
    assert main(["diff", "--no-color", str(f1), str(f2)]) == 0
    out, _ = capsys.readouterr()
    assert "\033[" not in out
    assert "-print('hello')" in out
    assert "+print('world')" in out


def test_cli_diff_global_no_color_flag(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    f1, f2 = _diff_pair(tmp_path)
    assert main(["--no-color", "diff", str(f1), str(f2)]) == 0
    out, _ = capsys.readouterr()
    assert "\033[" not in out


def test_cli_diff_host_only_no_color_env(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    original = tmp_path / "original.py"
    candidate = tmp_path / "candidate.py"
    original.write_text('print("one")\n')
    candidate.write_text('print("two")\n')
    assert main(["diff", "--host-only", str(original), str(candidate)]) == 0
    out, _ = capsys.readouterr()
    assert "\033[" not in out
    assert '-print("one")' in out
    assert '+print("two")' in out


def test_cli_verify_match(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["verify", str(target), str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "Tested equivalence" in out


def test_cli_verify_mismatch(capsys, tmp_path):
    f1 = tmp_path / "p1.py"
    f2 = tmp_path / "p2.py"
    f1.write_text("print('A')\n")
    f2.write_text("print('B')\n")

    ret = main(["verify", str(f1), str(f2)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "stdout differs" in err

class FakeTTY(io.StringIO):
    def isatty(self):
        return True


@pytest.fixture
def captured(monkeypatch):
    """Replace generate() with a stub that records the request and fails cleanly."""
    seen = []

    def fake_generate(request, provider):
        seen.append(request)
        return SimpleNamespace(
            warnings=[], plan=None, success=False, errors=["stub"],
            diff="", source_sha256="", candidate_source=None,
        )

    monkeypatch.setattr("phantom.cli.generate", fake_generate)
    return seen


@pytest.fixture
def plan_file(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text("{}", encoding="utf-8")
    return str(p)


def _fake_input(monkeypatch, answers):
    """Patch input() to return answers in order; return the list of prompts shown."""
    prompts = []
    it = iter(answers)

    def fake(prompt=""):
        prompts.append(prompt)
        return next(it)

    monkeypatch.setattr("builtins.input", fake)
    return prompts


# --- --stdin ---

def test_cli_generate_stdin_reads_program(monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", io.StringIO("print('hi')\n"))
    ret = main(["generate", "--stdin", "--intent", "note startup", "--plan-file", plan_file])
    assert ret == 2  # stub generate() reports failure; we only care about the request
    assert len(captured) == 1
    assert captured[0].source_code == "print('hi')\n"
    assert captured[0].source_file is None
    assert captured[0].intent == "note startup"


def test_cli_generate_stdin_requires_intent(capsys, monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", io.StringIO("print('hi')\n"))
    ret = main(["generate", "--stdin", "--plan-file", plan_file])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "--intent is required" in err
    assert captured == []


def test_cli_generate_stdin_never_prompts_even_on_terminal(monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", FakeTTY("print('hi')\n"))

    def no_input(prompt=""):
        raise AssertionError("input() must not be called with --stdin")

    monkeypatch.setattr("builtins.input", no_input)
    main(["generate", "--stdin", "--intent", "x", "--plan-file", plan_file])
    assert captured[0].placement == "beginning"
    assert captured[0].encoding == _ENCODING_ALIASES["comment"]


# --- interactive prompts ---

def test_cli_generate_terminal_empty_answers_pick_defaults(monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", FakeTTY())
    prompts = _fake_input(monkeypatch, ["", ""])
    target = FIXTURES_DIR / "valid_plain.py"
    main(["generate", str(target), "--intent", "x", "--plan-file", plan_file])
    assert len(prompts) == 2
    assert "Where should Phantom be added" in prompts[0]
    assert "Encoding?" in prompts[1]
    assert captured[0].placement == "beginning"
    assert captured[0].encoding == _ENCODING_ALIASES["comment"]


def test_cli_generate_terminal_answers_are_used(monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", FakeTTY())
    _fake_input(monkeypatch, ["end", "whitespace"])
    target = FIXTURES_DIR / "valid_plain.py"
    main(["generate", str(target), "--intent", "x", "--plan-file", plan_file])
    assert captured[0].placement == "end"
    assert captured[0].encoding == _ENCODING_ALIASES["whitespace"]


def test_cli_generate_terminal_flags_skip_prompts(monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", FakeTTY())
    prompts = _fake_input(monkeypatch, [])  # any input() call raises StopIteration
    target = FIXTURES_DIR / "valid_plain.py"
    main([
        "generate", str(target), "--intent", "x", "--plan-file", plan_file,
        "--placement", "end", "--encoding", "comment",
    ])
    assert prompts == []
    assert captured[0].placement == "end"


def test_cli_generate_terminal_eof_falls_back_to_defaults(monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", FakeTTY())

    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    target = FIXTURES_DIR / "valid_plain.py"
    main(["generate", str(target), "--intent", "x", "--plan-file", plan_file])
    assert captured[0].placement == "beginning"
    assert captured[0].encoding == _ENCODING_ALIASES["comment"]


# --- remote consent ---

def test_cli_generate_no_consent_builds_no_provider(capsys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))  # not a terminal
    calls = []
    monkeypatch.setattr("phantom.cli.get_provider", lambda name: calls.append(name))
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["generate", "--intent", "x", str(target)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "not authorized" in err
    assert calls == []


def test_cli_generate_allow_remote_builds_provider(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    calls = []

    def fake_get_provider(name):
        calls.append(name)
        raise ProviderError("stub provider failure")

    monkeypatch.setattr("phantom.cli.get_provider", fake_get_provider)
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["generate", "--intent", "x", "--allow-remote", str(target)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "stub provider failure" in err
    assert len(calls) == 1


@pytest.mark.parametrize("changed_host", [False, True])
def test_cli_diff_host_only(capsys, tmp_path, changed_host):
    original = tmp_path / "original.py"
    candidate = tmp_path / "candidate.py"
    first = '#: phantom:0.1.0 meta.author("original")\nprint("one")\n'
    second = '#: phantom:0.1.0 meta.author("candidate")\nprint("two")\n'
    if not changed_host:
        second = second.replace('print("two")', 'print("one")')
    original.write_text(first, encoding="utf-8")
    candidate.write_text(second, encoding="utf-8")
    assert main(["diff", "--host-only", str(original), str(candidate)]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert "meta.author" not in out
    if changed_host:
        assert '-print("one")' in out
        assert '+print("two")' in out
    else:
        assert out == ""
    assert original.read_text(encoding="utf-8") == first
    assert candidate.read_text(encoding="utf-8") == second


def test_cli_default_diff_keeps_instruction_changes(capsys, tmp_path):
    original = tmp_path / "original.py"
    candidate = tmp_path / "candidate.py"
    original.write_text('#: phantom:0.1.0 meta.author("original")\nprint(1)\n')
    candidate.write_text('#: phantom:0.1.0 meta.author("candidate")\nprint(1)\n')
    assert main(["diff", str(original), str(candidate)]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert '-#: phantom:0.1.0 meta.author("original")' in out
    assert '+#: phantom:0.1.0 meta.author("candidate")' in out
