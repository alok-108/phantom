"""Generate editors/vscode/test/fixtures.json from the real Python encoders.

The VS Code extension re-implements decoding in JavaScript. These fixtures are produced by the
Python implementation (the source of truth), so `node --test` in editors/vscode and the Python
test-suite together keep the two in agreement:

    python scripts/gen_vscode_fixtures.py          # rewrite the file
    pytest tests/test_vscode_fixtures.py           # fails when the committed file is stale

The output is plain ASCII (invisible characters appear as JSON escapes), so no hidden character
is ever stored in the repository.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from phantom.encoding import UnicodeEncoder, WhitespaceEncoder  # noqa: E402
from phantom.parser import parse  # noqa: E402
from phantom.validator import audit_source  # noqa: E402

OUTPUT = ROOT / "editors" / "vscode" / "test" / "fixtures.json"

BACKSLASH = chr(92)
NEWLINE = chr(10)
ZWSP, ZWNJ, ZWJ, BOM = (chr(c) for c in (0x200B, 0x200C, 0x200D, 0xFEFF))
WORD_JOINER = chr(0x2060)
RLO = chr(0x202E)


def _instruction_texts() -> dict[str, str]:
    accented = "h" + chr(0xE9) + "llo"
    return {
        "simple": 'phantom:0.1.0 meta.author("Ada")',
        "integer": 'phantom:0.1.0 counter.create("hits", 100)',
        "negative": 'phantom:0.1.0 counter.create("n", -3)',
        "unicode text": 'phantom:0.1.0 diagnostic.note("'
        + accented
        + " "
        + chr(0x2713)
        + " "
        + chr(0x65E5)
        + chr(0x672C)
        + " "
        + chr(0x1F600)
        + '")',
        "escapes": 'phantom:0.1.0 diagnostic.note("a' + BACKSLASH + "nb" + BACKSLASH + '"c")',
        "two instructions": 'phantom:0.1.0 counter.create("n", 3)'
        + NEWLINE
        + 'phantom:0.1.0 counter.increment("n")',
    }


def _block_lines(block: str) -> list[str]:
    return block.split(NEWLINE)


def _python_messages(lines: list[str]) -> list[str]:
    program = parse(NEWLINE.join(lines) + NEWLINE, "<fixture>")
    return [e.message for e in program.errors]


def build() -> dict[str, object]:
    cases = []
    for name, text in _instruction_texts().items():
        cases.append(
            {
                "name": name,
                "instructions": text.split(NEWLINE),
                "whitespace": _block_lines(WhitespaceEncoder.encode_block(text)),
                "zero_width": _block_lines(UnicodeEncoder.encode_block(text)),
            }
        )

    ws_ok = WhitespaceEncoder.encode(_instruction_texts()["simple"])
    zw_ok = UnicodeEncoder.encode(_instruction_texts()["simple"])
    broken = {
        "whitespace line too short": ["#:ws:begin", " \t \t", "#:ws:end"],
        "whitespace block without data": ["#:ws:begin", "#:ws:end"],
        "whitespace invalid utf-8": ["#:ws:begin", "\t" * 8, "#:ws:end"],
        "whitespace unterminated": ["#:ws:begin", *ws_ok],
        "zero-width incomplete group": ["#:zw:begin", "# " + zw_ok[:-1], "#:zw:end"],
        "zero-width rejected code point": ["#:zw:begin", "# " + zw_ok + WORD_JOINER, "#:zw:end"],
        "zero-width block without data": ["#:zw:begin", "# nothing here", "#:zw:end"],
        "zero-width unterminated": ["#:zw:begin", "# " + zw_ok],
    }
    invalid = [
        {"name": name, "lines": lines, "python_errors": _python_messages(lines)}
        for name, lines in broken.items()
    ]

    stray_sources = {
        "zero-width in code": ["x = 1", "y = 2" + ZWSP, "z = 3"],
        "word joiner in a comment": ["# note" + WORD_JOINER, "pass"],
        "bidi override": ["value = 'a" + RLO + "b'"],
        "payload inside a zw block is allowed": ["#:zw:begin", "# " + ZWSP + ZWNJ + ZWJ + BOM, "#:zw:end"],
        "bidi inside a zw block is still reported": ["#:zw:begin", "# " + ZWSP + RLO, "#:zw:end"],
        "astral character before the finding": ["s = '" + chr(0x1F600) + "'" + ZWJ],
        "clean": ["def f():", "    return 1"],
    }
    stray = []
    for name, lines in stray_sources.items():
        findings = audit_source(NEWLINE.join(lines) + NEWLINE, "<fixture>")
        # Python columns count code points; the extension reports UTF-16 offsets. They only
        # differ after an astral character, which the dedicated case below pins down explicitly.
        expected = [[f.source.line, _utf16_offset(lines[f.source.line - 1], f.source.column)] for f in findings]
        stray.append({"name": name, "lines": lines, "expected": expected})

    return {"cases": cases, "invalid": invalid, "stray": stray}


def _utf16_offset(line: str, code_point_index: int) -> int:
    return len(line[:code_point_index].encode("utf-16-le")) // 2


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=True) + NEWLINE,
        encoding="utf-8",
        newline=NEWLINE,
    )
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
