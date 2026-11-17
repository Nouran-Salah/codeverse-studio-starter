"""CLI and HTTP API smoke tests."""

import pytest

from codeverse.cli import app as cli_app


def test_cli_run_writes_requested_formats(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    monkeypatch.setenv("CODEVERSE_PROVIDER", "deterministic")
    result = CliRunner().invoke(
        cli_app,
        ["run", "Dynamic programming", "-f", "json", "-f", "markdown", "-o", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    suffixes = sorted(p.suffix for p in tmp_path.iterdir())
    assert suffixes == [".json", ".md"]


def test_cli_rejects_unknown_format(tmp_path):
    from typer.testing import CliRunner

    result = CliRunner().invoke(cli_app, ["run", "Sorting", "-f", "gif", "-o", str(tmp_path)])
    assert result.exit_code != 0


def test_api_creates_lesson(monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from codeverse.api import app

    monkeypatch.setenv("CODEVERSE_PROVIDER", "deterministic")
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"

    response = client.post("/lessons", json={"topic": "Graphs", "audience": "advanced"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    srt = client.post("/lessons/export/srt", json={"topic": "Graphs"})
    assert srt.status_code == 200 and "-->" in srt.text

    assert client.post("/lessons", json={"topic": ""}).status_code == 422
