"""Reviser agent: applies reviewer feedback to the script.

Runs inside a bounded loop (reviewer -> reviser -> storyboarder -> reviewer) so a lesson
gets improved automatically, but a bad model can never loop forever.
"""

from __future__ import annotations

from codeverse.agents.base import AgentContext, AgentOutput, run_with_fallback
from codeverse.agents.prompts import REVISER_SYSTEM, revision_prompt
from codeverse.agents.rubric import MIN_SECTION_WORDS
from codeverse.llm.base import LLMError, generate_structured
from codeverse.models.schemas import LessonPlan, LessonScript, ReviewResult

_ELABORATION = (
    " To make this concrete, think about how {topic} behaves in a small program you have "
    "written before. Ask what changes, what stays the same, and why. Saying the answer "
    "out loud is a quick way to check that the idea really makes sense to you."
)


def template_revision(plan: LessonPlan, script: LessonScript, review: ReviewResult) -> LessonScript:
    """Fix issues that can be repaired mechanically."""
    short = {i.target for i in review.issues if i.code == "SECTION_TOO_SHORT"}
    no_terms = {i.target for i in review.issues if i.code == "SECTION_NO_KEY_TERMS"}

    sections = []
    for section in script.sections:
        update = {}
        if section.heading in short:
            narration = section.narration.rstrip()
            while len(narration.split()) < MIN_SECTION_WORDS:
                narration += _ELABORATION.format(topic=plan.topic)
            update["narration"] = narration
        if section.heading in no_terms:
            update["key_terms"] = [plan.topic]
        sections.append(section.model_copy(update=update))
    return script.model_copy(update={"sections": sections})


def revise_script(
    plan: LessonPlan,
    script: LessonScript,
    review: ReviewResult,
    ctx: AgentContext | None = None,
) -> AgentOutput:
    ctx = ctx or AgentContext()

    def llm_call(provider):
        revised = generate_structured(
            provider,
            system=REVISER_SYSTEM,
            prompt=revision_prompt(script, review.issues, MIN_SECTION_WORDS),
            output_model=LessonScript,
            max_retries=ctx.max_retries,
        )
        if [s.heading for s in revised.sections] != [s.heading for s in script.sections]:
            raise LLMError("Reviser changed section headings.")
        return revised

    return run_with_fallback(
        "reviser", ctx, llm_call, lambda: template_revision(plan, script, review)
    )
