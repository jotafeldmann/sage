# SAGE

**Specification Agent for Generation and Execution**

SAGE is a small agentic spec-to-code workflow that takes a natural-language software specification, inspects an existing application repository, plans the work, generates or edits code, validates the result, and attempts bounded repairs when validation fails.

The original take-home assessment is preserved at [`docs/project.pdf`](docs/project.pdf). It is the canonical source of truth for assessment requirements. [`SPEC.md`](SPEC.md) translates those requirements into an actionable implementation specification for SAGE.

## How to Run

This starter pack contains specifications and documentation only. The first implementation milestone is intentionally left for the coding agent.

Recommended start:

```bash
# 1. Copy this starter pack into the provided boilerplate repository.

# 2. Configure environment variables when the agent implementation exists.
cp .env.example .env

# 3. Give your coding agent the main specification and Milestone 1 prompt.
#    Files to provide:
#    - SPEC.md
#    - prompts/milestone-1.md
#    - docs/project.pdf

# 4. After Milestone 1 exists, run SAGE against the small evaluation spec first.
# Example target CLI, to be implemented:
python -m sage specs/examples/product-search.md

# 5. Then run the official evaluation spec.
python -m sage specs/car-inventory.md
```

The exact CLI may change during implementation. Any deviation should be reflected here once it becomes real behavior.

## Stack

| Layer | Initial choice | Rationale |
|---|---|---|
| Agent language | Python | Fast iteration and strong agent tooling ecosystem |
| Workflow orchestration | LangGraph | Explicit shared state, conditional routing, and bounded repair cycles |
| LLM integration | LangChain | Provider abstraction and structured model/tool integration |
| Structured outputs | Pydantic | Validate planner and workflow-control outputs before execution |
| LLM provider | OpenAI-compatible, configured by environment | Keep model choice configurable instead of hardcoding application logic to a model |
| Observability | LangSmith, optional | Trace nodes, latency, token usage, failures, and retries during development |
| Generated app stack | Existing assessment boilerplate | React 19, TypeScript, Vite, Apollo Client, MUI, MSW, Vitest, Testing Library |
| Deterministic validation | Existing npm scripts | Compiler and tests provide stronger workflow gates than LLM-only review |

## Extras

Architecture, references, tradeoffs, evaluation strategy, optimization notes, security boundaries, boilerplate changes, measured cost, and retrospective notes live in [`docs/extras.md`](docs/extras.md).
