# Book Inventory Generalization Spec

## Purpose

This specification exists to test that SAGE can handle a domain unrelated to the official Car Inventory example without changing SAGE core code or prompts.

Build the feature inside the existing application structure.

## Requirements

### BOOK-REQ-001 - Display books

Display a list of books with:

- title;
- author;
- publication year;
- category.

Use a small local dataset unless the target boilerplate already provides a suitable data source.

### BOOK-REQ-002 - Search by title

Provide a case-insensitive search input that filters books by title.

### BOOK-REQ-003 - Sort by publication year

Allow books to be sorted by publication year.

### BOOK-REQ-004 - Empty state

Display a clear empty state when filters return no books.

### BOOK-REQ-005 - Tests

Add automated tests for search and sorting behavior.

## Constraints

- Reuse the existing stack and project structure.
- Do not introduce car-specific code or naming.
- Keep the implementation intentionally small.

## Acceptance Criteria

The evaluation passes when:

1. books render with the required fields;
2. title search works;
3. publication-year sorting works;
4. meaningful automated tests pass;
5. available typecheck/build validation passes;
6. no SAGE core implementation change was necessary solely because the domain changed from cars to books.
