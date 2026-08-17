"""Deterministic inspection of the target project.

No LLM is involved. SAGE reads package.json and the file listing to learn what
the project actually is - which npm scripts exist, which libraries are
available, where source and tests live. Nothing here assumes a particular
framework, directory layout, or script name, so an unfamiliar target project
plugs in without a code change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sage.tools.filesystem import WorkspaceError, WorkspaceFS

# Directory names commonly used for source and tests, checked against reality.
_SOURCE_HINTS = ("src", "app", "lib")
_TEST_HINTS = ("test", "tests", "__tests__", "spec")


@dataclass
class ProjectInfo:
    """A compact, factual description of the target project."""

    has_package_json: bool = False
    name: str = ""
    scripts: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    dev_dependencies: list[str] = field(default_factory=list)
    source_dirs: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    file_count: int = 0

    @property
    def all_libraries(self) -> list[str]:
        return sorted({*self.dependencies, *self.dev_dependencies})

    def to_dict(self) -> dict:
        return {
            "has_package_json": self.has_package_json,
            "name": self.name,
            "scripts": self.scripts,
            "dependencies": self.dependencies,
            "dev_dependencies": self.dev_dependencies,
            "source_dirs": self.source_dirs,
            "test_files": self.test_files,
            "config_files": self.config_files,
            "file_count": self.file_count,
        }

    def to_prompt_summary(self) -> str:
        """Compress the probe into the few lines a model actually needs.

        This is the context-management boundary: downstream prompts get this
        summary, never the repository itself.
        """
        if not self.has_package_json:
            return "Target project: no package.json found; treat as an empty project."

        lines = [
            f"Project name: {self.name or 'unknown'}",
            f"Available npm scripts: {', '.join(sorted(self.scripts)) or 'none'}",
            f"Libraries: {', '.join(self.all_libraries) or 'none'}",
            f"Source directories: {', '.join(self.source_dirs) or 'none detected'}",
            f"Config files: {', '.join(self.config_files) or 'none'}",
            f"Existing test files: {', '.join(self.test_files) or 'none'}",
            f"Total source files: {self.file_count}",
        ]
        return "\n".join(lines)


def probe_project(fs: WorkspaceFS) -> ProjectInfo:
    """Inspect the workspace and return factual project information."""
    files = fs.list_files()
    info = ProjectInfo(file_count=len(files))

    if "package.json" in files:
        info.has_package_json = True
        _load_package_json(fs, info)

    top_level_dirs = {path.split("/")[0] for path in files if "/" in path}
    info.source_dirs = sorted(d for d in top_level_dirs if d in _SOURCE_HINTS)

    info.test_files = [path for path in files if _looks_like_test(path)][:20]
    info.config_files = sorted(
        path
        for path in files
        if "/" not in path
        and (path.startswith("tsconfig") or path.endswith((".config.ts", ".config.js")))
    )
    return info


def _load_package_json(fs: WorkspaceFS, info: ProjectInfo) -> None:
    try:
        raw = json.loads(fs.read_text("package.json"))
    except (WorkspaceError, json.JSONDecodeError):
        return
    if not isinstance(raw, dict):
        return

    info.name = str(raw.get("name") or "")
    scripts = raw.get("scripts")
    if isinstance(scripts, dict):
        info.scripts = {str(k): str(v) for k, v in scripts.items()}
    info.dependencies = sorted(_keys(raw.get("dependencies")))
    info.dev_dependencies = sorted(_keys(raw.get("devDependencies")))


def _keys(value: object) -> list[str]:
    return [str(k) for k in value] if isinstance(value, dict) else []


def _looks_like_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if ".test." in name or ".spec." in name:
        return True
    return any(part in _TEST_HINTS for part in path.split("/")[:-1])
