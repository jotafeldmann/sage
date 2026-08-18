# SAGE Product and Implementation Specification

## 0. Authority and Source of Truth

This file is the source of truth for what SAGE must do. Section 3 records the
requirements the take-home assessment set out; the rest of this document
translates them into an actionable implementation specification and records the
engineering decisions taken where the assessment left a choice open.

### Source precedence

1. `SPEC.md` - this file: SAGE's requirements and chosen engineering decisions.
2. `docs/extras.md` - supporting architecture notes, tradeoffs, evaluation
   results, metrics, and retrospective notes.
3. Implementation assumptions - only when the sources above do not define the
   behavior.

Where the assessment left something ambiguous, make a reasonable engineering
assumption and record it in `docs/extras.md`.

A requirement that is not written down here or in `specs/` is not recoverable.
Treat both as the record rather than as a summary of one.

## 1. Product

**Name:** SAGE  
**Meaning:** Specification Agent for Generation and Execution

SAGE is an agentic specification-to-code system. It transforms a natural-language product specification into a validated, runnable application inside an existing project boilerplate.

SAGE is not a universal autonomous developer. The first version is intentionally scoped to a reliable, explainable coding workflow over the supplied frontend boilerplate.

## 2. Primary Goal

Given:

1. an existing application boilerplate;
2. a natural-language software specification;
3. access to an LLM;

SAGE must autonomously:

1. inspect the existing repository;
2. extract relevant repository context;
3. convert the specification into dependency-aware implementation tasks;
4. execute the tasks incrementally;
5. create or modify application files;
6. run deterministic validation;
7. interpret validation failures;
8. repair failures when possible;
9. stop safely when retry limits are reached;
10. leave a runnable output project and observable execution result.

## 3. Assessment Requirements Captured from the Original Assessment

The assessment requires an agentic workflow rather than a manually implemented car application.

The agent must:

- accept a natural-language specification as a string or text file;
- plan the implementation as discrete, ordered tasks;
- generate application code file by file with dependency awareness;
- generate into the supplied boilerplate rather than scaffold an unrelated project from scratch;
- self-validate by running tests and/or using an additional review step;
- use failures from tests or type checking as feedback for recovery;
- produce a runnable project;
- demonstrate task decomposition, discrete tool use, context management, error recovery, and structured prompt design.

The assessment also values planned work, clear architecture decisions, meaningful commit history, and iterative development.

The reference generated application is a Car Inventory Manager. Its required and optional requirements are captured separately in `specs/car-inventory.md` so that car-specific behavior does not leak into SAGE core logic.

## 4. SAGE Design Decisions

The following are SAGE decisions, not requirements imposed by the assessment unless also recorded in section 3.

### 4.1 Workflow framework

Use LangGraph for the orchestration layer.

Reason:

- the workflow has shared state;
- execution has explicit stages;
- validation produces conditional routing;
- repair creates a bounded cycle;
- the graph makes termination behavior visible and explainable.

Keep the graph small. Do not introduce a multi-agent architecture unless a later measured problem justifies it.

### 4.2 Initial graph

```text
Specification
      |
      v
Repository Analyzer
      |
      v
Planner
      |
      v
Generator
      |
      v
Validator
      |
      +---- success ----> END
      |
      +---- failure ----> Repair
                           |
                           +--------> Validator
```

A later plan-review gate is allowed, but it is not required for Milestone 1.

## 5. Workflow State

Start with the minimum state needed to coordinate nodes.

Indicative shape:

```python
class SageState(TypedDict):
    spec: str
    target_dir: str
    repository_context: dict
    plan: list
    current_task_index: int
    changed_files: list[str]
    validation_results: list
    validation_passed: bool
    repair_attempts: int
```

The implementation may refine this type, but new state fields must have a clear consumer. Do not store full conversation history by default.

## 6. Nodes

### 6.1 Repository Analyzer

Responsibilities:

