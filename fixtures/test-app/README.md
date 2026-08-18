# Temporary SAGE test fixture — NOT the assessment boilerplate

This directory is a **throwaway harness** used to exercise the SAGE workflow
while the official assessment boilerplate is unavailable.

It is **not**:

- the assessment's pre-built boilerplate (React 19, Vite, Apollo Client, MUI,
  MSW, Vitest), which was provided separately and never supplied;
- a reconstruction or substitute for it;
- the submission's `generated-app/` output directory.

It exists only so the plan → generate → validate → repair loop has *some* real
TypeScript project to act on. It deliberately contains no Apollo, no MSW and no
MUI, because SAGE must not develop assumptions about a stack it has not seen.

SAGE learns everything it knows about this project by reading `package.json` at
runtime. When the official boilerplate arrives, point `--target-dir` at it
instead; no SAGE code changes.
