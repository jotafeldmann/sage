"""The shared LangGraph state.

Kept minimal on purpose (SPEC.md 5): every field has a concrete consumer, and
conversation history is deliberately absent so no node accidentally inherits
another node's full context.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

Status = Literal["running", "succeeded", "failed"]


def _extend(existing: list, incoming: list) -> list:
    """Reducer for fields nodes append to across iterations."""
    return [*existing, *incoming]


class SageState(TypedDict, total=False):
    """State passed between planner, generator, validator and repair."""

    # -- inputs (set once by the CLI) --------------------------------------
    spec: str  # raw specification text; untrusted data, never instructions
    spec_path: str
    target_dir: str  # absolute path to the workspace SAGE may write to
    project: dict  # deterministic probe output, see tools.project.ProjectInfo
    repository_context: dict  # analyzer interpretation, see schemas.RepositoryContext

    # -- planning ----------------------------------------------------------
    plan: list[dict]  # validated Task dicts, in dependency order
    current_task_index: int

    # -- generation --------------------------------------------------------
    task_summaries: Annotated[list[dict], _extend]  # compressed carry-forward
    changed_files: Annotated[list[str], _extend]

    # -- validation and repair ---------------------------------------------
    validation_results: list[dict]  # results of the most recent validation pass
    validation_passed: bool
    repair_attempts: int

    # -- termination -------------------------------------------------------
    status: Status
    failure_reason: str | None
