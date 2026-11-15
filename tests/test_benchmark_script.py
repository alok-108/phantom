import subprocess
import sys


def test_benchmark_quick_reports_a_table():
    result = subprocess.run(
        [sys.executable, "scripts/benchmark_lexer_parser.py", "--quick"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    assert "| Case | Bytes |" in result.stdout
    assert "plain_50k_lines" in result.stdout
