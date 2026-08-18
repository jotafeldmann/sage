#!/usr/bin/env bash
# Restore fixtures/test-app to its committed, un-generated state.
#
# Manual recording re-runs the whole graph from the start each time you answer
# one more prompt. Without this reset, the second and later passes analyze a
# project SAGE has already generated into, and the recorded prompts stop
# representing a clean run.
#
# The fixture's committed baseline is whatever git tracks under src/, so this
# removes every untracked file there rather than naming generated files. Naming
# them was a real bug: the list was written for one evaluation spec and silently
# failed to clean up after a different one.
set -euo pipefail
cd "$(dirname "$0")/.."

git checkout -- fixtures/test-app/src
# -x because generated output is gitignored; scoped to src/ so nothing
# else in the fixture (notably node_modules) is ever touched.
git clean -qfdx fixtures/test-app/src
rm -rf fixtures/test-app/dist

echo "fixture reset: $(ls fixtures/test-app/src | tr '\n' ' ')"
