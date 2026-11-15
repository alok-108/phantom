# ADR 0002: Apply instructions at initialisation; run the host as a subprocess

* Status: accepted, 2026-10-21

## Context

Stock Python does not execute the instruction layer, so Phantom needs a launcher. Two designs were
possible: run the host inside the Phantom process and trace it (so instructions could fire at
their source line), or apply the instruction layer first and then run the host separately.

## Decision

`phantom run` parses and validates the file, applies **all** instructions in source order, fires
`phantom.pre_execute`, runs the host as a subprocess (`sys.executable FILE`, 30 s timeout), fires
`phantom.post_execute` and `phantom.shutdown`, prints the host's captured output and diagnostics,
and exits with the host's exit code.

## Consequences

* Good: the host is never modified or imported; a crashing or hanging host cannot corrupt
  Phantom's state; exit code, stdout and stderr are captured exactly.
* Good: no import hooks, tracing or interpreter changes, so nothing global is touched.
* Limitation: Phantom cannot observe inside the host. `counter.increment` is a statement about
  the program, not a hook in its control flow, and custom events cannot be fired from host code.
* Limitation: event handlers run in the Phantom process and are imported by dotted path, which
  executes the module's top-level code. There is no sandbox.
* Per-line hooks or a host-side API would be a new proposal (see `docs/proposals/`).
