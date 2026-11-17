"""Scriptwriter agent: lesson plan -> spoken narration, one section per outline item."""

from __future__ import annotations

from codeverse.agents.base import AgentContext, AgentOutput, run_with_fallback
from codeverse.agents.prompts import SCRIPT_SYSTEM, script_prompt
from codeverse.agents.rubric import MIN_SECTION_WORDS
from codeverse.llm.base import LLMError, generate_structured
from codeverse.models.schemas import LessonPlan, LessonScript, ScriptSection

# Deterministic narration patterns keyed by the role a section plays in the lesson.
_SECTION_PATTERNS = [
    (
        "Let's start with a clear definition of {topic}. We'll describe what it is, what "
        "problem it solves, and where you are likely to meet it in real code. Keep one "
        "question in mind: what would go wrong if {topic} did not exist?"
    ),
    (
        "Now let's build a mental model. Picture {topic} as a simple, physical system "
        "with parts you can point at. When you can predict what happens before running "
        "the code, the model is working. We'll test that prediction in the next part."
    ),
    (
        "Here is a small example, traced one step at a time. Pause before each step and "
        "guess the result, then compare it with what actually happens. Small, traceable "
        "examples are the fastest way to turn the idea of {topic} into real intuition."
    ),
    (
        "Finally, let's look at the mistakes people make most often with {topic}. For each "
        "one, we'll see the symptom, the cause, and a habit that prevents it. Recognizing "
        "these patterns early will save you hours of debugging later on."
    ),
]

_GENERIC_PATTERN = (
    "In this part we focus on {heading}. We connect it back to {topic}, show how it fits "
    "into the bigger picture, and work through one concrete case so the idea sticks. "
    "Try to restate the key point in your own words before moving on."
)


def template_script(plan: LessonPlan) -> LessonScript:
    sections = []
    for index, heading in enumerate(plan.outline):
        pattern = _SECTION_PATTERNS[index] if index < len(_SECTION_PATTERNS) else _GENERIC_PATTERN
        sections.append(
            ScriptSection(
                heading=heading,
                narration=pattern.format(topic=plan.topic, heading=heading.lower()),
                key_terms=[plan.topic],
            )
        )
    objectives = "; ".join(o[:1].lower() + o[1:].rstrip(".") for o in plan.learning_objectives)
    return LessonScript(
        introduction=(
            f"Welcome! In this lesson we'll build a solid understanding of {plan.topic}. "
            f"By the end, you'll be able to: {objectives}."
        ),
        sections=sections,
        conclusion=(
            f"That's the foundation of {plan.topic}. Explain the idea in your own words, "
            "then try it on a small example of your own."
        ),
    )


def write_script(plan: LessonPlan, ctx: AgentContext | None = None) -> AgentOutput:
    ctx = ctx or AgentContext()

    def llm_call(provider):
        script = generate_structured(
            provider,
            system=SCRIPT_SYSTEM,
            prompt=script_prompt(plan, MIN_SECTION_WORDS),
            output_model=LessonScript,
            max_retries=ctx.max_retries,
        )
        if [s.heading for s in script.sections] != plan.outline:
            raise LLMError("Script headings do not match the lesson outline.")
        return script

    return run_with_fallback("scriptwriter", ctx, llm_call, lambda: template_script(plan))
