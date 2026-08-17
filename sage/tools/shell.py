"""Constrained command execution.

The model never supplies a command string. It can only cause SAGE to run a
package script that (a) already exists in the target's package.json and (b) is
on `ALLOWED_SCRIPTS`. Commands are executed without a shell, in a fixed working
directory, with a timeout and a scrubbed environment (SPEC.md 7.2).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Scripts SAGE knows how to interpret as a validation gate.
ALLOWED_SCRIPTS = frozenset({"typecheck", "test", "build", "lint"})

# Install commands SAGE may run to make a target project runnable.
ALLOWED_INSTALL = {
    "ci": ["npm", "ci"],
    "install": ["npm", "install"],
}

DEFAULT_TIMEOUT_SECONDS = 300

# Environment variables never passed to a child process.
_SECRET_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_CREDENTIALS")


class ShellError(RuntimeError):
    """Raised when a command is not permitted."""


@dataclass(frozen=True)
class CommandResult:
    """Raw outcome of one command. Normalization happens in the validator."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part.strip())


class ScriptRunner:
    """Runs allowlisted npm scripts inside one project directory."""

    def __init__(
        self,
        root: Path | str,
        available_scripts: frozenset[str] | set[str] | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ShellError(f"project root is not a directory: {self.root}")
        self.available_scripts = frozenset(available_scripts or ())
        self.timeout = timeout

    def can_run(self, script: str) -> bool:
        return script in ALLOWED_SCRIPTS and script in self.available_scripts

    def run_script(self, script: str) -> CommandResult:
        """Run `npm run <script>`. Raises `ShellError` if not permitted."""
        if script not in ALLOWED_SCRIPTS:
            raise ShellError(f"script is not on the allowlist: {script!r}")
        if script not in self.available_scripts:
            raise ShellError(f"script is not defined by the target project: {script!r}")
        return self._execute(["npm", "run", "--silent", script])

    def install(self, mode: str = "ci") -> CommandResult:
        """Install target-project dependencies."""
        argv = ALLOWED_INSTALL.get(mode)
        if argv is None:
            raise ShellError(f"install mode is not permitted: {mode!r}")
        return self._execute(argv)

    def _execute(self, argv: list[str]) -> CommandResult:
        printable = " ".join(argv)
        try:
            completed = subprocess.run(  # noqa: S603 - argv is allowlisted, shell=False
                argv,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False,
                check=False,
                env=_child_env(),
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                command=printable,
                exit_code=124,
                stdout=_as_text(exc.stdout),
                stderr=f"command timed out after {self.timeout}s",
                timed_out=True,
            )
        except FileNotFoundError as exc:
            raise ShellError(f"command not available: {argv[0]}") from exc

        return CommandResult(
            command=printable,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def _child_env() -> dict[str, str]:
    """Copy the environment minus anything that looks like a credential."""
    return {
        key: value
        for key, value in os.environ.items()
        if not (
            key.startswith("SAGE_")
            or key.startswith("LANGSMITH_")
            or key.endswith(_SECRET_SUFFIXES)
        )
    }


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
