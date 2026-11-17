"""Shared helpers for agents: LLM-first execution with a deterministic fallback."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from codeverse.llm.base import LLMError, LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class AgentContext:
    """Dependencies injected into every agent call."""

    provider: LLMProvider | None = None
    max_retries: int = 2


@dataclass(frozen=True)
class AgentOutput(Generic[T]):
    value: T
    used_fallback: bool


def run_with_fallback(
    stage: str,
    ctx: AgentContext,
    llm_call: Callable[[LLMProvider], T],
    template_call: Callable[[], T],
) -> AgentOutput[T]:
    """Try the LLM path; on failure (or with no provider) use the deterministic template.

    A failed LLM call never crashes the run, but it is recorded so the artifact shows
    exactly which stages were template-generated.
    """
    if ctx.provider is None:
        return AgentOutput(template_call(), used_fallback=False)
    try:
        return AgentOutput(llm_call(ctx.provider), used_fallback=False)
    except LLMError as exc:
        logger.error("Stage %s fell back to the deterministic template: %s", stage, exc)
        return AgentOutput(template_call(), used_fallback=True)
