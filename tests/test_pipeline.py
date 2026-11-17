import dataclasses

import pytest

from codeverse.agents.planner import template_plan
from codeverse.agents.scriptwriter import template_script
from codeverse.models.schemas import Audience
from codeverse.pipeline import generate_lesson


def test_deterministic_pipeline_generates_approved_lesson(settings):
    artifact = generate_lesson("C++ pointers", "beginner", settings=settings)
    assert artifact.status == "approved"
    assert artifact.plan.topic == "C++ pointers"
    assert len(artifact.script.sections) == len(artifact.plan.outline)
    assert len(artifact.storyboard.scenes) == len(artifact.script.sections) + 2
    assert artifact.metadata.provider == "deterministic"
    assert artifact.metadata.revision_count == 0
    assert len(artifact.review_history) == 1


def test_every_stage_is_timed(settings):
    artifact = generate_lesson("Binary search", settings=settings)
    stages = [t.stage for t in artifact.metadata.timings]
    assert stages == ["planner", "scriptwriter", "storyboarder", "reviewer"]


@pytest.mark.parametrize("topic", ["", "   ", "?"])
def test_pipeline_rejects_empty_topic(topic, settings):
    with pytest.raises(ValueError, match="Topic cannot be empty"):
        generate_lesson(topic, settings=settings)


def test_pipeline_rejects_overlong_topic(settings):
    with pytest.raises(ValueError, match="at most"):
        generate_lesson("x" * 500, settings=settings)


def test_pipeline_rejects_unknown_audience(settings):
    with pytest.raises(ValueError):
        generate_lesson("Recursion", "toddler", settings=settings)


def _llm_plan(topic="Linked lists"):
    return template_plan(topic, Audience.BEGINNER).model_dump(mode="json")


def _short_script(plan_dict):
    plan = template_plan(plan_dict["topic"], Audience.BEGINNER)
    script = template_script(plan)
    sections = [s.model_copy(update={"narration": "Too short."}) for s in script.sections]
    return script.model_copy(update={"sections": sections}).model_dump(mode="json")


def test_llm_path_uses_provider_output(fake_provider_cls, settings):
    plan = _llm_plan()
    plan["title"] = "Linked Lists, Visually"
    script = template_script(template_plan("Linked lists", Audience.BEGINNER)).model_dump(
        mode="json"
    )
    provider = fake_provider_cls([plan, script])

    artifact = generate_lesson("Linked lists", settings=settings, provider=provider)
    assert artifact.plan.title == "Linked Lists, Visually"
    assert artifact.metadata.provider == "fake"
    assert artifact.metadata.fallbacks == []
    assert artifact.status == "approved"


def test_revision_loop_repairs_weak_script(fake_provider_cls, settings):
    plan = _llm_plan()
    good = template_script(template_plan("Linked lists", Audience.BEGINNER)).model_dump(mode="json")
    provider = fake_provider_cls([plan, _short_script(plan), good])

    artifact = generate_lesson("Linked lists", settings=settings, provider=provider)
    assert artifact.metadata.revision_count == 1
    assert [r.approved for r in artifact.review_history] == [False, True]
    assert artifact.status == "approved"


def test_revision_loop_is_bounded(fake_provider_cls, settings):
    plan = _llm_plan()
    short = _short_script(plan)
    # The model keeps returning weak scripts; the reviser's LLM output is also weak.
    provider = fake_provider_cls([plan], default=lambda _prompt: short)
    settings = dataclasses.replace(settings, max_revisions=2)

    artifact = generate_lesson("Linked lists", settings=settings, provider=provider)
    assert artifact.metadata.revision_count == 2
    assert len(artifact.review_history) == 3
    assert artifact.status == "needs_revision"


def test_llm_failure_falls_back_to_templates(fake_provider_cls, settings):
    provider = fake_provider_cls(default="definitely not json")
    artifact = generate_lesson("Tries", settings=settings, provider=provider)
    assert artifact.status == "approved"
    assert artifact.metadata.fallbacks == ["planner", "scriptwriter"]


def test_llm_cannot_change_requested_topic_or_audience(fake_provider_cls, settings):
    plan = _llm_plan("Something else entirely")
    plan["audience"] = "advanced"
    script = template_script(template_plan("Something else entirely", Audience.BEGINNER))
    provider = fake_provider_cls([plan, script.model_dump(mode="json")])
    artifact = generate_lesson("Heaps", "beginner", settings=settings, provider=provider)
    assert artifact.plan.topic == "Heaps"
    assert artifact.plan.audience is Audience.BEGINNER
