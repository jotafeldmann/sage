"""Extract the public surface of a source file.

Milestone 1 carried a task's dependencies forward as a one-line prose summary.
That told a task what a module *did* but not what it *exported*, so the first
task to consume another task's module had to guess the API - and in the
recorded Milestone 1 run, guessed wrong.

Sending the whole dependency file would fix that and undo the context budget.
Sending its exported declarations fixes it for a few hundred characters.

This is deliberately a shallow textual scan, not a parser. It reads declaration
lines and stops; it does not resolve types, follow imports, or understand
scope. A missed export costs a little context quality, never correctness -
validation remains the authority on whether the generated code is right.
"""

from __future__ import annotations

import re

# `export function f(`, `export const x`, `export interface I`, ...
_DECLARATION = re.compile(
    r"^export\s+(?:default\s+)?"
    r"(?:async\s+)?"
    r"(function\*?|const|let|var|class|interface|type|enum)\s+"
    r"([A-Za-z_$][\w$]*)"
)

# `export { a, b as c }`
_NAMED_LIST = re.compile(r"^export\s*\{([^}]*)\}")

# `export * from "./x"`
_STAR = re.compile(r"^export\s+\*")

# `export default Thing;`
_DEFAULT = re.compile(r"^export\s+default\s+([A-Za-z_$][\w$]*)\s*;?\s*$")

SIGNATURE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs")

# Ceiling on one rendered declaration, so a long generic signature cannot
# dominate the block.
MAX_DECLARATION_CHARS = 160


def extract_exports(source: str) -> list[str]:
    """Return one readable line per exported symbol, in source order."""
    found: list[str] = []

    for raw in source.splitlines():
        line = raw.strip()
        if not line.startswith("export"):
            continue

        declaration = _DECLARATION.match(line)
        if declaration:
            rendered = _render(line, declaration.group(1))
            if rendered and rendered not in found:
                found.append(rendered)
            continue

        named = _NAMED_LIST.match(line)
        if named:
            for entry in named.group(1).split(","):
                name = entry.strip()
                if name and name not in found:
                    found.append(name)
            continue

        if _STAR.match(line) and line not in found:
            found.append(line.rstrip(";"))
            continue

        default = _DEFAULT.match(line)
        if default:
            entry = f"default {default.group(1)}"
            if entry not in found:
                found.append(entry)

    return found


def _render(line: str, kind: str) -> str:
    """Trim a declaration to its signature, dropping the implementation.

    Where to cut depends on the kind of declaration, which is why this is not
    one blanket rule:

    * a `type` alias *is* its right-hand side, so nothing after `=` is dropped;
    * a function's signature ends after its parameter list and return type, and
      the parameter list may itself contain braces from destructuring;
    * everything else ends at its body or initialiser.
    """
    text = line.removeprefix("export").strip()

    if kind in ("type", "enum"):
        return _cap(text.rstrip(";").strip())

    if kind.startswith("function"):
        return _cap(_function_signature(text))

    for marker in (" {", " =>", " ="):
        index = text.find(marker)
        if index != -1:
            text = text[:index]
            break
    return _cap(text.rstrip("{;, ").strip())


def _function_signature(text: str) -> str:
    """Keep the parameter list whole, then any return type, then stop."""
    start = text.find("(")
    if start == -1:
        return text.rstrip("{;, ").strip()

    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                tail = text[index + 1 :]
                body = tail.find("{")
                suffix = (tail if body == -1 else tail[:body]).rstrip("{;, ").strip()
                if not suffix:
                    return text[: index + 1]
                joiner = "" if suffix.startswith(":") else " "
                return f"{text[: index + 1]}{joiner}{suffix}"
    # Unbalanced - the declaration spans lines; keep what we have.
    return text.rstrip("{;, ").strip()


def _cap(text: str) -> str:
    if len(text) > MAX_DECLARATION_CHARS:
        return text[:MAX_DECLARATION_CHARS] + " ..."
    return text


def describe_module(path: str, source: str) -> str | None:
    """Render one module's exports, or None when it has none worth showing."""
    if not path.endswith(SIGNATURE_SUFFIXES):
        return None
    exports = extract_exports(source)
    if not exports:
        return None
    lines = "\n".join(f"  {item}" for item in exports)
    return f"{path} exports:\n{lines}"
