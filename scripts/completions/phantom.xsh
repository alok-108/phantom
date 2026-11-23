# Xonsh completion for the Phantom command-line interface.
#
# Install by sourcing this file from your ~/.xonshrc:
#   source /path/to/phantom/scripts/completions/phantom.xsh
#
# The current CLI exposes check, inspect, run, generate, diff and verify.
# Version is a global option (--version / -V), not a subcommand. There is
# currently no decode subcommand.

from xonsh.completers.completer import add_one_completer
from xonsh.completers.tools import contextual_command_completer

_PHANTOM_SUBCOMMANDS = ("check", "inspect", "run", "generate", "diff", "verify")
_PHANTOM_GLOBAL_FLAGS = ("-h", "--help", "--version", "-V", "--no-color")
_PHANTOM_CAPABILITIES = (
    "cap.stdio",
    "cap.events",
    "cap.diagnostics",
    "cap.counters",
    "cap.metadata",
)

_PHANTOM_FLAGS = {
    "check": ("-h", "--help", "-q", "--quiet", "--strict", "--format", "--deny", "--allow-only"),
    "inspect": ("-h", "--help", "--json", "--strict", "--deny", "--allow-only"),
    "run": (
        "-h", "--help", "-q", "--quiet", "--timeout", "--max-output",
        "--deny", "--allow-only", "--handlers-from", "--allow-handler",
    ),
    "generate": (
        "-h", "--help", "--stdin", "--intent", "--placement", "--encoding", "--output", "-o",
        "--dry-run", "--provider", "--plan-file", "--allow-remote",
    ),
    "diff": ("-h", "--help", "--host-only", "--exit-code", "--no-color"),
    "verify": ("-h", "--help", "--timeout", "--max-output", "--args", "--stdin-file"),
}

_PHANTOM_VALUES = {
    "--format": ("text", "sarif"),
    "--encoding": ("comment", "whitespace", "unicode"),
    "--placement": ("beginning", "end", "line:1", "main-guard"),
    "--provider": ("gemini",),
    "--deny": _PHANTOM_CAPABILITIES,
    "--allow-only": _PHANTOM_CAPABILITIES,
}


@contextual_command_completer
def _phantom_completer(context):
    """Complete phantom subcommands, their flags and flag values."""
    if context.command != "phantom":
        return None

    words = [arg.value for arg in context.args[1:]]
    prefix = context.prefix
    subcommand = next((word for word in words if word in _PHANTOM_SUBCOMMANDS), None)

    if words and words[-1] in _PHANTOM_VALUES:
        candidates = _PHANTOM_VALUES[words[-1]]
    elif subcommand is None:
        candidates = _PHANTOM_SUBCOMMANDS + _PHANTOM_GLOBAL_FLAGS
    elif prefix.startswith("-"):
        candidates = _PHANTOM_FLAGS[subcommand]
    else:
        # A file or other positional argument: let xonsh's path completer answer.
        return None

    return {candidate for candidate in candidates if candidate.startswith(prefix)}


add_one_completer("phantom", _phantom_completer, "start")
