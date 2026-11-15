"""Regenerate the encoded example files under docs/examples/.

whitespace.py, unicode.py and hybrid.py contain invisible payloads that cannot
be written reliably by hand, so they are produced from the encoders.

Usage: python scripts/build_examples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from phantom.encoding import HybridCodec, encode_instruction  # noqa: E402
from phantom.ir import (  # noqa: E402
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    SourceLocation,
)

EXAMPLES = ROOT / "docs" / "examples"

HOST = '''"""{title}"""


def main() -> None:
    print("Executing core Python logic!")


if __name__ == "__main__":
    main()

'''


def _inst(itype: InstructionType, *args: object) -> PhantomInstruction:
    built = tuple(
        Argument(ArgumentType.INTEGER if isinstance(a, int) else ArgumentType.STRING, a)
        for a in args
    )
    return PhantomInstruction(itype, built, SourceLocation("example", 1))


def _write(name: str, body: str) -> None:
    (EXAMPLES / name).write_text(body, encoding="utf-8", newline="\n")
    print("wrote", name)


def main() -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)

    note = _inst(InstructionType.DIAGNOSTIC_NOTE, "hidden in whitespace")
    _write(
        "whitespace.py",
        HOST.format(title="Whitespace-encoded instruction (one byte per tab/space line).")
        + encode_instruction(note, EncodingMode.WHITESPACE)
        + "\n",
    )

    note = _inst(InstructionType.DIAGNOSTIC_NOTE, "hidden in zero-width characters")
    _write(
        "unicode.py",
        HOST.format(title="Zero-width-encoded instruction (4 invisible characters per byte).")
        + encode_instruction(note, EncodingMode.UNICODE)
        + "\n",
    )

    instructions = [
        _inst(InstructionType.META_AUTHOR, "Hybrid Example"),
        _inst(InstructionType.DIAGNOSTIC_NOTE, "from whitespace"),
        _inst(InstructionType.DIAGNOSTIC_NOTE, "from zero-width"),
    ]
    hybrid = HybridCodec.encode_instructions(
        instructions,
        mode_map={
            0: EncodingMode.COMMENT,
            1: EncodingMode.WHITESPACE,
            2: EncodingMode.UNICODE,
        },
    )
    _write(
        "hybrid.py",
        HOST.format(title="Comment, whitespace and zero-width instructions in one file.")
        + hybrid
        + "\n",
    )


if __name__ == "__main__":
    main()
