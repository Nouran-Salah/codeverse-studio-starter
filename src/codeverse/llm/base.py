"""Provider abstraction for structured LLM output.

Agents never talk to a model API directly. They call `generate_structured`, which asks a
provider for JSON matching a Pydantic schema, validates it, and retries with the
validation error fed back to the model. This keeps agents testable with a fake provider.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Raised when a provider cannot produce valid structured output."""


class LLMProvider(Protocol):
    name: str
    model: str | None

    def complete_json(self, system: str, prompt: str, schema: dict) -> str:
        """Return a raw JSON string intended to match `schema`."""
        ...


def generate_structured(
    provider: LLMProvider,
    *,
    system: str,
    prompt: str,
    output_model: type[T],
    max_retries: int = 2,
) -> T:
    """Ask `provider` for `output_model`, retrying on malformed or invalid JSON."""
    schema = output_model.model_json_schema()
    attempt_prompt = prompt
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            raw = provider.complete_json(system, attempt_prompt, schema)
            return output_model.model_validate_json(_strip_fences(raw))
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "Invalid %s from %s (attempt %d/%d): %s",
                output_model.__name__,
                provider.name,
                attempt + 1,
                max_retries + 1,
                exc,
            )
            attempt_prompt = (
                f"{prompt}\n\nYour previous answer was invalid:\n{_short(exc)}\n"
                "Return only JSON that matches the schema exactly."
            )
        except LLMError as exc:  # transport failure: retrying the same call may help
            last_error = exc
            logger.warning("Provider %s failed (attempt %d): %s", provider.name, attempt + 1, exc)

    raise LLMError(
        f"{provider.name} did not return a valid {output_model.__name__} "
        f"after {max_retries + 1} attempts: {last_error}"
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _short(exc: Exception, limit: int = 600) -> str:
    text = str(exc)
    return text if len(text) <= limit else text[:limit] + "..."
