# Phantom Language Specification v0.1.0

**Version:** 0.1.0 · **Host language:** Python ≥ 3.10 · **Source encoding:** UTF-8

This document is the normative contract for the lexer, parser, validator, runtime and generator. Where the implementation and this document disagree, that is a bug in one of them and must be fixed, not worked around. Keywords **MUST**, **SHOULD**, **MAY** are used in the RFC 2119 sense.

Status labels used below: *Implemented*, *Reserved* (syntax set aside, not accepted in v0.1.0).

---

## 1. Overview

A Phantom source file is an ordinary Python file that additionally carries a second layer of typed *instructions*.

1. **Host layer** — Python source, unchanged. `python file.py` runs it as normal Python.
2. **Instruction layer** — lines or blocks matching the grammar in §4–§6. They are Python comments or whitespace-only lines, so they do not change the host program's AST.

Standard Python does **not** execute the instruction layer. Instructions take effect only when the file is processed by Phantom (`phantom run`). Nothing in this specification requires modifying a Python installation, `sitecustomize`, import hooks or the environment.

## 2. Versions and conformance

- The specification version is `0.1.0`. The set of accepted versions is `{0.1.0}`.
- Every instruction carries a version (`phantom:<semver>`). An instruction with an unsupported version **MUST** produce a validation error.
- A conforming implementation **MUST NOT** use `eval`, `exec` or a shell on any decoded instruction text, and **MUST NOT** execute host code during parsing, validation or inspection.

## 3. File format

1. UTF-8 text, extension `.py`. Undecodable bytes are replaced when reading; no normalisation (NFC/NFKC) is applied.
2. Physical source lines are delimited only by `\n`, `\r\n`, or `\r`. Other Unicode separators (including U+0085, U+2028, and U+2029) are source-line content, not line endings. Parsing **MUST NOT** rewrite the file.
3. Line and column numbers are 1-based (line) and 0-based (column, stored; shown 1-based in diagnostics). The location of an instruction decoded from a whitespace or zero-width block is the location of its block's opening marker.

## 4. Instruction syntax (comment form)

```ebnf
phantom-line  = ws0 "#:" ws0 "phantom:" semver ws1 identifier "(" ws0 [arguments] ws0 ")" ws0
identifier    = category "." name
category      = [a-z] [a-z0-9]*
name          = [a-z] [a-z0-9_]*
arguments     = argument { ws0 "," ws0 argument }
argument      = string | integer
string        = '"' { char } '"'
char          = any character except '"' and '\' | '\' ( '"' | '\' | 'n' | 't' | 'r' )
integer       = [ "-" ] digit { digit }
semver        = digit+ "." digit+ "." digit+
digit         = [0-9]
ws0 = { space | tab }     ws1 = space | tab, { space | tab }
```

Rules:

- The instruction **MUST** occupy the whole line. A trailing comment, code before `#:`, or a `#:` inside a string literal makes the line ordinary source (a trailing comment after an otherwise complete instruction is reported as a warning). A line that begins with `#: phantom:` but does not match the grammar (missing parenthesis, no argument list, ...) is a parse error, so typos are never silently ignored.
- The space after `#:` is optional.
- Arguments are literals only. Expressions (`1+1`, `"a"+"b"`), names, calls and nesting are a parse error.
- Integer literals and version components use ASCII decimal digits (`0`–`9`) only. Unicode digits, including Arabic-Indic and fullwidth digits, are not numeric syntax; they remain allowed inside string literals. An otherwise complete comment instruction with a malformed version produces a parse error rather than being ignored.
- *Reserved:* an unquoted identifier argument (`ArgumentType.IDENTIFIER`) exists in the IR but is not accepted by the v0.1.0 parser.
- Ordinary comments, including ones mentioning `phantom:0.1.0`, are never instructions unless they match the whole grammar.

## 5. Instruction set

| Identifier | Arguments | Capability | Category |
| :--- | :--- | :--- | :--- |
| `event.declare` | `name: string` | `cap.events` | Executable |
| `event.on` | `event: string`, `handler: string` | `cap.events` | Executable |
| `diagnostic.note` | `message: string` | `cap.diagnostics` | Executable |
| `counter.create` | `name: string`, `limit: integer` | `cap.counters` | Executable |
| `counter.increment` | `name: string` | `cap.counters` | Executable |
| `counter.reset` | `name: string` | `cap.counters` | Executable |
| `meta.author` | `name: string` | `cap.metadata` | Metadata only |
| `meta.license` | `spdx: string` | `cap.metadata` | Metadata only |
| `meta.tags` | `tags: string` | `cap.metadata` | Metadata only |
| `meta.version` | `version: string` | `cap.metadata` | Metadata only |

"Executable" means the runtime performs an action; it never means Python code is evaluated. Unknown identifiers are a parse error and are never dispatched.

