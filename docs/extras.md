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

## External Dependencies and Known Limitations

### The official boilerplate is not available

`docs/project.pdf` lists the boilerplate under **"Repository: Provided
separately"**. It was not supplied with this workspace and is not present in it.
Everything the assessment says about that repository - React 19, Vite, Apollo
Client, MUI, MSW, Vitest, a `Car` type, a `GetCars` query, five seed cars - is
therefore **documentation, not something SAGE has ever seen**.

Decision: do not download, infer, or recreate a replacement and treat it as the
real target. A reconstruction would look like the boilerplate without being it,
and every difference would surface as a mystery failure during the Car Inventory
milestone.

Consequences, all deliberate:

- **SAGE assumes nothing about the target stack.** It discovers npm scripts,
  libraries and layout by reading `package.json` and the file listing at
  runtime. `tests/test_generalization.py` asserts that the strings `apollo`,
  `msw`, `graphql`, `mui` and the evaluation specs' vocabulary appear nowhere
  in SAGE core.
- **Validation commands are discovered, not assumed.** A project without a
  `typecheck` script is not a failing project; that gate is skipped and recorded
  as skipped.
- **`generated-app/` is intentionally empty.** It is the submission's output
  directory and stays empty until there is a real boilerplate to copy into it.
- **`fixtures/test-app/` is a throwaway harness**, labelled as such in the first
  line of its own README. It is minimal React + TypeScript + Vitest with no
  Apollo, MSW or MUI, precisely so that SAGE cannot quietly acquire habits from
  a stand-in.

To plug the real boilerplate in later: point `--target-dir` at it. No SAGE code
change is expected. That expectation is untested until the boilerplate exists,
and it is the main risk carried into Milestone 5.

### Other limitations after Milestone 1

- **Dependency file contents do not travel forward, only summaries.** A task
  that consumes another task's module is told what that module does, not what it
  looks like. In the recorded run this is exactly what caused the first
  validation failure: the test task had to guess the component's query surface
  and guessed wrong. Repair recovered it, which is the design working - but a
  cheaper fix would be to include dependency files' public signatures. Deferred
  to Milestone 3 rather than guessed at now.
- **`npm install` is never run automatically.** The target project's
  dependencies must already be installed.
- **One specification, one target directory, one pass.** No resume, no
  incremental re-plan, no partial-failure recovery beyond repair.
- **No token or cost measurement yet** - see *Average Cost Per Run*.

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

Architecture status after Milestone 2: **implemented as designed**, including
the Repository Analyzer node.

Milestone 1 deliberately shipped without that node, on the grounds that
repository inspection made no model call and so did not need to be one. Milestone
2 changed that judgement for a specific reason: the *interpretive* half of
analysis - what the installed libraries mean for someone about to change this
code, what conventions the files demonstrate, what already exists worth reusing -
is not derivable from a static rule. That part is a model call, and a model call
that mutates shared state is a node.

The split is now explicit:

| Layer | Answers | How |
|---|---|---|
| `tools/project.py` | *What is here?* | Static lookups over `package.json` and the file listing. No model. |
| `nodes/analyzer.py` | *What does it mean for the change I am about to make?* | One model call over a bounded sample of the ranked-important files. |

SPEC.md 6.1 asks for exactly this ordering - "prefer deterministic repository
inspection before asking the LLM to infer structure".

Implemented graph (`sage/graph.py`):

```text
START -> analyzer -> planner -> generator --+
                                   ^        | tasks remain
                                   +--------+
                                            | plan exhausted
                                            v
                                        validator
                                            |
                         succeeded ---------+--------- failed
                             |                            |
                             v                    budget remaining?
                            END                   yes -> repair -> validator
                                                  no  -> END
```

Three properties are deliberate:

* The **analyzer runs before planning**, so the planner is told what the project
  already is rather than inferring it from a bare dependency list.
* The generator's **self-edge** makes task-by-task execution visible in the
  graph rather than hidden inside a Python loop.
* The **validator is the only node that can set a terminal status**, so a run
  always ends explicitly `succeeded` or `failed` and never ambiguously.

