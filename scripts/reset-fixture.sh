#!/usr/bin/env bash
# Restore fixtures/test-app to its committed, un-generated state.
#
# Manual recording re-runs the whole graph from the start each time you answer
# one more prompt. Without this reset, the second and later passes analyze a
# project SAGE has already generated into, and the recorded prompts stop
# representing a clean run.
set -euo pipefail
cd "$(dirname "$0")/.."
git checkout -- fixtures/test-app/src/App.tsx
rm -f fixtures/test-app/src/products.ts \
      fixtures/test-app/src/ProductSearch.tsx \
      fixtures/test-app/src/ProductSearch.test.tsx
rm -rf fixtures/test-app/dist
echo "fixture reset: $(ls fixtures/test-app/src | tr '\n' ' ')"
