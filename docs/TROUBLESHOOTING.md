# Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `phantom: command not found` | Virtualenv not active or scripts dir not on `PATH` | Activate the venv, or run `python -m phantom …` |
| `Unknown instruction identifier: 'x.y'` | Not in the registry | Use one of the eight instructions ([LANGUAGE_GUIDE.md](LANGUAGE_GUIDE.md)) |
| `Unsupported spec version '…'` | `phantom:<ver>` is not `0.1.0` | Change the version |
| `Instruction '…' takes N argument(s), got M` | Wrong arity | Check the signature |
| `Argument 2 ('limit') of 'counter.create' must be integer, got string` | `"10"` instead of `10` | Remove the quotes |
| `Cannot parse argument near …` / `Expected ',' …` | Expression, bare word or missing comma in arguments | Arguments are only `"strings"` and integers |
| `Handler registered for undeclared event 'e'` | `event.on` before/without `event.declare` | Declare it earlier in the file (or use a built-in `phantom.*` event) |
| `Handler 'h' is not a dotted module path` | `"handler"` instead of `"module.handler"` | Use `module.function` |
| `Counter 'c' incremented before it is created` | Order matters | Put `counter.create` first |
| `Cannot decode whitespace block: … has length N, expected exactly 8` | A formatter changed the block | Re-generate it (`scripts/build_examples.py` style) or switch to comment encoding |
| `Cannot decode unicode block: Unknown or non-permitted character …` | Invisible character that is not one of the four, or a non-prefix visible character in the payload | Remove it; run `phantom check --strict` |
| `SyntaxError: invalid non-printable character U+200B` when running with Python | A zero-width line without the `# ` prefix (older output) | Regenerate the block; the encoder now emits `# ` |
| `Unterminated whitespace block` / `Empty unicode block` | Missing `#:ws:end`/`#:zw:end` or no payload | Close the block / add payload |
| `Failed to resolve handler 'm.f' …` | Module not importable from the host's directory, or attribute missing | Put the module beside the host file; check names |
| `[RuntimeWarning] Event '…' has already been declared` | Duplicate `event.declare` | Remove the duplicate |
| `exceeded limit` diagnostic | More increments than the limit | Raise the limit or remove increments |
| `phantom run` hooks print before host output | Host output is captured then printed | Expected |
| Host exit code 124 | Host exceeded 30 s | Make it faster; there is no timeout flag in v0.1.0 |
| `generate`: `remote generation not authorized` | No consent given non-interactively | Pass `--allow-remote` if you accept sending source to the provider |
| `generate`: `GEMINI_API_KEY is not set` | Missing key | Set the environment variable |
| `generate`: `google-genai is not installed` | Optional extra missing | `pip install "phantom-lang[llm]"` |
| `generate`: `'f' is ambiguous (defined at lines …)` | Two definitions share a name | Use `--placement line:N` |
| `generate`: `Line N is inside a multi-line construct` | The target is within a string/bracket | Choose another line |
| `generate`: `Host code differs …` | The candidate's AST differs from the original's | The candidate is not accepted; this should not happen with the insert-only transformer and indicates a bug |
| Garbled characters on Windows | Legacy console code page | `$env:PYTHONUTF8 = "1"` |

For anything unexpected, `phantom inspect --json FILE` shows exactly what was recognised and where.
