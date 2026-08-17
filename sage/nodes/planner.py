"""Planner node: specification -> ordered, dependency-aware tasks.

The planner never writes application code. Its only output is a plan, which is
schema-validated before anything downstream acts on it.
"""

from __future__ import annotations

from sage import prompts
from sage.llm.structured import complete_structured
from sage.runtime import Runtime
from sage.schemas.plan import Plan
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


def planner_node(state: SageState, runtime: Runtime) -> dict:
    """Produce a validated plan and reset the task cursor."""
    runtime.say("Planning implementation...")

    prompt = prompts.render(
        "planner",
        project_summary=runtime.project.to_prompt_summary(),
        spec=state["spec"],
        max_tasks=str(runtime.settings.max_tasks),
        schema=PLAN_SCHEMA,
    )
    plan = complete_structured(runtime.llm, prompt, Plan, tag="planner")

    tasks = plan.in_dependency_order()
    if len(tasks) > runtime.settings.max_tasks:
        # A cap on plan length is a control-plane limit: an untrusted
        # specification must not be able to lengthen the run indefinitely.
        runtime.say(
            f"  plan truncated from {len(tasks)} to {runtime.settings.max_tasks} tasks "
            "(SAGE_MAX_TASKS)"
        )
        tasks = tasks[: runtime.settings.max_tasks]

    runtime.say(f"{len(tasks)} tasks created.\n")
    return {
        "plan": [task.model_dump() for task in tasks],
        "current_task_index": 0,
        "status": "running",
    }
