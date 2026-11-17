from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from codeverse.models.schemas import (
    Audience,
    LessonPlan,
    LessonScript,
    ReviewResult,
    StageTiming,
    Storyboard,
)


class LessonState(TypedDict, total=False):
    """Shared LangGraph state. Nodes return only the keys they update.

    List fields annotated with `operator.add` are append-only: LangGraph merges each
    node's partial list into the running total instead of overwriting it.
    """

    topic: str
    audience: Audience
    plan: LessonPlan
    script: LessonScript
    storyboard: Storyboard
    review: ReviewResult
    review_history: Annotated[list[ReviewResult], operator.add]
    revision_count: int
    timings: Annotated[list[StageTiming], operator.add]
    fallbacks: Annotated[list[str], operator.add]
