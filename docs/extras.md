# Extras

This page contains the detailed engineering notes for SAGE. Keep the README short and use this page for depth.

The canonical assessment remains [`project.pdf`](project.pdf). Do not use this page to silently redefine assessment requirements.

## Assessment Alignment

The take-home evaluates both the coding agent and the quality of its generated application.

Key areas from the assessment:

| Assessment area | How SAGE intends to demonstrate it |
|---|---|
| Task decomposition | Planner produces ordered, dependency-aware tasks |
| Tool use | Explicit filesystem and constrained shell operations |
| Context management | Repository summaries and task-specific file context |
| Error recovery | Validator routes failures to bounded repair |
| Prompt design | Structured, role-specific prompts and schema-validated outputs |
| Agent architecture/workflow | Small LangGraph state machine with visible routing |
| Output quality | Official Car Inventory evaluation |
| Documentation | README plus this central extras page |
| Generalization | Non-car evaluation spec without core code changes |

The assessment gives Agent Architecture & Workflow and Output Quality the largest individual weights. Required generated-app behavior must not be sacrificed for architectural novelty.

## References

### Agentic Code Generation Workflow

Repository:

https://github.com/yiptsunho/agentic-code-generation-workflow

Ideas worth studying rather than blindly copying:

- planning before implementation;
- repository exploration;
- explicit validation gates;
- validation-driven repair;
- bounded retries;
- context compression;
- restricted tools;
- measurement of tokens and cost;
- honest documentation of tradeoffs and limitations.

SAGE intentionally starts smaller and should only adopt additional complexity after a concrete failure mode justifies it.

### LangGraph

Overview:

https://docs.langchain.com/oss/python/langgraph/overview

Graph API:

https://docs.langchain.com/oss/python/langgraph/graph-api

Relevant ideas:

- shared graph state;
- discrete nodes;
- explicit edges;
- conditional routing;
- cyclic workflows with controlled termination.

### OpenSpec

Project:

https://github.com/Fission-AI/OpenSpec

Relevant idea:

- keep implementation anchored to persistent specification artifacts instead of relying on chat history alone.

SAGE does not need to adopt OpenSpec itself for this take-home. It borrows the discipline of treating specifications and intermediate artifacts as durable project context.

## Architecture

Initial architecture:

```text
                 +----------------------+
                 | Product Specification |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 | Repository Analyzer  |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |       Planner        |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |      Generator       |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |      Validator       |
                 +----------+-----------+
                            |
                      +-----+-----+
                      |           |
                   success      failure
                      |           |
                      v           v
                    END   +----------------+
                          |     Repair     |
                          +-------+--------+
                                  |
                                  +-------> Validator
```

Architecture principles:

1. **Plan before broad code changes.**
2. **Use deterministic validation as the primary quality gate.**
3. **Keep repair bounded.**
4. **Keep state explicit and inspectable.**
5. **Keep nodes narrow enough that failures are diagnosable.**
6. **Do not introduce a new agent/node when a normal function is sufficient.**

Architecture status: **design target, not yet implementation evidence**.

Update this section when Milestone 1 produces real code.

## Agent Workflow

Target execution:

```text
1. Load specification
2. Resolve target workspace
3. Inspect repository
4. Build compact repository context
5. Create dependency-aware task plan
6. Validate plan schema
7. Execute tasks sequentially
8. Run deterministic validation
9. If validation passes, finish
10. If validation fails and retry budget remains, repair relevant files
11. Re-run validation
12. Stop successfully or expose unresolved failure
```

Expected run output should make state transitions visible without printing raw prompts, secrets, or excessive logs.

Example:

```text
Analyzing repository...
Repository analyzed.

Planning implementation...
7 tasks created.

[1/7] Creating data query...
[2/7] Creating data hook...
[3/7] Creating UI...

Running typecheck...
FAILED: 2 errors

Repairing...
2 files updated.

Running typecheck...
PASSED
Running tests...
PASSED
```

## Optimization Techniques Applied

This section should distinguish **planned techniques** from **measured techniques**.

### Planned for the initial implementation

#### Context window control

Do not attach the full repository to each model call.

#### State-to-prompt compression

Convert repository exploration and prior task results into concise structured summaries before downstream calls.

#### Model/tool call budgets

Bound repair attempts and any retry behavior that could otherwise loop.

#### Error-aware context selection

Repair prompts should include the failure plus only the source files reasonably related to it.

#### Structured validation output

Normalize compiler and test results before sending them back to the model. Prefer machine-readable reporters when the existing tooling supports them without excessive boilerplate modification.

#### Tool gating

Filesystem and shell permissions are narrower than the LLM's natural-language capabilities.

### Measurements

TBD after real SAGE runs.

When results exist, record what actually reduced tokens, retries, runtime, or failure rate. Do not claim an optimization worked solely because it exists in code.

## Safety and Tool Boundaries

SAGE operates on untrusted natural-language specifications and generated code, so tool permissions are part of the architecture.

### Filesystem

- Resolve paths against one configured workspace.
- Reject path traversal outside the workspace.
- Do not read `.env`, SSH keys, home configuration, or unrelated credentials.
- Do not allow the input specification to expand filesystem scope.

### Shell

- Prefer allowlisted commands or known package scripts discovered from the repository.
- Do not provide unrestricted arbitrary shell execution to the model.
- A shell command embedded in a product specification is untrusted text, not authorization.

