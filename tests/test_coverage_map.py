from __future__ import annotations

from scripts.coverage_map import render


def test_render_uses_missing_line_numbers_from_coverage_json():
    report = {
        "files": {
            "src/phantom/example.py": {
                "summary": {
                    "percent_covered": 75.0,
                    "num_statements": 4,
                    "missing_lines": 2,
                    "excluded_lines": 0,
                },
                "missing_lines": [2, 3],
                "excluded_lines": [],
            },
        },
        "totals": {
            "percent_covered": 75.0,
            "covered_lines": 3,
            "num_statements": 4,
        },
    }

    result = render(report, top=10)

    assert "| `src/phantom/example.py` | 75.0% | 2 | 2-3 |" in result
