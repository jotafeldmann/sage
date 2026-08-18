"""Human-in-the-loop provider.

SAGE writes the fully rendered prompt to disk and waits. You paste it into any
model session, save the reply next to it, and press Enter. Useful when no API
key is available, and it produces a transcript that `replay` can re-run for
free.
"""

from __future__ import annotations

import sys

from sage.llm.base import LLMAborted, Usage
from sage.llm.transcript import Transcript


class ManualLLM:
    """Blocks on the operator for each completion."""

    mode = "manual"

    def __init__(self, transcript: Transcript, stream=None) -> None:
        self.transcript = transcript
        self.usage = Usage()
        self._stream = stream or sys.stdout

    def complete(self, prompt: str, *, tag: str) -> str:
        stem = self.transcript.next_stem(tag)
        prompt_path = self.transcript.write_prompt(stem, prompt)
        response_path = self.transcript.response_path(stem)

        self._say("")
        self._say(f"  Manual model call [{tag}]")
        self._say(f"    prompt written to : {prompt_path}")
        self._say(f"    save the reply to : {response_path}")
        self._say("    then press Enter to continue (Ctrl-C to abort)")

        while True:
            try:
                input()
            except (EOFError, KeyboardInterrupt) as exc:
                raise LLMAborted("manual model call aborted by operator") from exc

            response = self.transcript.read_response(stem)
            if response and response.strip():
                self.usage.record(None, None)
                return response
            self._say(f"    no response yet at {response_path} - press Enter again")

    def _say(self, text: str) -> None:
        print(text, file=self._stream, flush=True)
