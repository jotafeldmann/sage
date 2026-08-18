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
| `generator` | 1 per task | The current task only; **its own requirement sections** of the spec plus the globally applicable ones; its dependencies' one-line summaries **and their exported signatures**; the analyzer's conventions list; and the contents of the files that task names |
| `validator` | 0 | Nothing. It is entirely deterministic. |
| `repair` | 1 per attempt | The failing command, its classified **failure kind** and matching guidance, **test counts**, parsed **diagnostics**, a truncated ANSI-stripped raw excerpt, only the **requirement sections behind the failing files**, and only the files those errors name |

Milestone 3 narrowed the specification and widened the dependency information in
the same prompt. Those pull in opposite directions on purpose: a task should see
*less* of what it does not implement and *more* of the API it must call.

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
its dependencies' summaries and signatures, and only the files that task names.

#### Requirement-scoped specifications

`sage/tools/requirements.py` slices the specification by the requirement ids the
planner recorded for each task. Globally applicable sections - purpose,
constraints, shared type definitions - are always kept; only unrelated
requirement sections are dropped. It fails open, returning the whole document
when ids cannot be resolved.

#### Signatures instead of files

`sage/tools/signatures.py` extracts exported declarations textually, so a task
consuming another task's module gets its API without its implementation. This
replaced guessing, which is how the recorded Milestone 1 run first failed.

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

Every command is normalized into `ValidationResult`: exit code, pass/fail, an
ANSI-stripped excerpt truncated to `MAX_OUTPUT_EXCERPT_CHARS` (4,000) keeping
the tail where compilers put diagnostics, the files it implicated, parsed
diagnostics, a classified failure kind, and test counts when the runner
reported them.

`sage/tools/diagnostics.py` reads the reporters a project already has, so no
target project has to be reconfigured to be validatable. Unrecognised output
degrades to "unknown kind, no counts" and the raw excerpt still travels, so a
parsing miss costs guidance quality and never information.

#### Failure-specific repair guidance

Failures are classified deterministically and each kind carries its own advice.
The classifier checks the most specific cause first, because a missing module is
reported by the compiler as a type error and a syntax error produces downstream
type errors - naming the symptom instead of the cause would send repair after
the wrong thing.

#### Tool gating

The model never supplies a command string. It can only cause an npm script to
run that is both allowlisted by SAGE and defined by the target project.

### Measurements

Measured from the committed cassettes. Prompt sizes are exact; nothing here is
estimated.

**Milestone 3, clean run** (`fixtures/cassettes/product-search/`) — 6 calls.

The Milestone 2 column was measured by checking that tag out into a worktree and
re-recording its prompts against the same pristine fixture, so this is a real
before/after on identical input rather than a comparison against differently
-recorded evidence:

| Call | M2 | M3 | Change |
|---|---:|---:|---:|
| `001-analyze-repository` | 4,644 | 4,644 | — |
| `002-planner` | 7,207 | 7,207 | — |
| `003-generate-task-1` | 4,681 | 4,413 | −268 |
| `004-generate-task-2` | 4,783 | 4,789 | **+6** |
| `005-generate-task-3` | 4,875 | 4,634 | −241 |
| `006-generate-task-4` | 4,822 | 4,638 | −184 |
| **Total** | **31,012** | **30,325** | **−687** |

Generation prompts specifically: **19,161 → 18,474 characters, −3.6%**. Analysis
and planning are untouched by Milestone 3 and come out byte-identical, which is
a useful check that the change landed where it was supposed to.

Two things in that table are worth more than the headline:

- **`task-2` got 6 characters bigger.** It is the one task that consumes another
  task's module, so it is the only one that gains a dependency-exports block —
  and the requirement slicing almost exactly cancelled it out. This is the
  honest shape of the trade: the saving is spent buying information the
  generator previously had to guess at.
- **A 3.6% reduction on this specification is not the interesting number.**
  `specs/examples/product-search.md` is 1,276 characters with four requirements,
  so there is very little to cut. Running the same slicing code over
  `specs/car-inventory.md` — 3,306 characters, eight requirements, plus optional
  sections — reduces a single-requirement slice to **59–64% of the document**,
  measured across all eight of its requirements. The mechanism scales with
  specification size; the fixture does not exercise it.

