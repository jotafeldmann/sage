"""Repository analyzer: understand the project before planning against it.

Runs deterministic inspection first (`probe_project`), then makes exactly one
model call to interpret what the facts mean for someone about to change the
code. SPEC.md 6.1 asks for that ordering explicitly: static inspection answers
*what is here*, and the model is only asked for the judgement a static rule
cannot supply.

The model sees a bounded sample of the project's most significant files, never
the repository. If the analysis call fails, the run continues on the
deterministic facts alone - a missing interpretation should degrade planning,
not abort it.
"""

from __future__ import annotations

from sage import prompts
from sage.deps import Deps
from sage.llm.base import LLMAborted, LLMError
from sage.llm.structured import complete_structured
from sage.schemas.repository import RepositoryContext
from sage.state import SageState

CONTEXT_SCHEMA = """{
  "architecture_notes": ["how the project is put together, one sentence each"],
  "conventions": ["concrete style rules visible in the sample"],
  "reusable_infrastructure": ["what already exists that new work should build on"],
  "integration_points": ["where new code should attach"],
  "testing_approach": "how this project tests, in one or two sentences"
}"""

# How many of the probe's ranked important files to actually show the model.
SAMPLE_FILE_LIMIT = 6

# Per-file ceiling for the sample, so one large file cannot dominate the prompt.
SAMPLE_FILE_CHARS = 2500


def analyzer_node(state: SageState, deps: Deps) -> dict:
    """Produce concise repository context for the planner."""
    deps.say("Analyzing repository...")
    deps.refresh_project()
    project = deps.project

    if not project.has_package_json:
        deps.say("  no package.json found; planning against an empty project.\n")
        return {"project": project.to_dict(), "repository_context": {}, "status": "running"}

    sample = _sample_files(deps)
    prompt = prompts.render(
        "analyzer",
        project_summary=project.to_prompt_summary(),
        sample_files=sample,
        schema=CONTEXT_SCHEMA,
    )

    try:
        context = complete_structured(deps.llm, prompt, RepositoryContext, tag="analyze-repository")
    except LLMAborted:
        raise  # an operator cancelling the run is not a degradable failure
    except LLMError as exc:
        # Deterministic facts are still available; planning degrades rather
        # than failing outright.
        deps.say(f"  analysis unavailable ({exc}); continuing on deterministic facts alone.\n")
        return {"project": project.to_dict(), "repository_context": {}, "status": "running"}

    deps.say(
        f"Repository analyzed: {project.framework} / {project.language}, "
        f"{project.test_runner} tests, {len(project.scripts)} scripts.\n"
    )
    return {
        "project": project.to_dict(),
        "repository_context": context.model_dump(),
        "status": "running",
    }


def _sample_files(deps: Deps) -> str:
    """Read a bounded sample of the files the probe ranked most significant."""
    paths = deps.project.important_files[:SAMPLE_FILE_LIMIT]
    files = deps.fs.read_many(paths)
    if not files:
        return "No readable source files were found in this project."

    blocks = []
    for path, contents in files.items():
        body = contents[:SAMPLE_FILE_CHARS]
        if len(contents) > SAMPLE_FILE_CHARS:
            body += "\n... [truncated]"
        blocks.append(f"### {path}\n```\n{body}\n```")
    return "\n\n".join(blocks)
