# Contributor Guide: extending Phantom

This guide is for people who want to **build on the idea**: add an instruction, an encoding, an LLM provider, an example, a test, or a research experiment. It is practical and specific to this codebase. For the short version (setup, PR rules) see [CONTRIBUTING.md](../CONTRIBUTING.md).

You do not need to understand everything. Pick a lane below.

| I want to… | Difficulty | Section |
| :--- | :--- | :--- |
| Fix a bug or improve an error message | Easy | [Small fixes](#1-small-fixes-and-first-contributions) |
| Add or improve a doc, example or test | Easy | [Small fixes](#1-small-fixes-and-first-contributions) |
| Add a new **instruction** | Medium | [Add an instruction](#3-add-an-instruction) |
| Add an **LLM provider** | Medium | [Add a provider](#5-add-an-llm-provider) |
| Add or change an **encoding** | Hard | [Add an encoding](#4-add-or-change-an-encoding) |
| Improve the **generator** or **verify** | Medium–Hard | [Generator ideas](#6-improve-the-generator-and-verify) |
| Run a **visibility / Phantom C** experiment | Research | [Research](#7-research-contributions) |
| Propose a **language change** | Any | [Proposals](#8-proposing-a-language-change) |

## 0. The mental model (5 minutes)

A Phantom file is Python plus a second layer of typed instructions.

```
source text ─► lexer ─► parser ─► IR ─► validator ─► runtime ─► host subprocess
                │          │       ▲
              encoding.py ─┘       └── grammar.py (the single registry of instructions)
```

Three rules hold everywhere:

1. **`SPECIFICATION.md` is the contract.** If code and spec disagree, one of them is a bug. Language changes start in the spec.
2. **One registry.** `grammar.INSTRUCTION_REGISTRY` is the only list of instructions. The parser, validator, runtime, `inspect` and the LLM prompt all read it.
3. **Data never becomes code.** Decoded text is parsed into string/integer literals and dispatched to explicit handlers. Never `eval`, `exec` or a shell on instruction data. `scripts/verify_release.py` fails if `eval(`/`exec(` appear in `src/`.

Read [ARCHITECTURE.md](ARCHITECTURE.md) for the module map and [RUNTIME.md](RUNTIME.md) for what actually happens at `phantom run` (instructions apply at **initialisation**, before the host starts).

## 1. Small fixes and first contributions

Good first contributions that need no design discussion:

- **Typos, unclear docs, missing troubleshooting entries** (`docs/TROUBLESHOOTING.md`).
- **More tests.** Edge cases for the parser (odd Unicode, CRLF, very long lines), the transformer (more unsafe insertion points: f-strings, decorators, `async` bodies), `audit_source` (more invisible code points).
- **Better diagnostics.** Messages in `parser.py` / `validator.py` that could say what to do next.
- **New examples** in `docs/examples/` (each must be run and its output asserted in `tests/test_examples.py`).
- **Windows / Linux / macOS reports.** macOS is untested; a report of `pytest` results there is genuinely useful.
- **Unicode survey:** which invisible characters does `--strict` miss? Add them with a test.

Workflow: fork → branch → change → `ruff check src tests scripts && pytest && python scripts/verify_release.py` → PR.

## 2. Development setup

```bash
git clone https://github.com/hayagrivai-labs/phantom.git
cd phantom
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

pytest                                    # ~200 tests, a few seconds
ruff check src tests scripts
python scripts/verify_release.py          # needs Python 3.11+
phantom run docs/examples/comments.py     # try it
```

Windows: set `PYTHONUTF8=1` so non-ASCII output renders.

**Where things are**

| Area | Files | Tests |
| :--- | :--- | :--- |
| Tokens / lines | `lexer.py` | `test_lexer.py` |
| Encodings | `encoding.py`, `grammar.py` | `test_encoding.py` |
| Parsing → IR | `parser.py`, `ir.py` | `test_parser.py`, `test_ir.py` |
| Validation, strict audit | `validator.py` | `test_validator.py`, `test_security.py` |
| Runtime, events, counters | `runtime.py`, `capabilities.py`, `host.py` | `test_runtime.py`, `test_capabilities.py`, `test_host.py` |
| CLI | `cli.py`, `diagnostics.py` | `test_cli.py`, `test_examples.py` |
| Generator | `generator/*` | `test_generator.py`, `test_equivalence.py` |

## 3. Add an instruction

This is the most natural way to extend the language. Adding an instruction takes **four code edits** plus tests and docs. Worked example: a hypothetical `meta.license(spdx)` (this exact change was tried on a throwaway copy: `check`, `inspect`, `run` and all existing tests worked with only these four edits).

**Before coding**, open a *Language proposal* issue (see [§8](#8-proposing-a-language-change)) and agree: identifier, arguments, what the runtime does, what validation rejects, what capability it needs.

**Edits**

1. `src/phantom/ir.py`: add the enum member.
   ```python
   META_LICENSE = "meta.license"
   ```
2. `src/phantom/grammar.py`: add the registry entry (name, argument types, description). Argument types are `STRING` or `INTEGER` only.
   ```python
   "meta.license": InstructionSpec(
       type=InstructionType.META_LICENSE,
       arguments=(ArgumentSpec("spdx", ArgumentType.STRING, description="SPDX license id"),),
       description="Declare the license of the instruction layer.",
   ),
   ```
3. `src/phantom/capabilities.py`: map it to a capability. Prefer an existing one; a new capability needs justification in the proposal.
   ```python
   InstructionType.META_LICENSE: frozenset({Capability.METADATA}),
   ```
4. `src/phantom/runtime.py`: add a branch in `PhantomRuntime.initialize`.
   ```python
   elif inst.type == InstructionType.META_LICENSE:
       self.set_metadata("license", inst.get_string_arg(0) or "")
   ```

**Free for you:** parsing, arity/type validation, `phantom inspect` output (with capabilities), and the LLM prompt (it is generated from the registry).

**Then**

5. Extra validation rules, if any, in `validator.py` (e.g. "must be a valid SPDX id"). Errors block `phantom run`; warnings do not.
6. Tests: a positive case, a negative case per validation rule, a runtime-effect test, and an `inspect` check. Put them next to the existing ones.
7. Docs: add it to `SPECIFICATION.md` §5 (syntax, arguments, validation, runtime, errors), `docs/LANGUAGE_GUIDE.md`, `CHANGELOG.md`, and `docs/RESEARCH_STATUS.md`.
8. Ideas that don't fit these four steps (e.g. firing custom events from host code, in-flow hooks) need an architecture proposal first; see [RUNTIME.md](RUNTIME.md) "Instructions are applied at initialisation".

**Instruction ideas, roughly by size**

| Idea | Notes |
| :--- | :--- |
| `meta.license`, `meta.tag`, `meta.link` | Metadata only; tiny |
| `diagnostic.warn` / `diagnostic.error` | New severities for notes |
| `counter.reset`, `counter.assert_max` | Small runtime additions |
| `event.fire(name)` | Fire custom events at initialisation; useful with handlers |
| `invariant.assert(...)` | Needs a *safe* condition language (no `eval`!) |
| `timer.*`, `trace.span` | On the v0.2.0 roadmap |
| Host-side fire API for custom events | Architecture change; proposal required |

## 4. Add or change an encoding

Hard, because every encoding must decode to the same text form (`phantom:<ver> <id>(<args>)`) and still leave **valid Python**.

Checklist for a new encoding:

1. Define the markers, payload format and error conditions in `SPECIFICATION.md` §6 first.
2. Add encoder and decoder classes in `encoding.py` (pure functions of text) and the constants in `grammar.py`.
3. Teach `lexer.py` its tokens and `parser.py` to decode a block into instructions.
4. **Round-trip tests:** encode → decode → equal; encode → `ast.parse` succeeds; host AST unchanged.
5. **Corruption tests:** truncated block, wrong length, non-UTF-8 payload, empty block, unterminated block. Each must be a parse error, never a guess.
6. **Tooling tests:** how does it behave under tab/space conversion, trailing-whitespace stripping, `ruff format`, CRLF, Unicode normalisation? Document the result in `docs/ENCODINGS.md` and `docs/COMPATIBILITY.md`, including when it breaks.
7. Make `phantom check --strict` aware of any new invisible characters.
8. Update `scripts/build_examples.py` and add an example.

Constraint: no encoding may be designed to defeat inspection. `phantom inspect` must be able to decode everything.

## 5. Add an LLM provider

The interface is one method (`generator/provider.py`):

```python
class MyProvider(LLMProvider):
    name = "myprovider"

    def complete(self, prompt: str) -> str:
        ...  # return the model's text; raise ProviderError on failure
```

Requirements: read credentials from the environment (never print them), set a timeout, wrap errors in `ProviderError` after passing messages through `redact()`, and register the name in `get_provider()`. Keep the SDK an **optional** dependency (add an extra in `pyproject.toml`; the core must stay dependency-free, which `verify_release.py` checks).

Testing: no paid calls in unit tests. Follow `TestGeminiWiring` in `tests/test_generator.py`, which drives the provider with a fake SDK module. Please verify the provider's *current* API and model names yourself and say in the PR whether you ran it live. Don't invent model IDs.

Ideas: OpenAI-compatible endpoint, Anthropic, local models via an HTTP server, a `--provider file:` mode for recorded responses.

## 6. Improve the generator and `verify`

Safe areas with clear value:

- **More unsafe-insertion detection** in `transformer.unsafe_insertion_lines` (see its tests).
- **Better placement:** `near:Class.method`, "before first `if __name__`", "associated with event X".
- **Smarter plans:** multi-instruction dependencies (declare-before-use) checked at plan time rather than candidate time.
- **Stronger `verify`:** multiple argument/stdin cases, return-value comparison, file-effect comparison, sandboxed execution (container), environment/time/seed pinning. Keep the honest result categories; never print "equivalent" without the "one run" caveat.
- **Interactive flow:** more clarifying questions (fragments, constraints) in `cli.cmd_generate`.

Invariants to preserve (tests enforce them): the transformer only inserts lines; the original file is never overwritten; the candidate is never executed by `generate`; model output is data, never code.

## 7. Research contributions

Phantom C and visibility research are welcome **as measurement and auditability work**. Read [research/PHANTOM_C.md](research/PHANTOM_C.md), [research/OBSERVABILITY.md](research/OBSERVABILITY.md) and [research/EXPERIMENTAL_METHOD.md](research/EXPERIMENTAL_METHOD.md) first. Open a *Research proposal* issue using the template: one property, one observer, a falsifiable hypothesis, controls, error analysis, reproducible inputs, and a plan to publish negative results.

Welcome examples: "which editors/diff tools render zero-width characters?", "how do formatters treat whitespace blocks?", "can a clean-room decoder reproduce `phantom inspect` from the spec alone?", a Phantom-aware editor extension or linter.

Not accepted: techniques whose purpose is to evade antivirus/endpoint monitoring or to conceal execution from authorized system owners, and any claim of total invisibility or undetectability.

## 8. Proposing a language change

1. Open an issue with the **Language proposal** template (motivation, syntax, semantics, validation, runtime, security, compatibility).
2. For anything non-trivial, copy [proposals/0000-template.md](proposals/0000-template.md) to `docs/proposals/NNNN-short-name.md` and open a PR with just the proposal. Discussion happens there.
3. Once accepted, implement in a separate PR with spec, code, tests, docs and changelog together.

A proposal is accepted when it is specified precisely enough to implement without guessing, doesn't weaken a safety rule (§0), and has an owner.

## 9. Definition of done for a PR

- [ ] `ruff check src tests scripts` clean.
- [ ] `pytest` passes; new behavior has positive **and** negative tests; no test was weakened.
- [ ] `python scripts/verify_release.py` passes.
- [ ] Spec and docs updated (and `tests/test_examples.py` if CLI output changed).
- [ ] CHANGELOG entry under "Unreleased".
- [ ] Features labelled honestly: *Implemented / Experimental / Proposed / Hypothesis* (see [RESEARCH_STATUS.md](RESEARCH_STATUS.md)).
- [ ] No new runtime dependency in the core; optional ones go in an extra.
- [ ] Commit messages explain *why*.

## 10. Safety rules (non-negotiable)

1. No `eval`/`exec`/shell on instruction data or model output.
2. Parsing, `check`, `inspect`, `diff` never execute or rewrite files.
3. No global interpreter changes (import hooks, `sitecustomize`, startup files).
4. No network use without explicit user consent; no secrets in logs.
5. No claims beyond what is tested; state limits plainly.
6. No evasion/concealment tooling (see [research/PHANTOM_C.md](research/PHANTOM_C.md) §6).

## 11. Getting help

Open a GitHub issue or discussion with what you tried and the command output. Maintainer review aims to be constructive; small PRs get reviewed fastest.
