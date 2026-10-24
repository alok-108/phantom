# Changelog

All notable changes to Phantom are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Source scanning uses Python physical line endings only (LF, CRLF, CR); strict audit flags NEL, line separator, and paragraph separator.
- Encoders emit the existing `\n`, `\r`, and `\t` escapes for string arguments, preserving these characters when instructions are parsed back in comment, whitespace, and Unicode modes.
- A line that starts with `#: phantom:` but does not match the grammar is now a parse error (it used to be silently ignored); a complete instruction followed by a trailing comment is ignored with a warning.
- `generate` fails when an inserted instruction cannot be read back from the candidate (the number of Phantom instructions must grow by exactly the number planned).
- Integer arguments and instruction versions now require ASCII digits in all encodings. Arabic-Indic, fullwidth, and other Unicode digits produce parse errors instead of being accepted as numbers; malformed versions in otherwise complete comment instructions are diagnosed instead of ignored.
- The host timeout is enforced even when the host leaves a child process holding the output pipes: the whole process tree is killed on expiry (#53).
- `phantom verify` no longer reports identical programs as different when they print their own path or fail with the same traceback at shifted line numbers, and no longer reports two programs that both crash identically as equivalent (now inconclusive) (#52).
- Preserve instruction-specific messages when capability checks fail, including all missing capabilities.
- SARIF `artifactLocation.uri` values are now percent-encoded URI references: spaces, `#`, `%` and other reserved characters in paths no longer produce invalid or truncated URIs, and absolute paths (POSIX and Windows drive letters) are emitted as `file:` URIs (#55).
- `validator.py` spelled the bidirectional controls it audits as raw characters; they are now explicit code points, and a test keeps invisible/bidirectional characters out of `src/`, `scripts/` and the workflows.
- Event handlers are invoked at most once per registration when an event fires, even if they raise `TypeError` or `ValueError`; signature validation no longer retries failing handlers or replaces their original error.

### Documentation
- `docs/CI.md`: using Phantom in CI (the reusable GitHub Action and `scripts/ci_check.sh`) and Phantom's own quality gates.
- Add Hindi translations of the README and Quickstart guide.

### Added
- Reusable GitHub Action (`action.yml`) that runs `phantom check` over files and directories, plus `scripts/ci_check.sh` (#28).
- Quality gates in CI: mypy on the Linux, Windows and macOS views, a coverage gate (90 %), and property-based tests with hypothesis (#26, #29).
- Tests for runtime initialization errors, denied instructions, version metadata, and handler resolution diagnostics.
- Experimental VS Code extension (`editors/vscode`): decodes hidden whitespace and zero-width instruction blocks on hover, reports them and stray invisible or bidirectional characters in the Problems panel, and highlights comment-encoded instructions. Its decoding is cross-checked against the Python encoders through generated fixtures (#36).
- Contributor automation: comment `/take` to be assigned a `help wanted` issue (and `/release` to give it back), a daily sweep that nudges and then releases inactive claims, path-based PR labels, and a thank-you on a first merged pull request.
- Maintainer inbox: a workflow that keeps one issue up to date with CI runs waiting for approval, pull requests without a maintainer response and the size of the beginner-issue pool, and pings the maintainers once per waiting pull request.
- `meta.license(spdx)` instruction: records an SPDX license identifier as metadata (capability `cap.metadata`).

### Security
- Instruction lines are matched in linear time: a crafted line (for example `#: phantom:0.1.0 a.b(` followed by a few thousand spaces) used to take minutes to parse because the pattern backtracked cubically (#78).
- Opt-in security controls for `phantom run`: `--deny CAP` / `--allow-only CAP` (also on `check` and `inspect`) enforce a capability policy before anything runs (#30), and `--handlers-from DIR` / `--allow-handler PATTERN` decide which `event.on` handler modules may be imported, before importing them (#31).

## [0.1.1] — 2026-10-21

Thanks to @jez-elijah (tests for `generate --stdin`, prompts and consent, #39) and @dbdefault (`phantom diff --host-only`, #40) for their first contributions.

### Changed
- The repository moved to https://github.com/hayagrivai-labs/phantom (old links redirect). Dependabot is configured to raise minimum versions only when needed.

### Added
- README demo and "Why / Try it" sections, a generated terminal demo and social preview image (`scripts/build_assets.py`), and a welcome workflow that greets first-time contributors.
- `phantom diff --host-only` compares the Python host layer without Phantom instructions, without executing or modifying either file.
- CLI: `--timeout` option for `phantom run` to configure host program execution timeout (defaults to 30.0s).
- Discoverability: README badges and a "contributors welcome" banner, a dev container for Codespaces, private vulnerability reporting, pinned starter issues, and a welcome discussion.
- Maintainer and community files: `MAINTAINERS.md`, `.github/CODEOWNERS`, `.github/dependabot.yml`, `docs/RELEASING.md`, and architecture decision records in `docs/adr/`.
- Contributor tooling: `docs/CONTRIBUTOR_GUIDE.md` (how to add instructions, encodings, providers, experiments), a rewritten `CONTRIBUTING.md`, issue templates (bug, feature, language proposal, research proposal), a pull request template, and a proposal template (`docs/proposals/0000-template.md`).

## [0.1.0] — 2026-10-21

Only items that exist in this repository and are covered by the test suite are listed.

### Added
- **Language:** seven instructions — `event.declare`, `event.on`, `diagnostic.note`, `counter.create`, `counter.increment`, `meta.author`, `meta.version` — with a formal grammar in `SPECIFICATION.md`.
- **Encodings:** comment (recommended), whitespace, zero-width Unicode, hybrid (`#:phantom:hybrid` header enables de-duplication). Whitespace/zero-width/hybrid are experimental.
- **Pipeline:** lexer, parser, frozen typed IR, validator (arity, types, ordering, counter limits, event/handler rules), diagnostics with caret context, SARIF 2.1.0 export.
- **Strict audit:** `--strict` for `check` and `inspect` reports bidirectional controls, rejected invisible code points and out-of-block zero-width characters.
- **Runtime:** capability model; lifecycle events `phantom.pre_execute`, `phantom.post_execute`, `phantom.shutdown`; bounded counters; diagnostics; host run as a subprocess with a 30-second timeout.
- **CLI:** `check`, `inspect`, `run`, `generate`, `diff`, `verify`; `python -m phantom`.
- **Generator:** provider interface (Gemini provider, retrying wrapper, static test provider), prompt builder from the real registry, plan parser/validator, local placement resolution (`beginning`, `end`, `line:N`, `near:NAME`), insert-only transformer that refuses unsafe insertion points, candidate validation including an AST-equality host-preservation check, unified diff, single-run behavior comparison with explicit verdicts.
- **Docs:** specification, language guide, encodings, runtime, generator, architecture, compatibility, troubleshooting, FAQ, threat model, research status, and the Phantom C research documents (`docs/research/`).
- **Tooling:** pytest suite, Ruff configuration, `scripts/verify_release.py`, GitHub Actions workflows (tests: Python 3.10–3.13 on Ubuntu and Windows; release-checks: gates, build, clean-venv install).
- Generator rejects stale/mismatched patches (optional per-instruction `anchor`; input digest re-checked before writing) and asks for placement and encoding interactively when run on a terminal without those flags.
- `phantom generate --plan-file` for offline, reproducible generation examples; `docs/examples/README.md`.

### Fixed during development (relevant if you saw earlier prototype output)
- Zero-width blocks are emitted with a leading `# ` so the file remains valid Python (bare zero-width lines are a `SyntaxError`).
- String-path event handlers could not be resolved because `runtime.py` used `sys` without importing it.
- The parser now decodes whitespace and zero-width blocks (an early CLI fallback only read comment encoding).
- Removed a duplicate fallback parser/validator from the CLI.

### Not included (see [ROADMAP.md](ROADMAP.md), [docs/RESEARCH_STATUS.md](docs/RESEARCH_STATUS.md))
- Phantom C (long-term research vision; documented in `docs/research/PHANTOM_C.md`, not implemented).
- Firing custom events from host code, in-flow hooks, repository-wide analysis, async dispatch, sandboxing, handler allow-lists.
- Live verification of the Gemini provider; macOS testing.
