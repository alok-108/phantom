import os
import shutil
import subprocess
import sys

import pytest


def get_git_bash():
    """Find Git Bash or standard bash, ignoring Windows WSL launcher stub."""
    # Check explicit Git Bash install paths on Windows
    possible_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Fall back to PATH search, but ignore System32\bash.exe (WSL launcher stub)
    bash_path = shutil.which("bash")
    if bash_path and "system32" not in bash_path.lower():
        return bash_path

    return None


BASH_PATH = get_git_bash()


@pytest.mark.skipif(BASH_PATH is None, reason="Git Bash (or non-WSL bash) is required for this test")
def test_ci_check_with_spaces_in_path():
    env = {
        **os.environ,
        "PHANTOM_PATHS": "tests/fixtures/space path",
    }
    result = subprocess.run(
        [BASH_PATH, "scripts/ci_check.sh"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout = result.stdout.replace("\r", "")
    stderr = result.stderr.replace("\r", "")

    assert result.returncode == 0, f"Script failed with stderr:\n{stderr}\nstdout:\n{stdout}"


def test_sarif_check_writes_valid_sarif(tmp_path):
    import json

    script = tmp_path / "good.py"
    script.write_text('#: phantom:0.1.0 counter.create("n", 3)\n')
    out = tmp_path / "out.sarif"
    env = {**os.environ, "PHANTOM_PATHS": str(script)}
    result = subprocess.run(
        [BASH_PATH, "scripts/sarif_check.sh", str(out)] if BASH_PATH else ["bash", "scripts/sarif_check.sh", str(out)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "2.1.0"
    assert data["runs"][0]["tool"]["driver"]["name"] == "phantom"


def test_sarif_check_still_writes_sarif_on_findings(tmp_path):
    import json

    script = tmp_path / "bad.py"
    script.write_text('#: phantom:0.1.0 counter.create("n", 0)\n')
    out = tmp_path / "out.sarif"
    env = {**os.environ, "PHANTOM_PATHS": str(script)}
    result = subprocess.run(
        [BASH_PATH, "scripts/sarif_check.sh", str(out)] if BASH_PATH else ["bash", "scripts/sarif_check.sh", str(out)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["runs"][0]["results"]) >= 1


def test_coverage_map_sorts_lowest_first(tmp_path):
    import json

    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "files": {
                    "src/phantom/a.py": {
                        "summary": {
                            "percent_covered": 50.0,
                            "num_statements": 10,
                            "missing_lines": [1, 2, 3, 5],
                            "excluded_lines": [],
                        }
                    },
                    "src/phantom/b.py": {
                        "summary": {
                            "percent_covered": 100.0,
                            "num_statements": 4,
                            "missing_lines": [],
                            "excluded_lines": [],
                        }
                    },
                },
                "totals": {
                    "percent_covered": 75.0,
                    "covered_lines": 12,
                    "num_statements": 14,
                },
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "scripts/coverage_map.py", str(report)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    assert "a.py" in result.stdout.split("b.py")[0]
    assert "1-3, 5" in result.stdout

