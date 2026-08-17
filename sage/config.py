"""Runtime configuration for SAGE.

Everything here is control plane. A product specification is untrusted input
and must never be able to change any of these values - notably the repair
budget, the task cap, or the workspace root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Bounds that guarantee the graph terminates. See SPEC.md section 6.5.
DEFAULT_MAX_REPAIR_ATTEMPTS = 2
DEFAULT_MAX_TASKS = 12

# Validation commands are *discovered* from the target project, never assumed.
# This is the preference order for the ones we know how to interpret.
VALIDATION_SCRIPT_PREFERENCE = ("typecheck", "test", "build")

# Ceiling on how much tool output is fed back into a model prompt.
MAX_OUTPUT_EXCERPT_CHARS = 4000

# Ceiling on a single file read into a prompt.
MAX_FILE_CHARS = 20_000


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


@dataclass(frozen=True)
class Settings:
    """Resolved SAGE settings for one run."""

    llm_mode: str
    api_base_url: str | None
    api_key: str | None
    model: str
    max_repair_attempts: int
    max_tasks: int
    target_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        api_key = os.getenv("SAGE_API_KEY") or None
        mode = os.getenv("SAGE_LLM_MODE") or ("api" if api_key else "manual")
        return cls(
            llm_mode=mode,
            api_base_url=os.getenv("SAGE_API_BASE_URL") or None,
            api_key=api_key,
            model=os.getenv("SAGE_MODEL") or "",
            max_repair_attempts=_int_env(
                "SAGE_MAX_REPAIR_ATTEMPTS", DEFAULT_MAX_REPAIR_ATTEMPTS
            ),
            max_tasks=_int_env("SAGE_MAX_TASKS", DEFAULT_MAX_TASKS),
            target_dir=Path(os.getenv("SAGE_TARGET_DIR") or "generated-app"),
        )
