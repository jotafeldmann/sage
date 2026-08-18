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

Architecture status after Milestone 1: **implemented**, with one deviation from
the design above - there is no Repository Analyzer *node*. Repository inspection
is a deterministic function (`sage/tools/project.py`) called by the nodes that
need it, because it involves no model call and no state transition. SPEC.md 4.1
asks for a normal function rather than a node in exactly this case. An explicit
analysis node remains Milestone 2's decision.

Implemented graph (`sage/graph.py`):

```text
START -> planner -> generator --+
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

Two properties are deliberate:

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
4.  planner    -> one model call -> Plan validated by Pydantic
5.  generator  -> one model call per task, in dependency order
6.  validator  -> runs the project's own typecheck / test / build
7.  pass       -> status=succeeded, exit 0
8.  fail       -> repair (bounded), then back to 6
9.  budget out -> status=failed, unresolved output printed, exit 1
```

Observed output from the recorded Milestone 1 run:

```text
SAGE: specs/examples/product-search.md -> .../fixtures/test-app
  provider: manual   transcript: .sage/runs/m1-product-search

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
| `planner` | 1 | Specification + the compressed project probe + the plan schema + one domain-neutral example |
| `generator` | 1 per task | The current task only, its dependencies' **one-line summaries**, and the contents of the files that task names |
| `validator` | 0 | Nothing. It is entirely deterministic. |
| `repair` | 1 per attempt | The failing command, a truncated ANSI-stripped error excerpt, and only the files those errors actually name |

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

### Measurements after Milestone 1

Measured on the recorded run against `specs/examples/product-search.md`
(7 model calls: 1 plan, 4 generation, 2 repair).

Prompt sizes actually sent:

| Call | Characters |
|---|---:|
| `001-planner` | 5,016 |
| `002-generate-task-1` | 4,169 |
| `003-generate-task-2` | 5,002 |
| `004-generate-task-3` | 4,181 |
| `005-generate-task-4` | 5,187 |
| `006-repair-1` | 9,220 |
| `007-repair-2` | 6,470 |
| **Total across 7 calls** | **39,245** |

**An honest caveat on these numbers.** The evaluation target is a deliberately
tiny fixture - about 3.5 KB of TypeScript source plus 1.2 KB of configuration.
Its entire contents would fit inside a single prompt. So these figures show that
per-call context stays small and roughly flat, but they are **not** evidence
that the context-management design saves anything, because there is nothing here
to save. The techniques below are structural properties of the implementation,
verified by reading the recorded prompts, not demonstrated wins. A meaningful
measurement needs a repository large enough for the naive approach to hurt -
that is Milestone 5's job, against the real boilerplate.

What the recorded prompts do verify:

- the planner and generator received the **compressed probe summary**
  (7 lines) rather than any file listing or file contents;
- `generate-task-2` received task-1's one-line summary, not `products.ts`;
- `generate-task-3` received the existing `App.tsx` **contents**, because that
  task names the file it modifies - so the generator inspects before editing;
- `repair-1` received exactly one file, `src/ProductSearch.test.tsx`, because
  that is the only file the vitest output named.

Token and cost figures are **not** recorded, because the measured run was
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

### A real defect the tests caught

LangGraph injects its own `Runtime` object into any node parameter named
`runtime`. SAGE's dependency container was bound with
`partial(node, runtime=deps)` and was being **silently replaced** by LangGraph's
own object at call time. Every node failed with `AttributeError` the first time
the graph ran for real. Renamed to `Deps`/`deps`.

Worth recording because it is the argument for the end-to-end graph tests: no
amount of unit testing the nodes in isolation would have found it.

## What I Would Improve

Now grounded in what Milestone 1 actually surfaced, rather than a wish list.

**Directly indicated by the recorded run:**

1. **Pass dependency signatures, not just summaries.** The first validation
   failure happened because the test task knew what the component *did* but not
   what it *looked like*. Sending dependencies' exported signatures - not full
   contents - would likely have avoided one full repair cycle. This is the single
   highest-value change and belongs in Milestone 3.
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
6. **A plan review gate.** Not yet justified - the one recorded plan was sound.
   Worth revisiting only if a measured run produces a bad plan.

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

| Metric | Value |
|---|---:|
| Runs measured | 1 |
| Model calls | 7 |
| Total prompt characters sent | 39,245 |
| Largest single prompt | 9,220 chars |
| Repair attempts | 2 |
| Validation commands executed | 7 (3 passes over typecheck/test/build) |
| Replay duration | ~8 s, dominated by npm |
| Input tokens | not reported by this provider mode |
| Output tokens | not reported by this provider mode |
| Cost | not measured |

Characters are not tokens, and one run on a small specification is not an
average. These stay as-is until real `api`-mode runs exist.

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
│   ├── nodes/{planner,generator,validator,repair}.py
│   ├── tools/{filesystem,shell,project}.py    the security boundary
│   ├── llm/{base,transcript,api,manual,replay,structured}.py
│   ├── prompts/{planner,generator,repair,_shared}.md
│   └── schemas/{plan,changes,validation}.py
├── tests/                        78 tests
├── fixtures/                     NOT part of the deliverable
│   ├── test-app/                 throwaway React/TS harness
│   └── cassettes/product-search/ the recorded Milestone 1 run
└── generated-app/                submission output; empty until the
                                  official boilerplate is available
```

Note the separation that matters: `sage/` contains no application-domain
knowledge, `specs/` contains all of it, and `fixtures/` is scaffolding that
would be deleted the day the real boilerplate arrives.
