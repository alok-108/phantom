"""Phantom's own source must not contain the characters it warns about.

Invisible and bidirectional characters embedded in source are exactly the "Trojan Source"
problem `phantom check --strict` exists to find, so the code that handles them spells them
as explicit code points (``chr(0x202E)``) and a reviewer can read every line.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCANNED = [
    *sorted((ROOT / "src").rglob("*.py")),
    *sorted((ROOT / "scripts").rglob("*.py")),
    *sorted((ROOT / ".github").rglob("*.yml")),
    ROOT / "action.yml",
    ROOT / "pyproject.toml",
]
# Categories: Cf (format: zero-width, bidi), Zl/Zp (line and paragraph separators),
# Cc (control) except the ordinary whitespace controls.
SUSPICIOUS_CATEGORIES = {"Cf", "Zl", "Zp", "Cc"}
ALLOWED_CONTROLS = {"\n", "\r", "\t", "\x0c"}


def _suspicious(text: str) -> list[tuple[int, str]]:
    found = []
    for line_no, line in enumerate(text.split("\n"), start=1):
        for ch in line:
            if unicodedata.category(ch) in SUSPICIOUS_CATEGORIES and ch not in ALLOWED_CONTROLS:
                found.append((line_no, f"U+{ord(ch):04X}"))
    return found


def test_the_scanner_itself_finds_hidden_characters():
    assert _suspicious("a" + chr(0x200B) + "b\nc" + chr(0x202E)) == [(1, "U+200B"), (2, "U+202E")]
    assert _suspicious("plain text\twith\r\nwhitespace") == []


def test_project_source_contains_no_invisible_or_bidirectional_characters():
    problems = {}
    for path in SCANNED:
        if not path.exists():
            continue
        found = _suspicious(path.read_text(encoding="utf-8"))
        if found:
            problems[str(path.relative_to(ROOT))] = found
    assert problems == {}, f"hidden characters in project files: {problems}"
