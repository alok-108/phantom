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


def test_cli_run_valid(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["run", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "=== Phantom Runtime" in out
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
