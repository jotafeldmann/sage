"""Recorded runs, replayed as regression tests.

These exercise the whole graph - analysis, planning, task-by-task generation,
validation via real `npm run` commands, and repair - against a real React
project. Only the model responses are recorded; everything else runs for real.

Skipped when the fixture's dependencies are not installed, since the validation
commands genuinely need them.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from sage.config import Settings
from sage.deps import Deps
from sage.graph import build_graph, recursion_limit
from sage.llm.replay import ReplayLLM
from sage.llm.transcript import Transcript
from sage.state import SageState

REPO = Path(__file__).resolve().parent.parent
CASSETTES = REPO / "fixtures/cassettes"
FIXTURE_APP = REPO / "fixtures/test-app"
SPEC = REPO / "specs/examples/product-search.md"

# The fixture is committed with only these two files under src/; everything
# else there is generated output. Listing what to *keep* rather than what to
# delete means a new evaluation spec needs no change here.
FIXTURE_BASELINE = ("App.tsx", "main.tsx")

EXPECTED_FILES = [
    "src/App.tsx",
    "src/ProductSearch.test.tsx",
    "src/ProductSearch.tsx",
    "src/products.ts",
]

pytestmark = pytest.mark.skipif(
    not (FIXTURE_APP / "node_modules").is_dir(),
    reason="fixture dependencies not installed (cd fixtures/test-app && npm install)",
)


@pytest.fixture
def app_copy(tmp_path: Path) -> Path:
    """A pristine copy of the fixture app, with node_modules symlinked in."""
    target = tmp_path / "app"
    shutil.copytree(
        FIXTURE_APP, target, ignore=shutil.ignore_patterns("node_modules", "dist", ".sage")
    )
    (target / "node_modules").symlink_to(FIXTURE_APP / "node_modules")

    for path in (target / "src").iterdir():
        if path.name not in FIXTURE_BASELINE:
            path.unlink()
    return target


def _replay(cassette: str, app: Path, spec: Path = SPEC) -> dict:
    settings = Settings(
        llm_mode="replay",
        api_base_url=None,
        api_key=None,
        model="",
        max_repair_attempts=2,
        max_tasks=12,
        target_dir=app,
    )
    deps = Deps.create(
        llm=ReplayLLM(Transcript(CASSETTES / cassette)), settings=settings, target_dir=app
    )
    deps.quiet = True

    initial: SageState = {
        "spec": spec.read_text(encoding="utf-8"),
        "spec_path": str(spec),
        "target_dir": str(app),
        "project": deps.project.to_dict(),
        "repository_context": {},
        "plan": [],
        "current_task_index": 0,
        "task_summaries": [],
        "changed_files": [],
        "validation_results": [],
        "validation_passed": False,
        "repair_attempts": 0,
        "status": "running",
        "failure_reason": None,
    }
    return build_graph(deps).invoke(initial, config={"recursion_limit": recursion_limit(deps)})


def test_the_clean_run_reaches_a_passing_application(app_copy: Path) -> None:
    final = _replay("product-search", app_copy)

    assert final["status"] == "succeeded"
    assert final["validation_passed"] is True
    assert final["repair_attempts"] == 0
    assert sorted(set(final["changed_files"])) == EXPECTED_FILES

    ran = {r["command"]: r for r in final["validation_results"] if not r["skipped"]}
    assert set(ran) == {"npm run typecheck", "npm run test", "npm run build"}
    assert all(result["passed"] for result in ran.values())


def test_the_plan_is_repository_aware(app_copy: Path) -> None:
    """Milestone 2: analysis happens before planning and reaches the plan."""
    final = _replay("product-search", app_copy)

    # The analyzer ran and its findings are in state.
    context = final["repository_context"]
    assert context["conventions"], "analyzer produced no conventions"
    assert context["testing_approach"]

    # The deterministic probe identified the stack rather than assuming it.
    assert final["project"]["framework"] == "React"
    assert final["project"]["test_runner"] == "Vitest"
    assert final["project"]["build_tool"] == "Vite"

    # The plan modifies the existing entry component instead of scaffolding a
    # parallel one, which is what "does not assume a fresh scaffold" means.
    planned_files = {path for task in final["plan"] for path in task["files"]}
    assert "src/App.tsx" in planned_files
    assert not any(p.startswith("src/components/") for p in planned_files)


def test_the_repair_run_recovers_from_a_real_failure(app_copy: Path) -> None:
    final = _replay("product-search-repair", app_copy)

    assert final["status"] == "succeeded"
    assert final["repair_attempts"] == 1
    assert sorted(set(final["changed_files"])) == EXPECTED_FILES


def test_the_generated_application_satisfies_the_specification(app_copy: Path) -> None:
    """Re-run the app's own test suite outside SAGE, as a reviewer would."""
    _replay("product-search", app_copy)

    completed = subprocess.run(
        ["npm", "run", "--silent", "test"],
        cwd=app_copy,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "4 passed" in completed.stdout + completed.stderr


def test_an_unseen_specification_runs_through_the_same_core(app_copy: Path) -> None:
    """Milestone 6: a different domain must need no SAGE change.

    The fixture, the graph, the prompts and the tools are identical to the
    product-search runs. Only the specification differs.
    """
    spec = REPO / "specs/examples/book-inventory.md"

    final = _replay("book-inventory", app_copy, spec=spec)

    assert final["status"] == "succeeded"
    assert final["validation_passed"] is True
    assert final["repair_attempts"] == 0
    assert sorted(set(final["changed_files"])) == [
        "src/App.tsx",
        "src/BookInventory.test.tsx",
        "src/BookInventory.tsx",
        "src/books.ts",
    ]


def test_the_unseen_specification_produces_a_distinct_plan(app_copy: Path) -> None:
    product = _replay("product-search", app_copy)
    books = _replay("book-inventory", app_copy)

    product_files = {path for task in product["plan"] for path in task["files"]}
    book_files = {path for task in books["plan"] for path in task["files"]}
    book_requirements = {r for task in books["plan"] for r in task["requirements"]}

    # Different files, and requirements traced to the specification that was
    # actually given.
    assert book_files != product_files
    assert all(r.startswith("BOOK-") for r in book_requirements)
    # The sorting requirement has no counterpart in the product-search spec.
    assert "BOOK-REQ-003" in book_requirements


def test_the_unseen_applications_tests_pass_outside_sage(app_copy: Path) -> None:
    _replay("book-inventory", app_copy, spec=REPO / "specs/examples/book-inventory.md")

    completed = subprocess.run(
        ["npm", "run", "--silent", "test"],
        cwd=app_copy,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "5 passed" in completed.stdout + completed.stderr
