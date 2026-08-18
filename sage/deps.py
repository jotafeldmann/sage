"""Per-run dependencies handed to the graph nodes.

LangGraph state carries data. Everything with behaviour - the model client, the
sandboxed filesystem, the command runner, the settings - lives here and is bound
to the nodes when the graph is built, so no node has to construct its own tools
and none of it is reachable from specification text.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from sage.config import Settings
from sage.llm.base import LLMClient
from sage.tools.filesystem import WorkspaceFS
from sage.tools.project import ProjectInfo, probe_project
from sage.tools.shell import ScriptRunner


@dataclass
class Deps:
    """Tools and configuration shared by every node in one run."""

    llm: LLMClient
    settings: Settings
    fs: WorkspaceFS
    project: ProjectInfo
    quiet: bool = False

    @classmethod
    def create(cls, llm: LLMClient, settings: Settings, target_dir: Path) -> Deps:
        fs = WorkspaceFS(target_dir)
        return cls(llm=llm, settings=settings, fs=fs, project=probe_project(fs))

    def refresh_project(self) -> None:
        """Re-probe after files change, so later stages see the current state."""
        self.project = probe_project(self.fs)

    def script_runner(self) -> ScriptRunner:
        return ScriptRunner(self.fs.root, available_scripts=set(self.project.scripts))

    def say(self, message: str) -> None:
        if not self.quiet:
            print(message, file=sys.stdout, flush=True)
