# ADR 0003: The generator is insert-only and treats model output as untrusted data

* Status: accepted, 2026-10-21

## Context

An LLM can be asked to "add Phantom instructions to this program", but letting it rewrite the
program risks silently changing behavior, and its output may be malformed, hostile or simply
wrong.

## Decision

* The model returns a JSON plan. It is parsed as data and validated against the registry; model
  line numbers are ignored and placement is resolved locally.
* The transformer only inserts whole lines, refuses insertion points inside multi-line strings,
  brackets and continuations, and rejects a plan whose optional `anchor` line does not match.
* A candidate is accepted only if it is valid Python, valid Phantom, and has an AST identical to
  the original's. Comments and blank lines cannot change an AST, so this is strong evidence the
  host program is unchanged.
* `generate` never executes the candidate, never overwrites the input, and writes a separate file
  only with `--output`. If the input changes during generation, nothing is written.
* A remote provider receives source only after explicit consent (`--allow-remote` or an
  interactive yes). `--plan-file` provides an offline path for tests and examples.

## Consequences

* The generator cannot refactor code, which is intended.
* `phantom verify` adds a single-run output comparison but is not a proof of equivalence.
* Providers are an optional extra; the core has no runtime dependencies.
