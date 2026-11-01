"""Phantom's own source must not contain the characters it warns about.

Invisible and bidirectional characters embedded in source are exactly the "Trojan Source"
problem `phantom check --strict` exists to find, so the code that handles them spells them
as explicit code points (``chr(0x202E)``) and a reviewer can read every line.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCANNED = [
    *sorted((ROOT / "src").rglob("*.py")),
    *sorted((ROOT / "scripts").rglob("*.py")),
    *sorted((ROOT / ".github").rglob("*.yml")),
    ROOT / "action.yml",
    ROOT / "pyproject.toml",
]
# Categories: Cf (format: zero-width, bidi), Zl/Zp (line and paragraph separators),
# Cc (control) except the ordinary whitespace controls.
SUSPICIOUS_CATEGORIES = {"Cf", "Zl", "Zp", "Cc"}
ALLOWED_CONTROLS = {"\n", "\r", "\t", "\x0c"}


def _suspicious(text: str) -> list[tuple[int, str]]:
    found = []
    for line_no, line in enumerate(text.split("\n"), start=1):
        for ch in line:
            if unicodedata.category(ch) in SUSPICIOUS_CATEGORIES and ch not in ALLOWED_CONTROLS:
                found.append((line_no, f"U+{ord(ch):04X}"))
    return found


def test_the_scanner_itself_finds_hidden_characters():
    assert _suspicious("a" + chr(0x200B) + "b\nc" + chr(0x202E)) == [(1, "U+200B"), (2, "U+202E")]
    assert _suspicious("plain text\twith\r\nwhitespace") == []


def test_project_source_contains_no_invisible_or_bidirectional_characters():
    problems = {}
    for path in SCANNED:
        if not path.exists():
            continue
        found = _suspicious(path.read_text(encoding="utf-8"))
        if found:
            problems[str(path.relative_to(ROOT))] = found
    assert problems == {}, f"hidden characters in project files: {problems}"

def test_py_typed_exists():
    assert (ROOT / "src" / "phantom" / "py.typed").is_file()


# Bash and zsh completion scripts must offer every subcommand and, scoped to
# each subcommand's case branch, every flag the live CLI accepts for it.
# Flags are the long form without dashes; value lists are checked separately.
COMPLETION_SCRIPTS = {
    "bash": ROOT / "scripts" / "completions" / "phantom.bash",
    "zsh": ROOT / "scripts" / "completions" / "phantom.zsh",
}
EXPECTED_COMPLETION_SUBCOMMANDS = ("check", "inspect", "run", "generate", "diff", "verify")
EXPECTED_COMPLETION_FLAGS = {
    "check": ("strict", "format", "deny", "allow-only"),
    "inspect": ("json", "strict", "deny", "allow-only"),
    "run": ("timeout", "deny", "allow-only", "handlers-from", "allow-handler"),
    "generate": ("stdin", "intent", "placement", "encoding", "output", "dry-run", "provider", "plan-file", "allow-remote"),
    "diff": ("host-only", "no-color"),
    "verify": ("timeout",),
}
EXPECTED_COMPLETION_VALUES = ("sarif", "whitespace", "unicode")


def _completion_branch(text: str, subcommand: str) -> str:
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.strip() == f"{subcommand})")
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == ";;")
    return "\n".join(lines[start:end])


def test_shell_completion_scripts_cover_cli():
    for shell, path in COMPLETION_SCRIPTS.items():
        assert path.exists(), f"scripts/completions/{path.name} is missing"
        text = path.read_text(encoding="utf-8")
        for subcommand in EXPECTED_COMPLETION_SUBCOMMANDS:
            assert subcommand in text, f"{shell} completions miss subcommand {subcommand}"
            branch = _completion_branch(text, subcommand)
            for flag in EXPECTED_COMPLETION_FLAGS[subcommand]:
                assert f"--{flag}" in branch, (
                    f"{shell} completions miss --{flag} scoped to {subcommand}"
                )
        for value in EXPECTED_COMPLETION_VALUES:
            assert value in text, f"{shell} completions miss the {value} value"


FISH_COMPLETION = ROOT / "scripts" / "completions" / "phantom.fish"
EXPECTED_FISH_SUBCOMMANDS = ("check", "inspect", "run", "generate", "diff", "verify")
# Flags the completion script must offer per subcommand (long form, no dashes).
EXPECTED_FISH_FLAGS = {
    "check": ("strict", "format", "deny", "allow-only"),
    "run": ("timeout", "deny", "allow-only", "handlers-from", "allow-handler"),
}


def test_fish_completion_script_covers_cli():
    assert FISH_COMPLETION.exists(), "scripts/completions/phantom.fish is missing"
    text = FISH_COMPLETION.read_text(encoding="utf-8")
    for subcommand in EXPECTED_FISH_SUBCOMMANDS:
        assert f"-a {subcommand}" in text, f"fish completions miss subcommand {subcommand}"
    for subcommand, flags in EXPECTED_FISH_FLAGS.items():
        condition = f"__fish_seen_subcommand_from {subcommand}"
        for flag in flags:
            line = next(
                (
                    line
                    for line in text.splitlines()
                    if f"-l {flag}" in line and condition in line
                ),
                None,
            )
            assert line is not None, (
                f"fish completions miss --{flag} scoped to {subcommand}"
            )
    assert "sarif" in text, "fish completions miss the sarif output format"


# Nano syntax highlighting for the Phantom instruction layer must exist and
# cover the documented instruction keywords and encoding markers (#121).
NANORC = ROOT / "scripts" / "syntax" / "phantom.nanorc"
PHANTOM_NANO_INSTRUCTIONS = (
    "event.declare",
    "event.on",
    "diagnostic.note",
    "diagnostic.warn",
    "counter.create",
    "counter.increment",
    "counter.decrement",
    "counter.reset",
    "meta.author",
    "meta.version",
    "meta.license",
    "meta.tags",
)
PHANTOM_NANO_MARKERS = ("#:ws:begin", "#:ws:end", "#:zw:begin", "#:zw:end", "#:phantom:hybrid")


def test_nano_syntax_highlights_phantom_instructions():
    assert NANORC.is_file(), "scripts/syntax/phantom.nanorc is missing"
    text = NANORC.read_text(encoding="utf-8")
    assert 'syntax "phantom" "\\.py$"' in text, "nanorc must define the phantom syntax for *.py"
    assert "#:[[:space:]]*phantom:[0-9]" in text, (
        "nanorc must highlight the #: phantom:<version> prefix"
    )
    for instruction in PHANTOM_NANO_INSTRUCTIONS:
        escaped = instruction.replace(".", r"\.")
        assert escaped in text, f"nanorc does not highlight {instruction}"
    for marker in PHANTOM_NANO_MARKERS:
        assert marker in text, f"nanorc does not highlight the {marker} marker"


def test_nano_syntax_prefix_is_anchored_to_phantom_comments():
    text = NANORC.read_text(encoding="utf-8")
    prefix_rules = [line for line in text.splitlines() if "phantom:[0-9]" in line]
    assert prefix_rules, "nanorc has no Phantom version-prefix rule"
    for rule in prefix_rules:
        assert '"^[[:space:]]*#:' in rule, (
            "the Phantom prefix rule must be anchored to a '#' comment, "
            "otherwise ordinary text is highlighted as an instruction"
        )


# Sublime text syntax highlighting test
# Check that scripts/syntax/Phantom.sublime-syntax exists and
# covers all keywords and markers (mirrored from nano test)
SUBLIME_SYNTAX = ROOT / "scripts" / "syntax" / "Phantom.sublime-syntax"
PHANTOM_SUBLIME_INSTRUCTIONS = (
    "event.declare",
    "event.on",
    "diagnostic.note",
    "diagnostic.warn",
    "counter.create",
    "counter.increment",
    "counter.decrement",
    "counter.reset",
    "meta.author",
    "meta.version",
    "meta.license",
    "meta.tags",
)
PHANTOM_SUBLIME_MARKERS = (
    "#:ws:begin",
    "#:ws:end",
    "#:zw:begin",
    "#:zw:end",
    "#:phantom:hybrid",
)


def test_sublime_syntax_highlights_phantom_instructions():
    assert SUBLIME_SYNTAX.is_file(), "scripts/syntax/Phantom.sublime-syntax is missing"
    text = SUBLIME_SYNTAX.read_text(encoding="utf-8")
    assert "%YAML 1.2" in text, "Phantom.sublime-syntax must use %YAML 1.2 format"
    assert "#: phantom:[0-9]" in text, (
        "Phantom.sublime-syntax must highlight the #: phantom:<version> prefix"
    )
    for instruction in PHANTOM_SUBLIME_INSTRUCTIONS:
        escaped = instruction.replace(".", r"\.")
        assert escaped in text, f"Phantom.sublime-syntax does not highlight {instruction}"
    for marker in PHANTOM_SUBLIME_MARKERS:
        assert marker in text, f"Phantom.sublime-syntax does not highlight the {marker} marker"


def test_sublime_syntax_prefix_is_anchored_to_phantom_comments():
    text = SUBLIME_SYNTAX.read_text(encoding="utf-8")
    prefix_rules = [line for line in text.splitlines() if "phantom:[0-9]" in line]
    assert prefix_rules, "Phantom.sublime-syntax has no Phantom version-prefix rule"
    for rule in prefix_rules:
        assert "#: phantom:" in rule, (
            "the Phantom prefix rule must be anchored to a '#:' comment"
        )


def test_sublime_syntax_prefix_matches_a_full_semver():
    # The spec version is major.minor.patch; a two-component pattern leaves
    # the patch segment (".0" in "0.1.0") unhighlighted.
    text = SUBLIME_SYNTAX.read_text(encoding="utf-8")
    assert r"#: phantom:[0-9]+\.[0-9]+\.[0-9]+" in text, (
        "the Phantom prefix rule must match a full major.minor.patch version"
    )


PRE_COMMIT_HOOKS = ROOT / ".pre-commit-hooks.yaml"


def test_pre_commit_hooks_definition_is_valid():
    assert PRE_COMMIT_HOOKS.is_file(), ".pre-commit-hooks.yaml is missing"
    raw = PRE_COMMIT_HOOKS.read_text(encoding="utf-8")

    try:
        import yaml
    except ImportError:  # PyYAML is optional; fall back to a structural check.
        pass
    else:
        loaded = yaml.safe_load(raw)
        assert isinstance(loaded, list), ".pre-commit-hooks.yaml must be a list"
        hooks = {hook["id"]: hook for hook in loaded}
        assert set(hooks) == {"phantom-check", "phantom-strict"}
        assert hooks["phantom-check"]["entry"] == "phantom check"
        assert hooks["phantom-strict"]["entry"] == "phantom check --strict"
        for hook in hooks.values():
            assert hook["language"] == "python"
            assert hook["types"] == ["python"]
            assert hook["pass_filenames"] is True
            assert hook["name"] and hook["description"]
        return

    for token in (
        "id: phantom-check",
        "id: phantom-strict",
        "entry: phantom check",
        "entry: phantom check --strict",
        "language: python",
        "types: [python]",
        "pass_filenames: true",
    ):
        assert token in raw, f".pre-commit-hooks.yaml missing {token!r}"

POWERSHELL_COMPLETION = ROOT / "scripts" / "completions" / "phantom.ps1"
EXPECTED_POWERSHELL_FLAGS = {
    "check": ("strict", "format", "deny", "allow-only"),
    "inspect": ("json", "strict", "deny", "allow-only"),
    "run": ("timeout", "deny", "allow-only", "handlers-from", "allow-handler"),
    "generate": ("stdin", "intent", "placement", "encoding", "output", "dry-run", "provider", "plan-file", "allow-remote"),
    "diff": ("host-only", "no-color"),
    "verify": ("timeout",),
}


def test_powershell_completion_script_covers_cli():
    assert POWERSHELL_COMPLETION.exists(), "scripts/completions/phantom.ps1 is missing"
    text = POWERSHELL_COMPLETION.read_text(encoding="utf-8")
    assert "Register-ArgumentCompleter" in text
    for subcommand in EXPECTED_COMPLETION_SUBCOMMANDS:
        assert subcommand in text, f"powershell completions miss subcommand {subcommand}"
    for subcommand, flags in EXPECTED_POWERSHELL_FLAGS.items():
        for flag in flags:
            assert f"--{flag}" in text, f"powershell completions miss --{flag} for {subcommand}"
    for value in EXPECTED_COMPLETION_VALUES:
        assert value in text, f"powershell completions miss the {value} value"


EMACS_MODE = ROOT / "scripts" / "syntax" / "phantom-mode.el"
PHANTOM_EMACS_INSTRUCTIONS = (
    "event.declare",
    "event.on",
    "diagnostic.note",
    "diagnostic.warn",
    "counter.create",
    "counter.increment",
    "counter.decrement",
    "counter.reset",
    "meta.author",
    "meta.version",
    "meta.license",
    "meta.tags",
)
PHANTOM_EMACS_MARKERS = ("#:ws:begin", "#:ws:end", "#:zw:begin", "#:zw:end", "#:phantom:hybrid")


def test_emacs_mode_highlights_phantom_instructions():
    assert EMACS_MODE.is_file(), "scripts/syntax/phantom-mode.el is missing"
    text = EMACS_MODE.read_text(encoding="utf-8")
    assert "define-derived-mode phantom-mode python-mode" in text, (
        "phantom-mode.el must derive from python-mode"
    )
    assert "#: *phantom:[0-9]" in text, (
        "phantom-mode.el must highlight the #: phantom:<version> prefix"
    )
    for instruction in PHANTOM_EMACS_INSTRUCTIONS:
        assert instruction in text, f"phantom-mode.el does not highlight {instruction}"
    for marker in PHANTOM_EMACS_MARKERS:
        assert marker in text, f"phantom-mode.el does not highlight the {marker} marker"


# Micro editor syntax definition must cover the instruction layer (#210).
MICRO_SYNTAX = ROOT / "scripts" / "syntax" / "phantom.yaml"


def test_micro_syntax_highlights_phantom_instructions():
    assert MICRO_SYNTAX.is_file(), "scripts/syntax/phantom.yaml is missing"
    text = MICRO_SYNTAX.read_text(encoding="utf-8")
    assert "filetype: phantom" in text, "phantom.yaml must define the phantom filetype"
    assert r"filename: '\.py$'" in text, "phantom.yaml must detect *.py files"
    assert r"#:\s*phantom:[0-9]" in text, (
        "phantom.yaml must highlight the #: phantom:<version> prefix"
    )
    for instruction in PHANTOM_NANO_INSTRUCTIONS:
        escaped = instruction.replace(".", r"\.")
        assert escaped in text, f"phantom.yaml does not highlight {instruction}"
    for marker in PHANTOM_NANO_MARKERS:
        assert marker in text, f"phantom.yaml does not highlight the {marker} marker"
