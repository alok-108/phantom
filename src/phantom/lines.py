"""Helpers for Python source's physical line boundaries."""
from __future__ import annotations


def split_physical_lines(text: str, keepends: bool = False) -> list[str]:
    """Split only on LF, CRLF, and CR, matching Python source line boundaries.

    Like ``str.splitlines``, an empty input yields no lines and a final line
    terminator does not create an extra trailing empty line.
    """
    if not text:
        return []
    lines: list[str] = []
    start = 0
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\r" or char == "\n":
            end = index + 1
            if char == "\r" and end < length and text[end] == "\n":
                end += 1
            lines.append(text[start:end] if keepends else text[start:index])
            start = end
            index = end
        else:
            index += 1
    if start < length:
        lines.append(text[start:])
    return lines
