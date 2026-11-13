# Examples

Every command and output here is produced by the files in this directory and is asserted by `tests/test_examples.py`. Run commands from the repository root. `PYTHONUTF8=1` is assumed on Windows.

| # | Example | File(s) | Command |
| :--- | :--- | :--- | :--- |
| 1–2 | Hello World; ordinary Python, no Phantom imports | `hello.py` | `phantom run docs/examples/hello.py` |
| 3 | Comment encoding | `comments.py` | `phantom run docs/examples/comments.py` |
| 4 | Whitespace encoding | `whitespace.py` | `phantom run docs/examples/whitespace.py` |
| 5 | Zero-width encoding | `unicode.py` | `phantom run docs/examples/unicode.py` |
| 6 | Hybrid encoding | `hybrid.py` | `phantom inspect docs/examples/hybrid.py` |
| 7 | Events and callbacks | `events.py` | `phantom run docs/examples/events.py` |
| 8 | Inspection and validation | `comments.py` | `phantom inspect …` / `phantom check …` |
| 9 | Invalid instruction | `invalid.py` | `phantom check docs/examples/invalid.py` |
| 10 | Generation from an existing program (offline plan) | `generation/` | below |
| 11 | Behavior-preservation comparison | `generation/` | below |
| 12 | Rejected generation / detected behavior change | `generation/` | below |
| 13 | Bounded counter lifecycle | `counters.py` | `phantom run docs/examples/counters.py` |

Examples 1–9 and 13 are walked through with output in [../QUICKSTART.md](../QUICKSTART.md) and [../RUNTIME.md](../RUNTIME.md). `whitespace.py`, `unicode.py` and `hybrid.py` are produced by `python scripts/build_examples.py` because their payload is invisible.

## 10. Generation (offline)

`--plan-file` supplies the model's JSON plan from a local file, so nothing is sent anywhere. The remaining pipeline (validation, insertion, checks) is the real one.

```bash
phantom generate docs/examples/generation/program.py --intent "annotate" \
    --plan-file docs/examples/generation/plan.json --output candidate.py
```

```text
Plan:
  - meta.author  [comment]  provenance
  - diagnostic.note  [comment]  reviewer hint

Diff:
--- program.py
+++ candidate
@@ -1,3 +1,5 @@
+#: phantom:0.1.0 meta.author("Example plan")
+#: phantom:0.1.0 diagnostic.note("total() annotated")
 """A small program to annotate."""
 
 

Checks: host syntax OK, Phantom instructions valid, host code unchanged (AST).
Behavior has NOT been executed; run 'phantom verify' to compare outputs.
Candidate written to candidate.py (original untouched).
```

Exit 0. `program.py` is unchanged; the candidate was written but **not run**.

## 11. Behavior comparison

```bash
phantom verify docs/examples/generation/program.py candidate.py
```

```text
Result: Tested equivalence for the single tested run
  note: Only one input (no arguments, no stdin) was exercised
This is not a proof of equivalence for other inputs, state or environments.
```

Exit 0. This executes both files. It says the two runs matched, nothing more.

## 12. Rejected and detected-different

A plan using an instruction that does not exist is rejected, and no candidate is produced:

```bash
phantom generate docs/examples/generation/program.py --intent "trace" \
    --plan-file docs/examples/generation/bad_plan.json
```

```text
error: instruction 1 (trace.span): unknown instruction
```

(exit 2; the plan summary is also printed.) `trace.span` is a *proposed* v0.2.0 instruction, not part of v0.1.0.

A program whose behavior changed is reported, not accepted:

```bash
phantom verify docs/examples/generation/program.py docs/examples/generation/changed.py
```

```text
  difference: stdout differs
--- original stdout
+++ candidate stdout
@@ -1 +1 @@
-12
+13
Result: Behavior difference detected
```

Exit 1. An inconclusive result (exit 3) occurs when a program times out; see `tests/test_equivalence.py`.
