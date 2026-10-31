"""Security regression tests."""

from __future__ import annotations

import socket
import sys

import pytest

from phantom.cli import main
from phantom.encoding import encode_instruction
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    SourceLocation,
)
from phantom.parser import parse, parse_file
from phantom.validator import validate


def _trap_source(marker):
    return (
        f"open({str(marker)!r}, 'w').write('executed')\n"
        '#: phantom:0.1.0 diagnostic.note("x")\n'
    )


def test_parse_does_not_execute_host(tmp_path):
    marker = tmp_path / "m.txt"
    path = tmp_path / "t.py"
    path.write_text(_trap_source(marker))
    parse_file(str(path))
    assert not marker.exists()


@pytest.mark.parametrize("cmd", ["check", "inspect"])
def test_check_and_inspect_do_not_execute(tmp_path, cmd, capsys):
    marker = tmp_path / "m.txt"
    path = tmp_path / "t.py"
    path.write_text(_trap_source(marker))
    assert main([cmd, str(path)]) == 0
    assert not marker.exists()


def test_arguments_are_data_not_code():
    payload = "__import__('os').system('echo pwned')"
    prog = parse(f'#: phantom:0.1.0 diagnostic.note("{payload}")\n')
    assert prog.instructions[0].get_string_arg(0) == payload
    assert validate(prog) == []


def test_unknown_instruction_never_dispatches():
    prog = parse('#: phantom:0.1.0 os.system("calc")\n')
    assert not prog.instructions and prog.has_errors


def test_integer_argument_cannot_smuggle_expression():
    prog = parse("#: phantom:0.1.0 counter.create(\"c\", 1+1)\n")
    assert prog.has_errors


def test_ordinary_comments_never_trigger():
    src = (
        "# phantom:0.1.0 meta.author(\"x\")\n"
        "#phantom:0.1.0 meta.author(\"x\")\n"
        "x = 1  # #: phantom:0.1.0 meta.author(\"x\")\n"
        "s = '#: phantom:0.1.0 meta.author(\"x\")'\n"
    )
    assert parse(src).instruction_count == 0


def test_rejected_invisible_codepoint_is_error_in_unicode_block():
    inst = PhantomInstruction(
        InstructionType.META_AUTHOR,
        (Argument(ArgumentType.STRING, "A"),),
        SourceLocation("t", 1),
    )
    block = encode_instruction(inst, EncodingMode.UNICODE).replace("# ", "# ⁠", 1)
    prog = parse(block + "\n")
    assert prog.has_errors


def test_parse_does_not_rewrite_file(tmp_path):
    path = tmp_path / "t.py"
    path.write_bytes(b'print(1)  \r\n#: phantom:0.1.0 meta.author("A")\r\n')
    before = path.read_bytes()
    parse_file(str(path))
    main(["check", str(path)])
    main(["inspect", str(path)])
    assert path.read_bytes() == before