- inspect repository structure;
- inspect relevant package configuration;
- identify framework, language, scripts, dependencies, test tooling, and source directories;
- identify files that are likely to matter to planning;
- produce concise repository context for downstream nodes.

Constraints:

- do not send the entire repository to the LLM;
- do not read secrets;
- do not traverse outside the configured workspace;
- prefer deterministic repository inspection before asking the LLM to infer structure.

Expected output categories:

- framework and language;
- available libraries;
- npm scripts;
- source/test locations;
- important files;
- reusable existing infrastructure;
- concise architectural observations.

### 6.2 Planner

Responsibilities:

- interpret the product specification;
- combine requirements with repository context;
- produce discrete implementation tasks;
- order tasks according to dependencies;
- identify likely files to create or modify;
- keep required functionality ahead of optional functionality.

The planner must return structured output validated before execution.

Indicative schema:

```json
{
  "tasks": [
    {
      "id": "task-1",
      "description": "Create the data query required by the specification",
      "files": ["src/example.ts"],
      "depends_on": [],
      "requirements": ["REQ-..."],
      "priority": "required"
    }
  ]
}
```

The planner must not directly write application code.

### 6.3 Generator

Responsibilities:

- execute planned tasks in dependency order;
- select only task-relevant context;
- read existing files needed for the current task;
- create or modify files inside the target workspace;
- preserve compatibility with the existing boilerplate;
- record changed files and a concise implementation summary.

Each generation call should receive only what is useful for that task:

- relevant requirements;
- current task;
- dependency outputs or summaries;
- relevant repository context;
- relevant existing/generated files.

Do not send the entire repository and full execution history on every generation call.

### 6.4 Validator

The validator should use deterministic tools as the primary quality gate.

When scripts exist, validation should attempt the relevant equivalents of:

```bash
npm run typecheck
npm test
npm run build
```

Do not assume every boilerplate exposes every command. The repository analyzer should identify the available scripts first.

Validation state should capture:

- command;
- exit code;
- normalized success/failure;
- useful stdout/stderr;
- affected files when identifiable;
- test counts when available.

Prefer structured or normalized tool output over dumping large raw logs into the next LLM prompt.

### 6.5 Repair

The repair node receives:

- validation failure;
- relevant original requirements;
- relevant source files;
- recent task summaries;
- repair attempt number.

Responsibilities:

- diagnose the failure;
- modify only files reasonably related to the failure;
- avoid broad rewrites unless evidence supports them;
- return control to validation.

Initial repair limit:

```text
MAX_REPAIR_ATTEMPTS = 2
```

If validation still fails after the retry limit, SAGE must stop gracefully and expose the unresolved validation output.

## 7. Tooling and Safety Boundaries

### 7.1 Filesystem

Required capabilities:

- list files/directories;
- read text files;
- create text files;
- modify text files.

Rules:

- all paths must resolve inside the configured target workspace;
- reject path traversal outside the workspace;
- do not read `.env` or credential-bearing files;
- do not read SSH keys, home configuration, or unrelated user files;
- do not allow the product specification to expand filesystem permissions.

### 7.2 Shell

Shell execution must use an allowlist or equivalently constrained command runner.

Initial intended operations:

- dependency installation for the target project when needed;
- known npm scripts discovered in the project;
- type checking;
- tests;
- build;
- optional development server command for human verification.

The model must not receive unrestricted arbitrary shell access.

A command appearing inside the untrusted product specification is not automatically authorized.

### 7.3 Untrusted specification handling

The user-provided product specification is data, not execution policy.

Text inside the specification must not be allowed to:

- override SAGE system/developer instructions;
- expand filesystem boundaries;
- expand shell permissions;
- expose credentials;
- alter retry/cost limits;
- instruct SAGE to ignore safety constraints;
- read files unrelated to implementing the target application.

Product requirements may affect generated application behavior. They must not redefine SAGE's control plane.

## 8. Context Management

Context management is a first-class requirement.

