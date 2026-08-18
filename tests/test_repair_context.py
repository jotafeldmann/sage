"""What the repair node puts in its prompt, and what it leaves out."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage.deps import Deps
from sage.nodes.repair import repair_node
from sage.state import SageState
from tests.conftest import ScriptedLLM

SPEC = """# Thing

## Purpose

Build a thing.

## Requirements

### THING-REQ-001 - Data

Provide the seed data.

### THING-REQ-002 - Display

Render the data in a list.

### THING-REQ-003 - Unrelated

Pineapple telemetry, which no failing file implements.

## Constraints

- Do not add a backend.
"""

PLAN = [
    {
        "id": "task-1",
        "description": "Data module.",
        "files": ["src/data.ts"],
        "depends_on": [],
        "requirements": ["THING-REQ-001"],
    },
    {
        "id": "task-2",
        "description": "List component.",
        "files": ["src/List.tsx"],
        "depends_on": ["task-1"],
        "requirements": ["THING-REQ-002"],
    },
]


def _deps(tmp_path: Path, settings, llm) -> Deps:
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "t", "scripts": {"typecheck": "true"}}), encoding="utf-8"
    )
    (tmp_path / "src" / "List.tsx").write_text(
        "export const List = () => null;\n", encoding="utf-8"
    )
    (tmp_path / "src" / "data.ts").write_text("export const data = [];\n", encoding="utf-8")
    instance = Deps.create(llm=llm, settings=settings, target_dir=tmp_path)
    instance.quiet = True
    return instance


def _state(failure: dict) -> SageState:
    return {
        "spec": SPEC,
        "plan": PLAN,
        "task_summaries": [
            {"id": "task-2", "summary": "Added the list.", "files": ["src/List.tsx"]}
        ],
        "changed_files": ["src/data.ts", "src/List.tsx"],
        "validation_results": [failure],
        "repair_attempts": 0,
    }


FAILURE = {
    "command": "npm run test",
    "exit_code": 1,
    "passed": False,
    "output_excerpt": "AssertionError: expected 1 to be 2",
    "files_mentioned": ["src/List.tsx"],
    "failure_kind": "test_failure",
    "diagnostics": ["src/List.tsx:4:1 expected 1 to be 2"],
    "tests_passed": 2,
    "tests_failed": 1,
    "tests_total": 3,
}


def _prompt(tmp_path, settings, failure: dict = FAILURE) -> str:
    llm = ScriptedLLM([json.dumps({"changes": [], "summary": "ok"})])
    repair_node(_state(failure), _deps(tmp_path, settings, llm))
    return llm.prompts[0][1]


def test_only_the_failing_files_requirements_are_sent(tmp_path, settings) -> None:
    prompt = _prompt(tmp_path, settings)

    # src/List.tsx belongs to task-2, which implements THING-REQ-002.
    assert "Render the data in a list." in prompt
    assert "Pineapple telemetry" not in prompt
    assert "Provide the seed data." not in prompt


def test_globally_applicable_specification_text_survives(tmp_path, settings) -> None:
    prompt = _prompt(tmp_path, settings)

    assert "Do not add a backend." in prompt


def test_the_failure_kind_and_its_guidance_are_supplied(tmp_path, settings) -> None:
    prompt = _prompt(tmp_path, settings)

    assert "Failure kind: test_failure" in prompt
    assert "Never delete a test" in prompt


def test_test_counts_reach_the_prompt(tmp_path, settings) -> None:
    prompt = _prompt(tmp_path, settings)

    assert "2 passed, 1 failed, of 3" in prompt


def test_structured_diagnostics_reach_the_prompt(tmp_path, settings) -> None:
    prompt = _prompt(tmp_path, settings)

    assert "src/List.tsx:4:1 expected 1 to be 2" in prompt


def test_only_the_implicated_file_is_sent(tmp_path, settings) -> None:
    prompt = _prompt(tmp_path, settings)

    assert "### src/List.tsx" in prompt
    assert "### src/data.ts" not in prompt


@pytest.mark.parametrize("failure", [{**FAILURE, "files_mentioned": []}])
def test_an_unattributable_failure_falls_back_to_the_whole_spec(
    tmp_path, settings, failure
) -> None:
    """Repair with too much context beats repair with the wrong context."""
    prompt = _prompt(tmp_path, settings, failure)

    assert "Pineapple telemetry" in prompt


def test_the_attempt_number_and_limit_are_stated(tmp_path, settings) -> None:
    prompt = _prompt(tmp_path, settings)

    assert "repair attempt 1 of 2" in prompt
