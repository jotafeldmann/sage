"""Schema-validated model output.

Workflow-control output must be validated before it drives execution
(SPEC.md 9). Because SAGE's providers are plain text in / text out, the schema
travels in the prompt and Pydantic enforces it on the way back. Malformed
output gets one bounded corrective retry, then fails loudly rather than
continuing with guessed values.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from sage.llm.base import LLMClient, LLMError

MAX_PARSE_ATTEMPTS = 2

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def complete_structured[T: BaseModel](
    client: LLMClient,
    prompt: str,
    model_cls: type[T],
    *,
    tag: str,
) -> T:
    """Call the model and return a validated `model_cls`, or raise `LLMError`."""
    current_prompt = prompt
    last_error = ""

    for attempt in range(1, MAX_PARSE_ATTEMPTS + 1):
        call_tag = tag if attempt == 1 else f"{tag}-retry{attempt - 1}"
        raw = client.complete(current_prompt, tag=call_tag)
        try:
            return model_cls.model_validate(_extract_json(raw))
        except (ValueError, ValidationError) as exc:
            last_error = str(exc)
            current_prompt = _corrective_prompt(prompt, raw, last_error)

    raise LLMError(
        f"{tag}: model did not return valid {model_cls.__name__} JSON after "
        f"{MAX_PARSE_ATTEMPTS} attempts. Last error: {last_error}"
    )


def _extract_json(raw: str) -> dict:
    """Pull a JSON object out of a reply that may be fenced or chatty."""
    if not raw or not raw.strip():
        raise ValueError("empty response")

    fenced = _FENCE.search(raw)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(raw)

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("response did not contain a JSON object")


def _corrective_prompt(original: str, bad_response: str, error: str) -> str:
    return (
        f"{original}\n\n"
        "---\n"
        "Your previous response could not be used.\n\n"
        f"Response received:\n{bad_response[:2000]}\n\n"
        f"Validation error:\n{error}\n\n"
        "Reply again with ONLY the corrected JSON object. No prose, no code fence."
    )
