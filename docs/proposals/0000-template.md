# Proposal NNNN: <short title>

- **Status:** Draft <!-- Draft / Accepted / Rejected / Implemented -->
- **Author:** <github handle>
- **Type:** Instruction / Encoding / Runtime / Generator / CLI / Other
- **Target version:** <e.g. 0.2.0>

## Summary
One paragraph. What changes for a user?

## Motivation
What can't be done today? Show a concrete example program. Why can't an existing instruction or tool do it?

## Specification
Exact syntax (EBNF if the grammar changes), identifier, arguments and types, encoding impact, ordering rules.

```python
#: phantom:0.1.0 category.name("example")
```

## Validation
Which rules are errors, which are warnings? Show the exact diagnostic text for each.

## Runtime behavior
What happens at `phantom run`? When is it applied (initialisation or later)? Failure behavior? Required capability (existing or new, with justification)?

## Safety and security
Does it import, execute, read/write files, use the network? How does it keep "data never becomes code"? Impact on `docs/THREAT_MODEL.md`.

## Compatibility
Effect on existing files and tools. Does an older Phantom report a clear error?

## Alternatives considered

## Testing plan
Positive tests, negative tests, round-trip/corruption tests (for encodings), example to add.

## Documentation plan
Spec sections, guides, changelog, status label (Proposed → Experimental → Implemented).

## Open questions
