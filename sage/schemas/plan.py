"""Implementation plan schema.

The planner returns JSON matching `Plan`. It is validated before any file is
touched, so a malformed or hostile plan fails loudly instead of driving the
generator with guessed values.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Task(BaseModel):
    """One discrete, dependency-aware unit of implementation work."""

    id: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=2000)
    files: list[str] = Field(default_factory=list, max_length=20)
    depends_on: list[str] = Field(default_factory=list, max_length=20)
    requirements: list[str] = Field(default_factory=list, max_length=20)
    priority: Literal["required", "optional"] = "required"


class Plan(BaseModel):
    """An ordered set of tasks with resolvable, acyclic dependencies."""

    tasks: list[Task] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_dependency_graph(self) -> Plan:
        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("task ids must be unique")

        known = set(ids)
        for task in self.tasks:
            unknown = set(task.depends_on) - known
            if unknown:
                raise ValueError(f"task {task.id!r} depends on unknown task(s): {sorted(unknown)}")
            if task.id in task.depends_on:
                raise ValueError(f"task {task.id!r} depends on itself")

        _assert_acyclic(self.tasks)
        return self

    def in_dependency_order(self) -> list[Task]:
        """Return tasks topologically sorted, preserving planner order on ties."""
        by_id = {task.id: task for task in self.tasks}
        ordered: list[Task] = []
        placed: set[str] = set()

        remaining = list(self.tasks)
        while remaining:
            progressed = False
            still_blocked = []
            for task in remaining:
                if all(dep in placed for dep in task.depends_on):
                    ordered.append(task)
                    placed.add(task.id)
                    progressed = True
                else:
                    still_blocked.append(task)
            remaining = still_blocked
            if not progressed:  # pragma: no cover - prevented by _assert_acyclic
                raise ValueError("dependency cycle detected")

        assert len(ordered) == len(by_id)
        return ordered


def _assert_acyclic(tasks: list[Task]) -> None:
    """Depth-first cycle detection over the dependency edges."""
    depends_on = {task.id: list(task.depends_on) for task in tasks}
    state: dict[str, int] = {}  # 0 = visiting, 1 = done

    def visit(node: str, trail: list[str]) -> None:
        mark = state.get(node)
        if mark == 1:
            return
        if mark == 0:
            cycle = " -> ".join([*trail[trail.index(node) :], node])
            raise ValueError(f"dependency cycle detected: {cycle}")
        state[node] = 0
        for dep in depends_on.get(node, []):
            visit(dep, [*trail, node])
        state[node] = 1

    for task_id in depends_on:
        visit(task_id, [])
