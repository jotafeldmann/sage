# Recorded run transcripts

Each directory is one complete SAGE run: every prompt SAGE built and every model
response it received, in order. Replaying one needs no network and no API key.

| Cassette | What it demonstrates |
|---|---|
| `product-search/` | The clean path. Analysis, a repository-aware plan, four generation tasks, and validation passing on the first attempt. 6 model calls, 0 repairs. |
| `product-search-repair/` | The recovery path. Identical up to the test task, which then guesses a query selector the component does not have. Validation fails, repair reads the real vitest output, and re-validation passes. 7 model calls, 1 repair. |

Replay either against the fixture:

```bash
python -m sage specs/examples/product-search.md \
  --target-dir fixtures/test-app \
  --llm replay --run-id fixtures/cassettes/product-search
```

Both are exercised by `tests/test_end_to_end.py`.

Responses are what `replay` serves, keyed by sequence and tag. The `.prompt.md`
files are informational: they are the evidence of exactly what context each node
received, and they are rewritten on every non-replay run.
