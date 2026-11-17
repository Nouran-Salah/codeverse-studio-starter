"""Versioned prompt templates. Bump PROMPT_VERSION whenever a prompt changes."""

from __future__ import annotations

from codeverse.models.schemas import Audience, LessonPlan, LessonScript, ReviewIssue

PROMPT_VERSION = "2"

_AUDIENCE_GUIDE = {
    Audience.BEGINNER: "no prior knowledge; avoid jargon, use everyday analogies",
    Audience.INTERMEDIATE: "knows programming basics; use precise terms and small code examples",
    Audience.ADVANCED: "experienced engineer; discuss trade-offs, complexity, and edge cases",
}

PLANNER_SYSTEM = (
    "You are an instructional designer for short computer-science explainer videos. "
    "Design lessons that teach one concept well in 2-6 minutes. Respond with JSON only."
)

SCRIPT_SYSTEM = (
    "You are a scriptwriter for educational CS videos. Write narration meant to be spoken: "
    "short sentences, concrete examples, no markdown. Respond with JSON only."
)

REVISER_SYSTEM = (
    "You are an editor improving an educational video script based on reviewer feedback. "
    "Fix every listed issue while keeping headings unchanged. Respond with JSON only."
)


def planner_prompt(topic: str, audience: Audience) -> str:
    return (
        f"Topic: {topic}\nAudience: {audience.value} ({_AUDIENCE_GUIDE[audience]})\n\n"
        "Produce a lesson plan with 2-4 measurable learning objectives (start each with a "
        "verb), 3-6 outline sections in teaching order, and any prerequisites."
    )


def script_prompt(plan: LessonPlan, min_words: int) -> str:
    outline = "\n".join(f"{i}. {h}" for i, h in enumerate(plan.outline, start=1))
    objectives = "\n".join(f"- {o}" for o in plan.learning_objectives)
    return (
        f"Lesson: {plan.title}\nAudience: {plan.audience.value} "
        f"({_AUDIENCE_GUIDE[plan.audience]})\n"
        f"Objectives:\n{objectives}\n\nOutline (one section per item, same headings, same "
        f"order):\n{outline}\n\nEach section's narration must be at least {min_words} words "
        "and list 1-4 key terms."
    )


def revision_prompt(script: LessonScript, issues: list[ReviewIssue], min_words: int) -> str:
    feedback = "\n".join(f"- [{i.code}] {i.message}" for i in issues)
    return (
        f"Reviewer feedback:\n{feedback}\n\nEvery section needs at least {min_words} words of "
        f"narration.\n\nCurrent script JSON:\n{script.model_dump_json(indent=2)}"
    )
