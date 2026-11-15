---
name: Language proposal
about: New or changed instruction, encoding, capability or runtime semantics
labels: proposal, language
---

Read [docs/CONTRIBUTOR_GUIDE.md section 8](https://github.com/hayagrivai-labs/phantom/blob/main/docs/CONTRIBUTOR_GUIDE.md#8-proposing-a-language-change) first.

**Motivation** - a concrete example program that cannot be expressed today.

**Syntax** (exact line(s) as they would appear):

```python
#: phantom:0.1.0 ...
```

**Arguments and types**

**Validation** - what is an error, what is a warning?

**Runtime behavior** - when applied, what it does, failure behavior, required capability.

**Safety** - does it import, execute, read/write files or use the network? How does "data never becomes code" still hold?

**Compatibility**

For anything non-trivial, a PR adding `docs/proposals/NNNN-name.md` (from `0000-template.md`) is the next step.