**An earlier figure in this section was wrong.** A −8.5% reduction was recorded
here at first. That compared Milestone 3 against Milestone 2 prompts recorded on
a dirty fixture (see *Real defects*), which were inflated. Measured properly the
figure is −3.6%.

**The standing caveat on all of these numbers.** The evaluation target is a
deliberately tiny fixture — about 3.5 KB of TypeScript plus 1.2 KB of config,
against a 1.3 KB specification. On a specification this small, slicing saves
hundreds of characters; on `specs/car-inventory.md` the same code cuts a
single-requirement slice to **59-64% of the document**, and on a large real
specification the gap widens further. But that is arithmetic on the input, not a
measured effect on model behaviour, cost, or quality. A meaningful measurement
needs a repository and a specification large enough for the naive approach to
hurt. That remains Milestone 5's job, against the real boilerplate.

What the recorded prompts verify by inspection:

- the analyzer received 4 files, not the repository, each fence-capped;
- the planner received the probe summary plus the analysis, not any file;
- `generate-task-2` received `src/products.ts`'s **exported signatures**
  (`interface Product`, `const products: Product[]`) — not the file, and not
  its non-exported internals;
- `generate-task-3` received the existing `App.tsx` **contents**, because that
  task names the file it modifies — so the generator inspects before editing;
- each generation prompt carried only its own task's requirement sections plus
  the globally applicable ones;
- `repair-1` received exactly one file, because that is the only file the vitest
  output named.

Token and cost figures are **not** recorded, because every measured run was
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

#### Milestone 3: controlled generation — PASSED

Same specification, same two cassettes, re-recorded after requirement slicing
and dependency signatures were added.

```text
fixtures/cassettes/product-search/         6 model calls, 0 repairs, PASSED
fixtures/cassettes/product-search-repair/  7 model calls, 1 repair,  PASSED

Final validation, both: typecheck PASSED, test PASSED, build PASSED
```

Milestone 3's definition of done, and where each part is verified:

| Requirement | Status | Evidence |
|---|---|---|
| Multiple dependency-aware tasks execute sequentially | Already held since M1 | `tests/test_graph.py` — 4 tasks, topological order, generator self-edge |
| Filesystem scope is enforced | Already held since M1 | `tests/test_filesystem.py` — 17 tests |
| Shell operations are constrained | Already held since M1 | `tests/test_shell.py` — 9 tests |
| Task-specific context instead of full-repository prompts | **Closed in M3** | `tests/test_generator_context.py`, `test_requirements.py`, `test_signatures.py` |

The first three were verified rather than rebuilt. The fourth was only partly
true before: the generator prompt was headed "Specification requirements
relevant to this task" and then pasted the entire specification underneath it.

What changed, visible in `004-generate-task-2.prompt.md`:

- the task now receives `src/products.ts`'s **exported signatures** —
  `interface Product`, `const products: Product[]` — where before it received
  only the sentence "Added the Product type and the three seed products";
- non-exported internals and function bodies do not travel;
- each generation prompt carries only its own requirement sections plus the
  globally applicable ones.

#### Milestone 4: autonomous validation and repair — PASSED

```text
fixtures/cassettes/product-search/         6 model calls, 0 repairs, PASSED
fixtures/cassettes/product-search-repair/  7 model calls, 1 repair,  PASSED
```

Definition of done, and where each part is verified:

| Requirement | Status | Evidence |
|---|---|---|
| typecheck/tests/build normalized into workflow state | **Closed in M4** | `ValidationResult` now carries `failure_kind`, `diagnostics`, and test counts; `tests/test_diagnostics.py` |
| At least one real validation failure repaired automatically | Already held since M1 | `product-search-repair` cassette; `tests/test_graph.py` |
| Retry limit terminates repeated failure safely | Already held since M1 | `test_repair_is_bounded_and_the_run_terminates` |

Test counts were the concrete miss: SPEC.md 6.4 lists them explicitly and
nothing was capturing them. Progress output now reads:

