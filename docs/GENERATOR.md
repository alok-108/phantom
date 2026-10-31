# Phantom Custom Code Generator

An optional, LLM-assisted workflow that proposes a *separate candidate file* containing Phantom instructions. Parsing, validation, inspection and execution never need it.

**Privacy first:** using a remote provider sends your source code to that provider's service, which processes whatever is submitted. Phantom does not claim the code stays local in that case. Nothing is sent unless you configure a provider and consent (`--allow-remote`, or answer `y` to the interactive prompt). Non-interactive runs without `--allow-remote` refuse.

## Workflow

```
program.py ──► [1 local checks] ──► [2 LLM plan] ──► [3 plan validation]
                                                       │
 candidate + diff ◄── [6 report] ◄── [5 candidate validation] ◄── [4 local transform]
```

1. **Local checks.** The input must be valid Python and at most 100 000 characters. The placement is resolved locally (`beginning`, `end`, `line:N`, `near:NAME`, `near:Class.method`, `main-guard`). An ambiguous or missing target (`near:f` with two `f`s, `near:A.m` with two `A`s or two `m`s) is reported and the model is not called. `main-guard` inserts before the first top-level `if __name__ == "__main__":` guard (`before-main-guard` is accepted as an alias).
2. **Plan.** The prompt contains the real instruction registry and the numbered source. The model must return a JSON plan (summary, encoding, instructions with arguments and rationale, expected behavior, limitations). Fenced or prose-wrapped JSON is tolerated; nothing else from the model is used.
3. **Plan validation.** Every instruction is checked against the registry: known identifier, argument count and types, supported encoding, integer line. An invented instruction is rejected. The model's own line numbers are ignored; the locally resolved line is used.
4. **Transform.** The transformer only *inserts whole lines*. It never edits, moves or removes existing lines. It refuses insertion points inside multi-line strings, brackets or backslash continuations. Line endings (LF/CRLF) are preserved.
   - **Stale or mismatched patches are rejected.** A plan instruction may carry an `anchor` (the exact text of the line it is inserted before); if the actual line differs, the plan is refused. Separately, `generate` records a SHA-256 of the input and, just before writing `--output`, re-reads the input file; if it changed during generation, the candidate is not written.
5. **Candidate validation.** The candidate must (a) be valid Python, (b) parse and validate as Phantom, and (c) have a Python AST identical to the original's. (c) is the host-preservation check: comments and blank lines cannot change an AST, so equal ASTs mean the executable program is unchanged.
6. **Report.** Plan, unified diff, and check results. The candidate is written only to the file named by `--output`, never over the input. **The candidate is never executed by `generate`.**

## Command

```bash
export GEMINI_API_KEY=...            # PowerShell: $env:GEMINI_API_KEY = "..."
pip install "phantom-lang[llm]"

phantom generate program.py --intent "count requests and note startup" \
    --placement end --encoding comment --allow-remote --output candidate.py
```

| Option | Meaning |
| :--- | :--- |
| `FILE` / `--stdin` | Program to annotate |
| `--intent TEXT` | What Phantom should do. Prompted interactively if omitted on a terminal; required otherwise |
| `--placement` | `beginning` (default), `end`, `line:N`, `near:NAME`, `near:Class.method`, `main-guard` (alias: `before-main-guard`). Asked interactively if omitted on a terminal |
| `--encoding` | Asked interactively if omitted on a terminal. `comment` (default; `comments` accepted), `whitespace`, `unicode`. `hybrid` is refused by the generator: it cannot be validated reliably for LLM-chosen layouts |
| `--output PATH` | Write the candidate here. Must differ from the input |
| `--dry-run` | Show plan and diff; write nothing |
| `--provider` | `gemini` (the only built-in) |
| `--plan-file PATH` | Use a local JSON plan instead of calling a provider; offline, nothing is sent (used by [the examples](examples/README.md)) |
| `--allow-remote` | Consent to sending the source to the provider |

Exit codes: `0` candidate produced and validated, `1` usage/configuration/consent error, `2` generation or validation failed.

Then compare:

```bash
phantom diff program.py candidate.py
phantom diff --host-only program.py candidate.py
phantom verify program.py candidate.py     # executes BOTH files — only for code you trust
phantom verify program.py candidate.py --args hello --args bye --stdin-file in.txt
```

