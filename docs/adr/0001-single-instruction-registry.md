# ADR 0001: One instruction registry is the source of truth

* Status: accepted, 2026-10-21

## Context

The parser, validator, runtime, `phantom inspect` and the LLM prompt all need to know which
instructions exist and what arguments they take. An early prototype kept a second, hand-written
parser and validator inside the CLI, and the two disagreed with each other and with the docs.

## Decision

`phantom.grammar.INSTRUCTION_REGISTRY` is the only list of instructions. Everything else reads it:

* the parser rejects identifiers that are not in the `InstructionType` enum;
* the validator derives arity and argument types from the registry entry;
* `inspect` derives capabilities from `capabilities.INSTRUCTION_CAPABILITIES`;
* the generator prompt and plan validation are built from the registry, so a model cannot invent
  an instruction by naming it.

Runtime behavior is the one place that is not data-driven: each instruction has an explicit
branch in `PhantomRuntime.initialize`, never `eval`/`exec` or a dynamic lookup of Python code.

## Consequences

* Adding an instruction takes four code edits (enum, registry, capability, runtime branch) and
  the parser, validator, `inspect` and the prompt pick it up automatically.
* A new instruction is a language change and needs a specification entry first.
* The duplicate fallback code was removed from the CLI.
