"""LLM provider layer."""

from __future__ import annotations

from codeverse.config import Settings
from codeverse.llm.base import LLMError, LLMProvider, generate_structured
from codeverse.llm.ollama import OllamaProvider

__all__ = ["LLMError", "LLMProvider", "OllamaProvider", "build_provider", "generate_structured"]


def build_provider(settings: Settings) -> LLMProvider | None:
    """Return the configured provider, or None for fully deterministic mode."""
    if settings.provider == "ollama":
        return OllamaProvider(
            settings.ollama_base_url, settings.ollama_model, timeout=settings.llm_timeout_seconds
        )
    return None
