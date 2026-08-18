"""Turn raw tool output into structured facts.

SPEC.md 6.4 asks validation state to capture test counts and affected files, and
to prefer normalized output over dumping raw logs into the next prompt. This
module is the normalization: it reads what compilers and test runners print and
extracts the few things the repair node can actually act on.

Everything here is regex over text, deliberately:

* it works with the reporters a project already has, so no target project has to
  be reconfigured to be validatable;
* an unrecognised format degrades to "no counts, unknown kind" rather than
  failing, and the raw excerpt still reaches repair.

Nothing here is specific to one project's tooling beyond recognising the output
shapes of common TypeScript and JavaScript tools.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

FailureKind = Literal[
    "missing_module",
    "syntax",
    "typecheck",
    "test_failure",
    "build",
    "timeout",
    "unknown",
]

# Guidance handed to the repair prompt for each kind of failure. Keeping this
# beside the classifier means adding a category forces a decision about what
# advice it deserves.
REPAIR_GUIDANCE: dict[str, str] = {
    "missing_module": (
        "An import cannot be resolved. Either the file was never created, or the "
        "import path or exported name is wrong. Check the exported names you were "
        "given before inventing a new file."
    ),
    "syntax": (
        "The code does not parse. Fix the malformed syntax exactly where it is "
        "reported; do not restructure anything else."
    ),
    "typecheck": (
        "The compiler rejected a type. Fix the types, not the test. Prefer "
        "correcting the annotation or the value over widening a type to `any`."
    ),
    "test_failure": (
        "The code compiles but behaves differently from what a test asserts. "
        "Decide which one is wrong. If the assertion contradicts the "
        "specification, fix the assertion; otherwise fix the implementation. "
        "Never delete a test or weaken it just to get a pass."
    ),
    "build": (
        "Type checking and tests are fine but the bundle failed. Look for an "
        "unresolved import, an asset path, or a config expectation."
    ),
    "timeout": (
        "The command did not finish. Look for an infinite loop, an unawaited "
        "promise, or a test that never resolves."
    ),
    "unknown": (
        "Diagnose from the raw output above and make the smallest change that "
        "addresses it."
    ),
}

# vitest: "Tests  1 failed | 2 passed (3)"      jest: "Tests: 1 failed, 2 passed, 3 total"
_VITEST_TESTS = re.compile(
    r"^\s*Tests\s+(?:(?P<failed>\d+)\s+failed\s*\|\s*)?(?P<passed>\d+)\s+passed"
    r"(?:\s*\|\s*(?P<skipped>\d+)\s+skipped)?\s*\((?P<total>\d+)\)",
    re.MULTILINE,
)
_JEST_TESTS = re.compile(
    r"^\s*Tests:\s+(?:(?P<failed>\d+)\s+failed,\s*)?(?:\d+\s+skipped,\s*)?"
    r"(?P<passed>\d+)\s+passed,\s*(?P<total>\d+)\s+total",
    re.MULTILINE,
)
_NO_TESTS = re.compile(r"No test files found", re.IGNORECASE)

# tsc: "src/App.tsx(12,5): error TS2322: Type 'x' is not assignable"
_TSC_DIAGNOSTIC = re.compile(
    r"^(?P<file>[\w./-]+\.\w+)\((?P<line>\d+),(?P<col>\d+)\):\s*error\s+"
    r"(?P<code>TS\d+):\s*(?P<message>.+)$",
    re.MULTILINE,
)
# esbuild/vite/eslint/vitest stack frames. A frame may be prefixed by a marker
# glyph such as vitest's arrow, so the file is not always at the start of the
# line; anything non-word before the path is skipped.
_COLON_DIAGNOSTIC = re.compile(
    r"^[^\w]*(?P<file>[\w./-]+\.\w+):(?P<line>\d+):(?P<col>\d+)"
    r"(?:[\s:-]+(?P<message>.*))?$",
    re.MULTILINE,
)

# vitest: "FAIL src/X.test.tsx > suite > case" followed by the error message.
_VITEST_FAILURE = re.compile(
    r"^\s*FAIL\s+(?P<file>[\w./-]+\.\w+)\s*>\s*(?P<case>.+?)\s*$\n"
    r"\s*(?P<message>\S.*?)\s*$",
    re.MULTILINE,
)

_MISSING_MODULE = re.compile(
    r"Cannot find module|Failed to resolve import|Module not found|TS2307", re.IGNORECASE
)
_SYNTAX = re.compile(
    r"SyntaxError|Unexpected token|Expression expected|TS1005|TS1128|Transform failed",
    re.IGNORECASE,
)
_TYPE_ERROR = re.compile(r"\bTS\d{4}\b|error TS")
_TEST_FAILURE = re.compile(
    r"AssertionError|expect\(|Unable to find|\bFAIL\b|\d+ failed", re.IGNORECASE
)

# Cap so a pathological log cannot fill the prompt with diagnostics.
MAX_DIAGNOSTICS = 15


@dataclass(frozen=True)
class TestCounts:
    """How many tests ran, when the runner said so."""

    passed: int
    failed: int
    total: int

    def describe(self) -> str:
        return f"{self.passed} passed, {self.failed} failed, of {self.total}"


def parse_test_counts(output: str) -> TestCounts | None:
    """Read a test runner's summary line, or None if there isn't one."""
    for pattern in (_VITEST_TESTS, _JEST_TESTS):
        match = pattern.search(output)
        if match:
            failed = int(match.group("failed") or 0)
            passed = int(match.group("passed") or 0)
            total = int(match.group("total") or passed + failed)
            return TestCounts(passed=passed, failed=failed, total=total)

    if _NO_TESTS.search(output):
        return TestCounts(passed=0, failed=0, total=0)
    return None


def parse_diagnostics(output: str, known_files: set[str] | None = None) -> list[str]:
    """Extract `file:line message` diagnostics, most useful format first."""
    found: list[str] = []

    for match in _TSC_DIAGNOSTIC.finditer(output):
        _add(
            found,
            f"{match.group('file')}:{match.group('line')}:{match.group('col')} "
            f"{match.group('code')} {match.group('message').strip()}",
        )

    # A failing test names the case, which is more use to repair than a line
    # number in a matcher library.
    for match in _VITEST_FAILURE.finditer(output):
        _add(found, f"{match.group('file')} > {match.group('case')}: {match.group('message')}")

    if not found:
        for match in _COLON_DIAGNOSTIC.finditer(output):
            file = match.group("file")
            # Stack frames inside dependencies are noise; only the project's own
            # files are actionable, and `known_files` is how that is decided.
            if known_files is not None and file.lstrip("./") not in known_files:
                continue
            message = (match.group("message") or "").strip()
            location = f"{file}:{match.group('line')}:{match.group('col')}"
            _add(found, f"{location} {message}".strip())

    return found[:MAX_DIAGNOSTICS]


def classify_failure(output: str, command: str = "", timed_out: bool = False) -> FailureKind:
    """Name the kind of failure, so repair can be given targeted guidance.

    Order matters: a missing module is reported by the compiler as a type error,
    and a syntax error often produces downstream type errors too. The most
    specific cause is checked first so the guidance names the real problem.
    """
    if timed_out:
        return "timeout"
    if _MISSING_MODULE.search(output):
        return "missing_module"
    if _SYNTAX.search(output):
        return "syntax"
    if _TYPE_ERROR.search(output):
        return "typecheck"
    if _TEST_FAILURE.search(output):
        return "test_failure"
    if "build" in command:
        return "build"
    return "unknown"


def guidance_for(kind: str) -> str:
    return REPAIR_GUIDANCE.get(kind, REPAIR_GUIDANCE["unknown"])


def _add(found: list[str], entry: str) -> None:
    if entry not in found:
        found.append(entry)
