"""Validator node: the deterministic quality gate.

No model is involved. SAGE runs the validation scripts the target project
actually defines, in a fixed preference order, stopping at the first failure.
Raw output is normalized and truncated before any of it reaches a prompt.

This node also decides termination: it is the only place that can mark a run
succeeded or failed, so the graph always ends in an explicit state.
"""

from __future__ import annotations

from sage.config import MAX_OUTPUT_EXCERPT_CHARS, VALIDATION_SCRIPT_PREFERENCE
from sage.deps import Deps
from sage.schemas.validation import ValidationResult, extract_mentioned_files, strip_ansi
from sage.state import SageState


def validator_node(state: SageState, deps: Deps) -> dict:
    """Run available validation commands and set the run's terminal status."""
    deps.refresh_project()
    runner = deps.script_runner()
    known_files = set(deps.fs.list_files())

    results: list[ValidationResult] = []
    passed = True

    for script in VALIDATION_SCRIPT_PREFERENCE:
        if not runner.can_run(script):
            # Absent scripts are skipped, not assumed. A target project that
            # has no typecheck script is not a failing project.
            results.append(
                ValidationResult(
                    command=f"npm run {script}",
                    exit_code=0,
                    passed=True,
                    skipped=True,
                    output_excerpt="script not defined by this project",
                )
            )
            continue

        deps.say(f"Running {script}...")
        outcome = runner.run_script(script)
        result = _normalize(outcome, known_files)
        results.append(result)
        deps.say("PASSED" if result.passed else f"FAILED (exit {result.exit_code})")

        if not result.passed:
            passed = False
            break  # first failure is the one worth repairing

    if not any(not r.skipped for r in results):
        deps.say("No validation scripts available in the target project.")

    return {
        "validation_results": [r.model_dump() for r in results],
        "validation_passed": passed,
        **_terminal_status(state, deps, passed),
    }


def _terminal_status(state: SageState, deps: Deps, passed: bool) -> dict:
    """Succeed, fail, or stay running with repair budget left."""
    if passed:
        return {"status": "succeeded", "failure_reason": None}

    attempts = state.get("repair_attempts", 0)
    if attempts >= deps.settings.max_repair_attempts:
        return {
            "status": "failed",
            "failure_reason": (
                f"validation still failing after {attempts} repair attempt(s) "
                f"(limit {deps.settings.max_repair_attempts})"
            ),
        }
    return {"status": "running", "failure_reason": None}


def _normalize(outcome, known_files: set[str]) -> ValidationResult:
    """Reduce a raw command result to the compact shape repair consumes."""
    output = strip_ansi(outcome.combined_output)
    return ValidationResult(
        command=outcome.command,
        exit_code=outcome.exit_code,
        passed=outcome.passed,
        output_excerpt=_excerpt(output),
        files_mentioned=extract_mentioned_files(output, known_files),
    )


def _excerpt(output: str) -> str:
    """Keep the tail, where compilers and test runners put the diagnostics."""
    if len(output) <= MAX_OUTPUT_EXCERPT_CHARS:
        return output
    return "... [earlier output truncated]\n" + output[-MAX_OUTPUT_EXCERPT_CHARS:]
