from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from codeverse.config import Settings
from codeverse.llm.base import LLMError


class FakeProvider:
    """Scripted provider: returns queued responses in order, records every call.

    A response may be a string (raw model output), a dict (serialized to JSON), an
    exception instance (raised), or a callable taking the prompt.
    """

    name = "fake"
    model = "fake-model"

    def __init__(self, responses: list | None = None, default: Callable | None = None):
        self.responses = list(responses or [])
        self.default = default
        self.calls: list[dict] = []

    def complete_json(self, system: str, prompt: str, schema: dict) -> str:
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        if self.responses:
            response = self.responses.pop(0)
        elif self.default is not None:
            response = self.default
        else:
            raise LLMError("FakeProvider ran out of responses")
        if isinstance(response, Exception):
            raise response
        if callable(response):
            response = response(prompt)
        return response if isinstance(response, str) else json.dumps(response)


@pytest.fixture
def fake_provider_cls():
    return FakeProvider


@pytest.fixture
def settings() -> Settings:
    return Settings(provider="deterministic", max_revisions=2, llm_max_retries=1)
