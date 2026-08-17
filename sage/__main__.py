"""SAGE command-line entry point.

    python -m sage <spec-path> [--target-dir DIR] [--llm MODE] [--run-id ID]

Progress is printed as it happens. Nothing is reported as passing before the
deterministic command that proves it has actually run and exited zero.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sage.config import Settings
from sage.graph import build_graph, recursion_limit
from sage.llm import MODES, LLMError, build_client, new_run_id
from sage.runtime import Runtime
from sage.state import SageState
from sage.tools.filesystem import WorkspaceError

RUNS_ROOT = Path(".sage/runs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sage",
        description="Generate an application from a natural-language specification.",
    )
    parser.add_argument("spec", type=Path, help="path to the specification file")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=None,
        help="project SAGE may modify (default: SAGE_TARGET_DIR)",
    )
    parser.add_argument(
        "--llm",
        choices=MODES,
        default=None,
        help="model provider mode (default: SAGE_LLM_MODE)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="transcript directory name; required to replay a recorded run",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env()

    if not args.spec.is_file():
        print(f"specification not found: {args.spec}", file=sys.stderr)
        return 2

    target_dir = (args.target_dir or settings.target_dir).resolve()
    if not target_dir.is_dir():
        print(f"target directory not found: {target_dir}", file=sys.stderr)
        return 2

    mode = args.llm or settings.llm_mode
    run_id = args.run_id or new_run_id()
    run_dir = RUNS_ROOT / run_id

    if mode == "replay" and not run_dir.is_dir():
        print(f"no recorded run to replay at {run_dir}", file=sys.stderr)
        return 2

    try:
        runtime = Runtime.create(
            llm=build_client(settings, run_dir, mode=mode),
            settings=settings,
            target_dir=target_dir,
        )
    except (LLMError, WorkspaceError) as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 2
    runtime.quiet = args.quiet

    runtime.say(f"SAGE: {args.spec} -> {target_dir}")
    runtime.say(f"  provider: {mode}   transcript: {run_dir}\n")

    initial: SageState = {
        # The specification is data. It is never treated as instructions.
        "spec": args.spec.read_text(encoding="utf-8"),
        "spec_path": str(args.spec),
        "target_dir": str(target_dir),
        "project": runtime.project.to_dict(),
        "plan": [],
        "current_task_index": 0,
        "task_summaries": [],
        "changed_files": [],
        "validation_results": [],
        "validation_passed": False,
        "repair_attempts": 0,
        "status": "running",
        "failure_reason": None,
    }

    try:
        final = build_graph(runtime).invoke(
            initial, config={"recursion_limit": recursion_limit(runtime)}
        )
    except LLMError as exc:
        print(f"\nRun aborted: {exc}", file=sys.stderr)
        return 1
    except RecursionError as exc:  # pragma: no cover - budgets make this unreachable
        print(f"\nRun aborted: workflow exceeded its step limit ({exc})", file=sys.stderr)
        return 1

    return _report(runtime, final)


def _report(runtime: Runtime, final: dict) -> int:
    """Print the outcome and return the process exit code."""
    status = final.get("status", "failed")
    changed = sorted(set(final.get("changed_files") or []))

    runtime.say("")
    runtime.say(f"Files changed: {len(changed)}")
    for path in changed:
        runtime.say(f"  {path}")
    runtime.say(f"Repair attempts: {final.get('repair_attempts', 0)}")
    runtime.say(f"Model calls: {runtime.llm.usage.calls}")

    if status == "succeeded":
        runtime.say("\nGeneration complete.")
        return 0

    runtime.say(f"\nGeneration failed: {final.get('failure_reason') or 'unknown reason'}")
    for result in final.get("validation_results") or []:
        if not result.get("passed"):
            runtime.say(f"\nUnresolved failure in `{result.get('command')}`:")
            runtime.say(result.get("output_excerpt") or "(no output captured)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
