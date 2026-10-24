"""Tests for the intermediate representation and diagnostics rendering."""

from __future__ import annotations

import dataclasses
import json

import pytest

from phantom import diagnostics
from phantom.ir import (
    Argument,
    ArgumentType,
    InstructionType,
    ParseError,
    PhantomInstruction,
    PhantomProgram,
    Severity,
    SourceLocation,
    ValidationError,
)
from phantom.parser import parse


def _inst():
    return PhantomInstruction(
        InstructionType.COUNTER_CREATE,
        (Argument(ArgumentType.STRING, "c"), Argument(ArgumentType.INTEGER, 3)),
        SourceLocation("f.py", 2, 4),
    )


def test_instructions_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _inst().type = InstructionType.META_AUTHOR  # type: ignore[misc]


def test_accessors():
    inst = _inst()
    assert inst.identifier == "counter.create"
    assert inst.get_string_arg(0) == "c" and inst.get_int_arg(1) == 3
    assert inst.get_string_arg(1) is None and inst.get_argument(9) is None
    assert str(inst) == 'phantom:0.1.0 counter.create("c", 3)'


def test_program_serialization_is_deterministic_json():
    prog = PhantomProgram([_inst()], "f.py")
    assert prog.to_json() == prog.to_json()
    data = json.loads(prog.to_json())
    assert data["instruction_count"] == 1 and data["instructions"][0]["type"] == "counter.create"


def test_has_errors_only_counts_errors():
    prog = PhantomProgram(errors=[ParseError("w", SourceLocation("f", 1), Severity.WARNING)])
    assert not prog.has_errors


def test_instructions_by_type():
    prog = PhantomProgram([_inst()])
    assert len(prog.instructions_by_type(InstructionType.COUNTER_CREATE)) == 1
    assert prog.instructions_by_type(InstructionType.META_AUTHOR) == []


def test_render_with_caret():
    src = '    #: phantom:0.1.0 foo.bar("x")\n'
    err = parse(src, "f.py").errors[0]
    text = diagnostics.render(err, src)
    assert "f.py:1:5" in text and "^" in text and src.strip() in text


def test_render_without_source_and_with_color():
    err = ValidationError("bad", _inst())
    assert "error: bad" in diagnostics.render(err)
    assert "\033[" in diagnostics.render(err, color=True)


def test_summary_counts():
    errs = [
        ValidationError("e", _inst()),
        ValidationError("w", _inst(), severity=Severity.WARNING),
    ]
    assert diagnostics.summary(errs) == "1 error(s), 1 warning(s)"


def test_sarif_shape():
    log = diagnostics.to_sarif([ValidationError("bad", _inst())])
    assert log["version"] == "2.1.0"
    result = log["runs"][0]["results"][0]
    assert result["level"] == "error"
    region = result["locations"][0]["physicalLocation"]["region"]
    assert region == {"startLine": 2, "startColumn": 5}
    json.loads(diagnostics.to_sarif_json([]))


def _sarif_uri(path: str) -> str:
    err = ParseError("bad", SourceLocation(path, 1))
    log = diagnostics.to_sarif([err])
    return log["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]


@pytest.mark.parametrize(
    ("path", "uri"),
    [
        ("src/app.py", "src/app.py"),
        ("my dir/app.py", "my%20dir/app.py"),
        ("issue#1/app.py", "issue%231/app.py"),
        ("50%/app.py", "50%25/app.py"),
        ("src\\pkg\\app.py", "src/pkg/app.py"),
        ("my dir\\app #2.py", "my%20dir/app%20%232.py"),
        ("/home/me/my dir/app.py", "file:///home/me/my%20dir/app.py"),
        ("C:\\Users\\me\\app.py", "file:///C:/Users/me/app.py"),
        ("d:/my dir/app.py", "file:///d:/my%20dir/app.py"),
    ],
)
def test_sarif_uri_is_encoded(path, uri):
    assert _sarif_uri(path) == uri
