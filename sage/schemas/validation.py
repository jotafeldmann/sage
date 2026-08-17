"""Normalized validation output.

Raw tool logs are noisy and expensive to feed back into a model. The validator
reduces every command run to this shape, and only the excerpt travels into the
repair prompt.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

# Matches leading file paths in tsc / vitest / eslint style diagnostics, e.g.
#   src/App.tsx(12,5): error TS2322: ...
#   src/App.tsx:12:5 - error ...
#   FAIL  src/App.test.tsx > renders
_PATH_PATTERN = re.compile(r"(?:^|[\s(\"'])([\w./-]+\.(?:tsx?|jsx?|mts|cts))(?=[\s:()\"',]|$)")


class ValidationResult(BaseModel):
    """The outcome of one deterministic validation command."""

    command: str
    exit_code: int
    passed: bool
    output_excerpt: str = ""
    files_mentioned: list[str] = Field(default_factory=list)
    skipped: bool = False


def extract_mentioned_files(output: str, known_files: set[str]) -> list[str]:
    """Pull workspace-relative source paths out of raw tool output.

    Only paths that actually exist in the workspace are returned, so noise in
    the log cannot cause the repair node to request arbitrary reads.
    """
    found: list[str] = []
    for match in _PATH_PATTERN.finditer(output):
        candidate = match.group(1).lstrip("./")
        if candidate in known_files and candidate not in found:
            found.append(candidate)
    return found
