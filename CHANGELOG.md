# Changelog

All notable changes to Phantom are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Language:** Added `meta.license` instruction to record SPDX license identifiers.
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