```text
Running test...
FAILED (exit 1) - 1 passed, 2 failed, of 3 [test_failure]
```

**What the repair prompt gained.** Before, it received the failing command, a
truncated raw log, and the whole specification. Now:

```text
Command: `npm run test`
Exit code: 1
Failure kind: test_failure
Tests: 1 passed, 2 failed, of 3

### Diagnostics
- src/ProductSearch.test.tsx > ProductSearch > narrows the visible products
  as you search: TestingLibraryElementError: Unable to find an element with
  the placeholder text of: Search products
- src/ProductSearch.test.tsx > ProductSearch > shows the empty state when
  nothing matches: TestingLibraryElementError: ...
```

**Measured cost of that, on identical input** (Milestone 3 checked out into a
worktree and re-recorded against the same pristine fixture):

| | M3 | M4 | Change |
|---|---:|---:|---:|
| Clean run total | 30,325 | 30,325 | — |
| Repair prompt | 9,303 | 9,735 | **+432** |
| Repair run total | 39,628 | 40,060 | +432 |

The clean run is byte-identical, which is the check that Milestone 4 touched
only validation and repair.

The repair prompt grew, and the breakdown is worth stating rather than
averaging away:

- requirement slicing **removed 340 characters** — the specification block fell
  from 1,276 to 936, keeping only `PRODUCT-REQ-004` (the requirement behind the
  failing test file) plus purpose, constraints and acceptance criteria;
- structured diagnostics **added 415** and failure-kind guidance **added 328**.

So Milestone 4 spends about 400 characters to replace "here is a log, find the
problem" with "here are the two failing cases, here is why, and here is what
this class of failure usually means". Whether that trade improves repair success
is **not measured** — the recorded run repairs successfully both before and
after, and one hand-authored run cannot separate the two.

#### Milestone 6: generalization — PASSED

`specs/examples/book-inventory.md`, a domain SAGE had never been run against,
carrying a sorting requirement that `product-search.md` does not have.

```text
Cassette:            fixtures/cassettes/book-inventory/
Plan:                4 dependency-aware tasks
Model calls:         6
Repair attempts:     0
Generated:           src/books.ts, src/BookInventory.tsx, src/App.tsx,
                     src/BookInventory.test.tsx
Final validation:    typecheck PASSED, test PASSED (5 tests), build PASSED
```

**The claim is verified, not asserted.** A sha256 over every file under `sage/`
was taken before the run and after it:

```text
before: 9f2e97a2fdb3dc39d441cadfed00d992f93a0fc7838f821cdb31717fc59493f9
after:  9f2e97a2fdb3dc39d441cadfed00d992f93a0fc7838f821cdb31717fc59493f9
```

No SAGE code and no prompt changed. `tests/test_generalization.py` additionally
asserts that no requirement identifier from any specification in `specs/`
appears anywhere in SAGE, and that more than one domain has actually been
recorded — so the claim cannot quietly rot.

Two mechanisms built for earlier milestones carried over untouched, which is the
substance of the result rather than the run itself:

- **Requirement slicing recognised `BOOK-REQ-*` with no new pattern**, because
  the identifier format is matched structurally rather than enumerated. A
  single-requirement slice of the book spec is 64% of the document.
- **Signature extraction carried `interface Book` and `const books: Book[]`**
  into the component task, exactly as it had carried the product type.

The analyzer prompt for this run is **byte-identical** to the product-search
one, because repository analysis describes the project and not the
specification. That is a design property worth naming: analysis is cacheable
per target directory precisely because it does not depend on the spec.

#### Evaluation 3: Official Car Inventory — NOT RUN

Blocked, and this is the one milestone that cannot be unblocked by any amount of
work here. `specs/car-inventory.md` requires Apollo Client, an MSW-backed
GraphQL mock, a `GetCars` query, a `Car` type and five seed cars — all of them
provided by the boilerplate `docs/project.pdf` lists as "provided separately",
which is not in this workspace. Generating against a reconstruction would prove
nothing about the real repository.

Everything the milestone needs on SAGE's side is in place and demonstrated on
two other specifications. What is missing is the input.

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

### Milestone 3 observations

