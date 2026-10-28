"""Apply a validated TransformationPlan to source text.

The transformer only ever inserts whole lines. It never edits, moves, or
removes existing lines, and it refuses insertion points inside multi-line
strings, brackets, or backslash continuations.
"""

from __future__ import annotations

import ast
import io
import tokenize

from phantom.encoding import encode_instruction
from phantom.generator.models import PlannedInstruction, TransformationPlan
from phantom.ir import (
    Argument,
    ArgumentType,
    EncodingMode,
    InstructionType,
    PhantomInstruction,
    SourceLocation,
)
from phantom.lines import split_physical_lines

_MODES = {
    "comment": EncodingMode.COMMENT,
    "whitespace": EncodingMode.WHITESPACE,
    "unicode": EncodingMode.UNICODE,
}


class TransformError(ValueError):
    """Raised when a plan cannot be applied safely."""


def unsafe_insertion_lines(source: str) -> set[int]:
    """Line numbers before which inserting a new line would change the program."""
    unsafe: set[int] = set()
    lines = split_physical_lines(source)
    try:
        depth = 0
        # tokenize's StringIO.readline only splits on LF, unlike Python's source
        # parser which recognizes lone CR as a physical line boundary.
        token_source = source.replace("\r\n", "\n").replace("\r", "\n")
        for tok in tokenize.generate_tokens(io.StringIO(token_source).readline):
            if tok.type == tokenize.OP:
                if tok.string in "([{":
                    depth += 1
                elif tok.string in ")]}":
                    depth = max(0, depth - 1)
            if tok.start[0] < tok.end[0]:
                unsafe.update(range(tok.start[0] + 1, tok.end[0] + 1))
            if depth > 0 and tok.type in (tokenize.NL, tokenize.NEWLINE):
                unsafe.add(tok.start[0] + 1)
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise TransformError(f"Source cannot be tokenized: {exc}") from exc
    for idx, line in enumerate(lines, start=1):
        if line.endswith("\\"):
            unsafe.add(idx + 1)
    return unsafe


def _to_instruction(planned: PlannedInstruction) -> PhantomInstruction:
    args = tuple(
        Argument(ArgumentType(a["type"]), a["value"]) for a in planned.arguments
    )
    return PhantomInstruction(
        InstructionType(planned.instruction_type),
        args,
        SourceLocation("<plan>", planned.placement_line, 0, _MODES[planned.encoding]),
    )


def apply_plan(source: str, plan: TransformationPlan) -> str:
    """Return `source` with the plan's instructions inserted."""
    if not plan.valid:
        raise TransformError("Plan is not valid: " + "; ".join(plan.validation_errors))

    raw_lines = split_physical_lines(source, keepends=True)
    lines = split_physical_lines(source)
    unsafe = unsafe_insertion_lines(source)
    total = len(lines)
    inserts: dict[int, list[str]] = {}
    for planned in plan.instructions:
        at = min(planned.placement_line, total + 1)
        if at in unsafe:
            raise TransformError(
                f"Line {planned.placement_line} is inside a multi-line construct; "
                "instructions cannot be inserted there"
            )
        if planned.anchor is not None:
            actual = lines[at - 1] if at <= total else ""
            if actual.strip() != planned.anchor.strip():
                raise TransformError(
                    f"Stale or mismatched patch: line {at} is {actual.strip()!r}, "
                    f"but the plan expected {planned.anchor.strip()!r}"
                )
        text = encode_instruction(_to_instruction(planned), _MODES[planned.encoding])
        inserts.setdefault(at, []).extend(text.split("\n"))

    def ending(line: str) -> str:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n") or line.endswith("\r"):
            return line[-1]
        return ""

    output: list[str] = []
    for lineno in range(1, total + 2):
        additions = inserts.get(lineno, [])
        if additions:
            prior_ending = ending(raw_lines[lineno - 2]) if lineno > 1 else ""
            next_ending = ending(raw_lines[lineno - 1]) if lineno <= total else ""
            separator = prior_ending or next_ending or next(
                (ending(line) for line in raw_lines if ending(line)), "\n"
            )
            if lineno == total + 1 and raw_lines and not ending(raw_lines[-1]):
                output.append(separator)
            output.append(separator.join(additions))
            if lineno <= total or source.endswith(("\n", "\r")) or not source:
                output.append(separator)
        if lineno <= total:
            output.append(raw_lines[lineno - 1])
    return "".join(output)

