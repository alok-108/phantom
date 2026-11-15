# Compatibility

## Tested versus claimed

| Item | Declared | Actually tested here |
| :--- | :--- | :--- |
| Python 3.13 | supported | Yes — full test suite, Windows 11 (CPython 3.13.1) |
| Python 3.10, 3.11, 3.12, 3.13 | supported (`requires-python >= 3.10`) | Yes — GitHub Actions `tests` workflow, all 8 jobs passed on the first push (commit `f61f342`) |
| Windows | supported | Yes — local development and CI (`windows-latest`) |
| Linux | supported | Yes — CI (`ubuntu-latest`) |
| macOS | expected to work | **Not tested** |

"Yes" means a run was observed. macOS is unverified. The CI results are for the test suite; the `release-checks` workflow (consistency gates, build, clean-venv install and CLI smoke test on Ubuntu / Python 3.12) also passed when triggered manually.

## Host language

Python only. Compiled-language hosts are the subject of the [Phantom C research vision](research/PHANTOM_C.md) and are not implemented.

## Encoding compatibility

| Tool / action | Comment | Whitespace | Zero-width |
| :--- | :--- | :--- | :--- |
| Python interpreter (`python file.py`) | ignored | ignored (blank lines) | ignored (comment) |
| `ast` / `tokenize` | comments | blank lines | comments |
| Code formatters (black, ruff format) | kept | **may strip** | usually kept; unverified per tool |
| Trailing-whitespace stripping | kept | **destroyed** | kept |
| Tabs↔spaces conversion | kept | **destroyed** | kept |
| Unicode normalisation / invisible-character filters | kept | kept | **may be destroyed or rejected** |
| Git `autocrlf` | kept | kept | kept (line endings are accepted either way) |

Formatter and editor rows other than the first three are expectations from how those tools are documented to behave, not measurements. Use `phantom check` after any automated rewrite.

## Line endings and Unicode

LF and CRLF are accepted. Source is read as UTF-8 (undecodable bytes replaced); there is no Unicode normalisation. Windows consoles with legacy code pages may mis-render non-ASCII diagnostics; set `PYTHONUTF8=1`.

## Dependencies

Core: standard library only. Optional `[llm]`: `google-genai>=1.0.0` (call shape verified against 2.32.0). Dev: `pytest`, `pytest-cov`, `ruff`.

## Known limitations

- No sandboxing of the host or of handler imports.
- `phantom verify` compares one run; see [GENERATOR.md](GENERATOR.md).
- Instruction effects are applied at initialisation, not at their source line.
- Custom events cannot be fired from host code.
- No cross-file analysis; no async/thread-safe dispatch.
