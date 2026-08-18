"""Deterministic repository inspection.

The probe must recognise what is present and say "unknown" about what is not.
It must never force an unfamiliar project into a shape SAGE expected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage.tools.filesystem import WorkspaceFS
from sage.tools.project import MAX_IMPORTANT_FILES, probe_project


def _project(root: Path, package: dict, files: dict[str, str] | None = None) -> WorkspaceFS:
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    for path, contents in (files or {}).items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")
    return WorkspaceFS(root)


def test_react_typescript_vite_project_is_identified(tmp_path: Path) -> None:
    fs = _project(
        tmp_path,
        {
            "name": "app",
            "scripts": {"typecheck": "tsc", "test": "vitest run"},
            "dependencies": {"react": "^19.0.0"},
            "devDependencies": {"vite": "^7.0.0", "vitest": "^3.0.0", "typescript": "^5.0.0"},
        },
        {"tsconfig.json": "{}", "src/main.tsx": "", "package-lock.json": "{}"},
    )

    info = probe_project(fs)

    assert info.language == "TypeScript"
    assert info.framework == "React"
    assert info.build_tool == "Vite"
    assert info.test_runner == "Vitest"
    assert info.package_manager == "npm"
    assert info.entry_points == ["src/main.tsx"]


@pytest.mark.parametrize(
    ("dependency", "expected"),
    [("vue", "Vue"), ("svelte", "Svelte"), ("@angular/core", "Angular"), ("preact", "Preact")],
)
def test_other_frameworks_are_recognised_too(tmp_path, dependency, expected) -> None:
    """SAGE is not hardwired to one framework."""
    fs = _project(tmp_path, {"name": "a", "dependencies": {dependency: "1.0.0"}})

    assert probe_project(fs).framework == expected


def test_an_unrecognised_project_degrades_to_unknown(tmp_path: Path) -> None:
    fs = _project(tmp_path, {"name": "mystery", "dependencies": {"some-unknown-lib": "1.0.0"}})

    info = probe_project(fs)

    assert info.framework == "unknown"
    assert info.test_runner == "unknown"
    assert info.build_tool == "unknown"
    assert info.package_manager == "unknown"
    # The raw dependency still reaches the model for interpretation.
    assert "some-unknown-lib" in info.all_libraries


def test_a_project_without_package_json_is_reported_as_empty(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    info = probe_project(WorkspaceFS(tmp_path))

    assert info.has_package_json is False
    assert "no package.json" in info.to_prompt_summary()


def test_package_manager_comes_from_the_lockfile(tmp_path: Path) -> None:
    fs = _project(tmp_path, {"name": "a"}, {"pnpm-lock.yaml": ""})

    assert probe_project(fs).package_manager == "pnpm"


def test_important_files_prefer_entry_points_and_existing_tests(tmp_path: Path) -> None:
    fs = _project(
        tmp_path,
        {"name": "a", "dependencies": {"react": "1"}, "devDependencies": {"typescript": "1"}},
        {
            "tsconfig.json": "{}",
            "src/main.tsx": "",
            "src/Widget.tsx": "",
            "src/Widget.test.tsx": "",
        },
    )

    important = probe_project(fs).important_files

    # Entry point first, then the test that demonstrates the project's style.
    assert important[0] == "src/main.tsx"
    assert "src/Widget.test.tsx" in important[:3]
    assert len(important) <= MAX_IMPORTANT_FILES


def test_important_files_are_capped(tmp_path: Path) -> None:
    files = {f"src/mod{i}.ts": "" for i in range(40)}
    fs = _project(tmp_path, {"name": "a"}, files)

    assert len(probe_project(fs).important_files) == MAX_IMPORTANT_FILES


def test_the_summary_stays_compact(tmp_path: Path) -> None:
    """The probe summary is a context-management boundary, not a file dump."""
    files = {f"src/mod{i}.ts": "x" * 500 for i in range(60)}
    fs = _project(tmp_path, {"name": "a", "dependencies": {"react": "1"}}, files)

    summary = probe_project(fs).to_prompt_summary()

    assert len(summary) < 1500
    assert "mod59" not in summary