Termination is bounded three independent ways: the repair budget
(`SAGE_MAX_REPAIR_ATTEMPTS`, default 2), a plan-length cap applied at planning
time (`SAGE_MAX_TASKS`, default 12), and a LangGraph recursion limit derived
from both. The task cap exists because plan length is otherwise attacker
-controlled via the specification.

## Agent Workflow

Actual execution, as implemented in Milestone 1:

```text
1.  CLI loads the specification file as data
2.  WorkspaceFS is opened on --target-dir; nothing outside it is reachable
3.  probe_project() reads package.json and the file listing (no model call)
4.  analyzer   -> one model call over a bounded file sample -> RepositoryContext
5.  planner    -> one model call -> Plan validated by Pydantic
6.  generator  -> one model call per task, in dependency order
7.  validator  -> runs the project's own typecheck / test / build
8.  pass       -> status=succeeded, exit 0
9.  fail       -> repair (bounded), then back to 7
10. budget out -> status=failed, unresolved output printed, exit 1
```

Observed output from the recorded Milestone 1 run:

```text
SAGE: specs/examples/product-search.md -> .../fixtures/test-app
  provider: manual   transcript: .sage/runs/m2-product-search

Analyzing repository...
Repository analyzed: React / TypeScript, Vitest tests, 4 scripts.

Planning implementation...
4 tasks created.

[1/4] Create the product data module ...
      1 file(s): src/products.ts
[2/4] Create the ProductSearch component ...
      1 file(s): src/ProductSearch.tsx
[3/4] Render ProductSearch from the existing App component.
      1 file(s): src/App.tsx
[4/4] Add tests covering initial visibility ...
      1 file(s): src/ProductSearch.test.tsx

Running typecheck...
PASSED
Running test...
FAILED (exit 1)

Repairing (attempt 1/2)...
1 file(s) updated.

Running typecheck...
PASSED
Running test...
FAILED (exit 1)

Repairing (attempt 2/2)...
1 file(s) updated.

Running typecheck...
PASSED
Running test...
PASSED
Running build...
PASSED

Files changed: 4
Repair attempts: 2
Model calls: 7

Generation complete.
```

Nothing is reported as passing before the command that proves it has exited
zero. The `PASSED` lines above are printed after the corresponding `npm run`
returned 0.

### Node responsibilities and the context each receives

| Node | Model call | Context it is given |
|---|---|---|
| `analyzer` | 1 | The deterministic probe summary + the contents of at most 6 ranked-important files, each capped at 2,500 chars |
| `planner` | 1 | Specification + the probe summary + the analyzer's findings + the plan schema + one domain-neutral example |
| `generator` | 1 per task | The current task only, its dependencies' **one-line summaries**, the analyzer's **conventions list**, and the contents of the files that task names |
| `validator` | 0 | Nothing. It is entirely deterministic. |
| `repair` | 1 per attempt | The failing command, a truncated ANSI-stripped error excerpt, and only the files those errors actually name |

Only the `conventions` list travels from analysis into generation, not the whole
`RepositoryContext`. The rest of the analysis is aimed at planning; repeating it
on every generation call would cost tokens per task for context the planner has
already acted on. The conventions earn their place because the first task in a
plan creates a *new* file and therefore has no existing sibling to imitate.

No node receives the repository, the full message history, or another node's
prompt.

## Optimization Techniques Applied

This section should distinguish **planned techniques** from **measured techniques**.

### Implemented in Milestone 1

Each technique below names the code that implements it.

#### Context window control

No model call receives the repository. `sage/nodes/generator.py` sends one task,
its dependencies' summaries, and only the files that task names.

#### State-to-prompt compression

`ProjectInfo.to_prompt_summary()` reduces the repository probe to seven lines.
Completed tasks travel forward as a one-line summary each, never as file
contents (`sage/state.py`, `task_summaries`).

#### Model/tool call budgets

`SAGE_MAX_REPAIR_ATTEMPTS` (2), `SAGE_MAX_TASKS` (12), a derived LangGraph
recursion limit, and `MAX_PARSE_ATTEMPTS` (2) for malformed structured output.

#### Error-aware context selection

`extract_mentioned_files()` parses source paths out of compiler and test output
and intersects them with files that actually exist, so repair receives only the
implicated files - and log noise cannot cause arbitrary reads.

#### Structured validation output

