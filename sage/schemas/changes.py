"""File-change schema used by the generator and repair nodes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    """A complete replacement of one text file inside the workspace.

    `path` is workspace-relative. It is re-validated by `WorkspaceFS` before
    anything is written, so a model cannot escape the workspace by proposing a
    traversal path here.
    """

    path: str = Field(min_length=1, max_length=400)
    contents: str
    rationale: str = Field(default="", max_length=1000)


class GenerationResult(BaseModel):
    """What a generator or repair call is allowed to return."""

    changes: list[FileChange] = Field(default_factory=list, max_length=20)
    summary: str = Field(default="", max_length=1000)
