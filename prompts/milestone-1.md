# Coding Agent Prompt: Implement Milestone 1

You are implementing **Milestone 1 only** of SAGE.

Before making changes, read these files in this order:

2. `SPEC.md`
3. `README.md`
4. `docs/extras.md`
5. `specs/examples/product-search.md`

`SPEC.md` is the source of truth: it records the take-home assessment's requirements and the implementation plan for SAGE.

## Objective

Implement the smallest complete SAGE vertical slice:

```text
spec -> plan -> generate -> validate -> bounded repair
```

Use `specs/examples/product-search.md` as the first evaluation input.

## Constraints

- Implement only what Milestone 1 requires.
- Do not implement the official Car Inventory app manually.
- Do not hardcode product-search behavior into SAGE core logic.
- Use LangGraph for workflow orchestration.
- Keep the graph small.
- Prefer normal functions over extra nodes when state transitions do not require a node.
- Keep LLM/provider/model configuration outside application-specific code.
- Do not provide unrestricted filesystem or shell access to the model.
- Do not read `.env` or credentials as repository context.
- Bound the repair loop to the limit defined in `SPEC.md`.

## Required process

Before coding:

1. inspect the repository;
2. identify existing Python/project tooling and the frontend boilerplate structure;
3. propose the minimal set of files needed for Milestone 1;
4. explain the graph state and routing;
5. identify the deterministic validation commands available in the repository.

Then implement.

## Definition of Done

Milestone 1 is complete only when:

- a spec file is loaded from disk;
- a LangGraph workflow exists;
- planner output is structured and validated;
- generation makes real changes in the target application;
- deterministic validation executes;
- failed validation can route to repair;
- repair is bounded;
- the product-search evaluation passes available typecheck/tests/build checks;
- README How to Run is updated to match the real command;
- `docs/extras.md` Architecture and Agent Workflow sections are updated to describe the real implementation rather than only the design target.

## Do Not Do Yet

Do not spend time on:

- multi-agent orchestration;
- vector databases;
- long-term memory;
- elaborate plan-review systems;
- the final Car Inventory run;
- generalized analytics dashboards;
- deployment;
- CI/CD;
- sophisticated UI for SAGE.

If you discover a conflict or ambiguity, consult `SPEC.md` and `specs/` before assuming.
