"""Tests for behavior comparison."""

from __future__ import annotations

from phantom.generator.diff import format_diff_colored
from phantom.generator.equivalence import compare_behavior, host_ast_equal
from phantom.generator.models import ComparisonVerdict, VerificationCase
from phantom.generator.validation import validate_candidate

BASE = "print('a')\n"


def test_ast_equal_ignores_comments_and_blank_lines():
    assert host_ast_equal(BASE, "# note\n\nprint('a')\n")
    assert not host_ast_equal(BASE, "print('b')\n")


def test_equivalent():
    res = compare_behavior(BASE, "#: phantom:0.1.0 meta.author(\"A\")\n" + BASE)
    assert res.verdict == ComparisonVerdict.EQUIVALENT
    assert any("Only one input" in n for n in res.notes)


def test_different_stdout():
    res = compare_behavior(BASE, "print('b')\n")
    assert res.verdict == ComparisonVerdict.DIFFERENT
    assert "stdout differs" in res.differences


def test_different_exit_code():
    res = compare_behavior(BASE, BASE + "raise SystemExit(3)\n")
    assert res.verdict == ComparisonVerdict.DIFFERENT
    assert res.candidate_exit_code == 3


def test_same_traceback_is_not_a_difference_despite_paths_and_line_numbers():
    boom = "raise ValueError('x')\n"
    res = compare_behavior(boom, "# c\n" + boom.replace("\n", "  \n"))
    assert res.differences == []
    # both fail the same way, which does not show that they behave alike
    assert res.verdict == ComparisonVerdict.INCONCLUSIVE


def test_syntax_error_is_validation_failure():
    res = compare_behavior(BASE, "print(\n")
    assert res.verdict == ComparisonVerdict.VALIDATION_FAILED


def test_timeout_is_inconclusive():
    loop = "while True:\n    pass\n"
    res = compare_behavior(loop, loop, timeout=0.5)
    assert res.verdict == ComparisonVerdict.INCONCLUSIVE


class TestCandidateValidation:
    def test_passes(self):
        report = validate_candidate(BASE, '#: phantom:0.1.0 meta.author("A")\n' + BASE)
        assert report.passed and not report.errors

    def test_host_change_detected(self):
        report = validate_candidate(BASE, "print('b')\n")
        assert not report.host_preserved and not report.passed

    def test_syntax_error_detected(self):
        report = validate_candidate(BASE, "print(\n")
        assert not report.host_syntax_valid

    def test_phantom_error_detected(self):
        report = validate_candidate(BASE, '#: phantom:0.1.0 event.on("x", "a.b")\n' + BASE)
        assert not report.phantom_valid and report.host_preserved

    def test_license_valid(self):
        report = validate_candidate(BASE, '#: phantom:0.1.0 meta.license("MIT")\n' + BASE)
        assert report.passed and not report.errors

    def test_license_wrong_type(self):
        report = validate_candidate(BASE, '#: phantom:0.1.0 meta.license(123)\n' + BASE)
        assert not report.passed
        # Check for the argument name or the expected type
        assert any("spdx" in e or "STRING" in e for e in report.errors)

    def test_license_wrong_arg_count(self):
        report = validate_candidate(BASE, '#: phantom:0.1.0 meta.license("MIT", "extra")\n' + BASE)
        assert not report.passed
        # Check for the argument name or a word indicating the count issue
        assert any("spdx" in e or "arity" in e or "argument" in e for e in report.errors)

def test_identical_programs_that_print_their_own_path_are_equivalent():
    source = "import sys\nprint(__file__)\nprint(repr(__file__))\nprint(sys.argv[0])\n"
    res = compare_behavior(source, source)
    assert res.verdict == ComparisonVerdict.EQUIVALENT, res.differences


def test_a_real_stdout_difference_is_still_found_next_to_path_output():
    res = compare_behavior("print(__file__)\nprint('a')\n", "print(__file__)\nprint('b')\n")
    assert res.verdict == ComparisonVerdict.DIFFERENT
    assert "stdout differs" in res.differences