`phantom diff --host-only` excludes the Phantom instruction layer using the existing host-layer diff helper. It only reads the files; it does not execute or modify either program. An empty diff indicates unchanged host text, not verified runtime equivalence. Without the flag, `phantom diff` continues to compare the complete source files.

`phantom diff` colors added lines green, removed lines red, and hunk headers cyan. Pass `--no-color` (before or after `diff`, e.g. `phantom diff --no-color program.py candidate.py`) or set the `NO_COLOR` environment variable to any value (per https://no-color.org) to get plain diff output with no ANSI escapes.


Running the candidate is a separate, explicit step by you (`phantom run candidate.py`).

## Providers

`phantom.generator.provider.LLMProvider` is a one-method interface (`complete(prompt) -> str`). Included:

- `GeminiProvider` — uses the optional `google-genai` package and `GEMINI_API_KEY`. The model defaults to `gemini-2.5-flash` and can be changed with `PHANTOM_GEMINI_MODEL`. Requests use a 60-second timeout. The call shape (`genai.Client(api_key=…, http_options=HttpOptions(timeout=ms))`, `client.models.generate_content(model=…, contents=…)`) was checked against `google-genai` 2.32.0. **It has not been exercised against the live API** (no key, no paid calls): the tests drive it with a fake SDK. Check the current `google-genai` documentation and available model names before relying on it.
- `RetryingProvider` — wraps any provider with bounded retries (default 2, max 5) and exponential backoff.
- `StaticProvider` — returns canned text; used by the tests and useful offline.

Errors from providers are passed through `redact()`, which masks the configured key and common key/token patterns. Redaction is best-effort pattern matching, not a guarantee.

Library use:

```python
from phantom.generator import GenerationRequest, StaticProvider, generate
result = generate(GenerationRequest(source_code=src, intent="…", placement="end"), provider)
result.success, result.diff, result.candidate_source, result.errors
```

## Behavior comparison (`phantom verify`)

`compare_behavior` runs the original and candidate in subprocesses (30 s timeout each) and compares stdout, stderr and exit code. Both programs are copied into temporary directories under the **same file name** (`program.py`), and the temporary directory is masked in both streams, so a program that prints its own path (`__file__`, `sys.argv[0]`) is not reported as different. Line numbers inside tracebacks of the script are masked too, because the candidate has extra lines.

| Result | Meaning | Exit |
| :--- | :--- | :--- |
| Tested equivalence for the single tested run | identical on this one run | 0 |
| Tested equivalence for N cases | identical on every case given | 0 |
| Behavior difference detected | stdout, stderr or exit code differ in at least one case | 1 |
| Validation failed | a file is not valid Python | 2 |
| Not verified (inconclusive) | no case differs, but at least one case timed out, failed to start, **or both programs failed with the same output** (for example because they import sibling modules or read files next to themselves, which are not in the temporary directory) | 3 |

### Multiple cases

Each use of ``--args`` starts one case with those arguments, and each use of ``--stdin-file`` gives one case the contents of that file as stdin. Cases are paired by position: the first argument group goes with the first stdin file, the second with the second, and so on. A case with no partner on one side gets no arguments or no stdin file on that side. With no case option at all, `verify` runs the single default case: no arguments and an empty stdin.

A case with a stdin file feeds the same bytes to both programs, so that case is a genuine comparison. A case with no stdin file gets an empty stdin (a program that reads input sees end-of-file), never Phantom's own stdin: sharing it let the first program consume piped input while the second saw EOF, so identical programs were reported as different (#82). `phantom run` still passes its stdin through, so interactive hosts keep working there. An argument that starts with a dash needs the ``--args=VALUE`` form so it is not read as another option.

Per case output names the case, its arguments, and its stdin file, and differences are reported per case. The overall result is a difference when any case differs, inconclusive when no case differs but some case is inconclusive, and equivalent only when every case matches.

An "equivalent" result is **not** a proof for other inputs. With no case option it exercises one run with no arguments and an empty stdin; with case options it exercises only the cases given. It does not capture return values, filesystem or network effects, timing, randomness, environment, or concurrency. The static AST check in step 5 is the stronger evidence for host preservation; `verify` complements it.

`verify` executes both programs in the current environment. It is not a sandbox. Do not use it on untrusted code.

## What the generator will not do

- Invent instructions: the registry is the only vocabulary.
- Fulfil requests the instruction set cannot express (for example "trace every function call"); such a request yields a plan that fails validation or an empty plan, with the errors shown.
- Modify host code, overwrite the input, run the candidate, or contact a provider without consent.
