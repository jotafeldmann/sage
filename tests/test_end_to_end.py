"""The recorded Milestone 1 run, replayed as a regression test.

This exercises the whole loop - plan, four generation tasks, validation via real
`npm run` commands, two repair attempts, and recovery - against a real React
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
CASSETTE = REPO / "fixtures/cassettes/product-search"
FIXTURE_APP = REPO / "fixtures/test-app"
SPEC = REPO / "specs/examples/product-search.md"

# Files the recorded run generates; the fixture must start without them.
GENERATED = ("src/products.ts", "src/ProductSearch.tsx", "src/ProductSearch.test.tsx")

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

    for generated in GENERATED:
        (target / generated).unlink(missing_ok=True)
    return target


def test_recorded_run_replays_to_a_passing_application(app_copy: Path) -> None:
    settings = Settings(
        llm_mode="replay",
        api_base_url=None,
        api_key=None,
        model="",
        max_repair_attempts=2,
        max_tasks=12,
        target_dir=app_copy,
    )
    deps = Deps.create(
        llm=ReplayLLM(Transcript(CASSETTE)), settings=settings, target_dir=app_copy
    )
    deps.quiet = True

    initial: SageState = {
        "spec": SPEC.read_text(encoding="utf-8"),
        "spec_path": str(SPEC),
        "target_dir": str(app_copy),
        "project": deps.project.to_dict(),
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

    final = build_graph(deps).invoke(
        initial, config={"recursion_limit": recursion_limit(deps)}
    )

    assert final["status"] == "succeeded"
    assert final["validation_passed"] is True

    # The recorded run needed both repair attempts to reach green.
    assert final["repair_attempts"] == 2

    # Every planned file was written.
    assert sorted(set(final["changed_files"])) == [
        "src/App.tsx",
        "src/ProductSearch.test.tsx",
        "src/ProductSearch.tsx",
        "src/products.ts",
    ]

    # All three deterministic gates ran and passed.
    ran = {r["command"]: r for r in final["validation_results"] if not r["skipped"]}
    assert set(ran) == {"npm run typecheck", "npm run test", "npm run build"}
    assert all(result["passed"] for result in ran.values())


def test_the_generated_application_satisfies_the_specification(app_copy: Path) -> None:
    """Re-run the app's own test suite outside SAGE, as a reviewer would."""
    test_recorded_run_replays_to_a_passing_application(app_copy)

    completed = subprocess.run(
        ["npm", "run", "--silent", "test"],
        cwd=app_copy,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    combined = completed.stdout + completed.stderr
    assert "4 passed" in combined
