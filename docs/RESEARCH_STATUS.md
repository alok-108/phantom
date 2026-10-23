# Research and Feature Status

Labels: **Implemented** · **Experimental** · **Proposed** · **Hypothesis** · **Future research** · **Out of scope for v0.1.0**. "Implemented" means shipped and tested; it does not mean production-hardened.

## Core

| Capability | Status | Notes |
| :--- | :--- | :--- |
| eight instructions (events, counters, notes, metadata) | Implemented | [SPECIFICATION.md](../SPECIFICATION.md) |
| Typed IR, lexer, parser, validator | Implemented | |
| Comment encoding | Implemented | Recommended |
| Whitespace encoding | Experimental | Fragile under formatters; see [ENCODINGS.md](ENCODINGS.md) |
| Zero-width Unicode encoding | Experimental | Fragile under normalisation; requires `# ` prefix to be valid Python |
| Hybrid encoding | Experimental | Header-gated de-duplication |
| Strict invisible-character audit | Implemented | No homoglyph detection |
| `check`, `inspect`, `run`, `diff` | Implemented | |
| Lifecycle events (`pre_execute`, `post_execute`, `shutdown`) | Implemented | |
| Custom events fired from host code | Out of scope for v0.1.0 | Needs a host-side API |
| Per-line / in-flow hooks | Proposed | Instructions apply at initialisation today |
| SARIF output for `check` | Implemented | |
| Capability model (library) | Implemented | CLI grants all; no restricted-mode flag |

## Generator

| Capability | Status | Notes |
| :--- | :--- | :--- |
| Plan → validate → insert-only transform → validate pipeline | Implemented | Mock-tested |
| Gemini provider | Experimental | Call shape checked against `google-genai` 2.32.0; never run live |
| Static AST host-preservation check | Implemented | |
| `verify` single-run behavior comparison | Experimental | One run; not a proof |
| Multi-run / input-fuzzing equivalence | Proposed | |
| Return-value, file-effect and timing comparison | Proposed | |
| Sandboxed comparison | Proposed | Use a container today |
| Additional providers | Proposed | Interface exists |
| Interactive questions (intent, placement, encoding, consent) | Implemented | Terminal only; non-interactive runs require flags and fail clearly |
| Clarifying questions about fragments/constraints | Proposed | Input must be valid Python; constraints come from flags |

## Language roadmap items (see [ROADMAP.md](../ROADMAP.md))

| Idea | Status |
| :--- | :--- |
| `invariant.assert`, `timer.*`, `trace.span` | Proposed (v0.2.0) |
| Language server / editor decoders | Proposed (v0.2.0) |
| Repository-wide event graphs | Proposed (v0.3.0) |
| Async / thread-safe dispatch | Proposed (v0.3.0) |
| SMT-based invariant verification | Future research |
| Bidirectional AI synchronisation with telemetry | Future research |

## Phantom C and visibility research

| Idea | Status | Document |
| :--- | :--- | :--- |
| **Phantom C**: dual-layer sources for compiled languages | Future research — not implemented | [PHANTOM_C.md](research/PHANTOM_C.md) |
| Observer-dependent visibility of a dual-layer program | Hypothesis | [OBSERVABILITY.md](research/OBSERVABILITY.md) |
| How third-party tools/editors treat the encodings | Hypothesis — unmeasured | [EXPERIMENTAL_METHOD.md](research/EXPERIMENTAL_METHOD.md) |
| Any form of undetectable execution or evasion of security products | Not a goal; rejected | [PHANTOM_C.md §6](research/PHANTOM_C.md) |

A research document is a record of a question, not of a capability.
