# Start Here

This pack is intended to be dropped into the repository that contains the take-home boilerplate.

> **That did not happen for this submission.** The boilerplate is listed in
> `docs/project.pdf` as "provided separately" and was never supplied, so this
> repository stands alone and SAGE was built to attach to a target project at
> runtime instead. See the notice at the top of [`README.md`](README.md).
> Sections below that assume the boilerplate is present describe the intended
> setup, not what happened.

## Files and roles

- `docs/project.pdf` - original assessment and canonical requirement source.
- `SPEC.md` - implementation contract for SAGE.
- `README.md` - short evaluator-facing entry point.
- `docs/extras.md` - central detailed engineering documentation.
- `specs/car-inventory.md` - official generated-application evaluation input.
- `specs/examples/product-search.md` - first small evaluation input.
- `specs/examples/book-inventory.md` - later generalization input.
- `prompts/milestone-1.md` - first prompt to give a coding agent.
- `prompts/milestone-template.md` - template for later milestone prompts.

## Recommended first session

1. Put this pack at the root of the provided assessment repository.
2. Do not manually build the Car Inventory application first.
3. Give your coding agent `prompts/milestone-1.md`.
4. Require the agent to inspect the existing boilerplate before implementation.
5. Keep the first target limited to `specs/examples/product-search.md`.
6. Commit Milestone 1 separately after deterministic validation passes.
7. Continue milestone by milestone from `SPEC.md`.

## Commit story

A reasonable sequence is:

```text
chore: add SAGE specification and project docs
feat: add minimal LangGraph generation loop
feat: add repository-aware planning
feat: constrain filesystem and shell tools
feat: add validation and repair loop
feat: generate car inventory reference app
 test: verify generalization with alternate spec
 docs: record evaluation results and measured cost
```

Use commits that match the work actually performed. The sequence above is guidance, not a requirement to create empty or misleading commits.