### 5.1 `event.declare(name)`
Declares an event. **Validation:** name non-empty; redeclaring a declared or built-in event is a *warning*. **Runtime:** redeclaring raises a runtime error that is reported, not fatal.

### 5.2 `event.on(event, handler)`
Registers `handler` for `event`. **Validation:** the event **MUST** have been declared earlier in the file (or be built-in); `handler` **MUST** be a dotted path of at least two identifier segments (`pkg.mod.func`). **Runtime:** the handler is stored as text and resolved by import at *fire time*. See §9.3 for the trust consequence.

### 5.3 `diagnostic.note(message)`
Appends an `INFO` diagnostic carrying the message and the instruction's source location.

### 5.4 `counter.create(name, limit)`
Creates a counter at 0 with an upper bound. **Validation (errors):** `limit > 0`; name non-empty and not already created.

### 5.5 `counter.increment(name)`
Increments by one. **Validation:** the counter **MUST** have been created earlier in the file (error); more `counter.increment` instructions than the counter's limit is a *warning*. **Runtime:** incrementing past the limit records an error diagnostic and leaves the counter at its limit; it does not abort the program.

### 5.6 `counter.reset(name)`
Resets a previously created bounded counter to 0, keeping its limit unchanged. **Validation:** the counter **MUST** have been created earlier in the file (error); increments counted against the limit restart from the reset, so increments after a reset are warned about only if they again exceed the limit. **Runtime:** resetting a counter that does not exist raises a runtime error that is reported, not fatal.

### 5.7 `meta.author(name)`
Record the author's name. A second instruction of the same kind is a *warning*.

### 5.8 `meta.version(version)`
Record the version string. A second instruction of the same kind is a *warning*.

### 5.9 `meta.license(spdx)`
Record the SPDX license identifier (e.g., `"MIT"`). A second instruction of the same kind is a *warning*.

### 5.10 `meta.tags(tags)`
Record keyword tags describing the probes, hooks, or diagnostics in the instruction layer, as a single comma-separated string (e.g., `"telemetry,audit,compliance"`). The string is stored verbatim as metadata; it is not split into a list. A second instruction of the same kind is a *warning*.

### 5.11 Built-in events
`phantom.pre_execute`, `phantom.post_execute`, `phantom.shutdown` exist without declaration. They are the only events the runtime fires (§9). Handlers for custom events may be registered but nothing fires them in v0.1.0.

## 6. Encodings

### 6.1 Comment
The form in §4. Recommended; survives formatters and code review.

### 6.2 Whitespace
```
#:ws:begin
<line>*            each line: exactly 8 characters, each a space (0) or tab (1)
#:ws:end
```
Each data line is one byte, most significant bit first. The bytes, decoded as UTF-8, **MUST** form one or more lines of instruction text of the form `phantom:<ver> <identifier>(<args>)` (no `#:`).
Data lines are whitespace-only, hence blank lines to Python. They **MUST NOT** be trimmed, re-indented or converted (tabs↔spaces, trailing-whitespace stripping); doing so corrupts the payload.
Errors: a data line whose length is not 8, a non-UTF-8 payload, an unterminated block, empty payload.

### 6.3 Zero-width Unicode
```
#:zw:begin
# <zero-width characters>        (visible "# " prefix, then the payload)
#:zw:end
```
Each character encodes 2 bits, MSB first; 4 characters are one byte:

| Code point | Bits |
| :--- | :--- |
| U+200B ZERO WIDTH SPACE | 00 |
| U+200C ZERO WIDTH NON-JOINER | 01 |
| U+200D ZERO WIDTH JOINER | 10 |
| U+FEFF ZERO WIDTH NO-BREAK SPACE | 11 |

- The `# ` prefix is **REQUIRED in files meant to run as Python**: a line made only of zero-width characters is a `SyntaxError` ("invalid non-printable character"). Only zero-width and rejected invisible characters on a data line are payload; the prefix and any other visible text are ignored.
- Decoding is strict: a code point in the *rejected* set (soft hyphen U+00AD, U+034F, U+061C, U+115F, U+1160, U+17B4, U+17B5, U+180E, U+2060–U+2064, U+206A–U+206F) inside a block is an error.
- Normalising, stripping or re-encoding the file may remove or alter these characters. Zero-width encoding is **not** a security mechanism.

### 6.4 Hybrid
A file may mix all three. The optional header `#:phantom:hybrid` enables hybrid de-duplication.
- Instructions are returned in source order.
- With the header, textually identical instructions collapse to the first occurrence, so precedence on equal text is **comment, then whitespace, then zero-width**. Without the header, nothing is collapsed.
- Different instructions never "conflict": they are all kept. Conflicts such as redeclaration are reported by validation (§7), not resolved silently.

## 7. Validation

Performed on the whole program before anything runs, in source order. **Errors** block execution; **warnings** do not.

