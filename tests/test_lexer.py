"""Tests for the Phantom lexer."""

from __future__ import annotations

from phantom.lexer import TokenType, tokenize


def _types(source):
    return [t.type for t in tokenize(source)]


def test_empty_source_has_only_eof():
    assert _types("") == [TokenType.EOF]


def test_plain_python_is_source_lines():
    assert _types("x = 1\ny = 2\n") == [TokenType.SOURCE_LINE] * 2 + [TokenType.EOF]


def test_comment_instruction_token_has_location():
    tok = tokenize('    #: phantom:0.1.0 meta.author("A")\n')[0]
    assert tok.type == TokenType.COMMENT_INSTRUCTION
    assert (tok.line, tok.column) == (1, 4)


def test_lookalike_comments_are_source():
    for line in ['# phantom:0.1.0 meta.author("A")', "#: hello", 'x = 1  # #: phantom:0.1.0 a.b("x")']:
        assert tokenize(line)[0].type == TokenType.SOURCE_LINE


def test_space_after_marker_is_optional():
    assert tokenize('#:phantom:0.1.0 meta.author("A")')[0].type == TokenType.COMMENT_INSTRUCTION


def test_ws_block_tokens():
    src = "#:ws:begin\n \t\n#:ws:end\n"
    assert _types(src) == [
        TokenType.WS_BEGIN,
        TokenType.WS_DATA_LINE,
        TokenType.WS_END,
        TokenType.EOF,
    ]


def test_zw_block_tokens():
    src = "#:zw:begin\n# ​‌\n#:zw:end\n"
    assert _types(src) == [
        TokenType.ZW_BEGIN,
        TokenType.ZW_DATA_LINE,
        TokenType.ZW_END,
        TokenType.EOF,
    ]


def test_markers_inside_blocks_do_not_nest():
    src = "#:ws:begin\n#:zw:begin\n#:ws:end\n"
    assert _types(src)[1] == TokenType.SOURCE_LINE


def test_hybrid_header():
    assert tokenize("#:phantom:hybrid\n")[0].type == TokenType.HYBRID_HEADER


def test_crlf_line_endings():
    toks = tokenize('x = 1\r\n#: phantom:0.1.0 meta.author("A")\r\n')
    assert [t.type for t in toks[:2]] == [TokenType.SOURCE_LINE, TokenType.COMMENT_INSTRUCTION]

def test_instruction_inside_docstring_is_source():
    src = (
        'def f():\n'
        '    """Docs.\n'
        '\n'
        '    Example:\n'
        '\n'
        '#: phantom:0.1.0 counter.create("hits", 3)\n'
        '    """\n'
        '#: phantom:0.1.0 counter.create("real", 1)\n'
    )
    types = _types(src)
    assert types[4] == TokenType.SOURCE_LINE
    assert types[-2] == TokenType.COMMENT_INSTRUCTION


def test_ws_marker_inside_multiline_string_is_source():
    src = 's = """\n#:ws:begin\n \t\n#:ws:end\n"""\n'
    assert TokenType.WS_BEGIN not in _types(src)


def test_instruction_in_untokenizable_file_falls_back_to_line_based():
    src = 'def f(:\n#: phantom:0.1.0 counter.create("broken", 1)\n'
    assert _types(src)[1] == TokenType.COMMENT_INSTRUCTION