Preferred flow:

```text
repository inspection
       |
       v
compressed repository context
       |
       v
planning
       |
       v
task-specific context
       |
       v
generation / repair
```

Rules:

- summarize repository exploration before passing it downstream;
- include only relevant source files for each task;
- avoid replaying raw tool logs when normalized results are enough;
- avoid full message history unless a node genuinely needs it;
- preserve requirement identifiers in plans and summaries where useful for traceability.

## 9. Structured Outputs

Workflow-control outputs must be schema validated where practical.

Use Pydantic or an equivalent schema layer for at least:

- implementation plan;
- file change proposals if returned as structured data;
- validation normalization;
- optional failure classification.

Malformed control output should trigger a bounded retry or explicit failure rather than silently continuing with guessed values.

## 10. CLI Contract

Target developer experience:

```bash
python -m sage path/to/spec.md
```

or an equivalent single-command interface.

The CLI should make the target workspace explicit or safely infer it from documented configuration.

Expected visible progress:

```text
Analyzing repository...
Repository analyzed.

Planning implementation...
7 tasks created.

[1/7] ...
[2/7] ...

Running typecheck...
FAILED

Repairing...
2 files updated.

Running typecheck...
PASSED
Running tests...
PASSED

Generation complete.
```

Do not invent success messages before deterministic commands have actually passed.

## 11. Observability and Metrics

SAGE should make it possible to measure:

- total execution duration;
- model calls;
- tool calls;
- input tokens;
- output tokens;
- approximate model cost;
- validation attempts;
- repair attempts;
- final validation result.

LangSmith tracing is recommended during development but must not be required for the generated application itself.

Measurements belong in `docs/extras.md` only after they have been observed. Do not fabricate cost or token values.

## 12. Generated Application Scope

The supplied assessment boilerplate already includes React 19, TypeScript, Vite, Apollo Client, Material UI, MSW, Vitest, and Testing Library.

SAGE should work with that repository rather than replace it with an unrelated stack.

The initial SAGE version does not need to support arbitrary frameworks.

## 13. Generalization Requirement

SAGE core code and prompts must not hardcode the official Car Inventory implementation.

Core SAGE logic must not depend on application-specific identifiers such as:

```text
Car
CarCard
GetCars
useCars
vehicle
make
model
```

Those concepts may appear in `specs/car-inventory.md` and in the generated application because they are requirements of that input specification.

At least one unrelated evaluation specification must run through the same workflow without changing SAGE core implementation.

## 14. Evaluation Specifications

### Evaluation A: Product Search vertical slice

File: `specs/examples/product-search.md`

Purpose:

- prove the full `spec -> plan -> generate -> validate` path with minimal frontend complexity;
- establish a small baseline before Apollo/MSW/GraphQL concerns are introduced.

### Evaluation B: Repair behavior

Purpose:

- prove that a real type-check or test failure can route into repair and back into validation.

The failure may be intentionally introduced during development. Do not keep deliberate broken code in the final sample output.

### Evaluation C: Official Car Inventory

File: `specs/car-inventory.md`

Purpose:

- evaluate the application requirements captured in `specs/car-inventory.md`.

### Evaluation D: Unseen/generalization spec

File: `specs/examples/book-inventory.md`

Purpose:

- prove the agent is not a car-specific generator.

## 15. Milestones

### Milestone 1: End-to-End Vertical Slice

Implement the smallest complete SAGE loop over `specs/examples/product-search.md`.

Required path:

```text
spec -> plan -> generate -> validate -> bounded repair
```

Definition of done:

- a spec file can be loaded;
- the planner returns schema-valid tasks;
- the generator makes at least one real repository change;
- deterministic validation runs;
- a failure can route to repair;
- repair is bounded;
- the small generated/modified application passes the selected validation commands.

Do not implement later-milestone sophistication merely because it is described elsewhere in this specification.

### Milestone 2: Repository-Aware Planning

