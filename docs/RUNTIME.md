# Runtime

`phantom run FILE [--timeout SECONDS] [-- HOST_ARGS]` is the only way Phantom instructions take effect. Standard `python FILE` ignores them.

## Lifecycle

| Step | What happens |
| :--- | :--- |
| 1 | Read and parse the file. Nothing is executed. |
| 2 | Validate. On any error: print diagnostics, **exit 2**, host never starts. |
| 3 | Create the runtime with the default capability grant. |
| 4 | **Initialise**: apply every instruction in source order (declare events, register handlers, create/increment counters, record notes and metadata). Runtime errors here are printed as `[RuntimeWarning]` on stderr and do not stop the run. |
| 5 | Fire `phantom.pre_execute(host_file, args)`. |
| 6 | Run the host as a subprocess: `sys.executable FILE ARGS…`, UTF-8, timeout (default 30 seconds, configurable with `--timeout`). |
| 7 | Fire `phantom.post_execute(host_file, result)`. |
| 8 | Fire `phantom.shutdown()`. |
| 9 | Print the host's captured stdout and stderr, then Phantom diagnostics. **Exit with the host's exit code** (124 if it timed out). |

Exit codes: `0` success, `1` file missing/unreadable or invalid `--timeout`, `2` validation failed, otherwise the host's code.

### Instructions are applied at initialisation

An instruction is not "triggered" when execution passes the line it is written on. The whole instruction layer is applied before the host starts. In particular `counter.increment` records a fact about the program; it is not a hook inside your loop. Per-line hooks inside host control flow are not part of v0.1.0.

## Event model

- **Built-in events**: `phantom.pre_execute`, `phantom.post_execute`, `phantom.shutdown`. These are the only events the runtime fires.
- **Custom events** can be declared with `event.declare` and have handlers registered, but nothing fires them in v0.1.0 (there is no host-side fire API).
- **Handlers** are dotted paths such as `"events.announce_done"`. They are resolved by import when the event fires, relative to the host's directory.
- **Order** is registration order, deterministically.
- **Handler arguments**: keyword arguments the handler declares by name, or all of them if it accepts `**kwargs`; a handler taking no arguments is called with none. `pre_execute`: `host_file`, `args`. `post_execute`: `host_file`, `result` (exit_code, stdout, stderr, duration_ms). `shutdown`: none.
- **Signature checks** happen before invocation. Only parameters accepting keywords receive matching event arguments; required positional-only parameters cannot be supplied by an event. If a callable has no inspectable signature, it receives the full event payload as keyword arguments once.
- **Errors**: an unresolvable handler, incompatible signature, or handler exception becomes one `ERROR` diagnostic; the remaining handlers still run. Each registered handler is invoked at most once per event firing. Exceptions raised inside a handler, including `TypeError` and `ValueError`, never trigger a retry.
- **Duplicates/missing**: redeclaring an event is a validation warning and a runtime error (reported, not fatal). Registering for an undeclared event is a validation error.

See `docs/examples/events.py`:

```text
$ phantom run docs/examples/events.py
=== Phantom Runtime v0.1.1 ===
[OK] Validation passed (2 instruction(s), 0 warning(s))
[hook] about to run events.py
[hook] finished with exit code 0
Doing the work.
```

Hook output precedes the host's output because the host's output is captured and printed after the run.

> **Trust:** resolving a handler imports its module, which executes that module's top-level code inside the Phantom process. Treat `event.on` paths like `import` statements and only run files you trust. See [THREAT_MODEL.md](THREAT_MODEL.md).

## Counters

`counter.create("n", L)` creates a counter at 0 with limit `L > 0`. `counter.increment("n")` adds 1. Past the limit the counter stays at `L` and an error diagnostic ("exceeded limit") is recorded; the program is not stopped. Validation warns when a file contains more increments than the limit.

## Diagnostics

`diagnostic.note("…")` records an `INFO` diagnostic with its location, printed after the host output:

```text
--- Phantom Diagnostics ---
[INFO] [docs/examples/comments.py:18:0 [comment]] Greeting counter initialised
```

## Capabilities

| Capability | Covers |
| :--- | :--- |
| `cap.stdio` | running the host and capturing its streams |
| `cap.events` | `event.declare`, `event.on`, firing |
| `cap.diagnostics` | `diagnostic.note` |
| `cap.counters` | `counter.*` |
| `cap.metadata` | `meta.*` |

`phantom inspect` shows the capabilities each instruction needs. The CLI grants all five. A restricted `CapabilityGrant` can be passed to `PhantomRuntime` from Python; operations then raise `CapabilityError` (initialisation reports it as a warning and skips the instruction). There is no command-line flag for restricted grants in v0.1.0.

## Host guarantees and non-guarantees

- The host runs as an ordinary Python subprocess. Phantom adds no imports, globals or decorators and does not edit the file.
- A host that reads its own source file or inspects its own comments will see the instruction layer; that is unavoidable.
- Phantom does not claim full Python compatibility merely because it can launch a program: it launches `sys.executable`, so behavior is that interpreter's.
- Resource limits: the host timeout only. On timeout the host **and every process it started** are killed (process group on POSIX, job object with a `taskkill` fallback on Windows), so a child that keeps the output pipes open cannot stretch the timeout. There is no memory or CPU sandboxing.
