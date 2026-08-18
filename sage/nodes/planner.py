"""Planner node: specification -> ordered, dependency-aware tasks.

The planner never writes application code. Its only output is a plan, which is
schema-validated before anything downstream acts on it.
"""

from __future__ import annotations

from sage import prompts
from sage.deps import Deps
from sage.llm.structured import complete_structured
from sage.schemas.plan import Plan
from sage.schemas.repository import RepositoryContext
from sage.state import SageState

PLAN_SCHEMA = """{
  "tasks": [
    {
      "id": "task-1",
      "description": "what to implement, in one or two sentences",
      "files": ["project/relative/path.ts"],
      "depends_on": ["id of a task that must happen first"],
      "requirements": ["identifier from the specification, if it has any"],
      "priority": "required | optional"
    }
  ]
}"""


def _context_summary(state: SageState) -> str:
    """Render the analyzer's findings, or say plainly that there are none."""
    raw = state.get("repository_context") or {}
    if not raw:
        return "No analysis was available for this project."
    return RepositoryContext.model_validate(raw).to_prompt_summary()


def planner_node(state: SageState, deps: Deps) -> dict:
    """Produce a validated plan and reset the task cursor."""
    deps.say("Planning implementation...")

    prompt = prompts.render(
        "planner",
        project_summary=deps.project.to_prompt_summary(),
        repository_context=_context_summary(state),
        spec=state["spec"],
        max_tasks=str(deps.settings.max_tasks),
        schema=PLAN_SCHEMA,
    )
    plan = complete_structured(deps.llm, prompt, Plan, tag="planner")

    tasks = plan.in_dependency_order()
    if len(tasks) > deps.settings.max_tasks:
        # A cap on plan length is a control-plane limit: an untrusted
        # specification must not be able to lengthen the run indefinitely.
        deps.say(
            f"  plan truncated from {len(tasks)} to {deps.settings.max_tasks} tasks "
            "(SAGE_MAX_TASKS)"
        )
        tasks = tasks[: deps.settings.max_tasks]

    deps.say(f"{len(tasks)} tasks created.\n")
    return {
        "plan": [task.model_dump() for task in tasks],
        "current_task_index": 0,
        "status": "running",
    }
