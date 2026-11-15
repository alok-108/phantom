"""Phantom generator diff helpers.

Unified diffs between original and candidate source, and a way to strip the
Phantom instruction layer so the remaining host layer can be compared.
"""

from __future__ import annotations

import difflib

from phantom.lexer import TokenType, tokenize
from phantom.lines import split_physical_lines

_LAYER_TOKENS = frozenset(
    {
        TokenType.COMMENT_INSTRUCTION,
        TokenType.HYBRID_HEADER,
        TokenType.WS_BEGIN,
        TokenType.WS_END,
        TokenType.WS_DATA_LINE,
        TokenType.ZW_BEGIN,
        TokenType.ZW_END,
        TokenType.ZW_DATA_LINE,
    }
)


def unified_diff(
    original: str,
    candidate: str,
    from_name: str = "original",
    to_name: str = "candidate",
) -> str:
    """Return a unified diff between two source texts ('' when identical)."""
    return "".join(
        difflib.unified_diff(
            split_physical_lines(original, keepends=True),
            split_physical_lines(candidate, keepends=True),
            fromfile=from_name,
            tofile=to_name,
        )
    )


def strip_phantom_layer(source: str) -> str:
    """Remove every line that belongs to the Phantom instruction layer."""
    drop = {tok.line for tok in tokenize(source) if tok.type in _LAYER_TOKENS}
    kept = [
        line for idx, line in enumerate(split_physical_lines(source, keepends=True), start=1)
        if idx not in drop
    ]
    return "".join(kept)


def host_layer_diff(original: str, candidate: str) -> str:
    """Diff of only the host layers; empty when the host code is untouched."""
    return unified_diff(
        strip_phantom_layer(original),
        strip_phantom_layer(candidate),
        "original (host layer)",
        "candidate (host layer)",
    )


_ADD = "\033[32m"
_REMOVE = "\033[31m"
_HUNK = "\033[36m"
_RESET = "\033[0m"


def format_diff_colored(diff_text: str, colored: bool = True) -> str:
    """Colorize a unified diff, or return it unchanged when ``colored`` is False.

    Added lines are green, removed lines red, and hunk headers cyan; the
    ``---``/``+++`` file headers take the color of their first character
    (``-``/``+``), and context lines stay plain. Callers only need to pass
    ``colored=False`` (for ``NO_COLOR`` / ``--no-color``) to get plain text.
    """
    if not colored:
        return diff_text
    out: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        if line.endswith("\r\n"):
            body, newline = line[:-2], "\r\n"
        elif line.endswith("\n"):
            body, newline = line[:-1], "\n"
        elif line.endswith("\r"):
            body, newline = line[:-1], "\r"
        else:
            body, newline = line, ""
        if body.startswith("+"):
            code = _ADD
        elif body.startswith("-"):
            code = _REMOVE
        elif body.startswith("@"):
            code = _HUNK
        else:
            out.append(line)
            continue
        out.append(f"{code}{body}{_RESET}{newline}")
    return "".join(out)
