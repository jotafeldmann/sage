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

The assessment's official boilerplate — React 19 with Apollo Client, MUI and
MSW — is listed in `docs/project.pdf` as "provided separately" and was not
available in this workspace. It was deliberately **not** reconstructed.

The project SAGE generated into here is therefore a copy of
[`../fixtures/test-app/`](../fixtures/test-app/), a minimal React + TypeScript +
Vitest harness. **It is not the assessment boilerplate.** SAGE discovers a target
project's scripts, libraries and layout at runtime rather than assuming any of
them, so pointing `--target-dir` at the real boilerplate is expected to require
no SAGE change — but that expectation is untested until the boilerplate exists.
