## What and why

<!-- What does this change, and why? Link the issue / proposal. -->

## Type
- [ ] Bug fix
- [ ] Docs / examples / tests only
- [ ] New or changed instruction / encoding (proposal linked: )
- [ ] Generator / provider
- [ ] Research artefact
- [ ] Other

## Checklist
- [ ] `ruff check src tests scripts` is clean
- [ ] `pytest` passes; I added positive **and** negative tests; no test was weakened
- [ ] `python scripts/verify_release.py` passes
- [ ] `SPECIFICATION.md` / docs updated where behavior changed (and `tests/test_examples.py` if CLI output changed)
- [ ] CHANGELOG entry under "Unreleased"
- [ ] Features are labelled honestly (Implemented / Experimental / Proposed / Hypothesis)
- [ ] No `eval`/`exec`/shell on instruction data or model output; no new core runtime dependency
- [ ] If this touches visibility research: it follows `docs/research/EXPERIMENTAL_METHOD.md` and contains no evasion technique

## How I tested it
<!-- Commands and results. For providers: say whether you ran it live. -->

---
⭐ *Enjoyed working on this? Consider dropping a **Star** on [alok-108/phantom](https://github.com/alok-108/phantom) to help other developers discover the project!*
