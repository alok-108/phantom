"""Tests for Phantom CLI."""

from __future__ import annotations

import io
import json
import re
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


def test_cli_check_multiple_files(capsys):
    valid = FIXTURES_DIR / "valid_comments.py"
    ret = main(["check", str(valid), str(valid)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "0 error(s)" in out


def test_cli_check_multiple_files_reports_errors(capsys):
    valid = FIXTURES_DIR / "valid_comments.py"
    invalid = FIXTURES_DIR / "invalid_instructions.py"
    ret = main(["check", str(valid), str(invalid)])
    assert ret == 2
    out, err = capsys.readouterr()
    assert "error(s)" in out + err


def test_cli_check_multiple_files_missing_file(capsys):
    valid = FIXTURES_DIR / "valid_comments.py"
    ret = main(["check", str(valid), "not_real_file.py"])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "not found" in err.lower()


def test_cli_check_json_valid(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["check", "--json", str(target)])
    assert ret == 0
    out, err = capsys.readouterr()
    assert err == ""
    results = json.loads(out)
    assert isinstance(results, list) and len(results) == 1
    result = results[0]
    assert result["file"] == str(target)
    assert result["valid"] is True
    assert result["instruction_count"] == 7
    assert result["errors"] == []
    assert result["warnings"] == []


def test_cli_check_json_invalid(capsys):
    target = FIXTURES_DIR / "invalid_instructions.py"
    ret = main(["check", "--json", str(target)])
    assert ret == 2
    out, _ = capsys.readouterr()
    results = json.loads(out)
    assert isinstance(results, list) and len(results) == 1
    result = results[0]
    assert result["valid"] is False
    assert result["errors"]
    for entry in result["errors"]:
        assert set(entry) == {"message", "line", "column", "severity"}
        assert entry["severity"] == "error"
        assert isinstance(entry["line"], int) and entry["line"] >= 1
        assert isinstance(entry["column"], int) and entry["column"] >= 1
    assert result["warnings"] == []


def test_cli_check_json_warnings_only(capsys, tmp_path):
    target = tmp_path / "warn_only.py"
    target.write_text(
        '#: phantom:0.1.0 event.declare("dup")\n'
        '#: phantom:0.1.0 event.declare("dup")\n'
        'print("hi")\n',
        encoding="utf-8",
    )
    ret = main(["check", "--json", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    results = json.loads(out)
    result = results[0]
    assert result["valid"] is True
    assert result["errors"] == []
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["severity"] == "warning"
    assert "already declared" in result["warnings"][0]["message"]


def test_cli_check_json_multiple_files(capsys):
    valid = FIXTURES_DIR / "valid_comments.py"
    invalid = FIXTURES_DIR / "invalid_instructions.py"
    ret = main(["check", "--json", str(valid), str(invalid)])
    assert ret == 2
    out, _ = capsys.readouterr()
    results = json.loads(out)
    assert isinstance(results, list) and len(results) == 2
    assert [r["valid"] for r in results] == [True, False]
    assert [r["file"] for r in results] == [str(valid), str(invalid)]


def test_cli_check_json_missing_file(capsys):
    ret = main(["check", "--json", "not_real_file.py"])
    assert ret == 1
    out, err = capsys.readouterr()
    assert "not found" in err.lower()
    results = json.loads(out)
    assert isinstance(results, list) and len(results) == 1
    result = results[0]
    assert result["valid"] is False
    assert result["instruction_count"] == 0
    assert len(result["errors"]) == 1
    assert "not found" in result["errors"][0]["message"].lower()
    assert result["errors"][0]["severity"] == "error"
    assert result["warnings"] == []


def test_cli_check_json_takes_precedence_over_sarif(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["check", "--json", "--format", "sarif", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    results = json.loads(out)
    assert isinstance(results, list)
    assert results[0]["valid"] is True


def test_cli_check_json_strict_findings_sorted_by_line(capsys, tmp_path):
    target = tmp_path / "mixed.py"
    target.write_text(
        "# leading comment with a zero-width space \u200b\n"
        "print(\"hi\")\n"
        '#: phantom:0.1.0 unknown.instruction("test")\n',
        encoding="utf-8",
    )
    ret = main(["check", "--strict", "--json", str(target)])
    assert ret == 2
    out, _ = capsys.readouterr()
    results = json.loads(out)
    errors = results[0]["errors"]
    assert [e["line"] for e in errors] == [1, 3]


def test_cli_check_json_non_utf8_keeps_byte_detail(capsys, tmp_path):
    bad = tmp_path / "bad_utf8.py"
    bad.write_bytes(b"print('hello')\n# \xff\xfe\n")
    ret = main(["check", "--json", str(bad)])
    assert ret == 1
    out, err = capsys.readouterr()
    assert "is not valid UTF-8 (byte 0xff at position 17)" in err
    results = json.loads(out)
    result = results[0]
    assert result["valid"] is False
    assert len(result["errors"]) == 1
    assert result["errors"][0]["message"] == (
        f"'{bad}' is not valid UTF-8 (byte 0xff at position 17)"
    )


def test_cli_inspect_text(capsys):
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main(["inspect", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "Instructions:" in out
    assert "event.declare" in out
    assert "Capabilities:" in out

    assert len(re.findall(r"Kind: [ \t]+metadata-only", out)) == 2
    assert len(re.findall(r"Kind: [ \t]+executable", out)) == 5
    assert out.count("Kind:") == 7


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

    expected_kinds = {
        "meta.author": "metadata-only",
        "meta.version": "metadata-only",
        "event.declare": "executable",
        "event.on": "executable",
        "diagnostic.note": "executable",
        "counter.create": "executable",
    }

    for inst in parsed["instructions"]:
        assert inst["kind"] == expected_kinds[inst["type"]]


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


def test_cli_run_invalid_utf8(capsys, tmp_path):
    bad = tmp_path / "bad_utf8.py"
    bad.write_bytes(b"print('hello')\n# \xff\xfe\n")
    ret = main(["run", str(bad)])
    assert ret == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "is not valid UTF-8 (byte 0xff" in err


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


def test_cli_subcommands_preserve_double_dash_positionals(capsys):
    target = FIXTURES_DIR / "valid_plain.py"
    # check -- file
    ret = main(["check", "--", str(target)])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "0 error(s)" in out

    # inspect -- file
    ret = main(["inspect", "--", str(target)])
    assert ret == 0

    # diff -- file file
    ret = main(["diff", "--", str(target), str(target)])
    assert ret == 0

    # verify -- file file
    ret = main(["verify", "--", str(target), str(target)])
    assert ret == 0


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


@pytest.mark.parametrize("host_only", [False, True])
@pytest.mark.parametrize("change", ["none", "instruction", "host"])
@pytest.mark.parametrize("exit_code", [False, True])
def test_cli_diff_exit_code(capsys, tmp_path, host_only, change, exit_code):
    original = tmp_path / "original.py"
    candidate = tmp_path / "candidate.py"
    first = '#: phantom:0.1.0 meta.author("original")\nprint(1)\n'
    second = first
    if change == "instruction":
        second = first.replace('"original"', '"candidate"')
    elif change == "host":
        second = first.replace("print(1)", "print(2)")
    original.write_text(first, encoding="utf-8")
    candidate.write_text(second, encoding="utf-8")
    flags = (["--host-only"] if host_only else []) + (["--exit-code"] if exit_code else [])
    args = ["diff", *flags, str(original), str(candidate)]
    changed = change == "host" or (change == "instruction" and not host_only)

    assert main(args) == int(exit_code and changed)
    out, err = capsys.readouterr()
    assert err == ""
    assert bool(out) == changed
    # Status selection must not change the diff or its color handling.
    assert main([*args, "--no-color"]) == int(exit_code and changed)
    plain, err = capsys.readouterr()
    assert err == ""
    assert "\x1b[" not in plain
    assert bool(plain) == changed
    if changed:
        assert "--- " in plain and "+++ " in plain and "@@ " in plain
    assert original.read_text(encoding="utf-8") == first
    assert candidate.read_text(encoding="utf-8") == second


@pytest.mark.parametrize("host_only", [False, True])
@pytest.mark.parametrize("exit_code", [False, True])
@pytest.mark.parametrize("bad_file", ["original", "candidate"])
@pytest.mark.parametrize("failure", ["missing", "directory", "utf8", "read"])
def test_cli_diff_file_error_exit_code(
    capsys, tmp_path, monkeypatch, host_only, exit_code, bad_file, failure,
):
    paths = {name: tmp_path / f"{name}.py" for name in ("original", "candidate")}
    for path in paths.values():
        path.write_text("print(1)\n", encoding="utf-8")
    target = paths[bad_file]
    if failure in ("missing", "directory"):
        target.unlink()
        if failure == "directory":
            target.mkdir()
        message = f"{bad_file.title()} file not found"
    elif failure == "utf8":
        target.write_bytes(b"\xff")
        message = "not valid UTF-8"
    else:
        # A deterministic read failure, including on Windows or under root.
        from phantom.cli import read_source

        def fail_read(path):
            if path == str(target):
                raise PermissionError("read denied")
            return read_source(path)

        monkeypatch.setattr("phantom.cli.read_source", fail_read)
        message = "Error reading files: read denied"
    flags = (["--host-only"] if host_only else []) + (["--exit-code"] if exit_code else [])

    assert main(["diff", *flags, str(paths["original"]), str(paths["candidate"])]) == (
        2 if exit_code else 1
    )
    out, err = capsys.readouterr()
    assert out == ""
    assert message in err


@pytest.mark.parametrize("args", [[], ["one.py"], ["one.py", "two.py", "--unknown"]])
def test_cli_diff_exit_code_usage_error(capsys, args):
    assert main(["diff", "--exit-code", *args]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error:" in err


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


def test_cli_verify_multiple_cases(capsys, tmp_path):
    f1 = tmp_path / "p1.py"
    f2 = tmp_path / "p2.py"
    f1.write_text("import sys\nprint(' '.join(sys.argv[1:]))\n")
    f2.write_text("import sys\nprint(' '.join(sys.argv[1:]))\n")
    stdin = tmp_path / "in.txt"
    stdin.write_text("alice\n")

    ret = main(
        [
            "verify",
            str(f1),
            str(f2),
            "--args",
            "a",
            "--args",
            "b",
            "--stdin-file",
            str(stdin),
        ]
    )
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "Case 1:" in out
    assert "Case 2:" in out


def test_cli_verify_missing_stdin_file_is_an_error(capsys, tmp_path):
    f1 = tmp_path / "p1.py"
    f2 = tmp_path / "p2.py"
    f1.write_text("print('A')\n")
    f2.write_text("print('A')\n")

    ret = main(["verify", str(f1), str(f2), "--stdin-file", str(tmp_path / "nope.txt")])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "Stdin file not found" in err

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

def test_verify_invalid_timeout(capsys):
    # Test negative timeout returns exit code 1 and error message
    exit_code = main(["verify", "file1.py", "file2.py", "--timeout", "-5"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Error: --timeout must be positive" in captured.err

def test_verify_invalid_max_output(capsys):
    # Test negative max-output returns exit code 1 and error message
    exit_code = main(["verify", "file1.py", "file2.py", "--max-output", "-1"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Error: --max-output must be positive" in captured.err



# --- Error paths (#62) ---


def _fail_parse(monkeypatch):
    def boom(path):
        raise ValueError("boom")

    monkeypatch.setattr("phantom.cli.parse_file", boom)


def test_cli_error_path_inspect_not_found(capsys):
    ret = main(["inspect", "not_real_file.py"])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "File not found: 'not_real_file.py'" in err


@pytest.mark.parametrize("command", ["check", "inspect"])
def test_cli_error_path_parse_failure(capsys, monkeypatch, command):
    _fail_parse(monkeypatch)
    target = FIXTURES_DIR / "valid_comments.py"
    ret = main([command, str(target)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert f"Failed to parse '{target}': boom" in err


def test_cli_error_path_run_not_found(capsys):
    ret = main(["run", "not_real_file.py"])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "File not found: 'not_real_file.py'" in err


def test_cli_error_path_run_parse_failure(capsys, monkeypatch):
    _fail_parse(monkeypatch)
    target = FIXTURES_DIR / "valid_plain.py"
    ret = main(["run", str(target)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert f"Failed to parse '{target}': boom" in err


def test_cli_error_path_run_rejects_non_positive_max_output(capsys):
    ret = main(["run", str(FIXTURES_DIR / "valid_plain.py"), "--max-output", "0"])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "--max-output must be positive" in err


def test_cli_error_path_run_drops_a_second_double_dash(capsys, tmp_path):
    # The first -- ends Phantom's options; a second one directly after it is
    # dropped too, so the host only sees what follows.
    target = tmp_path / "argv.py"
    target.write_text("import sys\nprint(sys.argv[1:])\n")
    ret = main(["run", "--quiet", str(target), "--", "--", "x"])
    assert ret == 0
    out, _ = capsys.readouterr()
    assert "['x']" in out


def test_cli_error_path_run_prints_runtime_warnings(capsys, monkeypatch):
    monkeypatch.setattr(
        "phantom.cli.PhantomRuntime.initialize",
        lambda self, program: [RuntimeError("handler not registered")],
    )
    ret = main(["run", "--quiet", str(FIXTURES_DIR / "valid_plain.py")])
    assert ret == 0
    _, err = capsys.readouterr()
    assert "[RuntimeWarning] handler not registered" in err


def test_cli_error_path_run_host_output_without_newline_and_on_stderr(capsys, tmp_path):
    target = tmp_path / "streams.py"
    target.write_text("import sys\nsys.stdout.write('out')\nsys.stderr.write('err')\n")
    ret = main(["run", "--quiet", str(target)])
    assert ret == 0
    out, err = capsys.readouterr()
    assert out == "out\n"
    assert err == "err\n"


def test_cli_error_path_run_reports_truncated_output(capsys, tmp_path):
    target = tmp_path / "loud.py"
    target.write_text("print('x' * 5000)\n")
    ret = main(["run", "--quiet", str(target), "--max-output", "100"])
    assert ret == 0
    _, err = capsys.readouterr()
    assert "[HostExecution] stdout truncated at the output cap" in err


def test_cli_error_path_generate_without_file_or_stdin(capsys, monkeypatch, plan_file):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    ret = main(["generate", "--intent", "x", "--plan-file", plan_file])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "provide a file or --stdin" in err


def test_cli_error_path_generate_file_not_found(capsys, monkeypatch, plan_file):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    ret = main(["generate", "not_real_file.py", "--intent", "x", "--plan-file", plan_file])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "File not found: 'not_real_file.py'" in err


@pytest.mark.parametrize(
    "answer, consented", [("y", True), ("yes", True), ("n", False), ("", False)]
)
def test_cli_error_path_generate_interactive_consent(capsys, monkeypatch, answer, consented):
    monkeypatch.setattr("sys.stdin", FakeTTY())
    monkeypatch.setattr("builtins.input", lambda prompt="": answer if "Continue?" in prompt else "")
    calls = []

    def fake_get_provider(name):
        calls.append(name)
        raise ProviderError("stub provider failure")

    monkeypatch.setattr("phantom.cli.get_provider", fake_get_provider)
    ret = main(["generate", "--intent", "x", str(FIXTURES_DIR / "valid_plain.py")])
    assert ret == 1
    _, err = capsys.readouterr()
    assert bool(calls) is consented
    assert ("stub provider failure" in err) is consented


def test_cli_error_path_generate_asks_for_intent_on_terminal(monkeypatch, captured, plan_file):
    monkeypatch.setattr("sys.stdin", FakeTTY())
    prompts = []

    def fake_input(prompt=""):
        prompts.append(prompt)
        return "note startup" if "What should Phantom do" in prompt else ""

    monkeypatch.setattr("builtins.input", fake_input)
    main(["generate", str(FIXTURES_DIR / "valid_plain.py"), "--plan-file", plan_file])
    assert any("What should Phantom do" in p for p in prompts)
    assert captured[0].intent == "note startup"


def test_cli_error_path_generate_unreadable_plan_file(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    ret = main(
        [
            "generate",
            str(FIXTURES_DIR / "valid_plain.py"),
            "--intent",
            "x",
            "--plan-file",
            str(tmp_path / "missing-plan.json"),
        ]
    )
    assert ret == 1
    _, err = capsys.readouterr()
    assert "cannot read plan file" in err


def test_cli_error_path_generate_prints_warnings_limitations_and_no_output(
    capsys, monkeypatch, plan_file
):
    def fake_generate(request, provider):
        return SimpleNamespace(
            warnings=["placement fell back to beginning"],
            plan=SimpleNamespace(instructions=[], limitations=["comments only"]),
            success=True,
            errors=[],
            diff="+# phantom: log",
            source_sha256="",
            candidate_source="# phantom: log\n",
        )

    monkeypatch.setattr("phantom.cli.generate", fake_generate)
    monkeypatch.setattr("sys.stdin", io.StringIO("print('hi')\n"))
    ret = main(["generate", "--stdin", "--intent", "x", "--plan-file", plan_file])
    assert ret == 0
    out, err = capsys.readouterr()
    assert "warning: placement fell back to beginning" in err
    assert "Limitations: comments only" in out
    assert "No --output given: candidate not saved." in out


def test_cli_error_path_verify_missing_candidate(capsys):
    ret = main(["verify", str(FIXTURES_DIR / "valid_plain.py"), "not_real_file.py"])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "Candidate file not found: 'not_real_file.py'" in err


def test_cli_error_path_verify_unreadable_stdin_file(capsys, tmp_path):
    f1 = tmp_path / "p1.py"
    f1.write_text("print('A')\n")
    bad = tmp_path / "input.txt"
    bad.write_bytes(b"\xff\xfe not utf-8")
    ret = main(["verify", str(f1), str(f1), "--stdin-file", str(bad)])
    assert ret == 1
    _, err = capsys.readouterr()
    assert "is not valid UTF-8" in err
