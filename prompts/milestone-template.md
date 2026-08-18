# Coding Agent Prompt: Implement Milestone N

Replace `N` with the milestone requested from `SPEC.md`.

Before making changes, read:

2. `SPEC.md`
3. the current implementation
4. `README.md`
5. `docs/extras.md`

## Objective

Implement **Milestone N only** from `SPEC.md`.

Do not redesign working behavior from previous milestones unless the current milestone requires it or validation proves it is incorrect.

## Required process

Before coding:

1. inspect the current repository state;
2. summarize what previous milestones already provide;
3. identify the smallest changes necessary for this milestone;
4. list the files you intend to modify;
5. identify validation commands you will run.

Then implement the milestone incrementally.

## Validation

Run the available deterministic validation relevant to the changes before finishing.

If validation fails:

- diagnose the failure from actual output;
- fix the minimum relevant code;
- re-run validation.

Do not report the milestone complete if required validation still fails.

## Documentation

Update documentation only where this milestone creates real behavior, measured results, tradeoffs, or boilerplate changes.

Do not invent metrics, cost values, or success claims.

## Source of truth

`SPEC.md` records the original take-home assessment and is authoritative.
