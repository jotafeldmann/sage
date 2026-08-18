"""The SAGE workflow graph.

    START -> planner -> generator --+
                          ^         | tasks remain
                          +---------+
                                    | plan exhausted
                                    v
                                validator
                                    |
                 succeeded ---------+--------- failed
                     |                            |
                     v                    budget remaining?
                    END                   yes -> repair -> validator
                                          no  -> END

Two properties matter here:

* The generator's self-edge makes task-by-task execution visible in the graph
  rather than hiding it in a Python loop.
* Termination is guaranteed three ways - the repair budget, the task cap
  applied at planning time, and LangGraph's recursion limit - and the validator
  is the only node that can set a terminal status, so a run never ends
  ambiguously.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from sage.deps import Deps
from sage.nodes import generator_node, planner_node, repair_node, validator_node
from sage.state import SageState

# Headroom over the worst case: max_tasks generator steps, plus validator and
# repair passes. LangGraph raises rather than looping if this is ever hit.
RECURSION_LIMIT_HEADROOM = 12


def route_after_generator(state: SageState) -> str:
    """Stay in the generator while planned tasks remain."""
    plan = state.get("plan") or []
    if state.get("current_task_index", 0) < len(plan):
        return "generator"
    return "validator"


def route_after_validator(state: SageState) -> str:
    """End on a terminal status, otherwise spend a repair attempt."""
    status = state.get("status", "running")
    if status in ("succeeded", "failed"):
        return END
    return "repair"


def build_graph(deps: Deps):
    """Compile the workflow with `deps` bound to every node."""
    builder = StateGraph(SageState)

    builder.add_node("planner", partial(planner_node, deps=deps))
    builder.add_node("generator", partial(generator_node, deps=deps))
    builder.add_node("validator", partial(validator_node, deps=deps))
    builder.add_node("repair", partial(repair_node, deps=deps))

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "generator")
    builder.add_conditional_edges(
        "generator",
        route_after_generator,
        {"generator": "generator", "validator": "validator"},
    )
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {"repair": "repair", END: END},
    )
    builder.add_edge("repair", "validator")

    return builder.compile()


def recursion_limit(deps: Deps) -> int:
    """A ceiling derived from the configured budgets, not a magic number."""
    generator_steps = deps.settings.max_tasks
    repair_steps = deps.settings.max_repair_attempts * 2  # repair + revalidate
    return generator_steps + repair_steps + RECURSION_LIMIT_HEADROOM