Every command is normalized into `ValidationResult`. Output is ANSI-stripped and
truncated to `MAX_OUTPUT_EXCERPT_CHARS` (4,000), keeping the tail where
compilers put diagnostics. ANSI stripping was added after the first recorded
repair prompt arrived full of vitest colour codes.

#### Tool gating

The model never supplies a command string. It can only cause an npm script to
run that is both allowlisted by SAGE and defined by the target project.

### Measurements

Measured from the committed cassettes. Prompt sizes are exact; nothing here is
estimated.

**Milestone 2, clean run** (`fixtures/cassettes/product-search/`) — 6 calls:

| Call | Characters |
|---|---:|
| `001-analyze-repository` | 5,779 |
| `002-planner` | 7,208 |
| `003-generate-task-1` | 4,850 |
| `004-generate-task-2` | 5,635 |
| `005-generate-task-3` | 4,875 |
| `006-generate-task-4` | 4,822 |
| **Total** | **33,169** |

**Milestone 1, for comparison** — 7 calls, total 39,245 chars, largest 9,220.

Two real observations from that comparison, and one non-observation:

1. **The planner prompt grew by ~2.2 KB** (5,016 → 7,208) — that is the analysis
   being carried into it. This is the direct, intended cost of Milestone 2.
2. **Per-generation prompts grew by ~0.7 KB each**, which is the conventions
   list. Bounded and flat, since it does not accumulate per task.
3. **Total fell** (39,245 → 33,169) only because this run needed no repair
   attempts. As explained under *Evaluation Results*, that is not attributable
   to the analyzer — both transcripts were hand-authored by the same author.
   The repair cassette is the fairer shape comparison: 7 calls like Milestone 1,
   and 44,489 characters against Milestone 1's 39,245. Repository analysis
   makes a run *more* expensive per attempt. It has to pay for itself by
   avoiding repairs, and that has not been measured.

**The standing caveat on all of these numbers.** The evaluation target is a
deliberately tiny fixture — about 3.5 KB of TypeScript plus 1.2 KB of config.
Its entire contents would fit in a single prompt. These figures show that
per-call context stays small and roughly flat, but they are **not** evidence
that the context-management design saves anything, because there is nothing here
to save. A meaningful measurement needs a repository large enough for the naive
approach to hurt. That is Milestone 5's job, against the real boilerplate.

What the recorded prompts do verify by inspection:

- the analyzer received 4 files, not the repository, each fence-capped;
- the planner received the probe summary plus the analysis, not any file;
- `generate-task-2` received task-1's one-line summary, not `products.ts`;
- `generate-task-3` received the existing `App.tsx` **contents**, because that
  task names the file it modifies — so the generator inspects before editing;
- `repair-1` (in the repair cassette) received exactly one file, because that is
  the only file the vitest output named.

Token and cost figures are **not** recorded, because both measured runs were
executed in `manual` mode, where no provider reports usage. `sage/llm/base.py`
tracks token counts only when a provider actually returns them, and reports
`None` otherwise rather than estimating. See *Average Cost Per Run*.

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

- Repair limit: 2 attempts (`SAGE_MAX_REPAIR_ATTEMPTS`).
- Plan length cap: 12 tasks (`SAGE_MAX_TASKS`). Plan length is otherwise
  controlled by the untrusted specification.
- Structured-output reparse: 2 attempts, then a hard failure.
- LangGraph recursion limit, derived from the two budgets above.
- When a budget is exhausted the unresolved validation output is printed and the
  process exits 1. There is no success message on a failed run.

### What is enforced in code, and where

| Boundary | Implementation | Test |
|---|---|---|
| Path traversal, absolute paths, symlink escape | `WorkspaceFS.resolve()` | `tests/test_filesystem.py` |
| `.env`, keys, `.npmrc`, `.netrc` unreadable | `DENIED_NAME_PATTERNS` | `tests/test_filesystem.py` |
| Only source files writable | `TEXT_SUFFIXES` check in `write_text()` | `tests/test_filesystem.py` |
| No arbitrary commands | `ScriptRunner`, `shell=False`, allowlist ∩ project scripts | `tests/test_shell.py` |
| Secrets stripped from child processes | `_child_env()` | `tests/test_shell.py` |
| Specification cannot raise limits or escape the workspace | end-to-end hostile spec through the real graph | `tests/test_injection.py` |
| Analysis cannot read secrets or inflate the prompt | bounded file sample from the probe's ranked list, `.env` denied by `WorkspaceFS` | `tests/test_analyzer.py` |
| Operator cancellation is never swallowed | `LLMAborted` re-raised past graceful degradation | `tests/test_analyzer.py` |

