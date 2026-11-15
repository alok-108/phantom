# Observability Vocabulary

**Status label: Proposed.** This note fixes terms so that future Phantom C discussions do not conflate separate properties.

## Why separate the properties

"Hidden" is used loosely. A dual-layer file can be easy to read yet hard to audit, or hard to see yet trivially detected by a tool. Phantom therefore measures these independently.

| Property | Question | Example measurement |
| :--- | :--- | :--- |
| **Readability** | Can a human reading the file in a given editor notice and understand the second layer? | Fraction of reviewers who notice the instruction in a rendered diff |
| **Detectability** | Can a given tool *flag* that something unusual is present? | Detection rate of `phantom check --strict` and of named third-party tools, with false-positive rate |
| **Auditability** | Given the grammar, can an independent party decode every instruction and its effect? | Whether a clean-room decoder reproduces `phantom inspect` output |
| **Provenance** | Can the origin and author of the layer be established? | Presence and integrity of `meta.author` / VCS history |
| **Execution visibility** | Which observers can see the instruction *take effect* at runtime? | Which runtime and OS event streams record the effect |

## Encoding visibility is not execution visibility

An instruction encoded in zero-width characters is *less visible as text* than a comment. That says nothing about whether its effect is visible once the Phantom runtime acts on it: handlers run as ordinary Python, and the host process is an ordinary subprocess visible to the OS. Phantom v0.1.0 makes no attempt to change that.

## What v0.1.0 provides

- Auditability: published grammar; `phantom inspect` decodes all four encodings.
- Detectability by Phantom's own tooling: `phantom check --strict` reports invisible and bidirectional code points outside a legitimate zero-width block.
- Provenance: `meta.author`, `meta.version`.

## What v0.1.0 does not provide

- Any measurement of how third-party tools treat these encodings.
- Any claim about readability in particular editors beyond the observation that zero-width characters are usually not rendered.