| # | Rule | Severity |
| :--- | :--- | :--- |
| V1 | Version is supported | error |
| V2 | Identifier is in the registry (else parse error) | error |
| V3 | Argument count equals the registry arity | error |
| V4 | Argument types match | error |
| V5 | `counter.create` limit > 0; counter names unique | error |
| V6 | `counter.increment` / `counter.reset` references a created counter | error |
| V7 | `event.on` references a declared/built-in event; handler is a dotted path | error |
| V8 | Redeclared event; duplicate `meta.*`; static increments exceed limit | warning |
| V9 | Block markers are terminated; payloads decode | parse error |

**Strict audit** (`--strict`, optional): reports as errors any bidirectional control (U+202A–U+202E, U+2066–U+2069, U+200E, U+200F), any rejected invisible code point, and any zero-width payload character found *outside* a `#:zw:` block. It does not detect homoglyphs.

## 8. Errors

1. **ParseError** — lexing/decoding/argument syntax; unknown identifier; unterminated block.
2. **ValidationError** — semantic rules in §7, plus strict-audit findings.
3. **RuntimeError** — failures while initialising or running: duplicate declaration, unresolved handler, handler exception, counter limit, missing capability. Runtime errors are reported as diagnostics or warnings and, except for host failure, do not change the host exit code.

## 9. Runtime contract (`phantom run FILE [-- ARGS...]`)

### 9.1 Lifecycle
1. Read and parse the file (no execution).
2. Validate. If any error exists: print it, exit **2**, run nothing.
3. Create the runtime with the default capability grant.
4. **Initialise:** process *every* instruction in source order — declare events, register handlers, create counters, apply increments and resets, record notes and metadata. Capability failures and runtime errors are reported as warnings.
5. Fire `phantom.pre_execute(host_file, args)`.
6. Run the host as a subprocess (`sys.executable FILE ARGS…`, 30 s timeout, UTF-8). Stdout, stderr and exit code are captured.
7. Fire `phantom.post_execute(host_file, result)`.
8. Fire `phantom.shutdown()`.
9. Print captured host stdout/stderr, then Phantom diagnostics. Exit with the **host's exit code** (124 on timeout).

### 9.2 Consequences to be aware of
- Instruction effects are applied at **initialisation**, not when execution reaches the line where the instruction is written. `counter.increment` is a statement about the program, not a hook in its control flow.
- Handlers run in the Phantom process, in registration order; a handler's exception becomes an error diagnostic and the next handler still runs. Handlers receive only the keyword arguments they declare.
- Handler output appears before the host's captured output.
- Line numbers refer to the original file; Phantom does not rewrite it, so no source map is needed for host tracebacks.

### 9.3 Trust
Resolving a handler path imports a module (`importlib.import_module`), which executes that module's top-level code in the Phantom process. A handler path in a file therefore has the authority of an import. Only run files you trust. The host's directory and the current directory are placed on `sys.path` for resolution.

### 9.4 Capability policy and handler allow-list (opt-in)
By default `phantom run` grants all five capabilities and allows any importable handler. Two opt-in restrictions exist:

- **Capability policy:** `--deny CAP` (repeatable) removes a capability; `--allow-only CAP` (repeatable) replaces the default set, and `--deny` is applied on top. `CAP` is `cap.events` or just `events`. The policy is checked **statically**: an instruction that needs a denied capability is a validation error naming the instruction and capability, so nothing runs. If `cap.stdio` is denied the host is not started (exit 2). `phantom check` accepts the same flags (to enforce a policy in CI) and `phantom inspect` marks the instructions a policy would block (`blocked_by_policy` in `--json`).
- **Handler allow-list:** `--handlers-from DIR` (repeatable) and `--allow-handler PATTERN` (repeatable, `fnmatch` against the dotted path, e.g. `myapp.hooks.*`). When either is given, a handler is imported only if it matches a pattern or its top-level module lives inside one of the directories. The decision is made **before** importing (the top-level module is located with `importlib.util.find_spec`, which does not execute it); a rejected handler becomes an `ERROR` diagnostic and its module is never imported. Installed packages and the standard library are rejected unless a pattern allows them. Python callables registered through the API are not restricted.

## 10. Host isolation
- Parsing, `check` and `inspect` read text only.
- Phantom never adds imports, globals or decorators to the host and never edits the host file. `phantom generate` writes only a *separate* candidate file, and only when `--output` is given.

## 11. Versioning
Semantic Versioning. Minor releases add instructions or encodings compatibly; major releases may change syntax or lifecycle semantics.

## 12. Forward compatibility
A v0.1.0 tool encountering an unknown identifier or version reports an error for that line and continues scanning the rest of the file. Future namespaces (e.g. `invariant.*`, `timer.*`, `trace.*`) are *Proposed*, not part of this version.

## 13. Unsupported in v0.1.0
Python expressions in arguments; nested instructions; identifier arguments; instructions in languages other than Python; multi-file/cross-module graphs; async or thread-safe dispatch; firing custom events from host code.
