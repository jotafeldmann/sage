"""Model access for SAGE.

Three interchangeable providers share one on-disk transcript format:

    api     - OpenAI-compatible endpoint, records as it goes
    manual  - writes the prompt, waits for a hand-pasted reply
    replay  - re-runs a recorded transcript, deterministically and for free
"""

from __future__ import annotations

from pathlib import Path

from sage.config import Settings
from sage.llm.api import ApiLLM
from sage.llm.base import LLMAborted, LLMClient, LLMError, Usage
from sage.llm.manual import ManualLLM
from sage.llm.replay import ReplayLLM
from sage.llm.structured import complete_structured
from sage.llm.transcript import Transcript, new_run_id

MODES = ("api", "manual", "replay")

__all__ = [
    "MODES",
    "ApiLLM",
    "LLMAborted",
    "LLMClient",
    "LLMError",
    "ManualLLM",
    "ReplayLLM",
    "Transcript",
    "Usage",
    "build_client",
    "complete_structured",
    "new_run_id",
]


def build_client(settings: Settings, run_dir: Path, mode: str | None = None) -> LLMClient:
    """Construct the provider for this run."""
    chosen = mode or settings.llm_mode
    if chosen not in MODES:
        raise LLMError(f"unknown LLM mode {chosen!r}; expected one of {', '.join(MODES)}")

    transcript = Transcript(run_dir)
    if chosen == "manual":
        return ManualLLM(transcript)
    if chosen == "replay":
        return ReplayLLM(transcript)
    return ApiLLM(
        model=settings.model,
        api_key=settings.api_key or "",
        base_url=settings.api_base_url,
        transcript=transcript,
    )
