# Architecture

Phantom is a pipeline of small, separately testable stages. Each stage consumes the previous stage's typed output; unvalidated strings never reach the runtime.

```
 source text
     │  lexer.py        line-oriented tokens: comment instruction, ws/zw block lines, hybrid header
     ▼
 tokens
     │  parser.py       decodes ws/zw payloads (encoding.py), tokenises arguments, builds the IR
     ▼
 PhantomProgram  (ir.py: frozen PhantomInstruction, Argument, SourceLocation, ParseError)
     │  validator.py    arity, types, ordering rules, strict audit
     ▼
 findings (ValidationError, severity ERROR/WARNING)  ──►  diagnostics.py  (text / SARIF)
     │  (errors stop here)
     ▼
 runtime.py            explicit handler per InstructionType; capabilities.py gates each one
     │  host.py         runs the host as a subprocess
     ▼
 exit status + diagnostics
```

## Modules

| Module | Responsibility |
| :--- | :--- |
| `grammar.py` | The authoritative registry (`INSTRUCTION_REGISTRY`), comment regex, ws/zw constants, rejected code points. Parser, validator, runtime and generator all read it. |
| `ir.py` | Enums and frozen dataclasses. Deterministic `to_dict()` / `to_json()`. |
| `lexer.py` | Classifies each line; tracks being inside a `#:ws:`/`#:zw:` block. Does no decoding. |
| `encoding.py` | Encoders/decoders for the four encodings; pure functions of text. |
| `parser.py` | Lexer tokens → `PhantomProgram`. Never imports or runs host code. |
| `validator.py` | Semantic rules (§7 of the spec) and `audit_source` for strict mode. |
| `diagnostics.py` | Rendering with caret context; SARIF 2.1.0 export. |
| `capabilities.py` | `Capability` enum, instruction→capability map, `CapabilityGrant`. |
| `runtime.py` | `PhantomRuntime`: events, counters, metadata, diagnostics; dispatch is an explicit `if inst.type == …` chain, never `eval`. |
| `host.py` | `execute_host_program`: subprocess with timeout; never modifies the file. |
| `source_map.py` | Maps lines between a source and a transformed text (used where line numbers shift). |
| `cli.py` | `check`, `inspect`, `run`, `generate`, `diff`, `verify`. |

## Public grammar helpers

`phantom.grammar` exposes five lookup helpers backed by `INSTRUCTION_REGISTRY`:
`is_known_instruction(id)` returns a boolean, `get_instruction_spec(id)` returns the
registered `InstructionSpec` or `None`, and `get_required_arg_count(id)` and
`get_total_arg_count(id)` return the argument counts or `-1` for an unknown identifier.
`list_instruction_ids()` returns a new, sorted list of every registered identifier;
changing that list does not change the registry.

## Generator (`phantom.generator`)

| Module | Responsibility |
| :--- | :--- |
| `models.py` | Request, plan, result and verdict dataclasses. |
| `prompts.py` | Builds the prompt from the real registry and the numbered source. |
| `provider.py` | `LLMProvider` interface; `GeminiProvider`, `RetryingProvider`, `StaticProvider`; `redact`. |
| `planner.py` | Parses model text into a `TransformationPlan` and validates it against the registry. |
| `transformer.py` | Placement resolution and insert-only application of a plan. |
| `validation.py` | Candidate checks: Python syntax, Phantom validity, AST preservation. |
| `equivalence.py` | `host_ast_equal` (static) and `compare_behavior` (dynamic). |
| `diff.py` | Unified diffs; `strip_phantom_layer` to compare only host layers. |
| `workflow.py` | `generate()` — orchestrates the above and returns a result; never writes files or runs code. |

The LLM is treated as an untrusted text source. Its output is parsed as JSON data, validated against the registry, and used only to choose *which registry instructions* to insert; placement is decided locally.

## Design decisions

- **One grammar.** The CLI used to contain its own fallback parser/validator; these were removed so there is a single implementation.
- **Parse ≠ run.** Parsing, checking and inspecting import nothing from the host and never write files; tests assert this.
- **Insert-only transformations.** The generator's strongest property is structural: it can only add lines, and the AST comparison verifies the host is unchanged.
- **Subprocess host.** The host runs outside the Phantom process, so a crashing or hanging host cannot corrupt runtime state, and exit code and output are captured precisely. The cost is that the Phantom runtime cannot observe inside host execution (see "Instructions are applied at initialisation" in [RUNTIME.md](RUNTIME.md)).

## Extending the instruction set

1. Add the `InstructionType` and registry entry in `ir.py` / `grammar.py`.
2. Add validation rules in `validator.py`.
3. Add the capability mapping and runtime handler.
4. Add positive and negative tests, spec text, and docs. See [CONTRIBUTING.md](../CONTRIBUTING.md).
