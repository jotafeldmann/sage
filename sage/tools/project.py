"""Deterministic inspection of the target project.

No LLM is involved here. SAGE reads package.json and the file listing to learn
what the project factually is: which npm scripts exist, which libraries are
installed, which framework and test runner are in use, where source and tests
live, and which files are most likely to matter when planning.

Two rules shape this module:

* **Facts here, interpretation elsewhere.** SPEC.md 6.1 asks for deterministic
  inspection before the model is asked to infer anything, so everything in this
  file is a static lookup or a filesystem fact. Judgement about what the
  libraries mean for the design belongs to the analyzer node.
* **Recognition, not assumption.** The tables below name general ecosystem
  frameworks and test runners so they can be *recognised if present*. They
  deliberately do not enumerate any particular boilerplate's data, mocking or
  component libraries; those arrive as raw dependency names and are interpreted
  by the analyzer. An unrecognised project degrades to "unknown" rather than
  being forced into a shape SAGE expected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sage.tools.filesystem import WorkspaceError, WorkspaceFS

# Directory names commonly used for source and tests, checked against reality.
_SOURCE_HINTS = ("src", "app", "lib")
_TEST_HINTS = ("test", "tests", "__tests__", "spec")

# Package name -> framework label. General ecosystem frameworks only.
_FRAMEWORK_MARKERS = (
    ("next", "Next.js"),
    ("nuxt", "Nuxt"),
    ("@remix-run/react", "Remix"),
    ("astro", "Astro"),
    ("@angular/core", "Angular"),
    ("svelte", "Svelte"),
    ("vue", "Vue"),
    ("solid-js", "Solid"),
    ("preact", "Preact"),
    ("react", "React"),
)

# Package name -> test runner label.
_TEST_RUNNER_MARKERS = (
    ("vitest", "Vitest"),
    ("jest", "Jest"),
    ("@playwright/test", "Playwright"),
    ("cypress", "Cypress"),
    ("mocha", "Mocha"),
    ("ava", "AVA"),
    ("node:test", "node:test"),
)

# Package name -> build tooling label.
_BUILD_MARKERS = (
    ("vite", "Vite"),
    ("webpack", "webpack"),
    ("rollup", "Rollup"),
    ("esbuild", "esbuild"),
    ("parcel", "Parcel"),
)

# Lockfile -> package manager.
_LOCKFILES = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lockb", "bun"),
    ("package-lock.json", "npm"),
)

# Basenames worth surfacing to the planner regardless of depth.
_ENTRY_BASENAMES = ("main", "index", "app", "root", "entry")

# How many files the probe will nominate as "important".
MAX_IMPORTANT_FILES = 12


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

    # Identified deterministically from the dependency list and file layout.
    language: str = "unknown"
    framework: str = "unknown"
    test_runner: str = "unknown"
    build_tool: str = "unknown"
    package_manager: str = "unknown"
    entry_points: list[str] = field(default_factory=list)
    important_files: list[str] = field(default_factory=list)

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
            "language": self.language,
            "framework": self.framework,
            "test_runner": self.test_runner,
            "build_tool": self.build_tool,
            "package_manager": self.package_manager,
            "entry_points": self.entry_points,
            "important_files": self.important_files,
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
            f"Language: {self.language}",
            f"Framework: {self.framework}",
            f"Build tool: {self.build_tool}",
            f"Test runner: {self.test_runner}",
            f"Package manager: {self.package_manager}",
            f"Available npm scripts: {', '.join(sorted(self.scripts)) or 'none'}",
            f"Libraries: {', '.join(self.all_libraries) or 'none'}",
            f"Source directories: {', '.join(self.source_dirs) or 'none detected'}",
            f"Entry points: {', '.join(self.entry_points) or 'none detected'}",
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

    info.language = _detect_language(files, info)
    info.framework = _match_marker(_FRAMEWORK_MARKERS, info.all_libraries)
    info.test_runner = _match_marker(_TEST_RUNNER_MARKERS, info.all_libraries)
    info.build_tool = _match_marker(_BUILD_MARKERS, info.all_libraries)
    info.package_manager = next((pm for lock, pm in _LOCKFILES if lock in files), "unknown")
    info.entry_points = _find_entry_points(files, info.source_dirs)
    info.important_files = _rank_important_files(files, info)

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


def _match_marker(markers: tuple[tuple[str, str], ...], libraries: list[str]) -> str:
    """First marker present wins; the tables are ordered most-specific first."""
    available = set(libraries)
    return next((label for package, label in markers if package in available), "unknown")


def _detect_language(files: list[str], info: ProjectInfo) -> str:
    """TypeScript if the project is configured for it, else JavaScript."""
    if any(f.startswith("tsconfig") for f in files) or "typescript" in info.all_libraries:
        return "TypeScript"
    if any(f.endswith((".js", ".jsx", ".mjs")) for f in files):
        return "JavaScript"
    return "unknown"


def _find_entry_points(files: list[str], source_dirs: list[str]) -> list[str]:
    """Shallow files in a source directory with a conventional entry name."""
    entries = []
    for path in files:
        head, _, tail = path.partition("/")
        if head not in source_dirs or "/" in tail:
            continue
        stem = tail.rsplit(".", 1)[0].lower()
        if stem in _ENTRY_BASENAMES:
            entries.append(path)
    return sorted(entries)


def _rank_important_files(files: list[str], info: ProjectInfo) -> list[str]:
    """Nominate the files most likely to matter when planning a change.

    Ordered by how much each one tells you about the project's conventions:
    entry points, then existing tests (which demonstrate the testing style),
    then configuration, then remaining shallow source files.
    """
    ranked: list[str] = []

    def add(candidates: list[str]) -> None:
        for path in candidates:
            if path not in ranked and len(ranked) < MAX_IMPORTANT_FILES:
                ranked.append(path)

    add(info.entry_points)
    add(info.test_files)
    add(info.config_files)
    add(sorted(
        path
        for path in files
        if path.split("/")[0] in info.source_dirs and path.endswith(_SOURCE_SUFFIXES)
    ))
    return ranked


_SOURCE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte")
