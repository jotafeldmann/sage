"""On-disk transcript of a run's model calls.

One format serves three purposes:

* `manual` writes the prompt here and waits for a response file;
* `api` records what it sent and received;
* `replay` reads it back.

That means any run - hand-pasted or live - becomes a deterministic, zero-cost
regression fixture.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

PROMPT_SUFFIX = ".prompt.md"
RESPONSE_SUFFIX = ".response.txt"

_UNSAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


class Transcript:
    """A numbered sequence of prompt/response pairs in one directory."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self._sequence = 0

    def next_stem(self, tag: str) -> str:
        """Advance the counter and return the stem shared by both files."""
        self._sequence += 1
        return f"{self._sequence:03d}-{_UNSAFE.sub('-', tag).strip('-') or 'call'}"

    def prompt_path(self, stem: str) -> Path:
        return self.directory / f"{stem}{PROMPT_SUFFIX}"

    def response_path(self, stem: str) -> Path:
        return self.directory / f"{stem}{RESPONSE_SUFFIX}"

    def write_prompt(self, stem: str, prompt: str) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.prompt_path(stem)
        path.write_text(prompt, encoding="utf-8")
        return path

    def write_response(self, stem: str, response: str) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.response_path(stem)
        path.write_text(response, encoding="utf-8")
        return path

    def read_response(self, stem: str) -> str | None:
        path = self.response_path(stem)
        return path.read_text(encoding="utf-8") if path.is_file() else None