def test_programs_that_both_crash_are_inconclusive_not_equivalent():
    source = "import module_that_does_not_exist_zz\nprint('unreachable')\n"
    res = compare_behavior(source, '#: phantom:0.1.0 meta.author("A")\n' + source)
    assert res.verdict == ComparisonVerdict.INCONCLUSIVE
    assert res.original_exit_code == res.candidate_exit_code == 1
    assert any("sibling modules" in n for n in res.notes)


def test_a_clean_nonzero_exit_that_differs_is_still_different():
    res = compare_behavior("raise SystemExit(2)\n", "raise SystemExit(3)\n")
    assert res.verdict == ComparisonVerdict.DIFFERENT


def test_a_different_exception_message_is_still_a_difference():
    res = compare_behavior("raise ValueError('a')\n", "# x\nraise ValueError('b')\n")
    assert res.verdict == ComparisonVerdict.DIFFERENT
    assert "stderr differs" in res.differences


class TestFormatDiffColored:
    """format_diff_colored is what `phantom diff` prints (see test_cli.py)."""

    DIFF = (
        "--- a.py\n+++ b.py\n@@ -1 +1 @@\n-print('hello')\n+print('world')\n"
        " print('same')\n"
    )

    def test_colored_wraps_added_removed_and_hunk_lines(self):
        out = format_diff_colored(self.DIFF)
        assert "\033[31m-print('hello')\033[0m" in out
        assert "\033[32m+print('world')\033[0m" in out
        assert "\033[36m@@ -1 +1 @@\033[0m" in out
        assert " print('same')" in out
        assert "\033[36m print('same')" not in out

    def test_uncolored_returns_diff_text_unchanged(self):
        assert format_diff_colored(self.DIFF, colored=False) == self.DIFF

    def test_uncolored_empty_diff_stays_empty(self):
        assert format_diff_colored("", colored=False) == ""
        assert format_diff_colored("") == ""
def test_multiple_argument_cases_all_match():
    source = "import sys\nprint(' '.join(sys.argv[1:]))\n"
    cases = [VerificationCase(args=["a"]), VerificationCase(args=["b", "c"])]
    res = compare_behavior(source, source, cases=cases)
    assert res.verdict == ComparisonVerdict.EQUIVALENT
    assert len(res.case_results) == 2
    assert all(c.verdict == ComparisonVerdict.EQUIVALENT for c in res.case_results)
    assert any("2 cases" in n for n in res.notes)


def test_difference_only_in_second_case_is_reported_per_case():
    original = "import sys\nprint('B' if sys.argv[1] == 'b' else sys.argv[1])\n"
    candidate = "import sys\nprint(sys.argv[1])\n"
    cases = [VerificationCase(args=["a"]), VerificationCase(args=["b"])]
    res = compare_behavior(original, candidate, cases=cases)
    assert res.verdict == ComparisonVerdict.DIFFERENT
    assert res.case_results[0].verdict == ComparisonVerdict.EQUIVALENT
    assert res.case_results[1].verdict == ComparisonVerdict.DIFFERENT
    assert "stdout differs" in res.case_results[1].differences


def test_stdin_case_feeds_the_same_text_to_both_programs():
    source = "print(input())\n"
    cases = [VerificationCase(stdin_text="alice\n"), VerificationCase(stdin_text="bob\n")]
    res = compare_behavior(source, source, cases=cases)
    assert res.verdict == ComparisonVerdict.EQUIVALENT
    assert res.case_results[0].original_stdout == "alice\n"
    assert res.case_results[1].original_stdout == "bob\n"


def test_match_plus_inconclusive_case_is_inconclusive_not_equivalent():
    source = (
        "import sys\n"
        "if sys.argv[1] == 'boom':\n"
        "    raise SystemExit(3)\n"
        "print(sys.argv[1])\n"
    )
    cases = [VerificationCase(args=["ok"]), VerificationCase(args=["boom"])]
    res = compare_behavior(source, source, cases=cases)
    assert res.verdict == ComparisonVerdict.INCONCLUSIVE
    assert res.case_results[0].verdict == ComparisonVerdict.EQUIVALENT
    assert res.case_results[1].verdict == ComparisonVerdict.INCONCLUSIVE
