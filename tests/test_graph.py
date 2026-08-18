"""End-to-end behaviour of the workflow: routing, repair, and termination.

These run the real graph, the real sandbox and real `npm run` commands. Only the
model is stubbed, so the deterministic half of SAGE is genuinely exercised.
"""

from __future__ import annotations

import json

import pytest

from sage.deps import Deps
from sage.graph import build_graph, recursion_limit
from sage.state import SageState
from tests.conftest import ScriptedLLM

PLAN = json.dumps(
    {
        "tasks": [
            {
                "id": "task-1",
                "description": "Implement the feature.",
                "files": ["src/Feature.tsx"],
                "depends_on": [],
                "requirements": ["REQ-001"],
                "priority": "required",
            }
        ]
    }
)


def _changes(path: str, contents: str, summary: str = "done") -> str:
    return json.dumps(
        {"changes": [{"path": path, "contents": contents, "rationale": "r"}], "summary": summary}
    )


def _project(tmp_path, scripts: dict[str, str]):
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "t", "scripts": scripts}), encoding="utf-8"
    )
    return tmp_path


def _run(deps: Deps, spec: str = "Build a feature.") -> dict:
    initial: SageState = {
        "spec": spec,
        "spec_path": "spec.md",
        "target_dir": str(deps.fs.root),
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
    return build_graph(deps).invoke(
        initial, config={"recursion_limit": recursion_limit(deps)}
    )


def test_run_succeeds_when_validation_passes(tmp_path, settings) -> None:
    root = _project(tmp_path, {"typecheck": "true", "test": "true"})
    llm = ScriptedLLM([PLAN, _changes("src/Feature.tsx", "export const Feature = () => null;\n")])
    deps = Deps.create(llm=llm, settings=settings, target_dir=root)
    deps.quiet = True

    final = _run(deps)

    assert final["status"] == "succeeded"
    assert final["validation_passed"] is True
    assert final["repair_attempts"] == 0
    assert final["changed_files"] == ["src/Feature.tsx"]
    assert (root / "src/Feature.tsx").is_file()
    # planner + one generator call, and nothing else.
    assert [tag for tag, _ in llm.prompts] == ["planner", "generate-task-1"]


def test_repair_runs_and_recovers_a_real_validation_failure(tmp_path, settings) -> None:
    # The gate passes only once the marker file exists, so the first validation
    # genuinely fails and the repair genuinely fixes it.
    root = _project(tmp_path, {"typecheck": "test -f src/marker.ts"})
    llm = ScriptedLLM(
        [
            PLAN,
            _changes("src/Feature.tsx", "export const Feature = () => null;\n"),
            _changes("src/marker.ts", "export const marker = true;\n", "added the missing module"),
        ]
    )
    deps = Deps.create(llm=llm, settings=settings, target_dir=root)
    deps.quiet = True

    final = _run(deps)

    assert final["status"] == "succeeded"
    assert final["repair_attempts"] == 1
    assert "repair-1" in [tag for tag, _ in llm.prompts]
    assert sorted(set(final["changed_files"])) == ["src/Feature.tsx", "src/marker.ts"]


def test_repair_is_bounded_and_the_run_terminates(tmp_path, settings) -> None:
    root = _project(tmp_path, {"typecheck": "false"})  # never passes
    llm = ScriptedLLM([PLAN] + [_changes("src/Feature.tsx", "export const x = 1;\n")] * 3)
    deps = Deps.create(llm=llm, settings=settings, target_dir=root)
    deps.quiet = True

    final = _run(deps)

    assert final["status"] == "failed"
    assert final["repair_attempts"] == settings.max_repair_attempts == 2
    # Exactly two repairs were attempted - no third, and no infinite loop.
    repair_tags = [tag for tag, _ in llm.prompts if tag.startswith("repair")]
    assert repair_tags == ["repair-1", "repair-2"]
    assert "after 2 repair attempt" in final["failure_reason"]


def test_failure_output_is_exposed_rather_than_hidden(tmp_path, settings) -> None:
    root = _project(tmp_path, {"typecheck": "echo 'src/Feature.tsx(1,1): error TS1005' && false"})
    llm = ScriptedLLM([PLAN] + [_changes("src/Feature.tsx", "export const x = 1;\n")] * 3)
    deps = Deps.create(llm=llm, settings=settings, target_dir=root)
    deps.quiet = True

    final = _run(deps)

    failure = next(r for r in final["validation_results"] if not r["passed"])
    assert "TS1005" in failure["output_excerpt"]
    # The failing file was identified and fed to repair.
    assert failure["files_mentioned"] == ["src/Feature.tsx"]


def test_absent_scripts_are_skipped_not_assumed(tmp_path, settings) -> None:
    root = _project(tmp_path, {"test": "true"})  # no typecheck, no build
    llm = ScriptedLLM([PLAN, _changes("src/Feature.tsx", "export const x = 1;\n")])
    deps = Deps.create(llm=llm, settings=settings, target_dir=root)
    deps.quiet = True

    final = _run(deps)

    assert final["status"] == "succeeded"
    by_command = {r["command"]: r for r in final["validation_results"]}
    assert by_command["npm run typecheck"]["skipped"] is True
    assert by_command["npm run build"]["skipped"] is True
    assert by_command["npm run test"]["skipped"] is False


@pytest.mark.parametrize("attempts", [0, 1, 5])
def test_recursion_limit_scales_with_the_configured_budgets(settings, workspace, attempts) -> None:
    from dataclasses import replace

    deps = Deps.create(
        llm=ScriptedLLM([]),
        settings=replace(settings, max_repair_attempts=attempts),
        target_dir=workspace,
    )

    assert recursion_limit(deps) == settings.max_tasks + attempts * 2 + 12
