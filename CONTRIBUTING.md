# Contributing to Phantom

Thanks for wanting to help. Phantom is an early-stage open-source language project and **contributions of every size are welcome**, from typo fixes to new instructions, providers and research experiments. By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

> Want to extend the idea itself (new instruction, encoding, provider, experiment)? Read the **[Contributor Guide](docs/CONTRIBUTOR_GUIDE.md)**. It has a step-by-step walkthrough for each.

## Quick start

```bash
git clone https://github.com/hayagrivai-labs/phantom.git      # or your fork
cd phantom
python -m venv .venv
source .venv/bin/activate                              # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Or open a ready-made environment with one click: [GitHub Codespaces](https://codespaces.new/hayagrivai-labs/phantom) (uses `.devcontainer/devcontainer.json`; it installs the dev extras and runs the tests).

Optional, for the LLM generator: `pip install -e ".[all]"` (needs Python ≥ 3.10).

## Your first pull request in about 10 minutes

1. Pick an issue labelled [`good first issue`](https://github.com/hayagrivai-labs/phantom/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) and comment `/take` on it: you are assigned automatically (up to two open issues at a time). Changed your mind? Comment `/release`. Claims with no activity for about three weeks are released automatically.
2. Fork the repo on GitHub, then:
   ```bash
   git clone https://github.com/<you>/phantom.git && cd phantom
   git checkout -b my-change
   python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   pytest -q                                              # everything should pass before you start
   ```
3. Make the change, and add a test that fails without it.
4. Run the checks: `ruff check src tests scripts && pytest -q && python scripts/verify_release.py`.
5. Push and open a pull request; fill in the template. A maintainer approves the first CI run on a fork, so it may take a short while to start.
6. Respond to review comments by pushing more commits to the same branch.

Stuck at any step? Ask in the issue; that is what `mentor available` is for.

## Before every pull request

```bash
ruff check src tests scripts
pytest
python scripts/verify_release.py        # needs Python 3.11+
```

CI runs the tests on Python 3.10–3.13 on Ubuntu and Windows and the release checks on Ubuntu. The PR checklist is in [docs/CONTRIBUTOR_GUIDE.md §9](docs/CONTRIBUTOR_GUIDE.md#9-definition-of-done-for-a-pr).

## Ways to contribute

| You want to… | Start here |
| :--- | :--- |
| Fix a bug, improve an error message, add tests | Pick an issue labelled `good first issue`, or open one |
| Improve docs or add an example | [Guide §1](docs/CONTRIBUTOR_GUIDE.md#1-small-fixes-and-first-contributions) |
| Add an instruction | [Guide §3](docs/CONTRIBUTOR_GUIDE.md#3-add-an-instruction) (four code edits) |
| Add or change an encoding | [Guide §4](docs/CONTRIBUTOR_GUIDE.md#4-add-or-change-an-encoding) |
| Add an LLM provider | [Guide §5](docs/CONTRIBUTOR_GUIDE.md#5-add-an-llm-provider) |
| Improve the generator or `verify` | [Guide §6](docs/CONTRIBUTOR_GUIDE.md#6-improve-the-generator-and-verify) |
| Run a visibility / Phantom C experiment | [Guide §7](docs/CONTRIBUTOR_GUIDE.md#7-research-contributions) |
| Propose a language change | [Guide §8](docs/CONTRIBUTOR_GUIDE.md#8-proposing-a-language-change) and the proposal template |
| Report a security issue | [SECURITY.md](SECURITY.md); do not open a public issue |

## Finding something to work on

Issues are labelled so you can pick by size and area:

| Label | Meaning |
| :--- | :--- |
| `good first issue` | Small, well specified, no design decisions |
| `difficulty: easy` / `medium` / `hard` | A few hours / needs some knowledge of the codebase / design decisions or tricky edge cases |
| `area: cli`, `parser`, `validator`, `runtime`, `generator`, `encodings`, `ci`, `docs` | Where in the code the work is |
| `mentor available` | A maintainer will help with questions and review |
| `needs design` | Discuss the approach in the issue before writing code |
| `help wanted` | Maintainers would welcome a contribution |
| `feedback` | We want to hear how you use it |

To take an issue, comment on it so nobody duplicates the work. A draft pull request is fine, and
so is asking questions in the issue. Architecture decisions are recorded in [docs/adr/](docs/adr/);
read them before proposing changes to the model.

## Project principles

1. **The specification is the contract.** Language changes start in [SPECIFICATION.md](SPECIFICATION.md).
2. **Honest claims.** Label features *Implemented / Experimental / Proposed / Hypothesis*; document limits; never claim more than is tested.
3. **Data never becomes code.** No `eval`/`exec`/shell on decoded instructions or model output.
4. **Parsing and inspection have no side effects.** They never execute or rewrite files.
5. **No evasion tooling.** Phantom C is a research vision about observability and auditability, not about hiding execution from monitors or authorized owners ([details](docs/research/PHANTOM_C.md)).

## Code style

- Python ≥ 3.10; `from __future__ import annotations` at the top of every module.
- Type hints on public functions; short docstrings where behavior isn't obvious.
- `ruff check` is the enforced style tool (line length 100 soft). `ruff format` is **not** enforced and must not be run over `docs/examples/` (whitespace-encoded files are sensitive to formatters).
- Tests live in `tests/`; every behavior change needs a positive and a negative test. Never weaken a test to make it pass.
- If you change CLI output, update the docs and `tests/test_examples.py` together.

## Pull requests

1. Open or comment on an issue first for anything larger than a small fix.
2. Branch from `main` (`git checkout -b fix/short-description`).
3. Keep PRs focused; include tests and docs in the same PR.
4. Fill in the PR template. Explain *why*, not only *what*.
5. A maintainer will review; please respond to feedback in the same PR.

## Reporting bugs and requesting features

Use the issue templates: **Bug report**, **Feature request**, **Language proposal**, **Research proposal**. For bugs, include `phantom --version`, Python version, OS, a minimal source file, the exact command and the full output.

## License

By contributing you agree that your contributions are licensed under the project's [MIT License](LICENSE).
