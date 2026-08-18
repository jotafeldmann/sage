# Car Inventory boilerplate

> ### This boilerplate was written for this project. It is **not** the assessment's.
>
> The assessment described a pre-built repository, provided separately by its
> owner. That repository was never supplied, so this one was written
> to stand in its place, matching the stack the assessment documents.
>
> It is a **good-faith reconstruction from the assessment's description, not a
> copy of the real thing.** Names, file layout, seed data and schema shape are
> our choices. If the official boilerplate arrives, prefer it — SAGE discovers a
> target project at runtime, so switching is a `--target-dir` change.

A React 19 + TypeScript application shell with a mocked GraphQL API, ready for
an agent to build a car inventory UI into.

## Quick start

```bash
npm install
npm run dev        # http://localhost:5173
npm test
npm run typecheck
npm run build
```

## Stack

| Layer | Choice |
|---|---|
| UI | React 19, TypeScript |
| Build | Vite 7 |
| Data | Apollo Client 4 against a relative `/graphql` endpoint |
| API mock | MSW 2 — a Service Worker in the browser, `setupServer` in tests |
| Components | Material UI 7 |
| Tests | Vitest 3, Testing Library, jsdom |

There is no backend. MSW intercepts every GraphQL request, so the same handlers
serve the browser and the test suite.

## What is here

```text
src/
├── main.tsx                 starts the mock API, then mounts App
├── App.tsx                  placeholder screen — the feature goes here
├── apollo/client.ts         Apollo Client pointed at /graphql
├── types/car.ts             Car and CarInput
├── graphql/operations.ts    GetCars, GetCar, AddCar + result types
└── mocks/
    ├── data.ts              five seed cars
    ├── handlers.ts          GraphQL resolvers over an in-memory store
    ├── browser.ts           setupWorker, used by main.tsx
    ├── server.ts            setupServer, used by vitest.setup.ts
    └── mockApi.test.tsx     smoke test for this wiring
```

### The `Car` type

```ts
interface Car {
  id: string;
  make: string;
  model: string;
  year: number;
  color: string;
  mobile: string;   // image for viewports <= 640px
  tablet: string;   // 641px – 1023px
  desktop: string;  // >= 1024px
}
```

### Available operations

| Operation | Kind | Purpose |
|---|---|---|
| `GetCars` | query | All cars |
| `GetCar($id)` | query | One car, or `null` |
| `AddCar($input)` | mutation | Appends a car and returns it |

`src/mocks/mockApi.test.tsx` exercises all of this and is the place a broken
setup fails first. It is a smoke test for the plumbing, not a feature test.

## Two things worth knowing before you edit

**Tests are isolated.** `vitest.setup.ts` resets the in-memory store after every
test, so a mutation in one test cannot leak into the next. The third smoke test
asserts exactly that.

**There is a jsdom workaround in `vitest.setup.ts`.** jsdom supplies its own
`AbortSignal`, which Node's `fetch` rejects, so every Apollo query would
otherwise fail under test. The setup file strips the signal after MSW installs
its interceptor. It is commented in place; it is not something you need to
replicate in application code.
