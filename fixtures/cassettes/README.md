# Recorded run transcripts

Each directory is one complete SAGE run: every prompt SAGE built and every model
response it received, in order. Replaying one needs no network and no API key.

| Cassette | Specification | What it demonstrates |
|---|---|---|
| `product-search/` | `product-search.md` | The clean path. 6 model calls, 0 repairs, validation passes first time. |
| `product-search-repair/` | `product-search.md` | The recovery path. Identical until the test task guesses a query selector the component does not have; validation fails, repair reads the real vitest output, re-validation passes. 7 calls, 1 repair. |
| `book-inventory/` | `book-inventory.md` | Generalization. A different domain, with a sorting requirement the other spec does not have, through byte-identical SAGE code and prompts. 6 calls, 0 repairs. |

Replay any of them against the fixture:

```bash
./scripts/reset-fixture.sh
python -m sage specs/examples/book-inventory.md \
  --target-dir fixtures/test-app \
  --llm replay --run-id fixtures/cassettes/book-inventory
```

All three are exercised by `tests/test_end_to_end.py`.

Run `scripts/reset-fixture.sh` before recording. Manual recording restarts the
whole graph on every pass, so without a reset the analyzer ends up sampling
files SAGE generated on the previous pass.

Responses are what `replay` serves, keyed by sequence and tag. The `.prompt.md`
files are informational: they are the evidence of exactly what context each node
received, and they are rewritten on every non-replay run.
