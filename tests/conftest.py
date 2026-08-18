"""Shared fixtures for the SAGE test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage.config import Settings
from sage.deps import Deps
from sage.llm.base import Usage
from sage.tools.filesystem import WorkspaceFS


class ScriptedLLM:
    """A model stub that returns queued responses and records the prompts."""

    mode = "scripted"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[tuple[str, str]] = []
        self.usage = Usage()

    def complete(self, prompt: str, *, tag: str) -> str:
        self.prompts.append((tag, prompt))
        self.usage.record(None, None)
        if not self._responses:
            raise AssertionError(f"ScriptedLLM ran out of responses at tag {tag!r}")
        return self._responses.pop(0)


# The graph now begins with an analyzer call, so any test driving the whole
# graph must supply a response for it before the planner's.
ANALYSIS = json.dumps(
    {
        "architecture_notes": ["A small TypeScript project."],
        "conventions": ["Named exports."],
        "reusable_infrastructure": [],
        "integration_points": ["src/"],
        "testing_approach": "No tests present yet.",
    }
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        llm_mode="replay",
        api_base_url=None,
        api_key=None,
        model="",
        max_repair_attempts=2,
        max_tasks=12,
        target_dir=Path("generated-app"),
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A throwaway project directory with a package.json SAGE can probe."""
    (tmp_path / "src").mkdir()
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "probe-target",
                "scripts": {"typecheck": "true", "test": "true", "dev": "true"},
                "dependencies": {"react": "^19.0.0"},
                "devDependencies": {"typescript": "^5.7.2"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "src" / "App.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def make_deps(settings, workspace):
    def _make(llm, quiet: bool = True) -> Deps:
        deps = Deps.create(llm=llm, settings=settings, target_dir=workspace)
        deps.quiet = quiet
        return deps

    return _make


@pytest.fixture
def fs(workspace) -> WorkspaceFS:
    return WorkspaceFS(workspace)
