# SAGE

**Specification Agent for Generation and Execution**

SAGE is a small agentic spec-to-code workflow that takes a natural-language software specification, inspects an existing application repository, plans the work, generates or edits code, validates the result with the project's own tooling, and attempts bounded repairs when validation fails.

The original take-home assessment is preserved at [`docs/project.pdf`](docs/project.pdf). It is the canonical source of truth for assessment requirements. [`SPEC.md`](SPEC.md) translates those requirements into an actionable implementation specification for SAGE.

---

> ### ⚠️ The assessment boilerplate was not available
>
> `docs/project.pdf` lists the pre-built application repository — React 19 with
> Apollo Client, MUI and MSW — under **"Repository: Provided separately"**. It
> was not supplied with this workspace and is not in it.
>
> **It was deliberately not downloaded, guessed at, or reconstructed.** A
> lookalike would differ from the real thing in ways that only surface as
> mystery failures later, and generating into it would prove nothing about the
> repository the agent is actually meant to work on.
>
> Two consequences, both visible in this repository:
>
> 1. **The Car Inventory application was not generated** (Milestone 5). It
>    needs that boilerplate's `GetCars` query, `Car` type, MSW mock layer and
>    five seed cars. Nothing on SAGE's side is missing — the input is.
> 2. **The sample output in [`generated-app/`](generated-app/) was generated
>    into a minimal React + TypeScript harness instead**, which is
>    [`fixtures/test-app/`](fixtures/test-app/) and is **not** the boilerplate.
>
> SAGE was built so this is a swap, not a rewrite: it discovers a target
> project's scripts, libraries and layout at runtime rather than assuming any of
> them, so pointing `--target-dir` at the real repository is expected to need no
> code change. [Milestone 6](docs/extras.md#milestone-6-generalization--passed)
> is the evidence — an unrelated domain ran through byte-identical SAGE — but
> the expectation stays **untested against the real boilerplate** until it
> exists.

---

**Status: Milestones 1–4, 6 and 7 complete.** Milestone 5 is blocked on the boilerplate above. The full `analyze → plan → generate → validate → repair` loop runs end to end. See [Current limitations](#current-limitations).

## How to Run

### Setup

SAGE needs Python 3.12+. This project uses [uv](https://docs.astral.sh/uv/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && uv pip install -e ".[dev]"
cp .env.example .env
```

### Run against a specification

```bash
python -m sage specs/examples/product-search.md --target-dir fixtures/test-app
```

SAGE writes only inside `--target-dir`. That directory must already be a project it can inspect; SAGE does not scaffold one.

### Model providers

SAGE has three interchangeable providers, selected with `--llm` or `SAGE_LLM_MODE`. All three share one on-disk transcript format under `.sage/runs/<run-id>/`, so a run recorded in any mode can be replayed in another.

| Mode | What it does | Needs a key |
|---|---|---|
| `api` | Calls an OpenAI-compatible endpoint (OpenAI, OpenRouter, Gemini's compatible endpoint). Records every call. | yes |
| `manual` | Writes each prompt to disk and waits while you paste the reply into any model session and save it back. | no |
| `replay` | Re-runs a recorded transcript, deterministically and for free. | no |

Replay a recorded run with no network and no API key:

```bash
python -m sage specs/examples/product-search.md --target-dir fixtures/test-app --llm replay --run-id fixtures/cassettes/product-search
```

Three runs are recorded: `product-search` (passes first time),
`product-search-repair` (fails validation, repairs, then passes), and
`book-inventory` (a different domain, run through byte-identical SAGE code).

### Checks

```bash
.venv/bin/python -m pytest && .venv/bin/ruff check sage tests
```

179 tests. Seven of them replay recorded runs against the fixture and are
skipped until that fixture's npm dependencies exist; running SAGE once, as
above, installs them.

### Sample output

[`generated-app/`](generated-app/) is a working application SAGE generated, not
written by hand, with the transcript that produced it committed alongside. It
runs with `cd generated-app && npm install && npm run dev`.

## Which model was used, and why

**No LLM provider was called to produce the recorded runs, and none of the
results in this repository come from a live model.** No API key was available in
the environment this was built in, so every model response in
[`fixtures/cassettes/`](fixtures/cassettes/) was written by hand through SAGE's
`manual` mode, which prints each prompt and waits for a pasted reply.

This matters when reading the results, so it is stated up front rather than in a
footnote:

- **What is genuinely demonstrated** is everything deterministic: the graph and
  its routing, the bounded repair loop, the sandbox and command allowlist,
  requirement slicing, signature extraction, output normalization, and the fact
  that real `npm run typecheck`, `npm test` and `npm run build` commands pass on
  generated code. All of that runs for real on every replay.
- **What is not demonstrated** is model behaviour: whether a given model plans
  well, writes good code, or repairs its own mistakes. A hand-authored
  transcript cannot show that, and no token counts, latencies or costs are
  reported anywhere because none were observed.

To run against a real provider, set `SAGE_API_KEY`, `SAGE_API_BASE_URL` and
`SAGE_MODEL` and pass `--llm api`. The client is `langchain-openai`, so any
OpenAI-compatible endpoint works — OpenAI, OpenRouter, or Google's
OpenAI-compatible Gemini endpoint, all three of which `docs/project.pdf`
suggests. The provider is configuration, not code: nothing in `sage/` names a
model or a vendor.

**Why the provider is pluggable rather than chosen.** SAGE needs the `api`,
`manual` and `replay` modes to be interchangeable, and a reply a human pastes in
cannot use a provider's structured-output feature. So schema enforcement lives
in the prompt with Pydantic validating the result, which is what `SPEC.md` §9
asks for anyway and what makes a recorded run replayable at zero cost.

## Stack

| Layer | Choice | Rationale |
|---|---|---|
| Agent language | Python 3.12 | Fast iteration and strong agent tooling ecosystem |
| Workflow orchestration | LangGraph | Explicit shared state, conditional routing, and a bounded repair cycle |
| LLM integration | langchain-openai | One client covers every OpenAI-compatible provider via `base_url` |
| Structured outputs | Pydantic | Planner and change output are validated before they drive execution |
| LLM provider | OpenAI-compatible, configured by environment | Model choice stays configuration, not code. **No provider was called for the recorded runs** — see above. |
| Deterministic validation | The target project's own npm scripts | The compiler and test suite are stronger gates than an LLM review |
| Agent checks | pytest, ruff | 179 tests covering tool boundaries, bounded repair, repository probing, context scoping, output normalization, and generalization |

## Current limitations

- **The assessment boilerplate is absent** — see the notice at the top. This is
  the one limitation that no further work here can remove.
- **The Car Inventory application (Milestone 5) was not generated**, for that
  reason. Milestone 6 was run instead: an unrelated domain through
  byte-identical SAGE code and prompts.
- **No LLM provider was ever called.** Every recorded run was hand-authored
  through `manual` mode, so nothing here demonstrates model behaviour and no
  token or cost figures are reported. See
  [Which model was used, and why](#which-model-was-used-and-why).
- **A task cannot see the rendered output of a component it tests**, only that
  component's exported signatures. The
  [`product-search-repair`](fixtures/cassettes/product-search-repair/) cassette
  reproduces exactly this: the test guesses a query selector, validation
  catches it, and repair fixes it. Letting validation catch it may be correct,
  but it is a choice rather than a solved problem.
- **`npm install` runs only when `node_modules` is missing.** SAGE does not
  detect a stale or partial install.

## Extras

Architecture, agent workflow, references, tradeoffs, evaluation results, optimization notes, security boundaries, git conventions, and measured costs live in [`docs/extras.md`](docs/extras.md).
