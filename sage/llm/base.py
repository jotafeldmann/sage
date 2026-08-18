"""The single interface every SAGE model call goes through."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Usage:
    """Counters SAGE can report without inventing numbers it did not observe.

    Token counts stay None unless a provider actually reported them.
    """

    calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None

    def record(self, input_tokens: int | None, output_tokens: int | None) -> None:
        self.calls += 1
        if input_tokens is not None:
            self.input_tokens = (self.input_tokens or 0) + input_tokens
        if output_tokens is not None:
            self.output_tokens = (self.output_tokens or 0) + output_tokens


@runtime_checkable
class LLMClient(Protocol):
    """Text in, text out.

    Deliberately not using provider-native structured output: a response that a
    human pastes in by hand cannot use it, and SAGE needs the api, manual and
    replay modes to be interchangeable. Schema enforcement therefore lives in
    the prompt plus Pydantic validation (see `sage.llm.structured`).
    """

    usage: Usage

    def complete(self, prompt: str, *, tag: str) -> str:
        """Return the model's reply to `prompt`. `tag` names the calling node."""
        ...


@dataclass
class LLMError(RuntimeError):
    """Raised when a model call cannot be completed."""

    message: str = ""
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class LLMAborted(LLMError):
    """The operator cancelled the run.

    Distinct from `LLMError` because it is a control-flow signal, not a model
    failure: nodes that degrade gracefully when analysis is unavailable must
    still stop when a human cancels.
    """

