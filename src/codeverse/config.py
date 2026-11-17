"""Runtime settings, read from environment variables (see `.env.example`)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ProviderName = Literal["deterministic", "ollama"]


@dataclass(frozen=True)
class Settings:
    provider: ProviderName = "deterministic"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    max_revisions: int = 2
    approval_threshold: int = 80

    @classmethod
    def from_env(cls) -> Settings:
        provider = os.getenv("CODEVERSE_PROVIDER", cls.provider).lower()
        if provider not in ("deterministic", "ollama"):
            raise ValueError(f"Unknown CODEVERSE_PROVIDER: {provider!r}")
        return cls(
            provider=provider,  # type: ignore[arg-type]
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", cls.ollama_base_url),
            ollama_model=os.getenv("OLLAMA_MODEL", cls.ollama_model),
            llm_timeout_seconds=float(os.getenv("CODEVERSE_LLM_TIMEOUT", cls.llm_timeout_seconds)),
            llm_max_retries=int(os.getenv("CODEVERSE_LLM_RETRIES", cls.llm_max_retries)),
            max_revisions=int(os.getenv("CODEVERSE_MAX_REVISIONS", cls.max_revisions)),
            approval_threshold=int(
                os.getenv("CODEVERSE_APPROVAL_THRESHOLD", cls.approval_threshold)
            ),
        )
