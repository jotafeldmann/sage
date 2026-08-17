"""Workspace-scoped filesystem access.

Every path the model proposes passes through here. The rules (SPEC.md 7.1):

* all paths resolve inside one configured workspace root;
* traversal and symlink escapes are rejected;
* credential-bearing files are never readable;
* the specification cannot widen any of this, because none of it is
  parameterised by specification content.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from sage.config import MAX_FILE_CHARS

# Never read these into a prompt, even inside the workspace.
DENIED_NAME_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "id_ed25519*",
    "*.p12",
    "*.pfx",
    "credentials*",
    ".npmrc",
    ".netrc",
)

# Directories that are noise, huge, or outside the source surface.
DENIED_DIR_NAMES = frozenset(
    {".git", "node_modules", "dist", "build", ".next", "coverage", ".venv", "__pycache__", ".sage"}
)

TEXT_SUFFIXES = frozenset(
    {
        ".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs",
        ".json", ".md", ".css", ".scss", ".html", ".txt", ".yml", ".yaml",
    }
)


class WorkspaceError(RuntimeError):
    """Raised when an operation would leave or violate the workspace."""


class WorkspaceFS:
    """Read and write text files, but only inside `root`."""

    def __init__(self, root: Path | str) -> None:
        resolved = Path(root).resolve()
        if not resolved.is_dir():
            raise WorkspaceError(f"workspace root is not a directory: {resolved}")
        self.root = resolved

    # -- path safety -------------------------------------------------------

    def resolve(self, relative_path: str) -> Path:
        """Resolve a workspace-relative path, or raise `WorkspaceError`.

        Rejects absolute paths, `..` traversal, denied filenames, and symlinks
        that point outside the workspace. Resolution is done on the fully
        realpath'd candidate so a symlinked parent directory cannot smuggle a
        write outside the root.
        """
        if not relative_path or not relative_path.strip():
            raise WorkspaceError("empty path")

        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise WorkspaceError(f"absolute paths are not allowed: {relative_path}")
        if any(part == ".." for part in candidate.parts):
            raise WorkspaceError(f"path traversal is not allowed: {relative_path}")

        target = (self.root / candidate).resolve()
        if target != self.root and self.root not in target.parents:
            raise WorkspaceError(f"path escapes the workspace: {relative_path}")

        if _is_denied_name(target.name):
            raise WorkspaceError(f"access to this file is denied: {relative_path}")
        relative_parts = target.relative_to(self.root).parts
        if any(part in DENIED_DIR_NAMES for part in relative_parts[:-1]):
            raise WorkspaceError(f"access to this directory is denied: {relative_path}")

        return target

    # -- reads -------------------------------------------------------------

    def exists(self, relative_path: str) -> bool:
        try:
            return self.resolve(relative_path).is_file()
        except WorkspaceError:
            return False

    def read_text(self, relative_path: str) -> str:
        """Read a text file, truncating at `MAX_FILE_CHARS`."""
        target = self.resolve(relative_path)
        if not target.is_file():
            raise WorkspaceError(f"not a file: {relative_path}")
        if target.suffix and target.suffix not in TEXT_SUFFIXES:
            raise WorkspaceError(f"not a readable text file: {relative_path}")

        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_FILE_CHARS:
            return text[:MAX_FILE_CHARS] + "\n... [truncated]"
        return text

    def read_many(self, relative_paths: list[str]) -> dict[str, str]:
        """Read several files, silently skipping any that are unreadable."""
        files: dict[str, str] = {}
        for path in relative_paths:
            try:
                files[path] = self.read_text(path)
            except WorkspaceError:
                continue
        return files

    def list_files(self, limit: int = 400) -> list[str]:
        """List workspace-relative source files, skipping denied directories."""
        found: list[str] = []
        for path in sorted(self.root.rglob("*")):
            if len(found) >= limit:
                break
            if not path.is_file():
                continue
            relative = path.relative_to(self.root)
            if any(part in DENIED_DIR_NAMES for part in relative.parts[:-1]):
                continue
            if _is_denied_name(path.name):
                continue
            found.append(relative.as_posix())
        return found

    # -- writes ------------------------------------------------------------

    def write_text(self, relative_path: str, contents: str) -> str:
        """Create or replace a text file. Returns the workspace-relative path."""
        target = self.resolve(relative_path)
        if target.suffix and target.suffix not in TEXT_SUFFIXES:
            raise WorkspaceError(f"refusing to write non-source file: {relative_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")
        return target.relative_to(self.root).as_posix()


def _is_denied_name(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in DENIED_NAME_PATTERNS)
