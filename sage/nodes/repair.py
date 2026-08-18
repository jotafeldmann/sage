"""Repair node: fix what deterministic validation reported.

Reached only when validation failed and budget remains; the validator has
already refused to route here past `SAGE_MAX_REPAIR_ATTEMPTS`.

Context is deliberately narrow: the failing command, a truncated error excerpt,
and only the files those errors actually name.
"""

from __future__ import annotations

from sage import prompts
from sage.deps import Deps
from sage.llm.structured import complete_structured
from sage.nodes.generator import CHANGES_SCHEMA, apply_changes
from sage.schemas.changes import GenerationResult
from sage.state import SageState
from sage.tools.diagnostics import guidance_for
from sage.tools.requirements import slice_for_requirements

# How many files to send into a repair prompt when the errors name a lot.
MAX_REPAIR_FILES = 6


def repair_node(state: SageState, deps: Deps) -> dict:
    """Attempt the smallest correction for the current failure."""
    attempt = state.get("repair_attempts", 0) + 1
    failure = _first_failure(state)

    deps.say(f"\nRepairing (attempt {attempt}/{deps.settings.max_repair_attempts})...")

    prompt = prompts.render(
        "repair",
        project_summary=deps.project.to_prompt_summary(),
        spec=_relevant_spec(state, failure),
        failed_command=failure.get("command", "unknown"),
        exit_code=str(failure.get("exit_code", "unknown")),
        failure_kind=failure.get("failure_kind") or "unknown",
        test_counts=_test_counts(failure),
        diagnostics=_diagnostics(failure),
        guidance=guidance_for(failure.get("failure_kind") or "unknown"),
        error_output=failure.get("output_excerpt") or "(no output captured)",
        completed_work=_completed_work(state),
        existing_files=_relevant_files(deps, state, failure),
        attempt=str(attempt),
        max_attempts=str(deps.settings.max_repair_attempts),
        schema=CHANGES_SCHEMA,
    )
    result = complete_structured(deps.llm, prompt, GenerationResult, tag=f"repair-{attempt}")

    written = apply_changes(deps, result)
    deps.say(f"{len(written)} file(s) updated.\n")
    deps.refresh_project()

    return {
        "repair_attempts": attempt,
        "changed_files": written,
        "task_summaries": [
            {
                "id": f"repair-{attempt}",
                "summary": result.summary or "repair attempt",
                "files": written,
            }
        ],
        "status": "running",
    }


def _test_counts(failure: dict) -> str:
    total = failure.get("tests_total")
    if total is None:
        return ""
    passed = failure.get("tests_passed")
    failed = failure.get("tests_failed")
    return f"Tests: {passed} passed, {failed} failed, of {total}"


def _diagnostics(failure: dict) -> str:
    entries = failure.get("diagnostics") or []
    if not entries:
        return "The tool did not emit parseable diagnostics; read the raw output below."
    return "\n".join(f"- {entry}" for entry in entries)


def _relevant_spec(state: SageState, failure: dict) -> str:
    """Only the requirements behind the code that broke.

    SPEC.md 6.5 asks repair to receive "relevant original requirements", not the
    whole document. The plan already records which requirements each task
    implements and which files it touches, so the failing files identify the
    requirements worth sending. If nothing matches, the full specification is
    used - repair working from too much context is far better than repair
    working from the wrong context.
    """
    implicated = set(failure.get("files_mentioned") or [])
    if not implicated:
        return state["spec"]

    wanted: list[str] = []
    for task in state.get("plan") or []:
        if implicated.intersection(task.get("files") or []):
            wanted.extend(r for r in (task.get("requirements") or []) if r not in wanted)

    return slice_for_requirements(state["spec"], wanted) if wanted else state["spec"]


def _first_failure(state: SageState) -> dict:
    for result in state.get("validation_results") or []:
        if not result.get("passed"):
            return result
    return {}


def _relevant_files(deps: Deps, state: SageState, failure: dict) -> str:
    """Files the errors named, falling back to what the run actually changed."""
    candidates = list(failure.get("files_mentioned") or [])
    if not candidates:
        for path in reversed(state.get("changed_files") or []):
            if path not in candidates:
                candidates.append(path)

    files = deps.fs.read_many(candidates[:MAX_REPAIR_FILES])
    if not files:
        return "No related source files could be identified from the failure output."
    return "\n\n".join(f"### {path}\n```\n{contents}\n```" for path, contents in files.items())


def _completed_work(state: SageState) -> str:
    summaries = state.get("task_summaries") or []
    if not summaries:
        return "No implementation summaries are available."
    return "\n".join(f"- {item['id']}: {item['summary']}" for item in summaries[-6:])
