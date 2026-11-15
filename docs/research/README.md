# Phantom Research

This directory holds research notes. **A document here describes a question or a hypothesis, not a feature.** Whether something is implemented is recorded only in [../RESEARCH_STATUS.md](../RESEARCH_STATUS.md).

| Document | Contents | Status |
| :--- | :--- | :--- |
| [PHANTOM_C.md](PHANTOM_C.md) | The long-term Phantom C vision: dual-layer sources for compiled languages and observer-dependent visibility | Future research |
| [OBSERVABILITY.md](OBSERVABILITY.md) | Vocabulary for separating readability, detectability, auditability and provenance | Proposed |
| [EXPERIMENTAL_METHOD.md](EXPERIMENTAL_METHOD.md) | Required structure for any visibility experiment, including negative results | Proposed |

## Status labels

Used across the project, in this order of maturity:

- **Implemented** — shipped in v0.1.0 and covered by tests.
- **Experimental** — shipped but with documented limitations or weak guarantees.
- **Proposed** — designed, not built.
- **Hypothesis** — a testable claim that has not been tested.
- **Future research** — a direction without a design yet.
- **Out of scope for v0.1.0** — deliberately excluded from this release.

## Ground rules

1. No claim of universal invisibility or undetectability.
2. No operational guidance for evading security products or hiding execution from authorized owners.
3. Negative results are published.
4. Research does not change the guarantees of a released version.
