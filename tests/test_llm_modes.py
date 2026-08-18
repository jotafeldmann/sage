"""The three providers must be interchangeable over one transcript format."""

from __future__ import annotations

import pytest

from sage.llm.base import LLMError
from sage.llm.replay import ReplayLLM
from sage.llm.transcript import Transcript


def test_replay_serves_recorded_responses_in_order(tmp_path) -> None:
    recording = Transcript(tmp_path)
    for tag, text in [("planner", "PLAN"), ("generate-task-1", "GEN")]:
        recording.write_response(recording.next_stem(tag), text)

    replay = ReplayLLM(Transcript(tmp_path))

    assert replay.complete("ignored", tag="planner") == "PLAN"
    assert replay.complete("ignored", tag="generate-task-1") == "GEN"
    assert replay.usage.calls == 2


def test_replay_fails_loudly_when_the_run_diverges(tmp_path) -> None:
    recording = Transcript(tmp_path)
    recording.write_response(recording.next_stem("planner"), "PLAN")

    replay = ReplayLLM(Transcript(tmp_path))
    replay.complete("ignored", tag="planner")

    with pytest.raises(LLMError, match="no recorded response"):
        replay.complete("ignored", tag="generate-task-1")


def test_transcript_stems_are_sequential_and_filename_safe(tmp_path) -> None:
    transcript = Transcript(tmp_path)

    assert transcript.next_stem("planner") == "001-planner"
    assert transcript.next_stem("generate-task-1") == "002-generate-task-1"
    # A tag can be derived from a model-supplied task id, so it is sanitized.
    assert transcript.next_stem("../../etc/passwd") == "003-etc-passwd"
    assert "/" not in transcript.next_stem("a/b/c")


def test_prompt_and_response_share_a_stem(tmp_path) -> None:
    transcript = Transcript(tmp_path)
    stem = transcript.next_stem("planner")

    prompt_path = transcript.write_prompt(stem, "the prompt")
    transcript.write_response(stem, "the response")

    assert prompt_path.name == "001-planner.prompt.md"
    assert transcript.read_response(stem) == "the response"
