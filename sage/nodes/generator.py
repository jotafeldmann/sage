"""Generator node: implement exactly one planned task per invocation.

The graph re-enters this node until the plan is exhausted, which keeps
incremental execution structural rather than hidden inside a loop.

Context management (SPEC.md 8) is the point of this node: each call receives the
current task, one-line summaries of the tasks it depends on, and the contents of
the files that task names - never the repository and never the run history.
"""

from __future__ import annotations

from sage import prompts
from sage.deps import Deps
from sage.llm.structured import complete_structured
from sage.schemas.changes import GenerationResult
from sage.state import SageState
from sage.tools.filesystem import WorkspaceError

CHANGES_SCHEMA = """{
  "changes": [
    {
      "path": "project/relative/path.ts",
      "contents": "the entire final file as a JSON string",
      "rationale": "one short sentence"
    }
  ],
  "summary": "one sentence describing what was implemented"
}"""


def generator_node(state: SageState, deps: Deps) -> dict:
    """Implement the task at `current_task_index` and advance the cursor."""
    plan = state.get("plan") or []
    index = state.get("current_task_index", 0)
    task = plan[index]
    position = f"{index + 1}/{len(plan)}"

    deps.say(f"[{position}] {task['description']}")

    prompt = prompts.render(
        "generator",
        project_summary=deps.project.to_prompt_summary(),
        spec=state["spec"],
        completed_work=_completed_work(state, task),
        task_position=position,
        task_description=task["description"],
        task_files=_bullets(task.get("files") or ["(you decide, following project layout)"]),
        existing_files=_existing_files(deps, task.get("files") or []),
        schema=CHANGES_SCHEMA,
    )
    result = complete_structured(
        deps.llm, prompt, GenerationResult, tag=f"generate-{task['id']}"
    )

    written = apply_changes(deps, result)
    deps.say(f"      {_describe(written)}")
    deps.refresh_project()

    return {
        "current_task_index": index + 1,
        "changed_files": written,
        "task_summaries": [
            {
                "id": task["id"],
                "summary": result.summary or task["description"],
                "files": written,
            }
        ],
        "status": "running",
    }


def apply_changes(deps: Deps, result: GenerationResult) -> list[str]:
    """Write proposed changes through the sandbox, skipping rejected paths.

    A path the workspace refuses is dropped with a warning rather than aborting
    the run: the validator is the authority on whether the result is good.
    """
    written: list[str] = []
    for change in result.changes:
        try:
            written.append(deps.fs.write_text(change.path, change.contents))
        except WorkspaceError as exc:
            deps.say(f"      refused write to {change.path!r}: {exc}")
    return written


def _completed_work(state: SageState, task: dict) -> str:
    """Summaries of this task's dependencies only - not the whole history."""
    depends_on = set(task.get("depends_on") or [])
    summaries = state.get("task_summaries") or []
    relevant = [item for item in summaries if item["id"] in depends_on]
    if not relevant:
        return "Nothing this task depends on has been implemented yet."

    lines = []
    for item in relevant:
        files = ", ".join(item["files"]) or "no files"
        lines.append(f"- {item['id']}: {item['summary']} ({files})")
    return "\n".join(lines)


def _existing_files(deps: Deps, paths: list[str]) -> str:
    files = deps.fs.read_many(paths)
    if not files:
        return "None of the files for this task exist yet. Create them."
    return "\n\n".join(
        f"### {path}\n```\n{contents}\n```" for path, contents in files.items()
    )


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _describe(written: list[str]) -> str:
    if not written:
        return "no files changed"
    return f"{len(written)} file(s): {', '.join(written)}"
