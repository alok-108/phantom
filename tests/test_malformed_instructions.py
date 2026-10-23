"""Typos in the instruction layer must be reported, never silently ignored."""

from __future__ import annotations

from pathlib import Path

import pytest

from phantom.cli import main
from phantom.generator.validation import validate_candidate
from phantom.parser import parse

DOCS_EXAMPLES = Path(__file__).parent.parent / "docs" / "examples"


@pytest.mark.parametrize(
    "line",
    [
        '#: phantom:0.1.0 meta.author("a"',
        '#: phantom:0.1.0 meta.author "a"',
        "#: phantom:0.1.0",
        "#: phantom:0.1.0 meta.author",
        '#:phantom:0.1.0 Meta.author("a")',
    ],
)
def test_malformed_instruction_is_a_parse_error(line):
    program = parse(f"x = 1\n{line}\n")
    assert program.instructions == []
    (error,) = program.errors
    assert error.severity.value == "error"
    assert error.source.line == 2
    assert "Malformed instruction" in error.message


def test_error_column_follows_indentation():
    program = parse('def f():\n    #: phantom:0.1.0 meta.author("a"\n    return 1\n')
    (error,) = program.errors
    assert (error.source.line, error.source.column) == (2, 4)


def test_trailing_comment_is_ordinary_source_with_a_warning():
    program = parse('#: phantom:0.1.0 meta.author("a")  # because\n')
    assert program.instructions == []
    (finding,) = program.errors
    assert finding.severity.value == "warning"
    assert not program.has_errors


@pytest.mark.parametrize(
    "line",
    [
        '# phantom:0.1.0 meta.author("a")',
        "# mentions #: phantom: in the middle",
        'text = "#: phantom:0.1.0 meta.author(1"',
        "#:ws:begin-not-a-marker",
        "#: hello",
    ],
)
def test_lookalikes_stay_ordinary_source(line):
    program = parse(line + "\n")
    assert program.instructions == []
    assert program.errors == []


def test_hybrid_header_is_not_malformed():
    program = parse('#:phantom:hybrid\n#: phantom:0.1.0 meta.author("a")\n')
    assert program.errors == []
    assert len(program.instructions) == 1


def test_documentation_examples_still_parse_cleanly():
    for path in DOCS_EXAMPLES.glob("*.py"):
        if path.name == "invalid.py":
            continue
        program = parse(path.read_text(encoding="utf-8"), str(path))
        assert not program.has_errors, (path.name, [str(e) for e in program.errors])


def test_check_fails_on_a_typo(tmp_path, capsys):
    path = tmp_path / "typo.py"
    path.write_text('#: phantom:0.1.0 meta.author("a"\nprint(1)\n', encoding="utf-8")
    assert main(["check", str(path)]) == 2
    captured = capsys.readouterr()
    assert "Malformed instruction" in captured.out + captured.err


def test_run_refuses_a_file_with_a_typo(tmp_path, capsys):
    path = tmp_path / "typo.py"
    path.write_text('#: phantom:0.1.0 counter.create("n", 3\nprint("ran")\n', encoding="utf-8")
    assert main(["run", str(path)]) == 2
    assert "ran" not in capsys.readouterr().out


class TestCandidateInstructionCount:
    def test_missing_instruction_is_a_failure(self):
        report = validate_candidate("print(1)\n", "print(1)\n", expected_added=1)
        assert not report.passed
        assert any("could not be read back" in e for e in report.errors)

    def test_expected_instruction_passes(self):
        candidate = '#: phantom:0.1.0 meta.author("a")\nprint(1)\n'
        assert validate_candidate("print(1)\n", candidate, expected_added=1).passed

    def test_existing_instructions_are_counted(self):
        original = '#: phantom:0.1.0 meta.author("a")\nprint(1)\n'
        candidate = '#: phantom:0.1.0 meta.version("1")\n' + original
        assert validate_candidate(original, candidate, expected_added=1).passed
        assert not validate_candidate(original, original, expected_added=1).passed

    def test_count_is_not_checked_when_not_requested(self):
        assert validate_candidate("print(1)\n", "print(1)\n").passed
