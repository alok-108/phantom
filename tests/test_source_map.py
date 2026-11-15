"""Tests for Phantom source map."""

from __future__ import annotations

from phantom.source_map import SourceMap, SourceMapping


def test_source_mapping_dataclass():
    m = SourceMapping(original_line=10, transformed_line=12, file="app.py")
    assert m.original_line == 10
    assert m.transformed_line == 12
    assert m.file == "app.py"


def test_source_map_basic():
    sm = SourceMap()
    sm.add_mapping(1, 5, file="a.py")
    sm.add_mapping(2, 6, file="a.py")

    assert sm.original_to_transformed(1, file="a.py") == 5
    assert sm.original_to_transformed(2, file="a.py") == 6
    assert sm.original_to_transformed(3, file="a.py") is None

    assert sm.transformed_to_original(5, file="a.py") == 1
    assert sm.transformed_to_original(6, file="a.py") == 2
    assert sm.transformed_to_original(7, file="a.py") is None


def test_source_map_explicit_file_does_not_fall_back_to_unrelated_default():
    sm = SourceMap()
    sm.add_mapping(1, 10, file="a.py")
    sm.add_mapping(2, 20, file="b.py")
    # Querying a file that has no mapping for line 1 should return None, NOT a's mapping
    assert sm.original_to_transformed(1, file="b.py") is None
    assert sm.transformed_to_original(10, file="b.py") is None
    # Querying nonexistent file returns None
    assert sm.original_to_transformed(1, file="nonexistent.py") is None
    assert sm.transformed_to_original(10, file="nonexistent.py") is None
    # File-less lookup does not match file-scoped mappings
    assert sm.original_to_transformed(1) is None
    assert sm.original_to_transformed(2) is None


def test_source_map_file_scoped_mappings_do_not_overwrite_default():
    sm = SourceMap()
    sm.add_mapping(1, 10, file="a.py")
    sm.add_mapping(1, 99, file="b.py")
    sm.add_mapping(1, 50)  # default mapping
    assert sm.original_to_transformed(1, file="a.py") == 10
    assert sm.original_to_transformed(1, file="b.py") == 99
    assert sm.original_to_transformed(1) == 50


def test_source_map_default_lookup():
    sm = SourceMap()
    sm.add_mapping(10, 20)
    assert sm.original_to_transformed(10) == 20
    assert sm.transformed_to_original(20) == 10
    assert sm.original_to_transformed(99) is None


def test_source_map_empty_file_treated_as_default():
    # Regression for #207: file="" is the default value, and _index_mapping
    # stores such mappings in the default dicts, so lookups with file=""
    # must hit those dicts instead of the per-file dicts.
    sm = SourceMap()
    sm.add_mapping(1, 10, file="")

    assert sm.original_to_transformed(1, file="") == 10
    assert sm.transformed_to_original(10, file="") == 1
    assert sm.original_to_transformed(1) == 10
    assert sm.transformed_to_original(10) == 1

    # Constructor path with an explicit empty file behaves the same.
    sm2 = SourceMap([SourceMapping(2, 20, file="")])
    assert sm2.original_to_transformed(2, file="") == 20
    assert sm2.transformed_to_original(20, file="") == 2


def test_source_map_identity_map():
    sm = SourceMap.identity_map(5, file="test.py")
    assert len(sm) == 5
    for i in range(1, 6):
        assert sm.original_to_transformed(i, file="test.py") == i
        assert sm.transformed_to_original(i, file="test.py") == i

    assert sm.original_to_transformed(6, file="test.py") is None


def test_source_map_iteration():
    sm = SourceMap.identity_map(3)
    mappings = list(sm)
    assert len(mappings) == 3
    assert mappings[0].original_line == 1
    assert mappings[0].transformed_line == 1