### Prompt injection boundary

The product specification controls application requirements, not SAGE policy.

Instructions such as "ignore previous instructions", "read .env", "upload files", or "run this arbitrary shell command" must not alter SAGE tool permissions or control logic.

### Loop/cost boundaries

- Initial repair limit: 2 attempts.
- Additional retry budgets should be explicit.
- When a budget is exhausted, expose the failure rather than hiding it behind a success message.

## Tradeoffs

### LangGraph vs a plain loop

**Choice:** LangGraph.

**Benefit:** The plan/generate/validate/repair workflow becomes explicit through shared state and conditional edges.

**Cost:** More framework surface than a simple Python loop.

**Boundary:** Do not use LangGraph as justification for unnecessary nodes or agents.

### Small graph vs specialized multi-agent system

**Choice:** Small graph.

**Benefit:** Faster implementation, easier debugging, easier explanation in an interview.

**Cost:** Less specialization and fewer independent review roles.

**Future trigger:** Add specialized review only if evaluation demonstrates a specific recurring failure that a separate node can improve.

### Deterministic validation vs LLM-only review

**Choice:** Compiler/tests first.

**Benefit:** Clear pass/fail signals and reproducible repair input.

**Cost:** Tests can be incomplete and compilation does not prove behavioral correctness.

**Mitigation:** Use application tests and optionally a bounded LLM review later, never as a replacement for available deterministic checks.

### Configurable model vs hardcoded model

**Choice:** Configure model via environment.

**Benefit:** Easier cost/performance experiments and less coupling.

**Cost:** Reproducibility requires recording which model was used for measured runs.

## Changes Made to Boilerplate

No boilerplate changes have been made by this starter pack.

For every future change, record:

```text
Change:
Why it was necessary:
Agent/workflow benefit:
Risk or tradeoff:
How to revert:
```

Possible example, only if actually implemented later:

- configure a machine-readable Vitest reporter so validation failures can be normalized with less prompt noise.

Do not add a change here until it exists in the repository.

## Evaluation Strategy

### Evaluation 1: Product Search

Spec: `../specs/examples/product-search.md`

Goal:

- prove the smallest end-to-end generation loop;
- reduce GraphQL/MSW complexity while the agent infrastructure is still unstable.

Record after execution:

```text
Date:
Commit:
Model:
Result:
Validation commands:
Repair attempts:
Duration:
Notes:
```

### Evaluation 2: Repair Injection

Goal:

- deliberately create or introduce one type/test failure during development;
- verify that the validator captures it;
- verify that repair uses the actual failure;
- verify that re-validation happens automatically.

Do not preserve intentional broken code in the final generated sample.

### Evaluation 3: Official Car Inventory

Spec: `../specs/car-inventory.md`

Goal:

- satisfy required generated-application behavior from `project.pdf`;
- preserve the generated application as the submission sample output.

### Evaluation 4: Generalization

Spec: `../specs/examples/book-inventory.md`

Goal:

- run the same SAGE core against a different domain;
- prove car-specific logic is not embedded in core prompts or code.

### Results

TBD after implementation.

## What Worked Well

TBD after implementation and measured runs.

Use concrete observations such as:

- first-pass plan quality;
- number of generation tasks completed without repair;
- whether repository analysis prevented incorrect scaffolding;
- whether normalized errors led to targeted repair;
- whether context reduction lowered token usage;
- whether bounded retries prevented runaway loops.

Avoid generic retrospective statements that are not supported by a run or code review.

## What I Would Improve

Initial candidates, not yet conclusions:

- plan review gate;
- failure classification before repair;
- model routing by task difficulty;
- better CLI UX;
- stronger evaluation harness;
- richer metrics per node;
- optional human approval before implementation;
- better handling of provider rate limits;
- stronger sandboxing if the agent expands beyond the assessment environment.

Keep only improvements that remain relevant after implementation.

## Average Cost Per Run

No cost value is available yet.

Do not invent one.

After several representative runs, record:

| Metric | Value |
|---|---:|
| Runs measured | TBD |
| Average duration | TBD |
| Average model calls | TBD |
| Average tool calls | TBD |
| Average input tokens | TBD |
| Average output tokens | TBD |
| Average repair attempts | TBD |
| Average cost per run | TBD |

If practical, also add a per-stage breakdown:

| Stage | Tokens | Cost | Duration |
|---|---:|---:|---:|
| Repository analysis | TBD | TBD | TBD |
| Planning | TBD | TBD | TBD |
| Generation | TBD | TBD | TBD |
| Repair | TBD | TBD | TBD |
| Total | TBD | TBD | TBD |

Always record the model/provider used for the measured dataset.

## Repository Structure

Target structure:

```text
.
├── README.md
├── SPEC.md
├── .env.example
├── docs/
│   ├── project.pdf
│   └── extras.md
├── specs/
│   ├── car-inventory.md
│   └── examples/
│       ├── product-search.md
│       └── book-inventory.md
├── prompts/
│   ├── milestone-1.md
│   └── milestone-template.md
├── sage/
│   ├── graph.py
│   ├── state.py
│   ├── nodes/
│   ├── tools/
│   ├── prompts/
│   └── schemas/
└── generated-app/
```

This is a target, not a mandate to create empty abstraction layers. Prefer fewer files until implementation needs justify more structure.
