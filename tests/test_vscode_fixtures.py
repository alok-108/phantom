"""The VS Code extension decodes in JavaScript; its fixtures come from the Python encoders."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "editors" / "vscode" / "test" / "fixtures.json"
GENERATOR = ROOT / "scripts" / "gen_vscode_fixtures.py"


@pytest.fixture(scope="module")
def generator():
    spec = importlib.util.spec_from_file_location("gen_vscode_fixtures", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_fixtures_are_up_to_date(generator):
    committed = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert committed == generator.build(), (
        "editors/vscode/test/fixtures.json is stale: run `python scripts/gen_vscode_fixtures.py`"
    )


def test_fixtures_cover_both_encodings_errors_and_stray_characters(generator):
    built = generator.build()
    assert len(built["cases"]) >= 5
    assert any(len(c["instructions"]) > 1 for c in built["cases"])
    assert all(c["python_errors"] for c in built["invalid"]), "every invalid case must fail in Python too"
    assert any(not c["expected"] for c in built["stray"]) and any(c["expected"] for c in built["stray"])


def test_fixture_file_is_plain_ascii():
    raw = FIXTURES.read_bytes()
    assert all(b < 0x80 for b in raw), "invisible characters must appear as JSON escapes"