`tests/test_injection.py` runs a specification that demands
`MAX_REPAIR_ATTEMPTS = 999`, `.env` disclosure, writes to `../../`, and
`curl … | sh`, and asserts that the repair count is still 2, no file appears
outside the workspace, no prompt in the entire run contains the secret, and no
shell command runs. The hostile text does still reach the prompt - delimited and
labelled as untrusted data, which is the point. Stripping it would be a filter
that a rephrasing defeats; SAGE's guarantee is that the tools cannot do what the
text asks regardless of whether the model is persuaded.

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

### Provider-native structured output vs in-prompt schema

**Choice:** In-prompt JSON schema, validated by Pydantic on the way back, with
one bounded corrective retry that shows the model its own bad output and the
validation error.

**Why:** SAGE needs `api`, `manual` and `replay` to be interchangeable. A reply
that a human pastes in by hand cannot use a provider's structured-output feature,
so the schema has to live somewhere both a provider and a person can honour.

**Cost:** More parsing code, and reliability now depends on prompt quality rather
than a provider guarantee. `_extract_json()` has to cope with fenced, prefixed
and chatty replies.

**Benefit beyond portability:** this is what SPEC.md 9 asks for anyway - malformed
control output fails loudly instead of driving the generator with guessed values.

### Recording every run

**Choice:** All three providers write the same prompt/response transcript to
`.sage/runs/<run-id>/`.

**Benefit:** Any run becomes a deterministic, zero-cost regression fixture. The
Milestone 1 end-to-end test replays a real recorded run - including its two
repair attempts - against a pristine copy of the fixture, with no network and no
API key, in about 12 seconds. It also means the exact context every node received
is inspectable after the fact, which is how the ANSI-noise problem was found.

**Cost:** Transcripts are bulky, and a replay diverges the moment the graph takes
a different path - `ReplayLLM` raises rather than silently substituting a
mismatched response.

### Configurable model vs hardcoded model

**Choice:** Configure model via environment.

**Benefit:** Easier cost/performance experiments and less coupling.

**Cost:** Reproducibility requires recording which model was used for measured runs.

## Changes Made to Boilerplate

**No changes have been made to the assessment boilerplate, because it is not
present in this workspace.** See *External Dependencies and Known Limitations*.

`fixtures/test-app/` is not the boilerplate, so its contents are not recorded
here as boilerplate changes. It is a throwaway harness created by this project.

One decision inside the fixture is worth stating, since it would be a real
boilerplate change if applied to the official repository:

```text
Change:              `test` script is `vitest run --passWithNoTests`
Why it was necessary: vitest exits 1 when a project has no test files, so a
                     project that SAGE has not yet written tests for would fail
                     validation before SAGE had done anything wrong.
Agent/workflow benefit: the baseline is green, so any failure the validator
                     reports is attributable to SAGE.
Risk or tradeoff:    a specification that asks for tests, and a run that then
                     silently produces none, would pass this gate. The plan
                     schema records test tasks, so this is visible in the plan,
                     but it is not enforced by the validator.
How to revert:       drop the flag from fixtures/test-app/package.json.
```

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

#### Evaluation 1 + 2: Product Search, including repair — PASSED

Evaluations 1 and 2 were satisfied by the same run: the repair path was exercised
by a genuine failure that arose during normal generation, so no failure had to be
injected artificially.

