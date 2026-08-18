"""Control output is parsed defensively and retried a bounded number of times."""

from __future__ import annotations

import json

import pytest

from sage.llm.base import LLMError
from sage.llm.structured import MAX_PARSE_ATTEMPTS, complete_structured
from sage.schemas.changes import GenerationResult
from sage.schemas.plan import Plan
from tests.conftest import ScriptedLLM

VALID_PLAN = json.dumps({"tasks": [{"id": "task-1", "description": "do it"}]})


@pytest.mark.parametrize(
    "raw",
    [
        VALID_PLAN,
        f"```json\n{VALID_PLAN}\n```",
        f"Here is the plan:\n\n{VALID_PLAN}\n\nHope that helps.",
        f"```\n{VALID_PLAN}\n```",
    ],
)
def test_json_is_recovered_from_chatty_or_fenced_replies(raw: str) -> None:
    plan = complete_structured(ScriptedLLM([raw]), "prompt", Plan, tag="planner")

    assert [task.id for task in plan.tasks] == ["task-1"]


def test_malformed_output_triggers_one_corrective_retry() -> None:
    llm = ScriptedLLM(["not json at all", VALID_PLAN])

    plan = complete_structured(llm, "original prompt", Plan, tag="planner")

    assert len(plan.tasks) == 1
    assert [tag for tag, _ in llm.prompts] == ["planner", "planner-retry1"]
    # The retry tells the model what was wrong instead of silently re-asking.
    retry_prompt = llm.prompts[1][1]
    assert "original prompt" in retry_prompt
    assert "not json at all" in retry_prompt


def test_persistently_malformed_output_fails_loudly() -> None:
    llm = ScriptedLLM(["garbage"] * MAX_PARSE_ATTEMPTS)

    with pytest.raises(LLMError, match="did not return valid Plan JSON"):
        complete_structured(llm, "prompt", Plan, tag="planner")

    assert llm.usage.calls == MAX_PARSE_ATTEMPTS


def test_schema_violation_is_treated_as_malformed() -> None:
    # Valid JSON, invalid Plan: the dependency does not exist.
    bad = json.dumps({"tasks": [{"id": "a", "description": "x", "depends_on": ["ghost"]}]})
    llm = ScriptedLLM([bad, VALID_PLAN])

    plan = complete_structured(llm, "prompt", Plan, tag="planner")

    assert plan.tasks[0].id == "task-1"
    assert "unknown task" in llm.prompts[1][1]


def test_empty_response_is_rejected() -> None:
    with pytest.raises(LLMError):
        complete_structured(ScriptedLLM(["", "   "]), "prompt", GenerationResult, tag="generate")
