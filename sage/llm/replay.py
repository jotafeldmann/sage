"""Replay a recorded run.

Deterministic and free. Any transcript produced by `manual` or `api` can be
replayed, which is how SAGE's end-to-end and repair-path tests run without a
network or an API key.
"""

from __future__ import annotations

from sage.llm.base import LLMError, Usage
from sage.llm.transcript import Transcript


class ReplayLLM:
    """Serves responses from a transcript directory in recorded order."""

    mode = "replay"

    def __init__(self, transcript: Transcript, strict_tags: bool = True) -> None:
        self.transcript = transcript
        self.usage = Usage()
        self.strict_tags = strict_tags

    def complete(self, prompt: str, *, tag: str) -> str:  # noqa: ARG002 - prompt unused by design
        stem = self.transcript.next_stem(tag)
        response = self.transcript.read_response(stem)
        if response is None:
            raise LLMError(
                f"no recorded response for {stem!r} in {self.transcript.directory}. "
                "The run diverged from the recording, or the cassette is incomplete."
            )
        self.usage.record(None, None)
        return response