```text
Date:                2026-08-17
Commit:              see `git log` for "feat: complete the Milestone 1 end-to-end run"
Model:               none - run in `manual` mode (no API key available in this
                     environment); responses authored through the paste bridge
Spec:                specs/examples/product-search.md
Target:              fixtures/test-app  (NOT the assessment boilerplate)
Result:              SUCCEEDED, exit 0
Plan:                4 tasks, dependency-ordered
Validation commands: npm run typecheck, npm run test, npm run build  (all
                     discovered from the target's package.json)
Repair attempts:     2 of 2
Final validation:    typecheck PASSED, test PASSED (4 tests), build PASSED
Model calls:         7  (1 plan, 4 generate, 2 repair)
Duration:            ~8s on replay, dominated by npm; wall time in manual mode is
                     not meaningful since it includes human paste latency
Transcript:          fixtures/cassettes/product-search/
```

What the repair loop actually did:

1. **First failure** (1 of 3 tests passing). The test task depends on the
   component task but receives only its one-line summary, so it guessed the
   input's query surface and used `getByPlaceholderText` against a component that
   uses a `<label>`. Repair received the failing command, the vitest output
   including the rendered DOM, and exactly one file - the test - and switched to
   `getByLabelText`.
2. **Second failure** (2 of 3 passing). A genuine logic error in the generated
   assertion: the test searched `"mo"` and asserted that *Mouse* disappears, but
   `"Mouse"` really does contain `"mo"`. Repair correctly concluded the assertion
   was wrong rather than the filter, chose a distinguishing search term, and
   added a case-insensitive multi-match case.
3. **Third validation**: typecheck, test and build all passed.

This is worth stating plainly: **both repair attempts were consumed and the run
recovered on the last one.** The bound is demonstrated as a real limit, not a
theoretical one. No deliberately broken code survives in the generated output.

Independently re-verified outside SAGE:

```text
cd fixtures/test-app
npm run typecheck   ->  exit 0
npm test            ->  4 passed (4)
npm run build       ->  exit 0
```

Requirement traceability:

| Requirement | Satisfied by |
|---|---|
| PRODUCT-REQ-001 seed products | `src/products.ts` — Keyboard, Monitor, Mouse |
| PRODUCT-REQ-002 case-insensitive search | `ProductSearch.tsx` — `name.toLowerCase().includes(needle)` |
| PRODUCT-REQ-003 empty state | `ProductSearch.tsx` — renders `No products found` |
| PRODUCT-REQ-004 tests | `ProductSearch.test.tsx` — 4 passing tests |

#### Milestone 2 re-run: repository-aware planning — PASSED

The same specification, re-run after the analyzer was added. Both cassettes are
committed and both are exercised by `tests/test_end_to_end.py`.

```text
Date:                2026-08-17
Spec:                specs/examples/product-search.md
Target:              fixtures/test-app  (NOT the assessment boilerplate)
Provider:            manual (no API key available), replayable via `--llm replay`

fixtures/cassettes/product-search/         6 model calls, 0 repairs, PASSED
fixtures/cassettes/product-search-repair/  7 model calls, 1 repair,  PASSED

Final validation, both: typecheck PASSED, test PASSED (4 tests), build PASSED
```

What the analyzer actually produced, and what changed downstream:

- It identified the project as Vite-bundled React 19 in TypeScript **with no
  router, state library or data layer**, and concluded that any data a feature
  needs must be local. The plan reflects that: `src/products.ts` is a local
  module, and no task proposes an API client.
- It read `vitest.setup.ts` and `vite.config.ts` and reported that jest-dom
  matchers are preloaded and Vitest globals are enabled. The plan's test task
  says to use the configured globals rather than proposing to set up a runner
  that already exists.
- It reported the flat `src/` layout with no `components/` directory. The plan
  places new files flat in `src/` and **modifies** `src/App.tsx` rather than
  scaffolding a parallel screen. `test_the_plan_is_repository_aware` asserts
  both of these.

**An honest caveat, which matters more than the result.** The Milestone 1 run
needed two repair attempts; this one needed none. That is *not* evidence that
repository analysis reduces repairs. Both transcripts were authored by hand
through the manual paste bridge by the same author, so the second run had the
benefit of knowing how the first one failed. A real comparison needs `--llm api`
runs against an unseen specification, with the analyzer switched on and off.
Until then, what is demonstrated is that the analysis *reaches* the planner and
*visibly shapes* the plan - which is Milestone 2's actual definition of done -
not that it improves outcomes.

#### Evaluation 3: Official Car Inventory — NOT RUN

Blocked on the boilerplate. Milestone 5.

