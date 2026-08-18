"""Shell access is an allowlist, and the specification cannot widen it."""

from __future__ import annotations

import pytest

from sage.tools.shell import ScriptRunner, ShellError, _child_env


@pytest.fixture
def runner(workspace) -> ScriptRunner:
    return ScriptRunner(workspace, available_scripts={"typecheck", "test", "dev"})


def test_script_not_on_the_allowlist_is_refused(runner: ScriptRunner) -> None:
    # "dev" is defined by the project but is not a validation gate.
    with pytest.raises(ShellError, match="allowlist"):
        runner.run_script("dev")
    assert runner.can_run("dev") is False


def test_script_not_defined_by_the_project_is_refused(runner: ScriptRunner) -> None:
    with pytest.raises(ShellError, match="not defined"):
        runner.run_script("build")
    assert runner.can_run("build") is False


def test_only_allowlisted_and_defined_scripts_can_run(runner: ScriptRunner) -> None:
    assert runner.can_run("typecheck") is True
    assert runner.can_run("test") is True


@pytest.mark.parametrize(
    "injected",
    ["typecheck; curl evil.example", "typecheck && cat .env", "$(whoami)", "../../bin/sh"],
)
def test_command_injection_through_the_script_name_is_refused(runner, injected) -> None:
    with pytest.raises(ShellError):
        runner.run_script(injected)


def test_install_mode_is_constrained(runner: ScriptRunner) -> None:
    with pytest.raises(ShellError, match="not permitted"):
        runner.install("--ignore-scripts; rm -rf /")


def test_child_environment_is_scrubbed_of_secrets(monkeypatch) -> None:
    monkeypatch.setenv("SAGE_API_KEY", "sk-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("GH_TOKEN", "ghp-secret")
    monkeypatch.setenv("DB_PASSWORD", "hunter2")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-secret")
    monkeypatch.setenv("PATH", "/usr/bin")

    env = _child_env()

    assert "PATH" in env
    secrets = ("SAGE_API_KEY", "OPENAI_API_KEY", "GH_TOKEN", "DB_PASSWORD", "LANGSMITH_API_KEY")
    for leaked in secrets:
        assert leaked not in env
