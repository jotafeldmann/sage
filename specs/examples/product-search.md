# Product Search Evaluation Spec

## Purpose

This is the smallest end-to-end evaluation specification for SAGE. It is intentionally simpler than the official Car Inventory case so agent orchestration can be tested without GraphQL/MSW complexity.

Build the feature inside the existing React + TypeScript application structure.

## Requirements

### PRODUCT-REQ-001 - Seed products

Display these three products:

- Keyboard
- Monitor
- Mouse

The data may be local for this evaluation.

### PRODUCT-REQ-002 - Search

Provide a search input that filters products by name.

Search should be case-insensitive.

### PRODUCT-REQ-003 - Empty state

When no products match the search, display:

```text
No products found
```

### PRODUCT-REQ-004 - Tests

Add automated tests covering at least:

- products are visible initially;
- searching narrows the visible products;
- a search with no matches displays the empty state.

## Constraints

- Reuse the existing project structure.
- Do not add a backend.
- Do not change frameworks.
- Keep the implementation minimal.

## Acceptance Criteria

The evaluation passes when:

1. the three products render;
2. search behavior works;
3. the empty state works;
4. meaningful tests pass;
5. available type checking/build validation passes.