#### Evaluation 4: Generalization — NOT RUN as a full generation

The *negative* half is enforced now: `tests/test_generalization.py` asserts that
no evaluation-spec vocabulary and no unseen-stack name appears in SAGE core. The
*positive* half - actually generating the book inventory - is Milestone 6.

## What Worked Well

Concrete observations from the one recorded run and the test suite. This is a
single run on a small specification; none of it is a general claim.

- **The deterministic validator is the most valuable component.** Both failures
  were caught by the project's own test runner, not by any model judgement, and
  both repair prompts were built from real compiler and test output.
- **Narrow repair context was sufficient.** Repair received one file each time
  and fixed the problem both times. The error-to-file mapping did not need to be
  clever - parsing paths out of the output and intersecting with files that exist
  was enough.
- **Recording every run paid for itself immediately.** Reading the saved prompts
  is how the ANSI-noise problem was found; that would have been invisible from
  the console output alone.
- **The graph made termination easy to reason about.** Making the validator the
  only node that can set a terminal status removed a whole class of "which node
  decides we are done" bugs.
- **Testing the injection boundary end-to-end, through the real graph, rather
  than unit-testing the sanitizer.** The guarantee that matters is that the tools
  cannot do what the hostile text asks - which is only observable at the whole
  -run level.

### Milestone 2 observations

- **Separating "what is here" from "what it means" was the right cut.** The
  deterministic probe answers factual questions cheaply and identically every
  run; the model is only asked for the judgement a static rule cannot supply.
  It also means a failed analysis degrades to "planning with facts only" rather
  than aborting.
- **Recognition tables beat assumptions.** Detecting the framework from what is
  installed, and reporting `unknown` when nothing matches, kept the
  generalization test passing unchanged while still satisfying SPEC.md 6.1's
  "identify framework" requirement. Enumerating a specific boilerplate's data
  and mocking libraries would have failed that test — correctly.
- **The prompt files were again the debugging surface.** Reading
  `002-planner.prompt.md` is how the analysis was confirmed to actually reach
  the planner, rather than trusting that the wiring was right.

### Real defects the tests and recordings caught

LangGraph injects its own `Runtime` object into any node parameter named
`runtime`. SAGE's dependency container was bound with
`partial(node, runtime=deps)` and was being **silently replaced** by LangGraph's
own object at call time. Every node failed with `AttributeError` the first time
the graph ran for real. Renamed to `Deps`/`deps`.

Worth recording because it is the argument for the end-to-end graph tests: no
amount of unit testing the nodes in isolation would have found it.

**Milestone 2: graceful degradation swallowed operator cancellation.** The
analyzer catches `LLMError` so a failed analysis does not abort the run. But
`ManualLLM` raised that same type when the operator pressed Ctrl-C, so cancelling
a run silently continued into planning with no analysis. Found while recording,
not by a test — pressing Enter at the analyzer prompt produced a planner prompt.
Fixed by adding `LLMAborted`, a subclass so every existing handler still catches
it, re-raised past the degradation path. Now covered by a test.

The general lesson: a broad `except` that implements a fallback needs to say
which failures it is a fallback *for*.

## What I Would Improve

Now grounded in what Milestone 1 actually surfaced, rather than a wish list.

**Still the highest-value change, and now the clearest one:**

1. **Pass dependency signatures, not just summaries.** Milestone 1's first
   failure happened because the test task knew what the component *did* but not
   what it *looked like*. Milestone 2 narrowed the gap - the generator now gets
   the conventions list - but did not close it: a task still cannot see the
   exported signatures of the module it depends on. The repair cassette
   reproduces exactly this failure, which makes it the obvious Milestone 3 work.
2. **Let the generator see sibling files it is about to integrate with.**
   Related to the above, and the same fix.

**Indicated by the implementation:**

3. **Failure classification before repair.** A typecheck error, a failed
   assertion, and a missing module deserve different repair prompts. Currently
   all three get the same one.
4. **Re-validate incrementally.** After a repair touching only test files, the
   full build does not need to re-run.
5. **Token and cost accounting.** The plumbing exists (`Usage`), but no run has
   yet gone through a provider that reports usage.
6. **A plan review gate.** Not yet justified - both recorded plans were sound.
   Worth revisiting only if a measured run produces a bad plan.
