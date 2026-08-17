"""OpenAI-compatible provider.

`base_url` is configurable so the same client works against OpenAI, OpenRouter,
or Google's OpenAI-compatible Gemini endpoint. Every call is recorded into the
run transcript, which makes a live run replayable afterwards.
"""

from __future__ import annotations

from sage.llm.base import LLMError, Usage
from sage.llm.transcript import Transcript


class ApiLLM:
    """Calls a chat-completions endpoint via langchain-openai."""

    mode = "api"

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        transcript: Transcript | None = None,
        temperature: float = 0.0,
    ) -> None:
        if not model:
            raise LLMError("SAGE_MODEL is not set; api mode needs an explicit model id")
        if not api_key:
            raise LLMError("SAGE_API_KEY is not set; api mode needs a key")

        from langchain_openai import ChatOpenAI

        self.transcript = transcript
        self.usage = Usage()
        self._client = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )

    def complete(self, prompt: str, *, tag: str) -> str:
        stem = self.transcript.next_stem(tag) if self.transcript else None
        if self.transcript and stem:
            self.transcript.write_prompt(stem, prompt)

        try:
            message = self._client.invoke(prompt)
        except Exception as exc:  # noqa: BLE001 - surfaced as a SAGE-level error
            raise LLMError(f"model call failed for {tag}: {exc}") from exc

        text = message.content if isinstance(message.content, str) else str(message.content)
        self.usage.record(*_token_counts(message))

        if self.transcript and stem:
            self.transcript.write_response(stem, text)
        return text


def _token_counts(message: object) -> tuple[int | None, int | None]:
    """Read usage off the response, or (None, None) if the provider omitted it."""
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict):
        return usage.get("input_tokens"), usage.get("output_tokens")
    return None, None
