"""Planner agent: topic -> title, objectives, prerequisites, and ordered outline."""

from __future__ import annotations

import re

from codeverse.agents.base import AgentContext, AgentOutput, run_with_fallback
from codeverse.agents.prompts import PLANNER_SYSTEM, planner_prompt
from codeverse.llm.base import generate_structured
from codeverse.models.schemas import Audience, LessonPlan

_PREREQUISITES = {
    Audience.BEGINNER: ["Basic familiarity with any programming language"],
    Audience.INTERMEDIATE: ["Comfort writing small programs", "Basic data structures"],
    Audience.ADVANCED: ["Solid programming experience", "Big-O analysis"],
}

_OBJECTIVES = {
    Audience.BEGINNER: (
        "Explain the core idea of {t} in plain language.",
        "Use {t} in a small, concrete example.",
        "Spot and avoid a common beginner mistake with {t}.",
    ),
    Audience.INTERMEDIATE: (
        "Explain how {t} works under the hood.",
        "Apply {t} to solve a realistic problem.",
        "Debug a typical bug caused by misusing {t}.",
    ),
    Audience.ADVANCED: (
        "Analyze the time and space trade-offs of {t}.",
        "Compare {t} with at least one alternative approach.",
        "Evaluate edge cases where {t} breaks down.",
    ),
}

# "How do pointers work in C++?" -> "pointers in C++"
_QUESTION_PREFIX = re.compile(
    r"^(?:what\s+(?:is|are)(?:\s+an?|\s+the)?|explain|how\s+(?:do|does|to\s+use)"
    r"|why\s+(?:do|does|is|are)|teach\s+me(?:\s+about)?)\s+",
    re.IGNORECASE,
)
_WORK_VERB = re.compile(r"\s+works?(?=\s|$)", re.IGNORECASE)


def clean_topic(topic: str) -> str:
    """Normalize whitespace and turn question-style requests into a topic noun phrase."""
    text = " ".join(topic.strip().rstrip("?.!").split())
    stripped = _QUESTION_PREFIX.sub("", text)
    if stripped != text:
        stripped = _WORK_VERB.sub("", stripped)
    return stripped.strip() or text


def _title_case_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def template_plan(topic: str, audience: Audience) -> LessonPlan:
    """Deterministic plan used offline, in tests, and as the LLM fallback."""
    name = clean_topic(topic)
    return LessonPlan(
        topic=name,
        audience=audience,
        title=f"Understanding {_title_case_first(name)}",
        learning_objectives=[o.format(t=name) for o in _OBJECTIVES[audience]],
        outline=[
            f"Introducing {name}",
            "Building a mental model",
            "Walking through an example",
            "Common mistakes and how to avoid them",
        ],
        prerequisites=_PREREQUISITES[audience],
    )


def plan_topic(topic: str, audience: Audience, ctx: AgentContext | None = None) -> AgentOutput:
    ctx = ctx or AgentContext()

    def llm_call(provider):
        plan = generate_structured(
            provider,
            system=PLANNER_SYSTEM,
            prompt=planner_prompt(clean_topic(topic), audience),
            output_model=LessonPlan,
            max_retries=ctx.max_retries,
        )
        # The model must not silently change the request.
        return plan.model_copy(update={"topic": clean_topic(topic), "audience": audience})

    return run_with_fallback("planner", ctx, llm_call, lambda: template_plan(topic, audience))