7. **Cache the analysis per target directory.** Every run re-analyzes a project
   that has not changed. A digest of the probe output would make the analyzer
   call skippable across runs. Not done, because with one small fixture it would
   optimise something that has never been observed to hurt.
8. **Measure whether analysis actually helps.** The honest gap called out under
   *Evaluation Results*: run the same unseen spec with the analyzer on and off,
   via `--llm api`, and compare repair counts. Until then Milestone 2 is
   justified by design reasoning, not evidence.

**Carried forward as risk:**

7. **The boilerplate assumption is untested.** "Point `--target-dir` at the real
   repository and nothing changes" is a design intent, not a verified fact.

## Average Cost Per Run

**No cost or token figures are available, and none are estimated here.**

The Milestone 1 run was executed in `manual` mode because no API key was
available in this environment. In that mode no provider reports usage, so
`Usage.input_tokens` and `Usage.output_tokens` are `None` rather than a guess -
`sage/llm/base.py` only accumulates counts a provider actually returned.

What *was* measured on that run:

| Metric | M1 run | M2 clean | M2 with repair |
|---|---:|---:|---:|
| Model calls | 7 | 6 | 7 |
| Total prompt characters | 39,245 | 33,169 | 44,489 |
| Largest single prompt | 9,220 | 7,208 | 9,310 |
| Repair attempts | 2 | 0 | 1 |
| Final validation | passed | passed | passed |
| Input tokens | not reported | not reported | not reported |
| Output tokens | not reported | not reported | not reported |
| Cost | not measured | not measured | not measured |

Characters are not tokens, and three hand-authored runs on one small
specification are not an average. These stay as-is until real `api`-mode runs
exist.

To produce real figures: set `SAGE_API_KEY`, `SAGE_API_BASE_URL` and
`SAGE_MODEL`, run with `--llm api`, and record `Usage` across several runs
together with the model used.

## Git and Release Conventions

- **Trunk:** `main`.
- **Commits:** Conventional Commits — `feat:`, `fix:`, `docs:`, `test:`,
  `chore:`. One commit per meaningful unit of work; the body explains *why*, and
  records defects found along the way.
- **Tags:** annotated `milestone-N`, applied only once that milestone's
  validation actually passes.
- **Remote:** `git@github.com:jotafeldmann/sage.git`.

```bash
git add -A
git commit -m "feat: ..."
git tag -a milestone-1 -m "Milestone 1: end-to-end vertical slice"
git push -u origin main --follow-tags
```

## Repository Structure

Actual structure after Milestone 1:

```text
.
├── README.md                     evaluator-facing entry point
├── SPEC.md                       SAGE implementation contract
├── pyproject.toml                Python 3.12, uv, ruff, pytest
├── .env.example                  required config keys, no secrets
├── docs/
│   ├── project.pdf               canonical assessment (preserved)
│   └── extras.md                 this page
├── specs/                        application specifications (SAGE inputs)
│   ├── car-inventory.md
│   └── examples/{product-search,book-inventory}.md
├── prompts/                      milestone prompts for the coding agent
├── sage/                         the agent
│   ├── __main__.py               CLI
│   ├── config.py                 control-plane settings and budgets
│   ├── state.py                  the LangGraph state
│   ├── deps.py                   per-run tools bound into the nodes
│   ├── graph.py                  the workflow and its routing
│   ├── nodes/{analyzer,planner,generator,validator,repair}.py
│   ├── tools/{filesystem,shell,project}.py    the security boundary
│   ├── llm/{base,transcript,api,manual,replay,structured}.py
│   ├── prompts/{analyzer,planner,generator,repair,_shared}.md
│   └── schemas/{plan,repository,changes,validation}.py
├── tests/                        100 tests
├── fixtures/                     NOT part of the deliverable
│   ├── test-app/                 throwaway React/TS harness, committed pristine
│   └── cassettes/                two recorded runs: clean, and with repair
└── generated-app/                submission output; empty until the
                                  official boilerplate is available
```

Note the separation that matters: `sage/` contains no application-domain
knowledge, `specs/` contains all of it, and `fixtures/` is scaffolding that
would be deleted the day the real boilerplate arrives.
