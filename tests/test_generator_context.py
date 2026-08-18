"""What the generator actually puts in a prompt.

Milestone 3's claim is that a generation call receives task-relevant context
rather than everything. These tests assert that by inspecting the built prompt.
"""

from __future__ import annotations

import json
from pathlib import Path

from sage.deps import Deps
from sage.nodes.generator import generator_node
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

Something no task in this test asks for: pineapple telemetry.

## Constraints

- Do not add a backend.
"""

PLAN = [
    {
        "id": "task-1",
        "description": "Create the data module.",
        "files": ["src/data.ts"],
        "depends_on": [],
        "requirements": ["THING-REQ-001"],
        "priority": "required",
    },
    {
        "id": "task-2",
        "description": "Create the list component.",
        "files": ["src/List.tsx"],
        "depends_on": ["task-1"],
        "requirements": ["THING-REQ-002"],
        "priority": "required",
    },
]


def _deps(tmp_path: Path, settings, llm) -> Deps:
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "t", "scripts": {"typecheck": "true"}}), encoding="utf-8"
    )
    (tmp_path / "src" / "data.ts").write_text(
        "export interface Item {\n  id: string;\n}\n\n"
        'export const items: Item[] = [{ id: "1" }];\n\n'
        "function internalHelper() {\n  return 'not-exported-secret';\n}\n",
        encoding="utf-8",
    )
    instance = Deps.create(llm=llm, settings=settings, target_dir=tmp_path)
    instance.quiet = True
    return instance


def _state(index: int) -> SageState:
    return {
        "spec": SPEC,
        "plan": PLAN,
        "current_task_index": index,
        "task_summaries": [
            {"id": "task-1", "summary": "Added the seed data.", "files": ["src/data.ts"]}
        ],
        "changed_files": ["src/data.ts"],
        "repository_context": {"conventions": ["Named exports only."]},
    }


def _run(tmp_path, settings, index: int) -> str:
    llm = ScriptedLLM([json.dumps({"changes": [], "summary": "ok"})])
    generator_node(_state(index), _deps(tmp_path, settings, llm))
    return llm.prompts[0][1]


def test_only_the_tasks_own_requirement_reaches_the_prompt(tmp_path, settings) -> None:
    prompt = _run(tmp_path, settings, index=1)  # task-2 wants THING-REQ-002

    assert "Render the data in a list." in prompt
    assert "pineapple telemetry" not in prompt
    assert "Provide the seed data." not in prompt


def test_globally_applicable_specification_text_still_reaches_the_prompt(
    tmp_path, settings
) -> None:
    prompt = _run(tmp_path, settings, index=1)

    assert "Build a thing." in prompt
    assert "Do not add a backend." in prompt


def test_dependency_exports_are_supplied(tmp_path, settings) -> None:
    prompt = _run(tmp_path, settings, index=1)

    assert "src/data.ts exports:" in prompt
    assert "interface Item" in prompt
    assert "const items: Item[]" in prompt


def test_dependency_bodies_and_private_helpers_are_not_supplied(tmp_path, settings) -> None:
    """Signatures, not whole files - that is what keeps this inside the budget."""
    prompt = _run(tmp_path, settings, index=1)

    assert "not-exported-secret" not in prompt
    assert "internalHelper" not in prompt


def test_a_task_without_dependencies_says_so(tmp_path, settings) -> None:
    prompt = _run(tmp_path, settings, index=0)

    assert "This task has no dependencies." in prompt


def test_the_conventions_from_analysis_reach_the_prompt(tmp_path, settings) -> None:
    prompt = _run(tmp_path, settings, index=0)

    assert "Named exports only." in prompt


def test_slicing_reduces_the_prompt(tmp_path, settings) -> None:
    """The saving is real, not just structural."""
    from sage.tools.requirements import slice_for_requirements

    sliced = slice_for_requirements(SPEC, ["THING-REQ-002"])

    assert len(sliced) < len(SPEC)