def _is_main_guard(node: ast.If) -> bool:
    """True if `node` is a top-level `if __name__ == "__main__":` guard."""
    test = node.test
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if len(test.comparators) != 1:
        return False
    left, right = test.left, test.comparators[0]

    def is_name(side: ast.expr, name: str) -> bool:
        return isinstance(side, ast.Name) and side.id == name

    def is_const(side: ast.expr, value: str) -> bool:
        return isinstance(side, ast.Constant) and side.value == value

    return (is_name(left, "__name__") and is_const(right, "__main__")) or (
        is_const(left, "__main__") and is_name(right, "__name__")
    )


def _first_line(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> int:
    """First line of a definition, including its decorators."""
    return min([node.lineno] + [d.lineno for d in node.decorator_list])


def _resolve_dotted(tree: ast.Module, name: str) -> int:
    """Resolve 'Class.method' (or deeper 'Outer.Inner.method') to a line.

    Each segment but the last must name a single class in the enclosing
    scope; the last names a single method (or nested class) of that class.
    """
    parts = name.split(".")
    if any(not part for part in parts):
        raise TransformError(f"Invalid placement name: '{name}'")
    scope: list[ast.stmt] = list(tree.body)
    for part in parts[:-1]:
        classes = [
            n for n in scope if isinstance(n, ast.ClassDef) and n.name == part
        ]
        if not classes:
            raise TransformError(f"No class named '{part}' found for '{name}'")
        if len(classes) > 1:
            lines = ", ".join(str(n.lineno) for n in classes)
            raise TransformError(
                f"'{part}' is ambiguous (defined at lines {lines}); "
                "use line:N instead"
            )
        scope = list(classes[0].body)
    last = parts[-1]
    targets = [
        n
        for n in scope
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.name == last
    ]
    if not targets:
        raise TransformError(f"No method named '{last}' in '{'.'.join(parts[:-1])}'")
    if len(targets) > 1:
        lines = ", ".join(str(n.lineno) for n in targets)
        raise TransformError(
            f"'{name}' is ambiguous (defined at lines {lines}); use line:N instead"
        )
    return _first_line(targets[0])


def resolve_placement(source: str, placement: str) -> int:
    """Resolve a placement spec to a 1-based insertion line.

    Accepted: 'beginning', 'end', 'line:N', 'near:NAME' (before the single
    function or class called NAME), 'near:Class.method' (before the single
    method of the single class of that name), and 'main-guard'
    (before the first top-level `if __name__ == "__main__":` guard;
    'before-main-guard' is accepted as an alias).

    Raises:
        TransformError: If the spec is unknown or ambiguous.
    """
    total = len(split_physical_lines(source))
    spec = placement.strip()
    if spec in ("", "beginning"):
        return 1
    if spec == "end":
        return total + 1
    if spec.startswith("line:"):
        try:
            line = int(spec[5:])
        except ValueError:
            raise TransformError(f"Invalid line placement: '{spec}'") from None
        if not 1 <= line <= total + 1:
            raise TransformError(f"Line {line} is outside the file (1-{total + 1})")
        return line
    if spec in ("main-guard", "before-main-guard"):
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise TransformError(f"Cannot resolve '{spec}': {exc.msg}") from exc
        guards = [
            n for n in tree.body if isinstance(n, ast.If) and _is_main_guard(n)
        ]
        if not guards:
            raise TransformError("No main guard (if __name__ == '__main__':) found")
        return guards[0].lineno
    if spec.startswith("near:"):
        name = spec[5:].strip()
        if not name:
            raise TransformError("Invalid placement name: 'near:' names nothing")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise TransformError(f"Cannot resolve '{spec}': {exc.msg}") from exc
        if "." in name:
            return _resolve_dotted(tree, name)
        hits = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and n.name == name
        ]
        if not hits:
            raise TransformError(f"No function or class named '{name}' found")
        if len(hits) > 1:
            lines = ", ".join(str(n.lineno) for n in hits)
            raise TransformError(
                f"'{name}' is ambiguous (defined at lines {lines}); use line:N instead"
            )
        return _first_line(hits[0])
    raise TransformError(f"Unknown placement '{placement}'")
