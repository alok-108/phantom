# Changelog

All notable changes to Phantom are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- Added instruction kind classification (`executable` or `metadata-only`) to `phantom inspect` text and JSON output.

### Added
- Bounded counter lifecycle example (`docs/examples/counters.py`) demonstrating `counter.create`, `counter.increment`, `counter.decrement`, `counter.reset`, and boundary handling (#262).
- Nushell tab completion script (`scripts/completions/phantom.nu`) for subcommands and flags (#264).
- TextMate syntax definition (`scripts/syntax/phantom.tmLanguage.json`) for the Phantom instruction layer (#263).
- Simplified Chinese quickstart guide (`docs/zh-CN/QUICKSTART.md`) (#153).
- `phantom diff --exit-code` returns `1` when differences exist and `2` on usage or file errors, including with `--host-only`; comparisons without the flag keep their existing exit codes (#229).
- French quickstart guide (`docs/fr/QUICKSTART.md`) (#173).
- Emacs major mode (`scripts/syntax/phantom-mode.el`) for syntax highlighting (#185).
- PowerShell tab completion script (`scripts/completions/phantom.ps1`) for subcommands and flags (#184).

### Fixed
- `audit_source` detects and reports nested or duplicate whitespace and zero-width block begin markers (`#:ws:begin` and `#:zw:begin`) (#239).
- Generation workflow clears stale model-provided anchors when overriding `placement_line` to local target placement, preventing false patch mismatch errors (#226).
- `GeminiProvider.complete` accesses `response.text` inside the error-handling block, properly catching and redacting `ValueError` from blocked or empty model responses (#222).
- `inspect_encoding` matches `#:phantom:hybrid` on whole physical lines only, preventing spurious hybrid mode detection when mentioned in comments or documentation (#221).
- `_invoke_callback` aligns positional-only arguments when earlier positional parameters with default values are omitted from the event payload (#248).
- `increment_counter` and `decrement_counter` check whether `cap.diagnostics` is granted before recording boundary diagnostics, preventing unhandled `CapabilityError` when diagnostics capability is denied (#249).
- `PhantomRuntime.execute_host` appends the host directory to `sys.path` rather than prepending it, preventing local scripts from shadowing standard-library modules during lifecycle hooks (#216).
- `CapabilityGrant` implements `__eq__` and `__hash__`, so grants with identical capability sets compare equal (#227).
- `execute_host_program` validates that `timeout` is a positive and finite number, raising `ValueError` on non-positive or non-finite values (#241).
- `phantom run` preserves Windows line endings in host output without adding blank lines (#238).
- The lexer falls back to scanning lines when Python's tokenizer raises a Unicode decoding error (#237).
- `apply_plan` no longer rejects a plan that inserts at the end of the file when its anchor names the last non-empty line: the anchor is now checked against that line instead of the non-existent line `total + 1`, so `--placement end` plans with an anchor are accepted while a mismatched anchor is still rejected (#137).
- `phantom check` omits the empty diagnostic summary when a file fails to load (#224).
- Validator no longer cascades spurious "before it is created" errors when `counter.create` has an invalid limit (#182).
- `SourceMap` no longer overwrites default line mappings with file-scoped mappings in multi-file source maps (#172).
- `audit_source` now detects and reports stray or unclosed whitespace block markers (`#:ws:begin` / `#:ws:end`) (#183).
- String literals now reject unrecognized escape characters and malformed `\x` hex escapes per Specification section 4 (#181).
- `parse_plan` now validates that `instructions`, `limitations`, and instruction `arguments` are lists, raising `ValueError` instead of unhandled `TypeError` on invalid model output (#166).
- Subcommands like `check`, `inspect`, `diff`, and `verify` now preserve positional arguments following `--` instead of stripping them (#165).
- Nano syntax highlighting includes the canonical `meta.tags` instruction alongside the other metadata keywords (#170).
- `decode_source` now raises `ValueError` for unterminated whitespace and zero-width blocks when decoding those modes explicitly (#168).
- `phantom verify` no longer lets the programs share Phantom's real stdin: the original consumed piped input and the candidate got EOF, so identical programs that read stdin were reported as different (and an interactive terminal was prompted twice). The default case and any case without `--stdin-file` now get an empty stdin; `phantom run` still passes stdin through (#82).
- `phantom check` accepts one or more files so pre-commit-style invocations that pass every changed path at once no longer fail with "unrecognized arguments" (#101).
- Property-based tests include all Unicode line separators after the lexer/decoder fixes, with explicit round-trip coverage in every encoding (#87).
