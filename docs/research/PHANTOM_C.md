# Phantom C — Long-Term Research Vision

**Status label: Future research. Not implemented in v0.1.0.**

Phantom C is a long-term research vision concerning the relationship between source representation, runtime behavior, observability, and the visibility of execution to different classes of observers.

The vision is preserved as part of the original Phantom project. It is not a claim that the current release provides undetectable execution, defeats security products, or conceals activity from authorized system owners. Its hypotheses remain subject to technical investigation, measurement, and review.

---

## 1. Where Phantom C comes from

Phantom v0.1.0 shows that a second, structured layer can sit beside ordinary Python without imports or decorators. The natural next question is whether the *same idea* generalises to compiled languages (C, Rust, Go), where the "source layer" and the "running program" are separated by a compiler, a linker, and an operating system, each of which sees something different.

"Phantom C" is the name for that investigation. The "C" stands for the compiled-language setting in which the question is sharpest. It is a research programme, not a product, a compiler, or a feature of this repository.

## 2. What is and is not claimed

| Statement | Status |
| :--- | :--- |
| Phantom v0.1.0 supports Python hosts only. | Implemented |
| A dual-layer source format can carry typed instructions next to Python. | Implemented (comment, whitespace, zero-width, hybrid) |
| The same model can be expressed for a compiled language. | Hypothesis |
| Different observers see different parts of a dual-layer program. | Hypothesis (to be measured) |
| Any layer is invisible, undetectable, or unscannable. | **Not claimed.** Rejected as a goal. |
| Phantom hides execution from authorized owners or administrators. | **Not claimed. Out of scope and not a design goal.** |

Nothing in v0.1.0 contains compiled-language support, linker integration, binary sections, or any mechanism intended to avoid inspection.

## 3. Observer categories

Phantom C studies *who can see what*. These observers have different capabilities and different information sources; none of them is assumed to be blind to Phantom instructions.

1. **Developers inspecting source code.** See the text of the file. Whitespace and zero-width encodings are not visible in most editors by default, but are visible to tools that render them or to `phantom inspect --strict`.
2. **Phantom-aware development tools.** Parsers, linters, editors and review tools that implement the grammar and can decode every encoding.
3. **Runtime diagnostics.** Facilities that observe a running program: the Phantom runtime's own diagnostic records, language-level tracing, profilers.
4. **Antivirus and endpoint-security products.** Analyse files and process behaviour using signatures, heuristics and telemetry that this project does not control or model. Their reaction to an unfamiliar embedded format is an *open empirical question*, not something this project asserts or aims to defeat.
5. **Operating-system monitoring facilities.** Process, file, network and audit events recorded by the OS, independent of what the source layer says.
6. **Authorized administrators and system owners.** Hold the legitimate authority to inspect and govern the system. A dual-layer format must remain fully inspectable to them.

## 4. Open research questions

These are preserved as open questions. None has an answer in this repository.

1. Can source-level unobtrusiveness coexist with reliable inspection?
2. How does *encoding visibility* differ from *execution visibility*?
3. How do source-level, runtime-level and operating-system-level observations of the same program differ?
4. How can an unfamiliar embedded instruction format be analysed by someone who has never seen it?
5. How should readability, detectability, auditability and provenance be measured *separately*, rather than conflated?
6. How do formatters, editors, Unicode normalisation and version-control transformations affect encoded metadata?
7. What limits exist on any claim of universal invisibility?
8. How can developer privacy coexist with legitimate administrative control?
9. What evidence would be needed to support or reject a proposed visibility hypothesis?
10. What risks arise when a dual-layer source format is poorly documented?

Question 10 is already addressed in v0.1.0 by publishing a formal grammar ([SPECIFICATION.md](../../SPECIFICATION.md)), an inspection command, and a strict audit mode (`phantom check --strict`, `phantom inspect --strict`).

## 5. Research standards

Every future Phantom C proposal must state:

- the exact property being studied;
- the observer and the environment;
- assumptions;
- a falsifiable hypothesis;
- the experimental design;
- measurement criteria;
- false-positive and false-negative considerations;
- limitations;
- reproducibility requirements;
- security and ethical implications;
- results, **including negative results**.

Claims such as "100% invisible" or "undetectable by every scanner" are not acceptable conclusions; they cannot be falsified by finite testing and are not goals of this project. See [EXPERIMENTAL_METHOD.md](EXPERIMENTAL_METHOD.md).

## 6. Boundaries

- This project does not implement, document or accept contributions of operational techniques for evading antivirus or endpoint-monitoring products, or for concealing execution from authorized system owners.
- The research aim is to *understand and improve auditability*: to make dual-layer formats analysable, not to make them hard to analyse.
- Keeping this vision visible does not imply it is implemented. See [RESEARCH_STATUS.md](../RESEARCH_STATUS.md) for the status of every feature and idea.

## 7. Related documents

- [VISION.md](../../VISION.md) — why Phantom exists.
- [ROADMAP.md](../../ROADMAP.md) — where Phantom C sits in the schedule.
- [SECURITY.md](../../SECURITY.md) and [THREAT_MODEL.md](../THREAT_MODEL.md) — the security posture of the shipped release.
- [OBSERVABILITY.md](OBSERVABILITY.md) — vocabulary for visibility claims.
- [EXPERIMENTAL_METHOD.md](EXPERIMENTAL_METHOD.md) — how to run an acceptable experiment.
