"""The workspace boundary must hold regardless of what a model proposes."""

from __future__ import annotations

import pytest

from sage.tools.filesystem import WorkspaceError, WorkspaceFS


@pytest.mark.parametrize(
    "path",
    [
        "../outside.ts",
        "src/../../outside.ts",
        "/etc/passwd",
        "/home/j/.ssh/id_rsa",
        "",
        "   ",
    ],
)
def test_paths_outside_the_workspace_are_rejected(fs: WorkspaceFS, path: str) -> None:
    with pytest.raises(WorkspaceError):
        fs.resolve(path)


@pytest.mark.parametrize(
    "name",
    [".env", ".env.local", "secrets.pem", "id_rsa", ".npmrc", "credentials.json"],
)
def test_credential_files_are_denied_even_inside_the_workspace(fs, workspace, name) -> None:
    (workspace / name).write_text("SECRET=1", encoding="utf-8")

    with pytest.raises(WorkspaceError):
        fs.read_text(name)
    assert name not in fs.list_files()


def test_symlink_escaping_the_workspace_is_rejected(fs, workspace, tmp_path) -> None:
    outside = tmp_path.parent / "outside-target.ts"
    outside.write_text("export const leaked = true;\n", encoding="utf-8")
    (workspace / "src" / "link.ts").symlink_to(outside)

    with pytest.raises(WorkspaceError):
        fs.read_text("src/link.ts")


def test_writes_land_inside_the_workspace(fs, workspace) -> None:
    written = fs.write_text("src/components/Widget.tsx", "export const Widget = () => null;\n")

    assert written == "src/components/Widget.tsx"
    assert (workspace / "src/components/Widget.tsx").is_file()


def test_non_source_files_cannot_be_written(fs) -> None:
    with pytest.raises(WorkspaceError):
        fs.write_text("install.sh", "rm -rf /")


def test_denied_directories_are_not_listed(fs, workspace) -> None:
    (workspace / "node_modules" / "pkg").mkdir(parents=True)
    (workspace / "node_modules" / "pkg" / "index.js").write_text("//", encoding="utf-8")

    assert not any(path.startswith("node_modules/") for path in fs.list_files())


def test_read_many_skips_unreadable_paths_without_failing(fs) -> None:
    files = fs.read_many(["src/App.tsx", "../escape.ts", "does/not/exist.ts"])

    assert list(files) == ["src/App.tsx"]
