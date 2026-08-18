"""Slice a specification down to what one task actually needs.

SPEC.md 6.3 says each generation call should receive "relevant requirements",
not the whole document. The planner already records which requirement
identifiers each task implements, so those identifiers are the handle.

A specification is split into two kinds of section:

* **requirement sections**, whose heading carries an identifier such as
  ``AREA-REQ-001`` or ``AREA-OPT-002``;
* **everything else** - purpose, constraints, acceptance criteria - which
  applies to the whole build.

A slice keeps every non-requirement section, because those are global, and only
the requirement sections the task names. When nothing can be resolved the full
specification is returned: losing a requirement is far worse than sending a few
paragraphs too many.

The identifier pattern is structural, not domain-specific. It matches the
"WORD-WORD-123" convention the evaluation specs happen to use without knowing
anything about what those words mean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# e.g. AREA-REQ-001, AREA-OPT-002, THING-REQ-005, REQ-1. Deliberately not
# examples taken from the evaluation specifications: identifiers from a spec
# SAGE has been run against should not appear in SAGE at all, not even in a
# comment, and tests/test_generalization.py enforces that.
_REQUIREMENT_ID = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-\d+)\b")

# Markdown ATX headings, capturing depth so nesting can be respected.
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Section:
    """One heading and the body beneath it."""

    level: int
    heading: str
    body: str
    ids: frozenset[str]

    @property
    def text(self) -> str:
        return f"{'#' * self.level} {self.heading}\n{self.body}".rstrip() + "\n"

    @property
    def is_requirement(self) -> bool:
        return bool(self.ids)


def split_sections(spec: str) -> tuple[str, list[Section]]:
    """Split a specification into its preamble and its headed sections."""
    lines = spec.splitlines()
    preamble: list[str] = []
    sections: list[Section] = []

    current: list[str] | None = None
    level = 0
    heading = ""

    def flush() -> None:
        if current is None:
            return
        body = "\n".join(current)
        sections.append(
            Section(
                level=level,
                heading=heading,
                body=body,
                ids=frozenset(_REQUIREMENT_ID.findall(heading)),
            )
        )

    for line in lines:
        match = _HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2).strip()
            current = []
        elif current is None:
            preamble.append(line)
        else:
            current.append(line)
    flush()

    return "\n".join(preamble).strip(), sections


def requirement_ids(spec: str) -> set[str]:
    """Every requirement identifier the specification defines in a heading."""
    _, sections = split_sections(spec)
    return {rid for section in sections for rid in section.ids}


def slice_for_requirements(spec: str, wanted: list[str] | set[str]) -> str:
    """Return the parts of `spec` relevant to `wanted`, or all of it.

    Falls back to the complete specification when the task names no
    requirements, or names none that the document actually defines.
    """
    requested = {r.strip().upper() for r in wanted if r and r.strip()}
    if not requested:
        return spec

    preamble, sections = split_sections(spec)
    if not sections:
        return spec

    defined = {rid for section in sections for rid in section.ids}
    if not requested & defined:
        return spec

    kept: list[Section] = []
    for index, section in enumerate(sections):
        if section.is_requirement:
            if section.ids & requested:
                kept.append(section)
                kept.extend(_descendants(sections, index))
        elif not _is_ancestor_of_only_unwanted(sections, index, requested):
            kept.append(section)

    if not kept:
        return spec

    chosen: list[Section] = []
    seen: set[int] = set()
    for section in kept:
        key = id(section)
        if key not in seen:
            seen.add(key)
            chosen.append(section)

    parts = [preamble] if preamble else []
    parts.extend(section.text for section in sorted(chosen, key=sections.index))
    return "\n".join(parts).strip() + "\n"


def _descendants(sections: list[Section], index: int) -> list[Section]:
    """Sections nested beneath `sections[index]`."""
    parent = sections[index]
    nested = []
    for section in sections[index + 1 :]:
        if section.level <= parent.level:
            break
        nested.append(section)
    return nested


def _is_ancestor_of_only_unwanted(
    sections: list[Section], index: int, requested: set[str]
) -> bool:
    """True when a non-requirement heading only groups unwanted requirements.

    A heading like "## Optional Requirements" is worth dropping entirely when
    none of the requirements beneath it were requested; keeping it would leave a
    bare heading with nothing under it.
    """
    nested = _descendants(sections, index)
    requirement_children = [section for section in nested if section.is_requirement]
    if not requirement_children:
        return False
    return not any(section.ids & requested for section in requirement_children)
