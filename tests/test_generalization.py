"""SAGE core must not know about any particular application domain.

SPEC.md 13 requires that no evaluation specification's vocabulary leaks into
SAGE's code or prompts. This test is the enforcement, so a future change that
tunes SAGE for one spec fails the suite.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SAGE_ROOT = Path(__file__).resolve().parent.parent / "sage"

# Identifiers from the evaluation specifications. They may appear in specs/ and
# in generated output; they must never appear in SAGE itself.
FORBIDDEN = (
    # Car Inventory (specs/car-inventory.md)
    "CarCard",
    "GetCars",
    "useCars",
    "AddCar",
    "useCarFilters",
    "vehicle",
    # Product Search (specs/examples/product-search.md). Its seed products are
    # ordinary English words (Keyboard/Monitor/Mouse) that collide with Python
    # vocabulary, so the distinctive empty-state string is the useful signal.
    "No products found",
    # Book Inventory (specs/examples/book-inventory.md)
    "publication year",
    "isbn",
)

# Stack details of a boilerplate SAGE has not seen. It must discover a target
# project's libraries at runtime, never assume them.
FORBIDDEN_STACK = ("apollo", "msw", "graphql", "material-ui", "@mui")


def _sage_sources() -> list[Path]:
    return sorted(
        path
        for path in SAGE_ROOT.rglob("*")
        if path.suffix in {".py", ".md"} and "__pycache__" not in path.parts
    )


def test_sage_sources_were_found() -> None:
    assert len(_sage_sources()) > 15


@pytest.mark.parametrize("term", FORBIDDEN)
def test_no_evaluation_domain_vocabulary_in_sage_core(term: str) -> None:
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    offenders = [path.name for path in _sage_sources() if pattern.search(path.read_text())]

    assert not offenders, f"{term!r} leaked into SAGE core: {offenders}"


@pytest.mark.parametrize("term", FORBIDDEN_STACK)
def test_no_unseen_stack_assumptions_in_sage_core(term: str) -> None:
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    offenders = [path.name for path in _sage_sources() if pattern.search(path.read_text())]

    assert not offenders, f"{term!r} assumes a stack SAGE should discover: {offenders}"


def test_validation_commands_are_discovered_not_hardcoded() -> None:
    """The preference list names scripts; it does not assume they exist."""
    from sage.config import VALIDATION_SCRIPT_PREFERENCE
    from sage.tools.shell import ScriptRunner

    runner = ScriptRunner(SAGE_ROOT.parent, available_scripts=set())

    # With nothing defined by the target, nothing is runnable.
    assert all(not runner.can_run(script) for script in VALIDATION_SCRIPT_PREFERENCE)


def test_the_cassettes_cover_more_than_one_domain() -> None:
    """Generalization is only demonstrated if a second domain was actually run."""
    cassettes = SAGE_ROOT.parent / "fixtures/cassettes"
    recorded = {path.name for path in cassettes.iterdir() if path.is_dir()}

    assert "product-search" in recorded
    assert "book-inventory" in recorded


def test_the_evaluation_specs_share_no_vocabulary_with_sage() -> None:
    """Every requirement id SAGE has been run against is absent from its code."""
    from sage.tools.requirements import requirement_ids

    specs = SAGE_ROOT.parent / "specs"
    sources = "\n".join(path.read_text() for path in _sage_sources())

    for spec in specs.rglob("*.md"):
        for rid in requirement_ids(spec.read_text()):
            assert rid not in sources, f"{rid} from {spec.name} leaked into SAGE core"
