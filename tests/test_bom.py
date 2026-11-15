"""A leading UTF-8 BOM must not hide the first instruction (#44)."""

from __future__ import annotations

import json

from phantom.cli import main
from phantom.parser import parse_file

BOM = b"\xef\xbb\xbf"
SOURCE = b'#: phantom:0.1.0 meta.author("a")\nprint(1)\n'
INVALID = b"#: phantom:0.1.0 bogus.thing()\nprint(1)\n"


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_parse_file_reads_first_instruction_after_bom(tmp_path):
    prog = parse_file(str(_write(tmp_path, "bom.py", BOM + SOURCE)))
    assert prog.errors == []
    assert len(prog.instructions) == 1
    inst = prog.instructions[0]
    assert inst.identifier == "meta.author"
    assert inst.source.line == 1
    assert inst.source.column == 0


def test_parse_file_same_result_with_and_without_bom(tmp_path):
    with_bom = parse_file(str(_write(tmp_path, "bom.py", BOM + SOURCE)))
    without = parse_file(str(_write(tmp_path, "plain.py", SOURCE)))
    assert [i.identifier for i in with_bom.instructions] == [
        i.identifier for i in without.instructions
    ]


def test_check_reports_error_in_first_instruction_after_bom(tmp_path, capsys):
    target = _write(tmp_path, "bom.py", BOM + INVALID)
    assert main(["check", str(target)]) == 2
    _, err = capsys.readouterr()
    assert "bogus.thing" in err
    assert ":1:1" in err


def test_check_strict_does_not_flag_leading_bom(tmp_path, capsys):
    target = _write(tmp_path, "bom.py", BOM + SOURCE)
    assert main(["check", "--strict", str(target)]) == 0
    out, err = capsys.readouterr()
    assert "U+FEFF" not in out + err


def test_check_strict_still_flags_feff_after_the_start(tmp_path, capsys):
    target = _write(tmp_path, "mid.py", SOURCE + "# \ufeff\n".encode())
    assert main(["check", "--strict", str(target)]) == 2
    _, err = capsys.readouterr()
    assert "U+FEFF" in err


def test_inspect_json_lists_first_instruction_after_bom(tmp_path, capsys):
    target = _write(tmp_path, "bom.py", BOM + SOURCE)
    assert main(["inspect", str(target), "--json"]) == 0
    out, _ = capsys.readouterr()
    parsed = json.loads(out)
    assert parsed["instruction_count"] == 1
    assert parsed["instructions"][0]["type"] == "meta.author"
