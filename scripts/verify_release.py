"""Release consistency gates for Phantom.

Checks things a test suite does not: that metadata, docs and files agree.
Exits non-zero if any gate fails. Does not build, publish or contact anything.

Requires Python 3.11+ (uses tomllib).

Usage: python scripts/verify_release.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "pyproject.toml", "README.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "SECURITY.md", "VISION.md", "ROADMAP.md", "SPECIFICATION.md",
    "AUTHORS.md", ".gitignore", ".editorconfig", ".gitattributes",
    ".pre-commit-hooks.yaml",
    "docs/INSTALLATION.md", "docs/QUICKSTART.md", "docs/LANGUAGE_GUIDE.md",
    "docs/ENCODINGS.md", "docs/RUNTIME.md", "docs/GENERATOR.md", "docs/ARCHITECTURE.md",
    "docs/COMPATIBILITY.md", "docs/TROUBLESHOOTING.md", "docs/FAQ.md",
    "docs/THREAT_MODEL.md", "docs/RESEARCH_STATUS.md", "docs/CONTRIBUTOR_GUIDE.md",
    "docs/proposals/0000-template.md", "MAINTAINERS.md", "docs/RELEASING.md", "docs/assets/demo.svg",
    "docs/assets/social-preview.png", ".github/workflows/welcome.yml",
    "docs/adr/0001-single-instruction-registry.md", ".github/dependabot.yml", ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.md", ".github/ISSUE_TEMPLATE/language_proposal.md",
    "docs/research/README.md", "docs/research/PHANTOM_C.md",
    "docs/research/OBSERVABILITY.md", "docs/research/EXPERIMENTAL_METHOD.md",
    "docs/examples/hello.py", "docs/examples/comments.py", "docs/examples/whitespace.py",
    "docs/examples/unicode.py", "docs/examples/hybrid.py", "docs/examples/events.py",
    "scripts/verify_release.py", ".github/workflows/tests.yml",
    ".github/workflows/release-checks.yml",
]

PHANTOM_C_REFERENCES = [
    "VISION.md", "ROADMAP.md", "SECURITY.md", "CHANGELOG.md",
    "docs/RESEARCH_STATUS.md", "docs/research/README.md",
]

# Phrases that would overstate what the project does.
FORBIDDEN_CLAIMS = [
    r"100\s*%\s*invisible",
    r"undetectable by (every|all|any)",
    r"guarantee[sd]? (identical|the same) behavio",
]

failures: list[str] = []


def check(ok: bool, message: str) -> None:
    print(("PASS  " if ok else "FAIL  ") + message)
    if not ok:
        failures.append(message)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    check(not missing, f"all required files exist{': missing ' + ', '.join(missing) if missing else ''}")

    pyproject = tomllib.loads(read("pyproject.toml"))
    version = pyproject["project"]["version"]
    version_py = re.search(r'__version__\s*=\s*"([^"]+)"', read("src/phantom/version.py"))
    check(version_py is not None and version_py.group(1) == version,
          f"version.py matches pyproject ({version})")
    check(f"[{version}]" in read("CHANGELOG.md"), "CHANGELOG has an entry for the version")
    check("[project.scripts]" in read("pyproject.toml")
          and pyproject["project"]["scripts"].get("phantom") == "phantom.cli:main",
          "console script 'phantom' points at phantom.cli:main")
    check(pyproject["project"]["requires-python"] == ">=3.10", "requires-python is >=3.10")
    check((pyproject["project"].get("dependencies") or []) == [],
          "core has no runtime dependencies")

    readme = read("README.md")
    check(f"**{version}**" in readme or f"Version **{version}**" in readme,
          "README states the current version")

    for rel in PHANTOM_C_REFERENCES:
        text = read(rel)
        check("PHANTOM_C" in text or "Phantom C" in text, f"{rel} references Phantom C")
    phantom_c = read("docs/research/PHANTOM_C.md")
    check("long-term research vision" in phantom_c and "not implemented" in phantom_c.lower(),
          "PHANTOM_C.md keeps the vision and states it is not implemented")

    skip_parts = {"build", "dist", "node_modules", "site-packages", "__pycache__"}
    scanned = [
        p
        for p in ROOT.rglob("*.md")
        if not any(part.startswith(".") and part != ".github" for part in p.relative_to(ROOT).parts)
        and not skip_parts & set(p.relative_to(ROOT).parts)
    ]
    for pattern in FORBIDDEN_CLAIMS:
        hits = [
            p.relative_to(ROOT).as_posix()
            for p in scanned
            if re.search(pattern, p.read_text(encoding="utf-8"), re.IGNORECASE)
            and p.name not in ("PHANTOM_C.md", "EXPERIMENTAL_METHOD.md", "verify_release.py")
        ]
        check(not hits, f"no overclaim matching /{pattern}/{' in ' + ', '.join(hits) if hits else ''}")

    # Relative links in markdown must resolve.
    broken: list[str] = []
    link = re.compile(r"\]\((?!https?://|#|mailto:)([^)#\s]+)")
    for md in scanned:
        for target in link.findall(md.read_text(encoding="utf-8")):
            if not (md.parent / target).resolve().exists():
                broken.append(f"{md.relative_to(ROOT).as_posix()} -> {target}")
    check(not broken, "markdown relative links resolve" + (": " + "; ".join(broken) if broken else ""))

    # No secrets or machine-specific paths in tracked-looking files.
    secret_patterns = [r"AIza[0-9A-Za-z_\-]{30,}", r"gh[pousr]_[0-9A-Za-z]{30,}",
                       r"sk-[0-9A-Za-z]{30,}", r"C:\\Users\\", r"/home/[a-z]+/"]
    leaks: list[str] = []
    for p in list((ROOT / "src").rglob("*.py")) + list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*")):
        if not p.is_file() or p.suffix not in {".py", ".md", ".toml", ".yml"}:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for pat in secret_patterns:
            if re.search(pat, text):
                leaks.append(f"{p.relative_to(ROOT).as_posix()} ({pat})")
    check(not leaks, "no secrets or machine-specific paths" + (": " + "; ".join(leaks) if leaks else ""))

    banned_imports = re.compile(r"\b(eval|exec)\s*\(")
    offenders = [
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "src").rglob("*.py")
        if banned_imports.search(re.sub(r'"""[\s\S]*?"""|#.*', "", p.read_text(encoding="utf-8")))
    ]
    check(not offenders, "no eval()/exec() calls in src" + (": " + ", ".join(offenders) if offenders else ""))

    print()
    if failures:
        print(f"{len(failures)} gate(s) failed")
        return 1
    print("all release gates passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
