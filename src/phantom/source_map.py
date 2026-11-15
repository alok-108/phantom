"""Phantom Source Mapping.

Provides line mapping between original source code and transformed code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceMapping:
    """A mapping from an original source line to a transformed source line."""

    original_line: int
    transformed_line: int
    file: str = ""


class SourceMap:
    """Bidirectional mapping between original and transformed source lines."""

    def __init__(self, mappings: list[SourceMapping] | None = None) -> None:
        self.mappings: list[SourceMapping] = list(mappings or [])
        self._orig_to_trans: dict[tuple[str, int], int] = {}
        self._trans_to_orig: dict[tuple[str, int], int] = {}
        self._default_orig_to_trans: dict[int, int] = {}
        self._default_trans_to_orig: dict[int, int] = {}

        for m in self.mappings:
            self._index_mapping(m)

    def _index_mapping(self, m: SourceMapping) -> None:
        if m.file:
            self._orig_to_trans[(m.file, m.original_line)] = m.transformed_line
            self._trans_to_orig[(m.file, m.transformed_line)] = m.original_line
        else:
            self._default_orig_to_trans[m.original_line] = m.transformed_line
            self._default_trans_to_orig[m.transformed_line] = m.original_line

    def add_mapping(
        self, original_line: int, transformed_line: int, file: str = ""
    ) -> None:
        """Add a mapping between an original line and transformed line."""
        mapping = SourceMapping(
            original_line=original_line,
            transformed_line=transformed_line,
            file=file,
        )
        self.mappings.append(mapping)
        self._index_mapping(mapping)

    def original_to_transformed(
        self, line: int, file: str | None = None
    ) -> int | None:
        """Convert an original line number to a transformed line number."""
        # Treat "" like None: _index_mapping only indexes a per-file
        # mapping when file is truthy, so "" lives in the default dicts.
        if file:
            return self._orig_to_trans.get((file, line))
        return self._default_orig_to_trans.get(line)

    def transformed_to_original(
        self, line: int, file: str | None = None
    ) -> int | None:
        """Convert a transformed line number to an original line number."""
        # Treat "" like None, matching _index_mapping (see above).
        if file:
            return self._trans_to_orig.get((file, line))
        return self._default_trans_to_orig.get(line)

    @classmethod
    def identity_map(cls, line_count: int, file: str = "") -> SourceMap:
        """Create a 1:1 identity mapping for lines 1 to line_count."""
        sm = cls()
        for i in range(1, max(0, line_count) + 1):
            sm.add_mapping(i, i, file=file)
        return sm

    def __len__(self) -> int:
        return len(self.mappings)

    def __iter__(self):
        return iter(self.mappings)
