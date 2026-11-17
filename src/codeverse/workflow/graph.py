"""LangGraph orchestration.

START -> planner -> scriptwriter -> storyboarder -> reviewer --approved--> END
                                        ^               |
                                        |            revise (bounded)
                                        +--- reviser <--+
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph

from codeverse.agents.base import AgentContext
from codeverse.agents.planner import plan_topic
from codeverse.agents.reviewer import review_lesson
from codeverse.agents.reviser import revise_script
from codeverse.agents.scriptwriter import write_script
from codeverse.agents.storyboarder import create_storyboard
from codeverse.config import Settings
from codeverse.models.schemas import StageTiming
from codeverse.workflow.state import LessonState

Node = Callable[[LessonState], dict]


def _timed(stage: str, fn: Node) -> Node:
    """Wrap a node so every run records how long each stage took."""

    def wrapper(state: LessonState) -> dict:
        start = time.perf_counter()
        update = fn(state)
        elapsed = (time.perf_counter() - start) * 1000
        update["timings"] = [StageTiming(stage=stage, duration_ms=round(elapsed, 3))]
        return update

    return wrapper


def _with_fallback(stage: str, output) -> dict:
    return {"fallbacks": [stage]} if output.used_fallback else {}


def build_workflow(settings: Settings | None = None, ctx: AgentContext | None = None):
    settings = settings or Settings()
    ctx = ctx or AgentContext(max_retries=settings.llm_max_retries)

    def planner(state: LessonState) -> dict:
        out = plan_topic(state["topic"], state["audience"], ctx)
        return {"plan": out.value, "revision_count": 0, **_with_fallback("planner", out)}

    def scriptwriter(state: LessonState) -> dict:
        out = write_script(state["plan"], ctx)
        return {"script": out.value, **_with_fallback("scriptwriter", out)}

    def storyboarder(state: LessonState) -> dict:
        return {"storyboard": create_storyboard(state["plan"], state["script"])}

    def reviewer(state: LessonState) -> dict:
        review = review_lesson(
            state["plan"], state["script"], state["storyboard"], settings.approval_threshold
        )
        return {"review": review, "review_history": [review]}

    def reviser(state: LessonState) -> dict:
        out = revise_script(state["plan"], state["script"], state["review"], ctx)
        return {
            "script": out.value,
            "revision_count": state.get("revision_count", 0) + 1,
            **_with_fallback("reviser", out),
        }

    def route_after_review(state: LessonState) -> Literal["reviser", "__end__"]:
        if state["review"].approved:
            return END
        if state.get("revision_count", 0) >= settings.max_revisions:
            return END
        return "reviser"

    graph = StateGraph(LessonState)
    for name, fn in [
        ("planner", planner),
        ("scriptwriter", scriptwriter),
        ("storyboarder", storyboarder),
        ("reviewer", reviewer),
        ("reviser", reviser),
    ]:
        graph.add_node(name, _timed(name, fn))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "scriptwriter")
    graph.add_edge("scriptwriter", "storyboarder")
    graph.add_edge("storyboarder", "reviewer")
    graph.add_conditional_edges("reviewer", route_after_review, ["reviser", END])
    graph.add_edge("reviser", "storyboarder")
    return graph.compile()
