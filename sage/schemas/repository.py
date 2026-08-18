"""Repository analysis schema.

The deterministic probe answers *what is here*. This schema captures the
interpretive half - *what it means for someone about to change this project* -
which is the one part of repository analysis a model does better than a static
rule (SPEC.md 6.1).

Every field is length-capped. This is context that will be pasted into later
prompts, so an analyzer that rambles must not be able to inflate every
downstream call.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RepositoryContext(BaseModel):
    """Concise architectural observations about the target project."""

    architecture_notes: list[str] = Field(default_factory=list, max_length=6)
    conventions: list[str] = Field(default_factory=list, max_length=8)
    reusable_infrastructure: list[str] = Field(default_factory=list, max_length=8)
    integration_points: list[str] = Field(default_factory=list, max_length=6)
    testing_approach: str = Field(default="", max_length=600)

    def to_prompt_summary(self) -> str:
        """Render as the compact block downstream prompts embed."""
        sections = (
            ("Architecture", self.architecture_notes),
            ("Conventions to follow", self.conventions),
            ("Existing infrastructure to reuse", self.reusable_infrastructure),
            ("Where new code should connect", self.integration_points),
        )
        lines: list[str] = []
        for title, items in sections:
            if items:
                lines.append(f"{title}:")
                lines.extend(f"  - {item}" for item in items)
        if self.testing_approach:
            lines.append(f"Testing approach: {self.testing_approach}")
        return "\n".join(lines) or "No additional observations."
