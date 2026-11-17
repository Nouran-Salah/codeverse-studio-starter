"""Ollama provider using the `/api/chat` endpoint with JSON-schema structured outputs.

Uses only the standard library so the base install stays light.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from codeverse.llm.base import LLMError


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 60.0, temperature: float = 0.3):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature

    def complete_json(self, system: str, prompt: str, schema: dict) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        data = self._post("/api/chat", payload)
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected Ollama response shape: {data!r:.300}") from exc

    def health_check(self) -> list[str]:
        """Return installed model names; raises LLMError if the server is unreachable."""
        request = urllib.request.Request(f"{self.base_url}/api/tags")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        return [m.get("name", "") for m in data.get("models", [])]

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            raise LLMError(f"Ollama HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"Ollama returned non-JSON body: {exc}") from exc