- **The plan already contained the handle for slicing.** `requirements` was
  recorded per task in Milestone 1 for traceability, and turned out to be
  exactly what was needed to scope the specification. Structured output paid off
  somewhere it was not designed for.
- **Failing open was the right default for slicing.** A specification SAGE
  cannot parse, or requirement ids that resolve to nothing, sends the whole
  document. Dropping a requirement silently would be a correctness bug; sending
  a few paragraphs too many is only a cost.
- **A textual scan was enough for signatures.** No TypeScript parser, no model
  call. A missed export costs a little context quality and never correctness,
  because deterministic validation is still the authority.

### Milestone 4 observations

- **The most valuable guidance is a prohibition.** The `test_failure` advice
  spends most of its words forbidding one specific repair: deleting or weakening
  a test to get a pass. That is the cheapest way to make a gate go green and the
  most damaging, because it disables the thing protecting the output.
- **Classifier ordering is the whole design.** Once the categories existed, the
  only interesting decision was which to check first. `TS2307` is simultaneously
  a type error and a missing module; calling it the latter is what makes the
  guidance useful.
- **Naming the failing test beat locating it.** vitest's stack frames point into
  `@testing-library`, not into the project. Parsing the `FAIL <file> > <case>`
  header gives repair the case name and the reason, which is what a human would
  actually read.

### Milestone 6 observations

- **Structural matching generalized; enumeration would not have.** The
  requirement-id regex matches a shape (`WORD-WORD-123`), so `BOOK-REQ-003`
  worked without SAGE having heard of books. Every place SAGE was tempted to
  enumerate — frameworks, test runners, requirement prefixes — and instead
  recognised a pattern or reported `unknown`, is a place this milestone passed
  for free.
- **The failures were all in the harness, never in SAGE.** Both defects found
  were the same mistake in scaffolding written while only one evaluation spec
  existed. The agent generalized; the test rig did not.
- **Repository analysis is specification-independent, and that is worth
  keeping.** The analyzer prompt is byte-identical across the two domains. It
  is what makes caching analysis per target directory a safe optimisation.

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

**Milestone 3: the recording method was contaminating its own evidence.**
Manual recording re-runs the entire graph on every pass, because each pass
answers one more prompt than the last. From the second pass onward the analyzer
was therefore sampling files SAGE had generated on the previous pass, and the
committed Milestone 2 analyzer prompt shows it reading its own `ProductSearch.tsx`.
The recorded figures were correspondingly too high.

Found by noticing that the analyzer prompt shrank between Milestone 2 and
Milestone 3 despite Milestone 3 not touching the analyzer — a change that had no
business happening. `scripts/reset-fixture.sh` now makes the reset explicit,
both cassettes are re-recorded from a pristine fixture, and the affected numbers
in *Measurements* are corrected.

The general lesson: when a measurement moves somewhere the change could not have
reached, the measurement is what is broken.

**Milestone 6: the harness was written for one specification.**
`scripts/reset-fixture.sh` deleted a hardcoded list of product-search files, so
running the book specification left `BookInventory.tsx` behind and the
re-recorded analyzer prompt sampled SAGE's own generated component.
`tests/test_end_to_end.py` had the identical bug. Both now list what to *keep* —
the two files the fixture actually commits — rather than what to delete.

Worth recording because of where it happened. SAGE generalized to a new domain
without a single change; the scaffolding around it did not. Code written while
only one example exists tends to encode that example, and the agent's own
generalization tests do not cover the harness.

## What I Would Improve

Now grounded in what Milestone 1 actually surfaced, rather than a wish list.

**Done in Milestone 3**: dependency signatures, and requirement-scoped
specifications for generation. **Done in Milestone 4**: failure classification
with per-kind guidance, normalized diagnostics and test counts, and
requirement-scoped specifications for repair too.

**Still open, indicated by the implementation:**

1. **A component's own rendered surface is still invisible to its test.** The
   repair cassette's failure is that the test task cannot know the component
   renders a `<label>` rather than a placeholder. Exported signatures do not
   capture that, because it is not in the module's type surface. Options: give
   test tasks the implementation file of the component under test, or run tests
   first and let repair handle it - which is what happens today, and arguably
   correctly.

