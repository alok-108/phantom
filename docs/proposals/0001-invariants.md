# Proposal 0001: `invariant.assert`, declarative checks that travel with the code

- **Status:** Draft (for discussion; nothing here is implemented)
- **Author:** @alok-108
- **Type:** Instruction / Runtime / CLI
- **Target version:** 0.2.0

## Summary

Add one instruction, `invariant.assert`, that states a condition about the *observable outcome of a run* ("the program exits with 0", "the counter `retries` stayed under 3", "it finished in under two seconds"). `phantom run` evaluates the conditions after the host finishes and `--fail-on-invariant` turns a violation into a failing exit status, so the same file that documents the expectation also enforces it in CI.

This is the proposed "killer use case" for the dual-layer idea: expectations live next to the code they describe, yet plain `python file.py` never sees them.

## Motivation

Today the instruction layer can count (`counter.*`), annotate (`diagnostic.note`) and label (`meta.*`), but nothing can *fail a run*. A team that wants "this script must exit 0 and take less than 5 seconds" has to put that in a separate CI script, away from the file it is about. Decorators or asserts inside the Python code would change the program itself, which is exactly what Phantom promises not to do.

```python
#: phantom:0.2.0 invariant.assert("exits cleanly", "exit_code == 0")
#: phantom:0.2.0 invariant.assert("fast enough", "duration_ms < 5000")
#: phantom:0.2.0 invariant.assert("retries bounded", "counter('retries') <= 3")

def main(): ...
```

## Specification

```
instruction = "invariant.assert" "(" string "," string ")"
```

| Argument | Type | Meaning |
| :--- | :--- | :--- |
| `name` | string | Short label shown in diagnostics; unique within the file |
| `condition` | string | An expression in the restricted language below |

### The condition language (the important part)

The condition is **data, never Python**. It is parsed with `ast.parse(condition, mode="eval")` and then walked by Phantom's own evaluator; `eval`, `exec`, `compile` and `__import__` are never called on it (this keeps `verify_release.py`'s "no eval/exec" gate meaningful). Only these node types are accepted; everything else is a validation error *before* the program runs:

- literals: integers, floats, strings, `True`, `False`, `None`;
- comparisons (`== != < <= > >=`, `in`, `not in`), `and`, `or`, `not`, and `+ - * // %` on numbers;
- these **names**, provided by the runtime after the host finished: `exit_code`, `duration_ms`, `stdout`, `stderr` (strings);
- these **functions**, a closed whitelist: `counter(name)` (current value), `meta(key)`, `len(x)`, `contains(text, part)`, `lines(text)` (list of lines), `any_line(text, part)`;
- no attribute access, no subscripts, no comprehensions, no lambdas, no other names or calls, no expressions longer than 200 characters, no more than 50 nodes.

Evaluation uses a step budget, so a condition cannot hang the runtime.

## Validation

- Unknown name or function: `error: Unknown name 'foo' in invariant 'fast enough'` with the column inside the condition string.
- Disallowed syntax: `error: 'lambda' is not allowed in an invariant condition`.
- `counter('x')` where `x` is never created: `error` (the same rule as `counter.increment`).
- Duplicate `name`: `warning`.

## Runtime behavior

Applied at the new built-in lifecycle point **after `phantom.post_execute`**. Each invariant produces a diagnostic: `INFO` when it holds, `ERROR` when it is violated (with the evaluated operands), and an `ERROR` if evaluation fails (for example comparing a string with a number). By default a violation does not change the exit status (consistent with "instructions never alter the program"); `phantom run --fail-on-invariant` exits with status 3 when any invariant is violated, and `phantom check --invariants-only` can lint the expressions without running anything. New capability: `cap.invariants` (so `--deny cap.invariants` can switch the feature off in a locked-down CI).

## Safety and security

- **Data never becomes code:** the evaluator interprets a whitelist of AST node types; there is no path to attribute access or imports. The property-based test-suite should generate random expressions and assert that no accepted expression can touch anything outside the provided names.
- No file system, network or process access. `stdout`/`stderr` are read-only strings that the host already produced.
- Resource use is bounded (expression size, step budget).
- Impact on `docs/THREAT_MODEL.md`: a new row "T10: expression evaluation", status Addressed once the evaluator is fuzzed; the existing "no eval/exec" release gate stays unchanged.

## Compatibility

New instruction, new minor version (`0.2.0`). An older Phantom reports `Unknown instruction identifier: 'invariant.assert'` (a clear error), and plain Python ignores the line. Existing files are unaffected.

## Alternatives considered

1. **Real Python expressions via `eval` with restricted globals.** Rejected: restricted `eval` is a well-known sandbox escape.
2. **A fixed set of checks (`invariant.exit_code(0)`, `invariant.max_duration_ms(5000)`)**. Safer and simpler to implement, but every new kind of check needs a language change. A reasonable *first* step if the expression language proves contentious: ship the three fixed forms first, add `assert` later.
3. **Put expectations in `pyproject.toml` or a separate YAML.** That is what exists today; the point of this proposal is colocation.
4. **SMT/formal verification** (see ROADMAP "Formal Invariant Verification"): out of scope; this proposal is runtime checking only.

## Testing plan

Positive and negative tests for every accepted and rejected node type; property-based tests that arbitrary generated expressions either validate and evaluate within the budget or are rejected with a diagnostic (never an exception); a negative test per Python escape attempt (`__import__('os')`, `().__class__`, `(lambda: 1)()`, very long expressions, deep nesting); `phantom run --fail-on-invariant` exit statuses; round trip through all three encodings (the expression is an ordinary string argument, so it inherits the escaping rules of #51/#75).

## Documentation plan

`SPECIFICATION.md` (new section 5.9 and the condition language grammar), `docs/LANGUAGE_GUIDE.md`, `docs/RUNTIME.md` (new lifecycle point), `docs/THREAT_MODEL.md`, `docs/CI.md` (an example using the GitHub Action), `CHANGELOG.md`. Status label: Proposed -> Experimental -> Implemented.

## Open questions

1. Is a closed whitelist of functions enough, or should invariants also be able to read the *host's return value* (needs the host-side API from #6)?
2. Should a violated invariant fail the run by default? (Proposed: no, opt in with `--fail-on-invariant`, so adding an invariant can never break a program that merely runs.)
3. Should `name` be required? (Proposed: yes, so CI output is readable.)
4. Is `0.2.0` the right version tag inside the instruction, or should instructions carry the spec version in which they were introduced?
5. Do we want the fixed-forms-first plan (alternative 2) to de-risk the first release?

Discussion is welcome in the pull request that adds this file or in a new issue linking it.
