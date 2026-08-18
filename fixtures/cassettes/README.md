# Recorded run transcripts

Each directory is one complete SAGE run: every prompt SAGE built and every model
response it received, in order.

`product-search/` is the Milestone 1 end-to-end run against
`specs/examples/product-search.md`, recorded in `--llm manual` mode. It includes
a real validation failure and two repair attempts.

Replay it with no network and no API key:

    python -m sage specs/examples/product-search.md \
      --target-dir fixtures/test-app \
      --llm replay --run-id product-search

Replay serves responses by sequence and tag, so the prompts are informational -
they are the evidence of exactly what context each node received. They are
rewritten on every run.
