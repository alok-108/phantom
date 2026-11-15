# Encodings

Phantom represents the same instruction model in four ways. All of them decode to text of the form `phantom:<version> <identifier>(<args>)` and are parsed by the same code. The formal definitions are in [SPECIFICATION.md §6](../SPECIFICATION.md).

| Encoding | Looks like | Survives formatters/review | Needs care |
| :--- | :--- | :--- | :--- |
| Comment | `#: phantom:0.1.0 meta.author("A")` | Yes | No |
| Whitespace | `#:ws:begin` … blank-looking lines … `#:ws:end` | **No** | Yes |
| Zero-width | `#:zw:begin` / `# ‌‌‌…` / `#:zw:end` | **No** | Yes |
| Hybrid | any mix, optional `#:phantom:hybrid` header | Per part | Yes |

**Recommendation:** use comment encoding. Use the others only when you have a specific reason and understand the corruption risks below.

## Comment

```python
#: phantom:0.1.0 counter.create("runs", 10)
```

- Must be a whole line (leading indentation allowed). A trailing `# #: …`, or `#:` inside a string, is not an instruction.
- A normal comment that mentions `phantom:0.1.0` is not an instruction.
- Malformed lines (unknown identifier, bad argument syntax, trailing comma) produce a parse error with file, line and column.

## Whitespace

```text
#:ws:begin
<8 chars of space/tab per line>   ← one byte each, space = 0, tab = 1, MSB first
#:ws:end
```

The text `phantom:0.1.0 diagnostic.note("x")` becomes one 8-character line per UTF-8 byte. To Python the data lines are blank lines, so the host AST is unchanged (checked in the tests).

Things that corrupt it:

- Editors/formatters that strip trailing whitespace or blank lines (`black`, `ruff format`, many editor "save" actions).
- Converting tabs to spaces (or the reverse), or re-indenting.
- Copy-paste through systems that collapse whitespace; email, chat, web forms.
- Git `core.whitespace`/`autocrlf` settings that rewrite line endings or trim whitespace.

Corruption is detected, not guessed around: a data line that is not exactly 8 characters, an invalid UTF-8 payload, or an unterminated block is a parse error. A payload that is corrupted *into another valid payload* would not be detected; use version control review for anything that matters.

## Zero-width Unicode

```text
#:zw:begin
# <U+200B/U+200C/U+200D/U+FEFF characters>
#:zw:end
```

| Code point | Bits |
| :--- | :--- |
| U+200B | 00 |
| U+200C | 01 |
| U+200D | 10 |
| U+FEFF | 11 |

Four characters make a byte. The visible `# ` prefix is required for the file to remain valid Python: a line consisting only of zero-width characters is a `SyntaxError` in CPython. (Earlier prototype output omitted the prefix; the encoder now emits it.)

Rejected code points (soft hyphen, word joiner, Hangul fillers, …) inside a block are errors. Outside a block, `phantom check --strict` reports every zero-width, rejected-invisible and bidirectional-control character.

Things that corrupt it:

- Unicode normalisation or "clean" filters; some editors and chat tools strip zero-width characters.
- Tools that replace U+FEFF at the start of a file or line.
- Anything that re-encodes the file.
- Reviewers: the payload is invisible in most editors. That is a property of the encoding, not a security feature. Treat unexplained invisible characters as suspicious; that is exactly what `--strict` is for.

## Hybrid

A file may contain all three. Instructions are returned in source order. With the `#:phantom:hybrid` header, textually identical instructions are collapsed to their first occurrence (so a comment copy wins over a whitespace copy of the same text); without it, nothing is collapsed and duplicates are reported by validation where they are errors or warnings.

There is no heuristic fallback: a block that cannot be decoded is an error even if another encoding in the file is fine.

## Tooling

```bash
phantom inspect FILE          # decoded instructions, with encoding and location
phantom inspect --json FILE   # machine-readable
phantom check --strict FILE   # also flag invisible/bidi characters outside zero-width blocks
python scripts/build_examples.py   # regenerates docs/examples/{whitespace,unicode,hybrid}.py
```

Python API: `phantom.encoding.encode_instruction(inst, mode)`, `decode_source(text, mode)`, `WhitespaceEncoder/Decoder`, `UnicodeEncoder/Decoder`, `HybridCodec`; `phantom.parser.parse(text)` returns a typed `PhantomProgram`.

## Parsing never rewrites your file

`parse`, `check` and `inspect` read the file and never write it (this is covered by a regression test that compares bytes before and after).
