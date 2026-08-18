# Sample generated output

**This directory was produced by SAGE, not written by hand.** It is the sample
output the assessment asks for: a generated application you can run.

## How it was generated

```bash
python -m sage specs/examples/product-search.md \
  --target-dir generated-app \
  --llm replay --run-id fixtures/cassettes/product-search
```

SAGE analyzed the project, planned four dependency-aware tasks, generated each
one, installed the project's dependencies, and ran its typecheck, test and build
scripts. Every prompt it built and every response it received is committed at
[`../fixtures/cassettes/product-search/`](../fixtures/cassettes/product-search/).

Files SAGE created or modified:

| File | Requirement |
|---|---|
| `src/products.ts` | PRODUCT-REQ-001 — product type and seed data |
| `src/ProductSearch.tsx` | PRODUCT-REQ-001..003 — search, filtering, empty state |
| `src/App.tsx` | modified to render the feature |
| `src/ProductSearch.test.tsx` | PRODUCT-REQ-004 — four tests |

Everything else here is the starting project SAGE was pointed at.

## Run it

```bash
npm install
npm run dev        # http://localhost:5173
npm run typecheck
npm test
npm run build
```

Verified: `typecheck` exits 0, four tests pass, `build` succeeds, and the dev
server renders the three products with working case-insensitive search and the
`No products found` empty state.

## An important caveat about the starting project

This sample was generated into [`../fixtures/test-app/`](../fixtures/test-app/),
a deliberately minimal React + TypeScript + Vitest harness — no Apollo, no MSW,
no MUI. That is the project the committed cassette reproduces.

It is **not** the assessment's boilerplate. The official repository — React 19
with Apollo Client, MUI and MSW — was provided separately and never supplied.

A replacement with that fuller stack now exists at
[`../boilerplate/`](../boilerplate/), also written by this project rather than
supplied by the assessment. This sample predates it and was not regenerated,
because the cassette that produced it — and the tests that replay it — target
the minimal harness.

SAGE discovers a target project's scripts, libraries and layout at runtime
rather than assuming any of them, so generating into either project, or into the
official repository if it arrives, is a `--target-dir` change rather than a code
change.
