# Quick Start

🌐 **Languages:** English · [हिन्दी](https://github.com/hayagrivai-labs/phantom/pull/hi/QUICKSTART.md) · [Português (Brasil)](https://github.com/hayagrivai-labs/phantom/pull/pt-BR/QUICKSTART.md)

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

## 10. Locking things down
You can restrict runtime capabilities using `--deny` or limit allowed handler directories using `--handlers-from`.

### Blocking Capabilities
Use `--deny` to block specific capabilities, such as `cap.counters`:

```bash
phantom inspect docs/examples/policy.py --deny cap.counters
```

Output:
```text
File: docs/examples/policy.py
Spec Version: 0.1.0
Total Instructions: 3

Instructions:
  [1] counter.create
      Arguments:    string='cap.counters', integer=10
      Source:       docs/examples/policy.py:10:0
      Encoding:     comment
      Capabilities: cap.counters
      Policy:       BLOCKED (denied: cap.counters)
  [2] counter.increment
      Arguments:    string='cap.counters'
      Source:       docs/examples/policy.py:11:0
      Encoding:     comment
      Capabilities: cap.counters
      Policy:       BLOCKED (denied: cap.counters)
  [3] event.on
      Arguments:    string='phantom.pre_execute', string='hooks.on_start'
      Source:       docs/examples/policy.py:12:0
      Encoding:     comment
      Capabilities: cap.events
```

Attempting to execute the file with denied capabilities will halt execution before the host starts (exit code 2):

```bash
phantom run docs/examples/policy.py --deny cap.counters
```

Output:
```text
=== Phantom Runtime v0.1.1 ===
[ERROR] docs/examples/policy.py:10:0 [comment]: Instruction 'counter.create' requires cap.counters, which the capability policy denies
[ERROR] docs/examples/policy.py:11:0 [comment]: Instruction 'counter.increment' requires cap.counters, which the capability policy denies
Validation failed: 2 error(s), 0 warning(s)
```

### Restricting Event Handlers
Use `--handlers-from` to restrict where handler modules can be imported from:

```bash
phantom run docs/examples/policy.py --handlers-from docs/examples
```

Output:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
[hook] starting docs/examples/policy.py
Running host program under policy rules.
```

If the handler module resides outside the specified directory, the runtime rejects the import:

```bash
phantom run docs/examples/policy.py --handlers-from /tmp/elsewhere
```

Output:
```text
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (3 instruction(s), 0 warning(s))
Running host program under policy rules.

--- Phantom Diagnostics ---
[ERROR] Failed to resolve handler 'hooks.on_start' for event 'phantom.pre_execute': handler 'hooks.on_start' is not allowed by the handler policy (module at docs\examples\hooks.py); it was not imported
```

## Next

[LANGUAGE_GUIDE.md](LANGUAGE_GUIDE.md) · [ENCODINGS.md](ENCODINGS.md) · [RUNTIME.md](RUNTIME.md) · [GENERATOR.md](GENERATOR.md)
