# Language Guide

The instruction layer is a small declarative language embedded next to your Python. The formal definition is [SPECIFICATION.md](../SPECIFICATION.md); this guide explains how to use it.

## Syntax

```python
#: phantom:0.1.0 category.name(arg1, arg2)
```

- one instruction per line, the whole line (leading indentation allowed);
- `phantom:0.1.0` is the specification version (required);
- arguments are comma-separated **string** (`"text"`) or **integer** (`42`, `-1`) literals — no expressions, names or nesting;
- strings support `\"`, `\\`, `\n`, `\t`, `\r`.

A comment that merely contains the word `phantom` is just a comment.

The encoders and generator write newline, carriage return, and tab characters in string arguments as `\n`, `\r`, and `\t`, so each instruction remains on one logical line. Literal backslash sequences (for example, the two characters `\n`) remain literal after a round trip. Other line separators, such as U+0085, U+2028, and U+2029, are not covered by these escapes and still have known round-trip limitations ([#51](https://github.com/hayagrivai-labs/phantom/issues/51)).

## Instructions

| Instruction | What it does | Notes |
| :--- | :--- | :--- |
| `event.declare(name)` | Declares an event | Redeclaring warns |
| `event.on(event, handler)` | Registers `"module.function"` for a declared event | Only the three lifecycle events are ever fired |
| `diagnostic.note(message)` | Records an `INFO` diagnostic with this line's location | Printed after the host output |
| `counter.create(name, limit)` | Counter at 0, bounded by `limit > 0` | Duplicate name is an error |
| `counter.increment(name)` | Adds 1 | Needs a prior `counter.create`; past the limit it logs an error diagnostic and stays at the limit |
| `meta.author(name)` | Records the author | Metadata only |
| `meta.version(version)` | Records a version label | Metadata only |
| `meta.license(name)` | Records a license label | Metadata only |

### Events

```python
#: phantom:0.1.0 event.on("phantom.pre_execute", "hooks.before")
#: phantom:0.1.0 event.on("phantom.post_execute", "hooks.after")
#: phantom:0.1.0 event.on("phantom.shutdown", "hooks.cleanup")
```

`hooks.py` (next to the host file):

```python
def before(host_file, args): ...
def after(host_file, result): print(result.exit_code)
def cleanup(): ...
```

Handlers get only the keyword arguments they name (or all if they take `**kwargs`). They run in registration order; a failing handler is reported and the next still runs. `event.declare` creates custom events you may attach handlers to, but v0.1.0 provides no way to fire them from your program. Importing a handler module executes it: only use trusted modules.

### Counters

```python
#: phantom:0.1.0 counter.create("api_calls", 3)
#: phantom:0.1.0 counter.increment("api_calls")
```

### When do instructions run?

All at once, in source order, **before the host starts**. The position of an instruction in the file matters only for ordering among instructions (for example `counter.create` must come before `counter.increment`) and for the location shown in diagnostics. An increment written inside a host loop is applied once, not once per iteration. Phantom does not observe the host's control flow.

## Argument types

| Type | Syntax | Notes |
| :--- | :--- | :--- |
| string | `"…"` | double quotes only |
| integer | `-?[0-9]+` | decimal |
| identifier | — | *reserved*, not accepted in v0.1.0 |

## Patterns that fit the model

**Provenance and notes for reviewers and tools**

```python
#: phantom:0.1.0 meta.author("Refactor bot v3")
#: phantom:0.1.0 meta.version("2.1.0")
#: phantom:0.1.0 diagnostic.note("Replaced O(n^2) scan; behavior unchanged")
```

**Lifecycle reporting without touching the program**

```python
#: phantom:0.1.0 event.on("phantom.post_execute", "audit.record_run")
```

**A declared budget that tooling can read**

```python
#: phantom:0.1.0 counter.create("migrations", 10)
```

## Errors

`phantom check FILE` prints each problem with file, line, column and a source excerpt. For example (real output):

```text
error: Counter limit must be > 0, got 0
  --> docs/examples/invalid.py:5:1
   5 | #: phantom:0.1.0 counter.create("retries", 0)
     | ^
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for the full list.

## Limitations

1. Instructions cannot read or change host variables, signatures or control flow.
2. Arguments are literals; expressions are rejected.
3. Instructions cannot be nested.
4. No per-line triggers and no firing of custom events from host code.
5. Python hosts only.
