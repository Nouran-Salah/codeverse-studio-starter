"""Public entry point: run the workflow and return a validated `LessonArtifact`."""

from __future__ import annotations

from codeverse import __version__
from codeverse.agents.base import AgentContext
from codeverse.agents.planner import clean_topic
from codeverse.config import Settings
from codeverse.llm import LLMProvider, build_provider
from codeverse.models.schemas import Audience, LessonArtifact, RunMetadata
from codeverse.workflow.graph import build_workflow

MAX_TOPIC_LENGTH = 200


def generate_lesson(
    topic: str,
    audience: Audience | str = Audience.BEGINNER,
    *,
    settings: Settings | None = None,
    provider: LLMProvider | None = None,
) -> LessonArtifact:
    """Plan, script, storyboard and review a lesson for `topic`.

    `provider` overrides the one built from `settings` (useful for tests and custom
    backends). With no provider configured, every stage is deterministic.
    """
    topic = clean_topic(topic)
    if not topic:
        raise ValueError("Topic cannot be empty.")
    if len(topic) > MAX_TOPIC_LENGTH:
        raise ValueError(f"Topic must be at most {MAX_TOPIC_LENGTH} characters.")
    audience = Audience(audience)

    settings = settings or Settings.from_env()
    provider = provider if provider is not None else build_provider(settings)
    ctx = AgentContext(provider=provider, max_retries=settings.llm_max_retries)

    workflow = build_workflow(settings, ctx)
    result = workflow.invoke(
        {"topic": topic, "audience": audience},
        {"recursion_limit": 10 + 3 * settings.max_revisions},
    )

    review = result["review"]
    return LessonArtifact(
        topic=topic,
        audience=audience,
        plan=result["plan"],
        script=result["script"],
        storyboard=result["storyboard"],
        review=review,
        review_history=result.get("review_history", []),
        metadata=RunMetadata(
            workflow_version=__version__,
            provider=provider.name if provider else "deterministic",
            model=getattr(provider, "model", None),
            revision_count=result.get("revision_count", 0),
            max_revisions=settings.max_revisions,
            timings=result.get("timings", []),
            fallbacks=result.get("fallbacks", []),
        ),
        status="approved" if review.approved else "needs_revision",
    )
