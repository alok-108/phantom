# Quick Start

Every command and output below was produced by running the repository's example files. Paths are relative to the repository root.

## 1. Install

```bash
python --version            # 3.10 or newer
pip install -e ".[dev]"
phantom --version
```

```text
phantom 0.1.1
```

(`python -m phantom …` is equivalent if the `phantom` script is not on your `PATH`.)

## 2. Look at a file

[docs/examples/comments.py](examples/comments.py) is ordinary Python followed by Phantom instructions in comments:

```python
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
```

It has no Phantom import, no decorator and no wrapper.

## 3. Plain Python ignores the instructions

```bash
python docs/examples/comments.py
```

```text
Hello, World!
```

## 4. Validate without running anything

```bash
phantom check docs/examples/comments.py
```

```text
0 error(s), 0 warning(s)
```

A broken file ([docs/examples/invalid.py](examples/invalid.py)) is rejected with the location and a caret, in line order, and exit status 2:

```bash
phantom check docs/examples/invalid.py
```

```text
error: Counter limit must be > 0, got 0
  --> docs/examples/invalid.py:5:1
   5 | #: phantom:0.1.0 counter.create("retries", 0)
     | ^
error: Handler registered for undeclared event 'never.declared'
  --> docs/examples/invalid.py:6:1
   6 | #: phantom:0.1.0 event.on("never.declared", "handlers.go")
     | ^
error: Unknown instruction identifier: 'system.exec'
  --> docs/examples/invalid.py:7:1
   7 | #: phantom:0.1.0 system.exec("calc")
     | ^
3 error(s), 0 warning(s)
```

(The summary line is printed last; errors go to stderr.) Unknown instructions are never executed.

## 5. Inspect

```bash
phantom inspect docs/examples/comments.py
```

```text
File: docs/examples/comments.py
Spec Version: 0.1.0
Total Instructions: 5

Instructions:
  [1] meta.author
      Arguments:    string='Ada Lovelace'
      Source:       docs/examples/comments.py:14:0
      Encoding:     comment
      Capabilities: cap.metadata
  ...
```

Use `--json` for machine-readable output and `--strict` to flag suspicious invisible characters. Inspection never runs the file.

## 6. Run with Phantom

```bash
phantom run docs/examples/comments.py
```

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (5 instruction(s), 0 warning(s))
Hello, World!

--- Phantom Diagnostics ---
[INFO] [docs/examples/comments.py:18:0 [comment]] Greeting counter initialised
```

`phantom run` validated the file, applied the instruction layer, ran the host as a subprocess, then printed the host output followed by the diagnostics. Its exit status is the host's. See [RUNTIME.md](RUNTIME.md) for the full lifecycle and for what the instructions do and do not do.

## 7. Hooks

[docs/examples/events.py](examples/events.py) registers plain functions for the built-in lifecycle events:

```bash
phantom run docs/examples/events.py
```

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (2 instruction(s), 0 warning(s))
[hook] about to run events.py
[hook] finished with exit code 0
Doing the work.
```

## 8. Other encodings

[whitespace.py](examples/whitespace.py), [unicode.py](examples/unicode.py) and [hybrid.py](examples/hybrid.py) carry their instructions in invisible form. They run under plain Python and under Phantom:

```bash
phantom run docs/examples/whitespace.py
```

```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (1 instruction(s), 0 warning(s))
Executing core Python logic!

--- Phantom Diagnostics ---
[INFO] [docs/examples/whitespace.py:11:0 [whitespace]] hidden in whitespace
```

Read [ENCODINGS.md](ENCODINGS.md) before using them for real work.

## 9. Generate (optional, remote)

```bash
phantom generate docs/examples/hello.py --intent "note the program start" \
    --allow-remote --dry-run
```

This sends the file to the configured provider (needs `pip install "phantom-lang[llm]"` and `GEMINI_API_KEY`). See [GENERATOR.md](GENERATOR.md).

## Next

[LANGUAGE_GUIDE.md](LANGUAGE_GUIDE.md) · [ENCODINGS.md](ENCODINGS.md) · [RUNTIME.md](RUNTIME.md) · [GENERATOR.md](GENERATOR.md)
