import pytest
from pydantic import BaseModel

from codeverse.config import Settings
from codeverse.llm import build_provider
from codeverse.llm.base import LLMError, generate_structured
from codeverse.llm.ollama import OllamaProvider


class Point(BaseModel):
    x: int
    y: int


def test_valid_json_is_parsed(fake_provider_cls):
    provider = fake_provider_cls([{"x": 1, "y": 2}])
    assert generate_structured(provider, system="s", prompt="p", output_model=Point) == Point(
        x=1, y=2
    )
    assert provider.calls[0]["schema"]["title"] == "Point"


def test_markdown_fences_are_tolerated(fake_provider_cls):
    provider = fake_provider_cls(['```json\n{"x": 3, "y": 4}\n```'])
    assert generate_structured(provider, system="s", prompt="p", output_model=Point).x == 3


def test_invalid_output_is_retried_with_error_feedback(fake_provider_cls):
    provider = fake_provider_cls(["not json", {"x": "oops"}, {"x": 5, "y": 6}])
    result = generate_structured(
        provider, system="s", prompt="p", output_model=Point, max_retries=2
    )
    assert result == Point(x=5, y=6)
    assert len(provider.calls) == 3
    assert "previous answer was invalid" in provider.calls[1]["prompt"]


def test_transport_errors_are_retried(fake_provider_cls):
    provider = fake_provider_cls([LLMError("timeout"), {"x": 1, "y": 1}])
    assert generate_structured(provider, system="s", prompt="p", output_model=Point).x == 1


def test_exhausted_retries_raise_llm_error(fake_provider_cls):
    provider = fake_provider_cls(["bad", "bad"])
    with pytest.raises(LLMError, match="after 2 attempts"):
        generate_structured(provider, system="s", prompt="p", output_model=Point, max_retries=1)


def test_build_provider_respects_settings():
    assert build_provider(Settings(provider="deterministic")) is None
    provider = build_provider(Settings(provider="ollama", ollama_model="llama3.2"))
    assert isinstance(provider, OllamaProvider) and provider.model == "llama3.2"


def test_settings_reject_unknown_provider(monkeypatch):
    monkeypatch.setenv("CODEVERSE_PROVIDER", "gpt-9000")
    with pytest.raises(ValueError, match="Unknown CODEVERSE_PROVIDER"):
        Settings.from_env()


def test_ollama_unreachable_raises_llm_error():
    provider = OllamaProvider("http://127.0.0.1:9", "m", timeout=0.5)
    with pytest.raises(LLMError):
        provider.complete_json("s", "p", {})


def test_ollama_provider_against_local_http_server():
    """End-to-end HTTP contract test using a stdlib server that mimics /api/chat."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.update(body)
            reply = json.dumps({"message": {"content": json.dumps({"x": 7, "y": 8})}})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(reply.encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = OllamaProvider(f"http://127.0.0.1:{server.server_port}", "qwen3:4b", timeout=5)
        result = generate_structured(provider, system="sys", prompt="hi", output_model=Point)
    finally:
        server.shutdown()

    assert result == Point(x=7, y=8)
    assert received["model"] == "qwen3:4b"
    assert received["stream"] is False
    assert received["format"]["title"] == "Point"  # JSON schema sent for structured output
    assert received["messages"][0] == {"role": "system", "content": "sys"}
