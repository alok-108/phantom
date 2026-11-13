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
