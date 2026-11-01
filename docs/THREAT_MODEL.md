# Threat Model (v0.1.0)

Scope: the `phantom` package and CLI as shipped. Status per threat: **Addressed** (a control exists and is tested), **Partial** (reduced, with a stated gap), **Out of scope** (not defended; reasons given).

## Assets and trust boundaries

- The user's machine and files.
- Source files, which may come from untrusted parties.
- Credentials (LLM API key).
- The user's source code, which is sensitive when sent to a remote provider.

Trust boundaries: (1) file contents → parser; (2) instruction data → runtime; (3) handler path → Python import; (4) LLM response → generator; (5) source → remote provider.

## Threats

| # | Threat | Status | Controls and gaps |
| :--- | :--- | :--- | :--- |
| T1 | **Malformed source** crashes or confuses the parser | Addressed | Total grammar with explicit parse errors; unknown identifiers, bad arguments, unterminated/empty/corrupt blocks are reported, not guessed. Tests in `test_parser.py`, `test_encoding.py`. Not fuzzed. |
| T2 | **Instruction data becomes code execution** (`eval`, shell, expression arguments) | Addressed | Arguments are string/integer literals only; no `eval`/`exec` on decoded data; dispatch is an explicit handler per registry type. `test_security.py` checks that payloads like `__import__('os').system(...)` stay inert data and that expression arguments fail to parse. |
| T3 | **Handler import executes attacker code** — `event.on("x","evil.run")` imports `evil` when the event fires | **Partial** | This is inherent to "callback by dotted path". Gating: the file must be run with `phantom run`; validation requires the event to be declared and the path to be dotted; failures are isolated. **Mitigation (opt-in):** `phantom run --handlers-from DIR` / `--allow-handler PATTERN` reject a handler *before* its module is imported; `--deny`/`--allow-only` restrict capabilities statically. **Gap:** both are off by default, so a plain `phantom run` still lets any importable module be named. Only run files you trust. |
| T4 | **Unsupported / hidden Unicode** (zero-width, bidirectional "Trojan Source") used to mislead reviewers | Partial | `phantom check --strict` / `inspect --strict` report bidirectional controls, rejected invisible code points, NEL (U+0085), line separator (U+2028), paragraph separator (U+2029), and zero-width characters outside `#:zw:` blocks, with Python physical line and column coordinates. Source line boundaries are only LF, CRLF, and CR, matching Python. **Gaps:** homoglyph/confusable identifiers are not detected; strict mode is opt-in; a legitimate `#:zw:` block is by design invisible. |
| T5 | **Ambiguous encodings** (same instruction in several encodings, conflicting results) | Addressed | Deterministic source-order result; hybrid de-dup only with explicit header; no heuristic fallback; undecodable blocks are errors. |
| T6 | **Malicious source file** (DoS via huge file/long lines) | Partial | Instruction lines are matched in linear time (an earlier pattern backtracked cubically: a 8 KB line took minutes, issue #78; now covered by parity and timing tests at 200 000 characters). There is still no size limit in the parser. The generator limits input to 100 000 characters. The host has a 30 s timeout. Property-based tests (hypothesis) fuzz the parser; no dedicated fuzzer or line-length limit yet. |
| T7 | **Untrusted LLM response** (injection, malformed JSON, invented instructions, hostile placement) | Addressed | Response is parsed as JSON data only; plan is validated against the registry; model line numbers are ignored; the transformer is insert-only; candidate must parse, validate and keep an identical AST; nothing the model returns is executed. A model can still choose *legitimate* instructions you did not intend; you review the plan and diff. |
| T8 | **Malformed transformation plans** | Addressed | Type, arity, encoding, range checks; max 50 instructions; empty plan rejected. |
| T9 | **Source-code privacy** with a remote provider | Partial | No network use without a configured provider and explicit consent; refuse non-interactively without `--allow-remote`; documented that the provider processes the submitted source. **Gap:** no automatic scrubbing of secrets *inside your source* before sending. Redaction covers Phantom's own error output only. |
| T10 | **Credential leakage** | Partial | Key read from the environment only, never printed; provider errors and CLI messages pass through `redact` (key + common patterns). Best-effort pattern matching; not guaranteed. |
| T11 | **Capability misuse** | Partial | Every instruction maps to a named capability checked before execution; library users can grant a subset. **Gap:** the CLI always grants all five and the capabilities are coarse (they do not constrain which handler modules load). |
| T12 | **Accidental behavior changes** from generation | Partial | Insert-only transformer; refuses unsafe insertion points; AST-equality check; separate candidate file; original never overwritten. `verify` compares one run only. Not a proof of equivalence. |
| T13 | **Supply chain** | Partial | Core has zero runtime dependencies. Optional `google-genai` is a normal PyPI dependency; pin and review it in sensitive environments. Release checks and CI are scripted; no package signing or SBOM yet. |
| T14 | **Unsafe execution of user-supplied programs** | **Out of scope** | `phantom run` and `phantom verify` execute the program with the user's privileges. No sandbox, no resource limits beyond the timeout. Use a container/VM for untrusted code. |
| T15 | **Silent source rewriting** | Addressed | Parsing, `check`, `inspect`, `diff` never write; `generate` writes only `--output`, refuses when it equals the input. Byte-comparison tests. |
| T16 | **Global interpreter modification** | Addressed | No import hooks, `sitecustomize`, `.pth` files or environment changes. A test asserts `sys.meta_path`/`sys.path_hooks` are unchanged by parsing. Installation runs no custom code (hatchling wheel). |
| T18 | **Visible text that is silently active** (instruction-looking lines inside docstrings or multi-line strings) | Addressed | The lexer uses Python tokenization to find lines inside string literals and treats them as ordinary source, so a docstring that documents the syntax is not executed; a file that cannot be tokenized falls back to line-based lexing. Tests in `test_lexer.py`. |
| T17 | **Using the format to conceal activity from owners/monitors** | Out of scope / not supported | Not a goal. All encodings are fully decodable by `phantom inspect`. See [research/PHANTOM_C.md](research/PHANTOM_C.md). |

## Residual risks to state plainly

1. A `phantom run` of an untrusted file is as dangerous as running that file, plus handler imports.
2. Whitespace and zero-width payloads are invisible to casual review. Use `--strict` in CI for repositories that accept outside contributions.
3. AST equality shows the *Python program* is unchanged; it does not show that the added Phantom effects are desirable.

## Reporting

See [SECURITY.md](../SECURITY.md).
