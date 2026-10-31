# Using Phantom in CI

`phantom check` reads files; it never executes them, so it is safe to run on pull requests from forks.

## GitHub Action

This repository ships a composite action (`action.yml`) that installs Phantom from the same revision you reference and checks every `*.py` file under the given paths.

```yaml
name: phantom
on: [pull_request]
permissions:
  contents: read
jobs:
  phantom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: hayagrivai-labs/phantom@main        # pin a tag or a commit SHA for stability
        with:
          paths: src tests                         # files or directories, space separated
          strict: "true"                           # also audit for hidden / bidirectional characters
          exclude: "tests/fixtures/*"              # optional, shell patterns
          args: "--deny cap.counters"              # optional, extra `phantom check` arguments
```

| Input | Default | Meaning |
| :--- | :--- | :--- |
| `paths` | `.` | Files or directories. Directories are searched for `*.py`; hidden directories, `venv` and `node_modules` are skipped. |
| `strict` | `true` | Adds `--strict`: reports zero-width and bidirectional characters outside `#:zw:` blocks. |
| `exclude` | empty | Space-separated shell patterns of files to skip. |
| `args` | empty | Extra arguments for `phantom check`, for example a capability policy (`--deny cap.events`, see SPECIFICATION section 9.4). |
| `python-version` | `3.12` | Python used to run Phantom. |
| `sarif` | `false` | When `"true"`, also write a SARIF log and upload it to GitHub code scanning (see below). |
| `sarif-file` | `phantom.sarif` | Path of the SARIF log to write and upload, when `sarif` is `"true"`. |

The step fails when any file has an error (exit code 2 from `phantom check`) and prints one `::error file=...` annotation per failing file. This repository runs the action on its own examples in `.github/workflows/phantom-self-check.yml`.

### Uploading SARIF to code scanning

With `sarif: "true"`, the action runs `phantom check --strict --format sarif` once over all selected files (files with no Phantom content simply contribute no findings) and uploads the result with `github/codeql-action/upload-sarif`, even when the check failed, so the findings still appear in code scanning. The job then fails if the check failed. The calling workflow must grant `security-events: write`; without it the upload step fails. This was not run against a live test repository in this change: the SARIF output was verified locally (valid SARIF 2.1.0, findings for the intentional negative example), and the upload step is the standard code scanning action.

```yaml
name: phantom-sarif
on: [pull_request]
permissions:
  contents: read
  security-events: write
jobs:
  phantom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: hayagrivai-labs/phantom@main
        with:
          paths: src
          sarif: "true"
```

## Without the action

```bash
pip install git+https://github.com/hayagrivai-labs/phantom.git
bash scripts/ci_check.sh src tests         # from a checkout of this repository
# or, per file:
phantom check --strict path/to/file.py
phantom check --format sarif path/to/file.py > phantom.sarif
```

`PHANTOM_STRICT`, `PHANTOM_EXCLUDE` and `PHANTOM_ARGS` configure `scripts/ci_check.sh` (see the header of the script).

## Running Phantom's own quality gates

The `tests` workflow runs `ruff`, the test suite on Python 3.10 to 3.13 on Linux and Windows, **mypy on three platform views** (`mypy --platform linux|win32|darwin`, because process handling branches on the platform), and a coverage gate (`fail_under = 90` in `pyproject.toml`). Locally:

```bash
ruff check src tests scripts
mypy --platform linux && mypy --platform win32      # also darwin
pytest --cov=phantom --cov-report=term-missing:skip-covered
```

The property-based tests (`tests/test_properties.py`, [hypothesis](https://hypothesis.readthedocs.io/)) generate instructions and arbitrary text; if one fails, hypothesis prints a minimal failing example and stores it in `.hypothesis/` so the next run replays it first.

### Multiline Paths

If directory paths contain spaces, pass them using YAML multiline strings:

```yaml
- uses: hayagrivai-labs/phantom@main
  with:
    paths: |
      my project/src
      tests/space dir
