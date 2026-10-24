"""Every command rejects a non-UTF-8 source file with one clear message (#54)."""

from __future__ import annotations

import pytest

from phantom.cli import main

_LATIN1 = b"# caf\xe9\nprint(1)\n"
_OK = b"print(1)\n"


@pytest.fixture
def files(tmp_path):
    bad = tmp_path / "latin1.py"
    bad.write_bytes(_LATIN1)
    ok = tmp_path / "ok.py"
    ok.write_bytes(_OK)
    return str(bad), str(ok)


@pytest.mark.parametrize(
    "argv",
    [
        ["check", "{bad}"],
        ["check", "{bad}", "--strict"],
        ["check", "{bad}", "--format", "sarif"],
        ["inspect", "{bad}"],
        ["inspect", "{bad}", "--json"],
        ["verify", "{bad}", "{ok}"],
        ["verify", "{ok}", "{bad}"],
        ["generate", "{bad}", "--intent", "x", "--dry-run"],
        ["diff", "{bad}", "{ok}"],
        ["diff", "{ok}", "{bad}", "--host-only"],
    ],
)
def test_non_utf8_file_is_a_clean_error(files, argv, capsys):
    bad, ok = files
    ret = main([a.format(bad=bad, ok=ok) for a in argv])
    out, err = capsys.readouterr()
    assert ret == 1
    assert err.strip() == f"Error: '{bad}' is not valid UTF-8 (byte 0xe9 at position 5)"
    assert "Traceback" not in out + err


def test_position_counts_a_leading_bom(tmp_path, capsys):
    bad = tmp_path / "bom.py"
    bad.write_bytes(b"\xef\xbb\xbf" + _LATIN1)
    assert main(["check", str(bad)]) == 1
    assert "(byte 0xe9 at position 8)" in capsys.readouterr().err


def test_valid_utf8_still_works(files, tmp_path, capsys):
    _, ok = files
    bom = tmp_path / "bom_ok.py"
    bom.write_bytes(b"\xef\xbb\xbf" + "# café\r\nprint(1)\r\n".encode())
    assert main(["check", str(bom)]) == 0
    assert main(["inspect", str(bom)]) == 0
    assert main(["diff", ok, str(bom)]) == 0
    assert "Error" not in capsys.readouterr().err
