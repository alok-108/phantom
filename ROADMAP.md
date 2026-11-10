# Phantom Project Roadmap

This document outlines the development trajectory of the Phantom dual-layer programming language, detailing completed milestones, immediate product goals, and long-term academic research.

---

## Release Milestones

```
  v0.1.0 (Current)             v0.2.0 (Planned)             v0.3.0 (Planned)             Future / Long-Term
┌────────────────────┐       ┌────────────────────┐       ┌────────────────────┐       ┌────────────────────┐
│ • 12 Instructions  │       │ • Extended Grammar │       │ • Repo-Wide Graphs │       │ • Phantom C research│
│ • 4 Encodings      │  ───> │ • Language Server  │  ───> │ • Async Dispatch   │  ───> │ • Observer studies │
│ • CLI Suite        │       │ • CLI Color        │       │ • State Invariants │       │ • Method + results │
│ • Gemini Generator │       │ • AST Integration  │       │ • CI/CD Verifier   │       │ • Formal invariants│
└────────────────────┘       └────────────────────┘       └────────────────────┘       └────────────────────┘
```

---

## Milestone Details

### v0.1.x — Initial Release (Current)
*Status: Released on GitHub (v0.1.1). Not on PyPI (see `docs/RELEASING.md`).*
- **Instruction Registry (Implemented):** 12 instructions: `event.declare`, `event.on`, `diagnostic.note`, `diagnostic.warn`, `counter.create`, `counter.increment`, `counter.decrement`, `counter.reset`, `meta.author`, `meta.version`, `meta.license`, and `meta.tags` ([registry](src/phantom/grammar.py), [tests](tests/test_grammar.py)).
- **Encodings:** 4 fully functional encoding modes (Comment, Whitespace 8-bit, Zero-Width Unicode 2-bit, and Hybrid).
- **Core Architecture:**
  - Lexical scanner and multi-encoding parser.
  - Frozen, strongly typed Intermediate Representation (`PhantomProgram`, `PhantomInstruction`).
  - Static validator checking argument counts, types, and strict Unicode policies.
  - 9-step runtime execution engine.
- **Command-Line Interface:** `phantom check`, `inspect`, `run`, `generate`, `diff`, `verify`; strict invisible-character audit; SARIF export for `check`.
- **Diagnostics (Implemented):** `check` renders source context and caret markers and can export SARIF; the rendering API supports ANSI color, but the CLI currently calls it without color ([implementation](src/phantom/diagnostics.py), [CLI](src/phantom/cli.py), [tests](tests/test_ir.py)). A [GitHub Action](action.yml) can upload SARIF.
- **LLM Integration:** Provider-independent generator pipeline (Gemini provider included, untested against the live API) with plan validation, an insert-only transformer, and AST-based host-preservation checking.
- **Implemented controls and limits:** `run` supports capability restrictions and handler allow-lists; the runtime API can fire custom events ([policy tests](tests/test_policy.py), [runtime tests](tests/test_runtime.py)). Sandboxed comparison remains a gap.

---

### v0.2.0 — Developer Tooling & Extended Grammar (Target: Q2 2027)
*Status: In Planning. The first concrete design is [proposal 0001: `invariant.assert`](docs/proposals/0001-invariants.md) (a draft for discussion).*
- **Extended Instruction Set:**
  - `invariant.assert(condition_expr)`: Declarative assertions evaluated at lifecycle points.
  - `timer.create(name)` / `timer.record(name)`: Built-in execution duration instrumentation.
  - `trace.span(name)`: Distributed trace context markers without OpenTelemetry SDK bloat.
- **Language Server Protocol (LSP) Server (`phantom-lsp`):**
  - Real-time syntax highlighting for comment-encoded instructions.
  - Visual decoders and hover cards for whitespace and zero-width Unicode blocks in VS Code and Neovim.
  - Autocompletion for instruction identifiers and event names.
- **Enhanced Diagnostics & Error Reporting:**
  - **Proposed:** Enable ANSI/colorized diagnostics in the CLI; source context, caret markers and SARIF export are already implemented as described above.
- **Host AST Awareness:**
  - Correlating Phantom instruction line positions with host Python AST nodes (e.g., associating an instruction with the immediately following function or class definition).

---

### v0.3.0 — Distributed Coordination & Advanced Events (Target: Q4 2027)
*Status: Proposed*
- **Repository-Wide Dual-Layer Analysis:**
  - Project-level instruction graph indexing (directory checks exist; graph indexing is proposed).
  - Cross-module event resolution (listening in `module_b.py` to events declared in `module_a.py`).
  - Detection of dangling event handlers and cyclic dependencies across packages.
- **Asynchronous & Thread-Safe Dispatch:**
  - Support for `asyncio` event handlers.
  - Thread-safe atomic counter increments in multi-threaded host environments.
- **CI/CD Guardrails & Automated Regressions:**
  - Extend CI integrations to enforce encoding consistency and behavioral preservation on pull requests; the existing GitHub Action checks files and can upload SARIF, while the broader guardrails and GitLab integration are proposed.
  - Differential behavioral testing with automated fuzz inputs.

---

## Long-Term Research & Academic Explorations

### 1. Phantom C: Polyglot Compiled Dual-Layering
*Status: Future research — not implemented. The named long-term vision of the project; see [docs/research/PHANTOM_C.md](docs/research/PHANTOM_C.md).*
- Exploring how the dual-layer model applies to compiled systems languages such as C, Rust, and Go.
- Investigating how a dual-layer representation could be carried through compilers and linkers while remaining fully inspectable.
- Studying, with falsifiable hypotheses and published negative results, what different observers (developers, tools, runtime diagnostics, security products, the OS, authorized administrators) can see. No goal of evading monitoring or concealing execution from authorized owners; no claim of undetectability.
- For complete details, see [Phantom C Research Vision](docs/research/PHANTOM_C.md).

### 2. Formal Invariant Verification
*Status: Academic Concept*
- Exploring translation of Phantom `invariant.*` declarations into formal SMT solver inputs (e.g., Z3) to mathematically prove host function properties before deployment.

### 3. Bidirectional AI Synchronization
*Status: Future research*
- Developing continuous background agents that adjust instruction layers dynamically in response to production telemetry while preserving human-authored host code intact.