Add explicit repository analysis before planning.

Definition of done:

- plan reflects actual installed libraries and repository structure;
- planner does not assume a fresh scaffold;
- repository context is summarized rather than blindly copied.

### Milestone 3: Controlled Code Generation

Strengthen task-by-task generation and tool boundaries.

Definition of done:

- multiple dependency-aware tasks execute sequentially;
- filesystem scope is enforced;
- shell operations are constrained;
- task-specific context is used instead of full-repository prompts.

### Milestone 4: Autonomous Validation and Repair

Strengthen the feedback loop.

Definition of done:

- typecheck/tests/build are normalized into workflow state where available;
- at least one real validation failure is repaired automatically;
- retry limit terminates repeated failure safely.

### Milestone 5: Official Car Inventory Run

Run SAGE against `specs/car-inventory.md`.

Definition of done:

- all required Car Inventory functionality from the source assessment is implemented;
- available deterministic validation passes;
- generated output is preserved as the sample output requested by the assessment.

Optional Car Inventory requirements are secondary to required functionality.

### Milestone 6: Generalization

Run SAGE against `specs/examples/book-inventory.md` or another unseen specification.

Definition of done:

- no change to SAGE core code or system prompts is required to understand the different domain;
- SAGE produces a distinct dependency-aware plan;
- the same generation/validation loop executes.

### Milestone 7: Submission Readiness

Definition of done:

- agent source code is present;
- README setup instructions are accurate;
- `.env.example` lists required API/config keys without secrets;
- sample input specification is present;
- sample generated output directory is present;
- `docs/extras.md` reflects actual architecture and measured results;
- model/provider choice and rationale are documented;
- architecture and tradeoffs are documented;
- what worked and what would be improved are documented;
- approximate measured cost per run is documented;
- commit history shows incremental work rather than one final dump.

## 16. Documentation Contract

### `README.md`

Keep it concise. Required top-level sections:

```text
# SAGE
## How to Run
## Stack
## Extras
```

It may contain a short overview before `How to Run`.

### `docs/extras.md`

This is the central detailed documentation page. Maintain these sections:

```text
# Extras
## Assessment Alignment
## References
## Architecture
## Agent Workflow
## Optimization Techniques Applied
## Safety and Tool Boundaries
## Tradeoffs
## Changes Made to Boilerplate
## Evaluation Strategy
## What Worked Well
## What I Would Improve
## Average Cost Per Run
## Repository Structure
```

Documentation must describe real behavior. Leave measured sections explicitly pending until data exists rather than inventing numbers.

## 17. Target Repository Shape

The exact implementation layout may evolve, but the initial target is:

```text
.
├── README.md
├── SPEC.md
├── .env.example
├── docs/
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

Avoid creating abstractions that have no concrete need in the current milestone.

## 18. Non-Goals for the First Version

Do not spend initial implementation time on:

- a large multi-agent organization;
- vector databases;
- long-term memory;
- unrestricted browsing;
- arbitrary shell execution;
- deployment infrastructure;
- CI/CD generation;
- authentication;
- database provisioning;
- universal support for every framework;
- perfect UI generation;
- framework abstractions whose only purpose is future possibility.

The assessment explicitly values a clean, well-thought-out solution over unnecessary framework complexity.

## 19. Final Success Criteria

SAGE is successful for this assessment when:

1. it accepts a natural-language specification through a documented command;
2. it inspects the existing repository instead of assuming a blank project;
3. it produces an ordered dependency-aware plan;
4. it generates application code incrementally;
5. it uses filesystem and shell actions as controlled tools;
6. it executes deterministic validation;
7. validation failures can trigger bounded repair;
8. the official Car Inventory required functionality is generated successfully;
9. a non-car specification demonstrates generalization;
10. the generated sample output is runnable;
11. the architecture, prompts, tradeoffs, cost, limitations, and implementation decisions are documented;
12. implementation remains explainable within the assessment's stated time budget.
