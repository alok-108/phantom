# Phantom Vision: Dual-Layer Source Architecture

> "What if source code could carry two distinct, concurrent conversations — one with the compiler, and another with runtime coordinators, telemetry engines, and artificial intelligence agents — without either conversation interfering with the other?"

---

## The Genesis of Phantom

Modern software engineering suffers from an escalating tension: **the host application code is overwhelmed by meta-concerns**. 

When we inspect enterprise software today, a significant portion of the lines on screen do not describe the core business domain or algorithmic transformation. Instead, they represent scaffolding:
- OpenTelemetry / Prometheus metrics tracking calls
- Distributed tracing spans and context injection
- Lifecycle event hooks and pub/sub notifications
- Diagnostic assertions and invariant assertions
- Framework-specific decorators (`@retry`, `@timed`, `@observable`, `@validate`)
- AI agent directives, lint hints, and provenance metadata

This tangle creates severe challenges:
1. **Cognitive Overhead:** Developers reading a 50-line function must mentally filter out 30 lines of decorators, logging calls, and instrumentation hooks just to comprehend the core calculation.
2. **Import Graph Pollution:** Introducing an observability or event system forces dozens of external dependencies into the host module's import graph.
3. **Rigid Coupling:** Modifying telemetry, monitoring, or coordination logic often requires rewriting function signatures, wrapping closures, or touching fragile AST structures.

Phantom was born to resolve this dilemma through a radically simpler paradigm: **The Dual-Layer Source Model**.

---

## The Dual-Layer Concept

A Phantom program is a single source file that exists simultaneously in two distinct layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SOURCE FILE (e.g. app.py)                       │
├────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Host Code (Standard Python)                                  │
│    def process_order(order_id: str, amount: float) -> bool:            │
│        if amount <= 0:                                                 │
│            return False                                                │
│        return debit_account(order_id, amount)                          │
├────────────────────────────────────────────────────────────────────────┤
│  Layer 2: Phantom Instruction Layer                                    │
│    #: phantom:0.1.0 counter.create("orders_processed", 10000)          │
│    #: phantom:0.1.0 event.declare("order.completed")                   │
│    #: phantom:0.1.0 counter.increment("orders_processed")              │
│    #: phantom:0.1.0 diagnostic.note("Order processed successfully")    │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Host Layer (Imperative Foundation):**
   Standard, idiomatic Python code. It imports only what it needs, executes pure algorithmic logic, and follows standard language conventions.
2. **Instruction Layer (Declarative Meta-Plane):**
   Structured, typed Phantom instructions embedded in the file via comment directives, whitespace bit-encodings, or zero-width Unicode sequences. This layer declares events, tracks counters, binds callbacks, and records diagnostics.

---

## The No-Import, No-Decorator, No-Wrapper Philosophy

Traditional Python frameworks achieve meta-programming through decorators (`@event_handler`), inheritance (`class MyService(Observable)`), or explicit runtime calls (`metrics.increment()`). 

Phantom deliberately rejects this model in favor of three core principles:

1. **Zero Host Imports:**
   The host Python file does **not** import `phantom`, `phantom.runtime`, or any helper library. The host module has zero dependency on Phantom at the source level.
2. **Zero Decorators or Wrappers:**
   Functions and classes remain pristine. No decorators alter function signatures, wrap stack frames, or inject hidden state into the Python object model.
3. **Transparent Execution Split:**
   - When run with the standard CPython interpreter:
     ```bash
     python app.py
     ```
     Python treats comment-encoded Phantom lines as ordinary comments; whitespace blocks are blank lines and zero-width blocks are comments. The application runs unchanged, with no Phantom code involved.
   - When run with the Phantom runner:
     ```bash
     phantom run app.py
     ```
     The Phantom engine extracts the instruction layer, constructs the Intermediate Representation (IR), validates it, applies it, and then runs the host program as a subprocess. Stock Python never executes the instruction layer; Phantom does not modify the interpreter.

---

## Cognitive Augmentation & AI Collaboration

As more code is written with LLM assistance, a structured second layer offers possible advantages. These are design goals to investigate, not capabilities that v0.1.0 claims:

- **AI Intent Plane:**
  An AI agent generating or refactoring code can express its intent, invariants, diagnostic expectations, and lifecycle triggers in the Phantom layer while leaving the host Python code readable and concise.
- **Bi-Directional Communication:**
  Humans can inspect the host logic without distraction, or inspect the instruction layer via `phantom inspect` to see what events and diagnostics the agent attached.
- **Automated Verification:**
  Because the instruction layer is formally structured (unlike freeform natural language comments), automated tools can statically verify whether a proposed code transformation satisfies declared invariants and event contracts.

---

## Research Vision: The Path to Phantom C

Looking beyond Python v0.1.0, Phantom explores fundamental questions of source representation, compiler theory, and program observability.

The long-term research direction is **Phantom C**: an investigation into whether dual-layer semantics can be generalised to compiled languages (C, Rust, Go), and into how source representation, runtime behavior and observability relate for different classes of observer (developers, tools, runtime diagnostics, security products, the operating system, and authorized system owners). It is a research question, not a claim: Phantom does not provide undetectable execution, does not defeat security products, and does not conceal activity from authorized owners.

> For the comprehensive formal research vision, observer taxonomy, and research questions, see [Phantom C Research Vision](docs/research/PHANTOM_C.md).

---

## Honesty: Implemented vs. Aspirational

To maintain clarity and engineering integrity, we explicitly delineate what is real today versus what is future exploration:

### Implemented in v0.1.0
- Eight instructions: `event.declare`, `event.on`, `diagnostic.note`, `counter.create`, `counter.increment`, `meta.author`, `meta.license`, `meta.version`.
- A formal grammar, lexer, parser, typed IR and validator.
- Four encodings: comment (recommended), whitespace, zero-width Unicode, hybrid. The last three are *experimental* (fragile under formatters and normalisation).
- CLI: `check`, `inspect`, `run`, `generate`, `diff`, `verify`.
- Lifecycle events with plain-function handlers; a capability model.
- An optional LLM-assisted generator with a validated, insert-only transformer and an AST-based host-preservation check. The Gemini provider has not been run against the live API in this repository.

### Not implemented (research and roadmap)
- **Phantom C** — compiled-language dual layers and observer-visibility research. *Future research.* See [docs/research/PHANTOM_C.md](docs/research/PHANTOM_C.md).
- Hooks inside host control flow; firing custom events from host code. *Proposed.*
- Repository-wide event graphs; async dispatch. *Proposed (v0.3.0).*
- Formally verified invariants. *Future research.*

The per-feature status table is [docs/RESEARCH_STATUS.md](docs/RESEARCH_STATUS.md).

Phantom v0.1.0 is a foundation: it shows that a second structured layer can sit next to Python cleanly and inspectably. It is not a finished system.
