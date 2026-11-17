"""Storyboarder agent: script -> renderer-independent scenes.

Scene durations are derived from narration length, so the storyboard stays in sync with
the script after every revision.
"""

from __future__ import annotations

import math

from codeverse.agents.rubric import WORDS_PER_SECOND
from codeverse.models.schemas import LessonPlan, LessonScript, Storyboard, StoryboardScene

_PADDING_SECONDS = 2  # breathing room for transitions


def narration_seconds(text: str) -> int:
    seconds = math.ceil(len(text.split()) / WORDS_PER_SECOND) + _PADDING_SECONDS
    return max(3, min(120, seconds))


def create_storyboard(plan: LessonPlan, script: LessonScript) -> Storyboard:
    scenes = [
        StoryboardScene(
            scene_number=1,
            title="Lesson introduction",
            narration_reference="introduction",
            visual_description=(
                f"Title card '{plan.title}'. Fade in one visual metaphor for {plan.topic} "
                "and list the learning objectives as bullet points."
            ),
            on_screen_text=plan.title,
            estimated_duration_seconds=narration_seconds(script.introduction),
        )
    ]
    for index, section in enumerate(script.sections):
        terms = ", ".join(section.key_terms) or plan.topic
        scenes.append(
            StoryboardScene(
                scene_number=len(scenes) + 1,
                title=section.heading,
                narration_reference=f"sections[{index}]",
                visual_description=(
                    f"Explanatory animation for '{section.heading}'. Label and highlight: "
                    f"{terms}. One idea on screen at a time, simple motion between states."
                ),
                on_screen_text=section.heading,
                estimated_duration_seconds=narration_seconds(section.narration),
            )
        )
    scenes.append(
        StoryboardScene(
            scene_number=len(scenes) + 1,
            title="Recap",
            narration_reference="conclusion",
            visual_description=(
                "Recap the key ideas as a checklist that ticks off each objective. "
                "End with a short practice prompt."
            ),
            on_screen_text="Key takeaways",
            estimated_duration_seconds=narration_seconds(script.conclusion),
        )
    )
    return Storyboard(scenes=scenes)
