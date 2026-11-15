"""Instruction lines must be matched in linear time, and with the same language as before.

The original pattern ended in ``\\(\\s*(.*?)\\s*\\)\\s*$``; on a line like
``#: phantom:0.1.0 a.b(`` followed by a few thousand spaces it needed minutes to reject.
Since `phantom check` is meant to run on pull requests from forks, that was a denial of service.
"""

from __future__ import annotations

import re
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from phantom.cli import main
from phantom.grammar import (
    COMMENT_LINE_PATTERN,
    COMMENT_VERSION_CANDIDATE_PATTERN,
    INSTRUCTION_TEXT_PATTERN,
)
from phantom.parser import parse

# The previous implementation, kept only as the reference for the parity tests below.
_OLD_COMMENT = re.compile(
    r"^(\s*)#:\s*phantom:([0-9]+\.[0-9]+\.[0-9]+)\s+"
    r"([a-z][a-z0-9]*\.[a-z][a-z0-9_]*)"
    r"\(\s*(.*?)\s*\)\s*$"
)
_OLD_CANDIDATE = re.compile(
    r"^(\s*)#:\s*phantom:(\S+)\s+"
    r"([a-z][a-z0-9]*\.[a-z][a-z0-9_]*)"
    r"\(\s*(.*?)\s*\)\s*$"
)
_OLD_TEXT = re.compile(
    r"^phantom:([0-9]+\.[0-9]+\.[0-9]+)\s+([a-z][a-z0-9]*\.[a-z][a-z0-9_]*)\(\s*(.*?)\s*\)$"
)

_ALPHABET = list('#:phantom0.1 ab_()," \t\\') + ["\x0c"]
lines = st.text(alphabet=st.sampled_from(_ALPHABET), max_size=70)
shaped = st.builds(
    lambda indent, ws1, ws2, ident, ws3, args, ws4, tail: (
        f"{indent}#:{ws1}phantom:0.1.0{ws2}{ident}({ws3}{args}{ws4}){tail}"
    ),
    st.text(" \t", max_size=3),
    st.text(" ", max_size=2),
    st.text(" \t", min_size=1, max_size=3),
    st.sampled_from(["meta.author", "a.b", "event.on", "x1.y_2", "Bad.Id", "nodot"]),
    st.text(" \t", max_size=3),
    st.text(alphabet=st.sampled_from(list('ab1,"() \\')), max_size=12),
    st.text(" \t", max_size=3),
    st.sampled_from(["", " ", "  # note", "x"]),
)


def _same(old: re.Match[str] | None, new) -> bool:
    if old is None or new is None:
        return old is None and new is None
    return all(old.group(i) == new.group(i) for i in range(1, old.re.groups + 1))


@settings(max_examples=400, deadline=None)
@given(line=st.one_of(lines, shaped))
def test_comment_pattern_accepts_exactly_what_it_used_to(line):
    assert _same(_OLD_COMMENT.match(line), COMMENT_LINE_PATTERN.match(line)), repr(line)


@settings(max_examples=400, deadline=None)
@given(line=st.one_of(lines, shaped))
def test_candidate_pattern_accepts_exactly_what_it_used_to(line):
    assert _same(_OLD_CANDIDATE.match(line), COMMENT_VERSION_CANDIDATE_PATTERN.match(line)), repr(line)


@settings(max_examples=400, deadline=None)
@given(text=st.one_of(lines, shaped.map(lambda s: s.split("#:", 1)[-1].strip())))
def test_decoded_text_pattern_accepts_exactly_what_it_used_to(text):
    assert _same(_OLD_TEXT.match(text), INSTRUCTION_TEXT_PATTERN.match(text)), repr(text)


def test_fullmatch_is_available_and_consistent():
    line = '#: phantom:0.1.0 meta.author("a")'
    assert COMMENT_LINE_PATTERN.fullmatch(line).group(4) == '"a"'
    assert COMMENT_LINE_PATTERN.fullmatch(line + " tail") is None


N = 200_000
HEAD = "#: phantom:0.1.0 meta.author("
ADVERSARIAL = {
    "spaces after an unclosed parenthesis": HEAD + " " * N,
    "whitespace around a missing ')'": "#:" + " " * N + "phantom:0.1.0 a.b(" + " " * N,
    "spaces before the last character": HEAD + '"a"' + " " * N + "x",
    "tabs before the last character": HEAD + '"a"' + "\t" * N + "x",
    "many closing parentheses": HEAD + ")" * N,
    "closing parenthesis then spaces": HEAD + '"a")' + " " * N,
    "long version candidate": "#: phantom:" + "1" * N + " a.b()",
    "indentation only": " " * N + "#: phantom:0.1.0 a.b(",
    "alternating ') '": HEAD + ") " * N + "x",
}


@pytest.mark.parametrize("name", sorted(ADVERSARIAL))
def test_adversarial_line_is_parsed_in_well_under_a_second_or_two(name):
    source = ADVERSARIAL[name] + "\n"
    started = time.perf_counter()
    parse(source, "<adversarial>")
    elapsed = time.perf_counter() - started
    # The old implementation needed minutes for several of these; linear time is a few ms.
    assert elapsed < 5.0, f"{name}: {elapsed:.1f}s for {len(source)} characters"


def test_check_command_survives_a_hostile_file(tmp_path):
    path = tmp_path / "hostile.py"
    path.write_text(ADVERSARIAL["whitespace around a missing ')'"] + "\n", encoding="utf-8")
    started = time.perf_counter()
    assert main(["check", str(path)]) == 2  # a malformed instruction is an error
    assert time.perf_counter() - started < 5.0