**Indicated by the implementation:**

2. **Re-validate incrementally.** After a repair touching only test files, the
   full build does not need to re-run.
3. **Token and cost accounting.** The plumbing exists (`Usage`), but no run has
   yet gone through a provider that reports usage.
4. **A plan review gate.** Not yet justified - both recorded plans were sound.
   Worth revisiting only if a measured run produces a bad plan.
5. **Cache the analysis per target directory.** Every run re-analyzes a project
   that has not changed, and Milestone 6 showed the analyzer prompt is
   byte-identical across two different specifications — so the result is
   genuinely reusable, not merely similar. A digest of the probe output would
   make the call skippable. Still not done, because with one small fixture it
   would optimise something that has never been observed to hurt, but the
   evidence that it is *safe* now exists.
6. **Measure whether analysis, slicing and guidance actually help.** The honest gap called out under
   *Evaluation Results*: run the same unseen spec with the analyzer on and off,
   via `--llm api`, and compare repair counts. Until then Milestone 2 is
   justified by design reasoning, not evidence.

**Carried forward as risk:**

7. **The boilerplate assumption is untested.** "Point `--target-dir` at the real
   repository and nothing changes" is a design intent, not a verified fact.

## Average Cost Per Run

**No cost, token or latency figure is available, and none is estimated here.**

Every recorded run was executed in `manual` mode, because no API key was
available in the environment this was built in. In that mode there is no
provider to report usage, so `Usage.input_tokens` and `Usage.output_tokens` stay
`None` rather than becoming a guess — `sage/llm/base.py` only accumulates counts
a provider actually returned.

What *was* measured, from the committed cassettes:

| Metric | product-search | with repair | book-inventory |
|---|---:|---:|---:|
| Model calls | 6 | 7 | 6 |
| Total prompt characters | 30,325 | 40,060 | 31,091 |
| Largest single prompt | 7,207 | 9,735 | 7,306 |
| Repair attempts | 0 | 1 | 0 |
| Tasks planned | 4 | 4 | 4 |
| Tests generated | 4 | 3 | 5 |
| Final validation | passed | passed | passed |
| Input tokens | not reported | not reported | not reported |
| Output tokens | not reported | not reported | not reported |
| Cost | not measured | not measured | not measured |

The two specifications cost within 2.5% of each other, which is what you would
expect: similar size, four tasks each. Nothing here suggests SAGE is tuned to
either.

Characters are not tokens, and hand-authored runs on small specifications are
not an average.

### How to produce real numbers

```bash
SAGE_API_KEY=... SAGE_API_BASE_URL=https://openrouter.ai/api/v1 SAGE_MODEL=... \
  python -m sage specs/examples/product-search.md --target-dir fixtures/test-app --llm api
```

`ApiLLM` records into the same transcript format, so an `api` run is replayable
afterwards and its `Usage` counters carry whatever the provider reported. Record
the model alongside the numbers; they are meaningless without it.

## Model and Provider Choice

**No model produced the results in this repository.** See *Average Cost Per Run*
above and the README section of the same name. This section records the design
decision, not an experimental result.

**Choice:** any OpenAI-compatible endpoint, selected by environment variable,
via `langchain-openai`.

**Why not commit to one vendor:**

- `docs/project.pdf` explicitly leaves the provider open and names Anthropic,
  OpenAI, Gemini's OpenAI-compatible endpoint and OpenRouter as acceptable;
- the assessment says it will run the agent with its own keys, so hardcoding a
  vendor would make the submission harder to evaluate, not easier;
- nothing in `sage/` names a model or a vendor, which is checked by the same
  generalization suite that keeps domain vocabulary out.

**What this costs:** reproducibility depends on recording which model was used
for a measured run, since the same prompts against different models are
different experiments. No such record exists yet because no such run exists.

**The pluggability is load-bearing, not decorative.** `manual` mode is what made
this project testable at all without a key, and `replay` mode turns any
transcript into a free, deterministic regression test — which is how the
end-to-end suite works. A design that assumed a live provider would have left
the whole loop unverifiable here.

