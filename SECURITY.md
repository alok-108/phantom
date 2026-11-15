# Security Policy

This document states Phantom's security posture honestly, including what it does *not* protect against. The full analysis is in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## Supported versions

| Version | Status |
| :--- | :--- |
| 0.1.x | Current (pre-release until published) |

## Posture

1. **No implicit execution.** Standard Python does not execute Phantom instructions. They take effect only under `phantom run`. Parsing, `check`, `inspect` and `diff` read text and never execute or rewrite your files (regression-tested).
2. **No evaluation of instruction data.** Decoded text is parsed into typed string/integer literals and dispatched through an explicit handler per registry entry. There is no `eval`, `exec` or shell use on it. Unknown instructions fail.
3. **Validation before dispatch.** Errors stop `phantom run` before anything is applied or executed.
4. **Capabilities.** Each instruction maps to a named capability (`cap.stdio`, `cap.events`, `cap.diagnostics`, `cap.counters`, `cap.metadata`). Library users can restrict them; the CLI grants all.
5. **Inspection of hidden encodings.** `phantom check --strict` and `phantom inspect --strict` report bidirectional controls, rejected invisible code points, and zero-width characters outside a legitimate `#:zw:` block. They do **not** detect homoglyphs. Whitespace and zero-width encodings are not secrets and provide no security.
6. **LLM generator.** Opt-in. Your source is sent to the remote provider only after explicit consent; the provider processes whatever is submitted. Model output is treated as untrusted data (JSON plan validated against the registry; insert-only transformation; AST-equality check); generated code is never run automatically; the original file is never overwritten.
7. **Interpreter integrity.** Phantom installs no import hooks, `sitecustomize` or startup files and changes no environment settings.

## Important caveats

- **`phantom run` and `phantom verify` execute programs with your privileges, with no sandbox.** Run only files you trust, or use a container/VM.
- **Handler paths import modules.** `event.on(…, "pkg.func")` imports `pkg` when the event fires, executing its top-level code. Treat it like an `import` statement. There is no allow-list yet.
- Redaction of secrets in Phantom's output is best-effort pattern matching.

## Research and Phantom C

[Phantom C](docs/research/PHANTOM_C.md) is a long-term research vision about source representation, runtime behavior and the visibility of execution to different observers. It is **not implemented**, introduces no hidden capability into this release, and is **not** a claim of undetectable execution or of defeating security products. This project does not implement, document or accept contributions of techniques for evading antivirus or endpoint-monitoring products, or for concealing execution from authorized system owners.

## Reporting a vulnerability

No dedicated security mailbox is published for this project, and none is invented here. Report privately to the maintainer (GitHub: [alok-108](https://github.com/alok-108)); private vulnerability reporting is enabled on [the repository](https://github.com/hayagrivai-labs/phantom/security/advisories/new), so please use that. Please include: affected version, a minimal source file, steps to reproduce, and impact. Please do not disclose publicly before a fix is available.

Examples of relevant issues: parser crashes or hangs on crafted input, any path from instruction data to code execution, capability bypass, encoding spoofing that defeats `--strict`, generator behavior that modifies host code or writes to the input file.
