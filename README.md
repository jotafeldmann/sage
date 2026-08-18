# SAGE

**Specification Agent for Generation and Execution**

SAGE is a small agentic spec-to-code workflow that takes a natural-language software specification, inspects an existing application repository, plans the work, generates or edits code, validates the result with the project's own tooling, and attempts bounded repairs when validation fails.

The original take-home assessment is preserved at [`docs/project.pdf`](docs/project.pdf). It is the canonical source of truth for assessment requirements. [`SPEC.md`](SPEC.md) translates those requirements into an actionable implementation specification for SAGE.

**Status: Milestone 3 complete.** The full `analyze → plan → generate → validate → repair` loop runs end to end. See [Current limitations](#current-limitations).

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

Two runs are recorded: `product-search` (passes first time) and
`product-search-repair` (fails validation, repairs, then passes).

### Checks

```bash
.venv/bin/python -m pytest && .venv/bin/ruff check sage tests
```

## Stack

| Layer | Choice | Rationale |
|---|---|---|
| Agent language | Python 3.12 | Fast iteration and strong agent tooling ecosystem |
| Workflow orchestration | LangGraph | Explicit shared state, conditional routing, and a bounded repair cycle |
| LLM integration | langchain-openai | One client covers every OpenAI-compatible provider via `base_url` |
| Structured outputs | Pydantic | Planner and change output are validated before they drive execution |
| LLM provider | OpenAI-compatible, configured by environment | Model choice stays configuration, not code |
| Deterministic validation | The target project's own npm scripts | The compiler and test suite are stronger gates than an LLM review |
| Agent checks | pytest, ruff | 138 tests covering tool boundaries, bounded repair, repository probing, context scoping, and generalization |

## Current limitations

- **The official assessment boilerplate is not present.** `docs/project.pdf` lists it as "provided separately" and it was not supplied with this workspace. SAGE has therefore been built to discover a target project's scripts, libraries and layout at runtime rather than assume that stack. `fixtures/test-app/` is a clearly-labelled throwaway harness used to exercise the loop; it is **not** the boilerplate and **not** the submission's `generated-app/`, which remains empty by design.
- Milestones 4–7 are not implemented.

## Extras

Architecture, agent workflow, references, tradeoffs, evaluation results, optimization notes, security boundaries, git conventions, and measured costs live in [`docs/extras.md`](docs/extras.md).