## Submission Checklist

Verified against `docs/project.pdf`'s submission requirements from a clean
checkout of exactly the files git tracks, with a fresh virtualenv.

| Requirement | Status |
|---|---|
| A git repository containing the agent source code | `sage/`, 8 focused commits, tags `milestone-1..4`, `milestone-6` |
| README with setup instructions, architecture overview, design decisions | Verified by following it literally in a clean checkout |
| A sample spec file the agent consumes | `specs/examples/product-search.md`, `book-inventory.md`, `specs/car-inventory.md` |
| A sample output directory (a generated app we can run) | `generated-app/` — generated by SAGE, runs with `npm install && npm run dev` |
| `.env.example` listing required keys, without secrets | Every `SAGE_*` variable it lists is read by `sage/config.py`; no values. The `LANGSMITH_*` entries are annotated as SDK-consumed and unverified |
| Which LLM(s) you used and why | README *Which model was used, and why* — **none was called**, stated plainly |
| Agent architecture, diagram welcome | *Architecture* and *Agent Workflow* above |
| What worked well and what you would improve | *What Worked Well*, *What I Would Improve* |
| Approximate cost per run | *Average Cost Per Run* — measured characters, **no invented cost** |
| Working demo: run the agent with the sample spec, output compiles and runs | `--llm replay` reproduces a full run with no key; output passes typecheck, tests, build, and renders in a browser |
| We may modify the spec slightly to test generalization | Milestone 6: an unrelated domain through byte-identical SAGE |
| `docs/project.pdf` preserved | Unmodified |

Two requirements are not met, both for the same reason:

- **Milestone 5, the official Car Inventory application, was not generated.** It
  needs the boilerplate's Apollo client, MSW GraphQL mock, `GetCars` query,
  `Car` type and five seed cars. That boilerplate is "provided separately" per
  the assessment and is not in this workspace.
- **The sample output was therefore generated into a minimal harness**, not into
  the official boilerplate. `generated-app/README.md` says so in its own caveat
  section rather than letting the directory imply otherwise.

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

```text
.
├── README.md                     evaluator-facing entry point
├── SPEC.md                       SAGE implementation contract
├── START_HERE.md                 starter-pack orientation
├── pyproject.toml                Python 3.12, uv, ruff, pytest
├── .env.example                  required config keys, no secrets
├── docs/
│   ├── project.pdf               canonical assessment (unmodified)
│   └── extras.md                 this page
├── specs/                        application specifications (SAGE inputs)
│   ├── car-inventory.md          official evaluation, not yet run
│   └── examples/{product-search,book-inventory}.md
├── prompts/                      milestone prompts for the coding agent
├── scripts/reset-fixture.sh      restores the fixture before recording
├── sage/                         the agent
│   ├── __main__.py               CLI
│   ├── config.py                 control-plane settings and budgets
│   ├── state.py                  the LangGraph state
│   ├── deps.py                   per-run tools bound into the nodes
│   ├── graph.py                  the workflow and its routing
│   ├── nodes/{analyzer,planner,generator,validator,repair}.py
│   ├── tools/
│   │   ├── {filesystem,shell}.py         the security boundary
│   │   ├── project.py                    deterministic repository probe
│   │   ├── {requirements,signatures}.py  context scoping
│   │   └── diagnostics.py                output normalization
│   ├── llm/{base,transcript,api,manual,replay,structured}.py
│   ├── prompts/{analyzer,planner,generator,repair,_shared}.md
│   └── schemas/{plan,repository,changes,validation}.py
├── tests/                        179 tests
├── fixtures/                     scaffolding, not part of the deliverable
│   ├── test-app/                 throwaway React/TS harness, committed pristine
│   └── cassettes/                three recorded runs: clean, repair, unseen domain
└── generated-app/                SAGE's own output, runnable, with the
                                  transcript that produced it committed
```

The separation that matters: `sage/` contains no application-domain knowledge,
`specs/` contains all of it, `fixtures/` is scaffolding that would be deleted the
day the real boilerplate arrives, and `generated-app/` is a product of the
system rather than an input to it.
