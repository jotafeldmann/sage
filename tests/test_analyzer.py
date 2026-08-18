"""The analyzer must inspect deterministically, bound what it sends, and degrade
gracefully when the model call fails."""

from __future__ import annotations

import json
from pathlib import Path

from sage.deps import Deps
from sage.nodes.analyzer import SAMPLE_FILE_CHARS, SAMPLE_FILE_LIMIT, analyzer_node
from sage.schemas.repository import RepositoryContext
from tests.conftest import ANALYSIS, ScriptedLLM


class FailingLLM:
    """A provider that never produces usable output."""

    def __init__(self) -> None:
        from sage.llm.base import Usage

        self.usage = Usage()
        self.prompts: list[tuple[str, str]] = []

    def complete(self, prompt: str, *, tag: str) -> str:
        self.prompts.append((tag, prompt))
        self.usage.record(None, None)
        return "the model is having a bad day"


def _deps(tmp_path: Path, settings, llm, files: dict[str, str] | None = None) -> Deps:
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "target",
                "scripts": {"typecheck": "tsc", "test": "vitest run"},
                "dependencies": {"react": "^19.0.0"},
                "devDependencies": {"vitest": "^3.0.0", "typescript": "^5.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    for path, contents in (files or {"src/main.tsx": "export const x = 1;\n"}).items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")

    deps = Deps.create(llm=llm, settings=settings, target_dir=tmp_path)
    deps.quiet = True
    return deps


def _state(deps: Deps) -> dict:
    return {"spec": "Build something.", "target_dir": str(deps.fs.root)}


def test_analysis_is_returned_as_validated_context(tmp_path, settings) -> None:
    deps = _deps(tmp_path, settings, ScriptedLLM([ANALYSIS]))

    result = analyzer_node(_state(deps), deps)

    context = RepositoryContext.model_validate(result["repository_context"])
    assert context.conventions == ["Named exports."]
    # The deterministic facts travel alongside the interpretation.
    assert result["project"]["framework"] == "React"
    assert result["project"]["test_runner"] == "Vitest"


def test_the_prompt_carries_deterministic_facts_and_a_file_sample(tmp_path, settings) -> None:
    llm = ScriptedLLM([ANALYSIS])
    deps = _deps(tmp_path, settings, llm)

    analyzer_node(_state(deps), deps)

    tag, prompt = llm.prompts[0]
    assert tag == "analyze-repository"
    assert "Framework: React" in prompt
    assert "Test runner: Vitest" in prompt
    assert "src/main.tsx" in prompt


def test_the_file_sample_is_bounded(tmp_path, settings) -> None:
    """A big repository must not become a big prompt."""
    files = {f"src/mod{i:02d}.ts": "x" * 9000 for i in range(30)}
    llm = ScriptedLLM([ANALYSIS])
    deps = _deps(tmp_path, settings, llm, files)

    analyzer_node(_state(deps), deps)

    _, prompt = llm.prompts[0]
    # Count sampled-file headings, not code fences: the template has its own
    # fence around the output schema.
    shown = sum(1 for line in prompt.splitlines() if line.startswith("### "))
    assert shown == SAMPLE_FILE_LIMIT
    assert "[truncated]" in prompt
    assert len(prompt) < SAMPLE_FILE_LIMIT * (SAMPLE_FILE_CHARS + 2000)


def test_analysis_failure_degrades_instead_of_aborting(tmp_path, settings) -> None:
    """A failed interpretation must not lose the deterministic facts."""
    deps = _deps(tmp_path, settings, FailingLLM())

    result = analyzer_node(_state(deps), deps)

    assert result["repository_context"] == {}
    assert result["status"] == "running"
    assert result["project"]["framework"] == "React"


def test_a_project_without_package_json_skips_the_model_call(tmp_path, settings) -> None:
    (tmp_path / "src").mkdir()
    llm = ScriptedLLM([])  # any call would raise
    deps = Deps.create(llm=llm, settings=settings, target_dir=tmp_path)
    deps.quiet = True

    result = analyzer_node(_state(deps), deps)

    assert result["repository_context"] == {}
    assert llm.prompts == []


def test_secrets_are_never_sampled(tmp_path, settings) -> None:
    llm = ScriptedLLM([ANALYSIS])
    deps = _deps(tmp_path, settings, llm)
    (tmp_path / ".env").write_text("API_KEY=super-secret\n", encoding="utf-8")

    analyzer_node(_state(deps), deps)

    assert "super-secret" not in llm.prompts[0][1]


def test_context_summary_is_compact_and_labelled() -> None:
    context = RepositoryContext(
        architecture_notes=["A."],
        conventions=["B."],
        reusable_infrastructure=["C."],
        integration_points=["D."],
        testing_approach="E.",
    )

    summary = context.to_prompt_summary()

    assert "Architecture:" in summary
    assert "Conventions to follow:" in summary
    assert "Existing infrastructure to reuse:" in summary
    assert "Testing approach: E." in summary


def test_empty_context_renders_without_pretending() -> None:
    assert RepositoryContext().to_prompt_summary() == "No additional observations."


def test_operator_abort_is_not_swallowed_as_a_degraded_analysis(tmp_path, settings) -> None:
    """Cancelling a run must stop it, not silently continue without analysis."""
    import pytest

    from sage.llm.base import LLMAborted, Usage

    class AbortingLLM:
        def __init__(self) -> None:
            self.usage = Usage()

        def complete(self, prompt: str, *, tag: str) -> str:
            raise LLMAborted("operator cancelled")

    deps = _deps(tmp_path, settings, AbortingLLM())

    with pytest.raises(LLMAborted):
        analyzer_node(_state(deps), deps)
