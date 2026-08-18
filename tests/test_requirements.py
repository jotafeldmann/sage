"""Requirement-scoped specification slicing.

The rule that matters: a slice may drop detail a task does not need, but it
must never drop something globally applicable, and it must fail open - a
specification it cannot parse is passed through whole.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sage.tools.requirements import requirement_ids, slice_for_requirements

REPO = Path(__file__).resolve().parent.parent

SPEC = """# Widget Builder

## Purpose

Build a widget.

## Required Requirements

### WIDGET-REQ-001 - Show widgets

Display the widgets.

### WIDGET-REQ-002 - Filter widgets

Provide a filter.

## Optional Requirements

### WIDGET-OPT-001 - Theming

Support themes.

## Constraints

- Do not add a backend.
"""


def test_only_the_requested_requirement_survives() -> None:
    sliced = slice_for_requirements(SPEC, ["WIDGET-REQ-001"])

    assert "Display the widgets." in sliced
    assert "Provide a filter." not in sliced
    assert "Support themes." not in sliced


def test_globally_applicable_sections_are_always_kept() -> None:
    """Purpose and Constraints apply to every task, so they must survive."""
    sliced = slice_for_requirements(SPEC, ["WIDGET-REQ-001"])

    assert "Build a widget." in sliced
    assert "Do not add a backend." in sliced


def test_a_grouping_heading_with_nothing_left_under_it_is_dropped() -> None:
    sliced = slice_for_requirements(SPEC, ["WIDGET-REQ-001"])

    assert "Optional Requirements" not in sliced
    # The heading that still has a wanted child is kept.
    assert "Required Requirements" in sliced


def test_several_requirements_can_be_requested_at_once() -> None:
    sliced = slice_for_requirements(SPEC, ["WIDGET-REQ-001", "WIDGET-OPT-001"])

    assert "Display the widgets." in sliced
    assert "Support themes." in sliced
    assert "Provide a filter." not in sliced


@pytest.mark.parametrize("wanted", [[], [""], ["NOT-A-REAL-ID-999"]])
def test_unresolvable_requirements_fall_back_to_the_whole_spec(wanted) -> None:
    """Losing a requirement is worse than sending a few paragraphs too many."""
    assert slice_for_requirements(SPEC, wanted) == SPEC


def test_a_spec_with_no_headings_is_passed_through() -> None:
    plain = "Just build something reasonable, please."

    assert slice_for_requirements(plain, ["ANY-REQ-001"]) == plain


def test_identifiers_are_matched_case_insensitively() -> None:
    assert "Display the widgets." in slice_for_requirements(SPEC, ["widget-req-001"])


def test_requirement_ids_are_discovered_structurally() -> None:
    assert requirement_ids(SPEC) == {"WIDGET-REQ-001", "WIDGET-REQ-002", "WIDGET-OPT-001"}


@pytest.mark.parametrize(
    ("spec_path", "requirement", "must_keep", "must_drop"),
    [
        (
            "specs/examples/product-search.md",
            "PRODUCT-REQ-003",
            "No products found",
            "Provide a search input that filters products by name",
        ),
        (
            "specs/car-inventory.md",
            "CAR-REQ-002",
            "filters the displayed cars by model",
            "Extract GraphQL data-fetching logic",
        ),
    ],
)
def test_slicing_works_on_the_real_evaluation_specs(
    spec_path, requirement, must_keep, must_drop
) -> None:
    spec = (REPO / spec_path).read_text(encoding="utf-8")

    sliced = slice_for_requirements(spec, [requirement])

    assert must_keep in sliced
    assert must_drop not in sliced
    assert len(sliced) < len(spec)


def test_shared_context_survives_slicing_of_the_car_spec() -> None:
    """The Car type applies to every task and must not be sliced away."""
    spec = (REPO / "specs/car-inventory.md").read_text(encoding="utf-8")

    sliced = slice_for_requirements(spec, ["CAR-REQ-002"])

    assert "interface Car" in sliced
    assert "Do not create a real backend" in sliced
