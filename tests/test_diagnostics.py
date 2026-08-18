"""Normalization of compiler and test-runner output.

The contract is modest on purpose: recognise the common shapes, and degrade to
"unknown, no counts" on anything else. The raw excerpt always still reaches
repair, so a parsing miss costs guidance quality, never information.
"""

from __future__ import annotations

import pytest

from sage.tools.diagnostics import (
    REPAIR_GUIDANCE,
    classify_failure,
    guidance_for,
    parse_diagnostics,
    parse_test_counts,
)

VITEST_FAIL = """
 ✓ src/ProductSearch.test.tsx > shows every product initially
 × src/ProductSearch.test.tsx > narrows the visible products

 Test Files  1 failed (1)
      Tests  2 failed | 1 passed (3)
"""

JEST_FAIL = """
Tests:       1 failed, 2 passed, 3 total
Snapshots:   0 total
"""

TSC_FAIL = """
src/App.tsx(12,5): error TS2322: Type 'string' is not assignable to type 'number'.
src/products.ts(3,1): error TS2307: Cannot find module './missing'.
"""


def test_vitest_counts_are_read() -> None:
    counts = parse_test_counts(VITEST_FAIL)

    assert counts is not None
    assert (counts.passed, counts.failed, counts.total) == (1, 2, 3)


def test_jest_counts_are_read() -> None:
    counts = parse_test_counts(JEST_FAIL)

    assert counts is not None
    assert (counts.passed, counts.failed, counts.total) == (2, 1, 3)


def test_an_all_passing_run_is_read() -> None:
    counts = parse_test_counts("      Tests  4 passed (4)\n")

    assert counts is not None
    assert (counts.passed, counts.failed, counts.total) == (4, 0, 4)


def test_a_project_with_no_tests_reports_zero_rather_than_nothing() -> None:
    counts = parse_test_counts("No test files found, exiting with code 1")

    assert counts is not None
    assert counts.total == 0


def test_unparseable_output_yields_no_counts() -> None:
    assert parse_test_counts("something went wrong") is None


def test_compiler_diagnostics_are_extracted_with_position_and_code() -> None:
    diagnostics = parse_diagnostics(TSC_FAIL)

    assert diagnostics[0].startswith("src/App.tsx:12:5 TS2322")
    assert "not assignable" in diagnostics[0]
    assert len(diagnostics) == 2


def test_diagnostics_are_capped() -> None:
    from sage.tools.diagnostics import MAX_DIAGNOSTICS

    noisy = "\n".join(f"src/f{i}.ts({i},1): error TS1000: broken" for i in range(50))

    assert len(parse_diagnostics(noisy)) == MAX_DIAGNOSTICS


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("error TS2307: Cannot find module './x'", "missing_module"),
        ("Failed to resolve import \"./x\" from \"src/App.tsx\"", "missing_module"),
        ("src/App.tsx(1,1): error TS1005: ';' expected.", "syntax"),
        ("src/App.tsx(12,5): error TS2322: Type mismatch", "typecheck"),
        ("AssertionError: expected 1 to be 2", "test_failure"),
        ("Unable to find an element by: [data-testid]", "test_failure"),
        ("something entirely unrecognised", "unknown"),
    ],
)
def test_failures_are_classified(output: str, expected: str) -> None:
    assert classify_failure(output) == expected


def test_the_most_specific_cause_wins() -> None:
    """A missing module is *reported* as a type error; the real cause should win."""
    output = "src/App.tsx(1,1): error TS2307: Cannot find module './products'."

    assert classify_failure(output) == "missing_module"


def test_a_timeout_is_classified_regardless_of_output() -> None:
    assert classify_failure("", timed_out=True) == "timeout"


def test_a_build_only_failure_is_classified_from_the_command() -> None:
    assert classify_failure("bundling stopped", command="npm run build") == "build"


@pytest.mark.parametrize("kind", list(REPAIR_GUIDANCE))
def test_every_classification_has_guidance(kind: str) -> None:
    assert guidance_for(kind).strip()


def test_unknown_kinds_fall_back_to_generic_guidance() -> None:
    assert guidance_for("something-new") == REPAIR_GUIDANCE["unknown"]


def test_test_failure_guidance_forbids_deleting_tests() -> None:
    """The most dangerous repair is one that makes the gate stop checking."""
    assert "Never delete a test" in guidance_for("test_failure")


VITEST_FAILURE_BLOCK = """
 FAIL  src/ProductSearch.test.tsx > ProductSearch > narrows the visible products
TestingLibraryElementError: Unable to find an element with the placeholder text of: Search

 ❯ Object.getElementError node_modules/@testing-library/dom/dist/config.js:37:19
 ❯ src/ProductSearch.test.tsx:18:33
"""


def test_a_failing_test_is_named_with_its_case_and_message() -> None:
    """The case name is more actionable than a line number in a matcher library."""
    diagnostics = parse_diagnostics(VITEST_FAILURE_BLOCK)

    assert diagnostics
    assert "src/ProductSearch.test.tsx > ProductSearch > narrows" in diagnostics[0]
    assert "Unable to find an element" in diagnostics[0]


def test_stack_frames_inside_dependencies_are_not_reported() -> None:
    """Only the project's own files are actionable."""
    diagnostics = parse_diagnostics(
        " ❯ node_modules/@testing-library/dom/dist/config.js:37:19\n"
        " ❯ src/ProductSearch.test.tsx:18:33\n",
        known_files={"src/ProductSearch.test.tsx"},
    )

    assert diagnostics == ["src/ProductSearch.test.tsx:18:33"]
