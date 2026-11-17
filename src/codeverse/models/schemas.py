"""Pydantic data contracts shared by every workflow stage.

Each agent returns one of these models, so malformed output (from a template or an LLM)
is rejected at the stage boundary instead of leaking into later stages.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Audience(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LessonPlan(BaseModel):
    topic: str = Field(min_length=1)
    audience: Audience
    title: str = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1, max_length=6)
    outline: list[str] = Field(min_length=2, max_length=8)
    prerequisites: list[str] = Field(default_factory=list)

    @field_validator("learning_objectives", "outline")
    @classmethod
    def _no_blank_items(cls, items: list[str]) -> list[str]:
        cleaned = [item.strip() for item in items]
        if any(not item for item in cleaned):
            raise ValueError("items must not be blank")
        return cleaned


class ScriptSection(BaseModel):
    heading: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    key_terms: list[str] = Field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.narration.split())


class LessonScript(BaseModel):
    introduction: str = Field(min_length=1)
    sections: list[ScriptSection] = Field(min_length=1)
    conclusion: str = Field(min_length=1)

    @property
    def word_count(self) -> int:
        return (
            len(self.introduction.split())
            + sum(s.word_count for s in self.sections)
            + len(self.conclusion.split())
        )


class StoryboardScene(BaseModel):
    scene_number: int = Field(ge=1)
    title: str
    narration_reference: str
    visual_description: str
    on_screen_text: str
    estimated_duration_seconds: int = Field(ge=3, le=120)


class Storyboard(BaseModel):
    scenes: list[StoryboardScene] = Field(min_length=1)

    @property
    def total_duration_seconds(self) -> int:
        return sum(scene.estimated_duration_seconds for scene in self.scenes)


class Severity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"


class ReviewIssue(BaseModel):
    code: str
    severity: Severity
    message: str
    target: str | None = Field(default=None, description="Section heading or field affected.")


class ReviewResult(BaseModel):
    approved: bool
    score: int = Field(ge=0, le=100)
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str = ""

    @property
    def blocking_issues(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.severity is Severity.BLOCKING]

    @property
    def warnings(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]


class StageTiming(BaseModel):
    stage: str
    duration_ms: float = Field(ge=0)


class RunMetadata(BaseModel):
    workflow_version: str
    provider: str
    model: str | None = None
    revision_count: int = Field(default=0, ge=0)
    max_revisions: int = Field(default=0, ge=0)
    timings: list[StageTiming] = Field(default_factory=list)
    fallbacks: list[str] = Field(
        default_factory=list,
        description="Stages where the LLM failed and the deterministic template was used.",
    )


class LessonArtifact(BaseModel):
    topic: str
    audience: Audience
    plan: LessonPlan
    script: LessonScript
    storyboard: Storyboard
    review: ReviewResult
    review_history: list[ReviewResult] = Field(default_factory=list)
    metadata: RunMetadata
    status: Literal["needs_revision", "approved"]
