"""Prompt templates.

Templates use `{{TOKEN}}` placeholders rather than str.format, because the
prompts embed JSON schemas and examples full of literal braces.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

_DIR = Path(__file__).parent
_TOKEN = re.compile(r"\{\{([A-Z_]+)\}\}")


@cache
def _load(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8")


def render(name: str, **values: str) -> str:
    """Render a template, failing loudly on any unfilled placeholder.

    `{{BOUNDARY}}` is supplied automatically so every prompt that carries
    specification text also carries the untrusted-input warning.
    """
    template = _load(name)
    values = {"boundary": _load("_shared").strip(), **values}
    rendered = _TOKEN.sub(lambda m: values.get(m.group(1).lower(), m.group(0)), template)

    leftover = _TOKEN.findall(rendered)
    if leftover:
        raise KeyError(f"prompt {name!r} has unfilled placeholders: {sorted(set(leftover))}")
    return rendered
