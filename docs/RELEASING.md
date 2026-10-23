# Releasing

How a Phantom release is made. Maintainers only.

## Where releases live today

Releases are GitHub releases with a wheel and an sdist attached (for example
[v0.1.0](https://github.com/hayagrivai-labs/phantom/releases/tag/v0.1.0)). Phantom is installable with
`pip install git+https://github.com/hayagrivai-labs/phantom.git` or from a downloaded wheel.

**It is not on PyPI, and the name `phantom-lang` cannot be used there.** On 2026-10-21 that name
was already taken by an unrelated project ("Phantom ML compiler", versions 0.1.0 and 0.2.0). Before
any PyPI upload the distribution name must change (in `pyproject.toml` `[project] name`, the docs
and the CI smoke test). The import package `phantom` also collides with that project's import
name, so decide on the import name at the same time. A version number can be uploaded to PyPI only
once, so rehearse on TestPyPI first.

## Each release

1. Update `version` in `pyproject.toml` and `__version__` in `src/phantom/version.py`.
2. Move the `[Unreleased]` entries in `CHANGELOG.md` under the new version heading with a date.
3. Make sure `main` is green: `ruff check src tests scripts`, `pytest`,
   `python scripts/verify_release.py`, and the `tests` workflow.
4. Build and smoke-test in a clean environment:
   ```bash
   python -m build
   python -m venv /tmp/clean && /tmp/clean/bin/pip install dist/*.whl
   /tmp/clean/bin/phantom --version && /tmp/clean/bin/phantom check docs/examples/comments.py
   ```
5. Tag and release. Pushing a `vX.Y.Z` tag runs the `release-checks` workflow, which fails if the
   tag does not match the package version.
   ```bash
   git tag vX.Y.Z && git push origin vX.Y.Z
   gh release create vX.Y.Z dist/* --title "Phantom X.Y.Z" --notes-file notes.md
   ```
6. Thank every contributor with a merged pull request by name in the release notes (`gh pr list --state merged --search "merged:>=YYYY-MM-DD"` helps). Release notes must list only what is implemented and tested, say what was **not** verified
   (for example the live Gemini provider, macOS), and keep Phantom C described as research.
7. Verify the release page, the attached files and the CI run for the tag.

## Version policy

Semantic Versioning (see [SPECIFICATION.md](../SPECIFICATION.md) section 11). Adding an
instruction is a minor release; changing the meaning of an existing one is major.
