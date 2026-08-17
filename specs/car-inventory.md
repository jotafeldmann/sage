# Car Inventory Manager

## Purpose

Build a working Car Inventory Manager inside the existing assessment boilerplate.

This file is an application specification intended to be consumed by SAGE. The original assessment at `docs/project.pdf` remains authoritative if this file is ambiguous or incomplete.

## Required Requirements

### CAR-REQ-001 - Fetch and display cars

Display a list of cars fetched through Apollo Client from the mock GraphQL API provided by the boilerplate.

Use the `GetCars` query and the MSW-backed GraphQL mock infrastructure already provided by the project.

### CAR-REQ-002 - Search by model

Provide a search input that filters the displayed cars by model.

Search should update the visible list in a clear and usable way.

### CAR-REQ-003 - Sort cars

Allow the user to sort the car list by:

- year;
- make.

The implementation should make the active sort understandable to the user.

### CAR-REQ-004 - Testing

Provide an acceptable level of automated testing for the required application behavior.

At minimum, tests should cover meaningful user-visible behavior rather than only rendering a component without assertions.

## Existing Car Shape

The boilerplate provides a `Car` type with these fields:

```ts
interface Car {
  id: string;
  make: string;
  model: string;
  year: number;
  color: string;
  mobile: string;
  tablet: string;
  desktop: string;
}
```

The assessment states that the boilerplate provides five seed cars.

Reuse the existing type/schema/mock infrastructure rather than duplicating it unnecessarily.

## Optional Requirements

Optional functionality should only be attempted after all required requirements and validation are working.

### CAR-OPT-001 - `useCars()` hook

Extract GraphQL data-fetching logic into a reusable `useCars()` custom hook.

### CAR-OPT-002 - Responsive images

Render the appropriate image field based on viewport width:

- `mobile` at widths less than or equal to 640px;
- `tablet` from 641px through 1023px;
- `desktop` at 1024px and above.

### CAR-OPT-003 - Material UI cards

Use Material UI cards to present car data such as:

- make;
- model;
- year;
- color;
- image.

### CAR-OPT-004 - Add Car

Provide an Add Car form that submits through the GraphQL `AddCar` mutation.

## Optional Extras

These are lower priority than the optional requirements above:

- `GetCar` query for an individual car;
- year filter that works alongside model search;
- reusable `useCarFilters()` hook for filter logic.

## Constraints

- Work inside the existing boilerplate.
- Do not replace the configured frontend stack without a concrete requirement.
- Do not create a real backend or database. The assessment uses MSW to mock the API.
- Do not add authentication, deployment, or CI/CD as part of this application.
- Functional correctness has higher priority than visual polish.

## Acceptance Criteria

The required specification is complete when:

1. the app displays cars returned by the provided mock GraphQL layer;
2. model search changes the displayed results correctly;
3. sorting by year works;
4. sorting by make works;
5. automated tests cover meaningful required behavior;
6. the project's available typecheck/test/build validation passes;
7. the project remains runnable using the supplied boilerplate workflow.
