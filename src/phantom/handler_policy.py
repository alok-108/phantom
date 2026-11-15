"""Opt-in restriction of which modules ``event.on`` handlers may import.

``event.on("event", "pkg.func")`` imports ``pkg`` when the event fires, which runs
that module's top-level code. A ``HandlerPolicy`` decides *before* anything is
imported whether a handler path is allowed. It never imports the module it is
asked about: the top-level module is located with ``importlib.util.find_spec``
(which does not execute it), and sub-modules live inside the allowed package.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _module_location(top_level: str) -> tuple[Path | None, str]:
    """Return (file system location, description) of a top-level module.

    The location is None for built-in/frozen modules; the description says why.
    Raises LookupError if no such module exists (nothing would be imported).
    """
    module = sys.modules.get(top_level)
    spec = getattr(module, "__spec__", None) if module is not None else None
    if spec is None:
        try:
            spec = importlib.util.find_spec(top_level)
        except (ImportError, ValueError):
            spec = None
    if spec is None:
        raise LookupError(top_level)
    if spec.submodule_search_locations:
        first = next(iter(spec.submodule_search_locations), None)
        if first:
            return Path(first).resolve(), f"package at {Path(first).resolve()}"
    origin = spec.origin
    if origin and origin not in ("built-in", "frozen"):
        return Path(origin).resolve(), f"module at {Path(origin).resolve()}"
    return None, f"{origin or 'built-in'} module"


@dataclass(frozen=True)
class HandlerPolicy:
    """Which handler paths may be imported.

    A handler is allowed if it matches one of ``patterns`` (``fnmatch`` against the
    full dotted path, e.g. ``myapp.hooks.*``) or if its top-level module lives inside
    one of ``directories``. With neither configured the policy is disabled and
    everything is allowed (the default).
    """

    directories: tuple[Path, ...] = field(default_factory=tuple)
    patterns: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls, directories: Iterable[str | Path] = (), patterns: Iterable[str] = ()
    ) -> HandlerPolicy:
        return cls(
            tuple(Path(d).resolve() for d in directories),
            tuple(patterns),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.directories or self.patterns)

    def denial(self, handler_path: str) -> str | None:
        """Return the reason a handler is not allowed, or None if it is allowed."""
        if not self.enabled:
            return None
        if any(fnmatch.fnmatchcase(handler_path, pattern) for pattern in self.patterns):
            return None
        top_level = handler_path.split(".", 1)[0]
        try:
            location, description = _module_location(top_level)
        except LookupError:
            return None  # not importable at all: resolution fails without running anything
        if location is not None and any(_is_within(location, d) for d in self.directories):
            return None
        return (
            f"handler '{handler_path}' is not allowed by the handler policy "
            f"({description}); it was not imported"
        )