def test_generate_without_consent_makes_no_network_call(tmp_path, monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-not-a-real-key")
    path = tmp_path / "p.py"
    path.write_text("print(1)\n")
    assert main(["generate", "--intent", "x", str(path)]) == 1


def test_generate_never_overwrites_input(tmp_path, capsys):
    from phantom.cli import cmd_generate, create_parser
    from phantom.generator import StaticProvider

    path = tmp_path / "p.py"
    path.write_text("print(1)\n")
    plan = (
        '{"encoding":"comment","instructions":[{"instruction_type":"meta.author",'
        '"arguments":[{"type":"string","value":"A"}],"placement_line":1}]}'
    )
    args = create_parser().parse_args(
        ["generate", str(path), "--intent", "x", "--output", str(path)]
    )
    assert cmd_generate(args, StaticProvider(plan)) == 1
    assert path.read_text() == "print(1)\n"

    out = tmp_path / "candidate.py"
    args = create_parser().parse_args(
        ["generate", str(path), "--intent", "x", "--output", str(out)]
    )
    assert cmd_generate(args, StaticProvider(plan)) == 0
    assert path.read_text() == "print(1)\n" and "meta.author" in out.read_text()


def test_dry_run_writes_nothing(tmp_path):
    from phantom.cli import cmd_generate, create_parser
    from phantom.generator import StaticProvider

    path = tmp_path / "p.py"
    path.write_text("print(1)\n")
    out = tmp_path / "c.py"
    plan = (
        '{"encoding":"comment","instructions":[{"instruction_type":"meta.author",'
        '"arguments":[{"type":"string","value":"A"}],"placement_line":1}]}'
    )
    args = create_parser().parse_args(
        ["generate", str(path), "--intent", "x", "--dry-run", "--output", str(out)]
    )
    assert cmd_generate(args, StaticProvider(plan)) == 0
    assert not out.exists()


def test_unsupported_generator_encoding_refused(tmp_path):
    path = tmp_path / "p.py"
    path.write_text("print(1)\n")
    assert main(["generate", str(path), "--intent", "x", "--encoding", "hybrid"]) == 1


def test_no_global_interpreter_changes():
    """Importing and using Phantom must not install import hooks or sitecustomize."""
    hooks_before = (list(sys.meta_path), list(sys.path_hooks))
    parse("x = 1\n")
    assert (list(sys.meta_path), list(sys.path_hooks)) == hooks_before


class TestStrictAudit:
    def test_clean_source(self):
        from phantom.validator import audit_source

        assert audit_source("print('héllo ✓')\n") == []

    def test_legitimate_zw_block_is_clean(self):
        from phantom.validator import audit_source

        inst = PhantomInstruction(
            InstructionType.META_AUTHOR,
            (Argument(ArgumentType.STRING, "A"),),
            SourceLocation("t", 1),
        )
        assert audit_source(encode_instruction(inst, EncodingMode.UNICODE) + "\n") == []

    @pytest.mark.parametrize("ch", ["​", "⁠", "‮", "⁦"])
    def test_hidden_characters_outside_block_flagged(self, ch):
        from phantom.validator import audit_source

        (finding,) = audit_source(f"x = 'a{ch}b'\n", "f.py")
        assert f"U+{ord(ch):04X}" in finding.message
        assert finding.source.line == 1 and finding.source.column == 6

    def test_rejected_character_inside_block_flagged(self):
        from phantom.validator import audit_source

        src = "#:zw:begin\n# ​⁠\n#:zw:end\n"
        assert [f.message for f in audit_source(src)][0].startswith("Unexpected invisible code point U+2060")

    def test_unclosed_zw_block_reported_at_eof(self):
        from phantom.validator import audit_source

        src = "#:zw:begin\nx = 1\n# rogue \u200b\n"
        findings = audit_source(src, "unclosed.py")
        assert len(findings) == 1
        assert "Unterminated zero-width block missing closing marker '#:zw:end'" in findings[0].message
        assert findings[0].source.line == 1

    def test_unexpected_closing_zw_marker_reported(self):
        from phantom.validator import audit_source

        src = "x = 1\n#:zw:end\ny = 2\n"
        findings = audit_source(src, "stray_close.py")
        assert len(findings) == 1
        assert "Unexpected zero-width block closing marker '#:zw:end' without preceding begin marker" in findings[0].message
        assert findings[0].source.line == 2

    def test_unclosed_ws_block_reported_at_eof(self):
        from phantom.validator import audit_source

        src = "#:ws:begin\nx = 1\n"
        findings = audit_source(src, "unclosed_ws.py")
        assert len(findings) == 1
        assert "Unterminated whitespace block missing closing marker '#:ws:end'" in findings[0].message
        assert findings[0].source.line == 1

    def test_unexpected_closing_ws_marker_reported(self):
        from phantom.validator import audit_source

        src = "x = 1\n#:ws:end\ny = 2\n"
        findings = audit_source(src, "stray_close_ws.py")
        assert len(findings) == 1
        assert "Unexpected whitespace block closing marker '#:ws:end' without preceding begin marker" in findings[0].message
        assert findings[0].source.line == 2

    def test_cli_strict_exit_codes(self, tmp_path, capsys):
        bad = tmp_path / "bad.py"
        bad.write_text("x = 1  # ‮\n", encoding="utf-8")
        assert main(["check", "--strict", str(bad)]) == 2
        assert main(["check", str(bad)]) == 0
        assert main(["inspect", "--strict", str(bad)]) == 2
