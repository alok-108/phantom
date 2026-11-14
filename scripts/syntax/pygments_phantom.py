"""Pygments lexer for Phantom dual-layer Python.

Phantom keeps ordinary Python as the host language and places a typed
instruction layer in comments, for example:

    #: phantom:0.1.0 meta.author("Payments team")
    #:ws:begin ... #:ws:end    (whitespace encoding)
    #:zw:begin ... #:zw:end    (zero-width encoding)
    #:phantom:hybrid           (hybrid-mode header)

This module is a standalone Pygments lexer. It extends Pygments' ordinary
Python lexer and adds tokens for the Phantom instruction layer. Pygments is an
optional tool dependency; when it is not installed this module raises a clear
``ImportError`` only if it is imported.

Usage from Python::

    import sys

    sys.path.insert(0, "scripts/syntax")
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments_phantom import PhantomLexer

    highlight(source, PhantomLexer(), HtmlFormatter())

See docs/INSTALLATION.md ("Editor Support") for details.
"""

from __future__ import annotations

import re

try:
    from pygments.lexer import bygroups, inherit
    from pygments.lexers.python import PythonLexer
    from pygments.token import (
        Comment,
        Keyword,
        Name,
        Number,
        Punctuation,
        String,
        Whitespace,
    )
except ImportError as exc:  # pragma: no cover - exercised only without Pygments
    raise ImportError(
        "the Phantom Pygments lexer requires Pygments; install it with "
        "'pip install pygments'"
    ) from exc


INSTRUCTION_NAMES = (
    "event.declare",
    "event.on",
    "diagnostic.note",
    "diagnostic.warn",
    "counter.create",
    "counter.increment",
    "counter.decrement",
    "counter.reset",
    "meta.author",
    "meta.version",
    "meta.license",
    "meta.tags",
)

INSTRUCTION_PATTERN = r"\b(?:" + "|".join(re.escape(name) for name in INSTRUCTION_NAMES) + r")\b"


class PhantomLexer(PythonLexer):
    """Pygments lexer for Phantom's instruction layer inside Python sources."""

    name = "Phantom"
    aliases = ["phantom", "phantom-python"]
    filenames = ["*.py"]
    mimetypes = ["text/x-phantom"]
    url = "https://github.com/alok-108/phantom"
    version_added = "0.1.1"

    tokens = {
        "root": [
            (
                r"^([ \t]*)(#:)([ \t]*)(phantom:)([0-9]+\.[0-9]+\.[0-9]+)",
                bygroups(
                    Whitespace,
                    Comment.Preproc,
                    Whitespace,
                    Comment.Special,
                    Number,
                ),
                "instruction",
            ),
            (
                r"^([ \t]*)(#:)(ws|zw)(:)(begin|end)\b",
                bygroups(
                    Whitespace,
                    Comment.Preproc,
                    Keyword,
                    Punctuation,
                    Keyword,
                ),
                "marker",
            ),
            (
                r"^([ \t]*)(#:)(phantom)(:)(hybrid)\b",
                bygroups(
                    Whitespace,
                    Comment.Preproc,
                    Comment.Special,
                    Punctuation,
                    Keyword,
                ),
                "marker",
            ),
            (
                r"^([ \t]*)(#:)([ \t]*)(?![a-z]+:)",
                bygroups(Whitespace, Comment.Preproc, Whitespace),
                "comment",
            ),
            (INSTRUCTION_PATTERN, Name.Function),
            inherit,
        ],
        "instruction": [
            (r"\n", Whitespace, "#pop"),
            (INSTRUCTION_PATTERN, Name.Function),
            (r'"(?:[^"\\\n]|\\.)*"', String.Double),
            (r"'(?:[^'\\\n]|\\.)*'", String.Single),
            (r"-?\b[0-9]+\b", Number.Integer),
            (r"[(),]", Punctuation),
            (r"[ \t]+", Whitespace),
            (r"[^\s]+", Comment.Single),
        ],
        "marker": [
            (r"\n", Whitespace, "#pop"),
            (r".+", Comment.Single),
        ],
        "comment": [
            (r"\n", Whitespace, "#pop"),
            (r".+", Comment.Single),
        ],
    }
