# Experimental Method

**Status label: Proposed.** Any experiment about visibility, detection or observer behaviour must follow this template before results are reported in this repository.

## Template

1. **Property.** Name exactly one property from [OBSERVABILITY.md](OBSERVABILITY.md).
2. **Observer and environment.** Tool, version, configuration, OS, and whether the system belongs to the experimenter. Experiments are run only on systems the experimenter owns or is authorised to test.
3. **Assumptions.** What is taken for granted (default settings, no tuning, etc.).
4. **Hypothesis.** Falsifiable and bounded, e.g. "Editor X renders zero-width characters as visible glyphs in diff view." Never "X cannot see it."
5. **Design.** Corpus (including benign controls with *no* Phantom content), sample size, randomisation, how inputs are generated (use `scripts/build_examples.py`-style generators so inputs are reproducible).
6. **Measurement.** Metric, how a positive is decided, and who decides.
7. **Error analysis.** False positives on the benign controls; false negatives; confidence intervals where a rate is reported.
8. **Limitations.** Version-specificity, configuration-specificity, sample limits.
9. **Reproducibility.** Exact versions, commands, and the input files or generators.
10. **Ethics and security review.** Who could be harmed by publishing this result. Results that primarily help evade monitoring of systems the reader does not own are not published here.
11. **Results, including negative results.** A hypothesis that fails is reported with the same prominence as one that holds.

## Acceptance rules

- A result is valid only for the versions and settings tested.
- "No detection observed" is reported as exactly that, never as "undetectable".
- Proposals that cannot satisfy items 1–11 stay labelled **Hypothesis** or **Future research** in [RESEARCH_STATUS.md](../RESEARCH_STATUS.md).
