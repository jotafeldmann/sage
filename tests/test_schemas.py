"""Malformed control output must fail loudly, not drive the generator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sage.schemas.plan import Plan
from sage.schemas.validation import extract_mentioned_files


def _task(task_id: str, depends_on: list[str] | None = None) -> dict:
    return {
        "id": task_id,
        "description": f"do {task_id}",
        "files": [f"src/{task_id}.ts"],
        "depends_on": depends_on or [],
    }


def test_empty_plan_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Plan.model_validate({"tasks": []})


def test_duplicate_task_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Plan.model_validate({"tasks": [_task("a"), _task("a")]})


def test_unresolvable_dependency_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown task"):
        Plan.model_validate({"tasks": [_task("a", ["ghost"])]})


def test_self_dependency_is_rejected() -> None:
    with pytest.raises(ValidationError, match="itself"):
        Plan.model_validate({"tasks": [_task("a", ["a"])]})


def test_dependency_cycle_is_rejected() -> None:
    with pytest.raises(ValidationError, match="cycle"):
        Plan.model_validate({"tasks": [_task("a", ["b"]), _task("b", ["a"])]})


def test_longer_dependency_cycle_is_rejected() -> None:
    tasks = [_task("a", ["c"]), _task("b", ["a"]), _task("c", ["b"])]
    with pytest.raises(ValidationError, match="cycle"):
        Plan.model_validate({"tasks": tasks})


def test_tasks_are_returned_in_dependency_order() -> None:
    plan = Plan.model_validate(
        {"tasks": [_task("ui", ["data"]), _task("tests", ["ui"]), _task("data")]}
    )

    assert [task.id for task in plan.in_dependency_order()] == ["data", "ui", "tests"]


def test_error_output_only_yields_files_that_exist() -> None:
    output = (
        "src/App.tsx(12,5): error TS2322: Type 'string' is not assignable.\n"
        "../../etc/passwd.ts:1:1 - error\n"
        "node_modules/react/index.d.ts(3,1): error\n"
    )

    found = extract_mentioned_files(output, known_files={"src/App.tsx", "src/other.tsx"})

    assert found == ["src/App.tsx"]


def test_ansi_colour_codes_are_stripped_from_excerpts() -> None:
    from sage.schemas.validation import strip_ansi

    coloured = "\x1b[36m<div>\x1b[39m\n\x1b[31mFAILED\x1b[0m src/App.test.tsx"

    assert strip_ansi(coloured) == "<div>\nFAILED src/App.test.tsx"
